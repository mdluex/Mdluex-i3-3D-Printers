#!/usr/bin/env python3
"""
Klipper Wi-Fi Autopilot - v3.1
Monitors Wi-Fi and provides a captive portal for easy setup.

v3.1 Changes:
- Fixed open hotspot creation (uses nmcli con add for open networks)
- Improved LCD message error handling
"""

import time
import subprocess
import requests
import logging
import threading
import os
from flask import Flask, jsonify, request, render_template_string, redirect

# --- CONFIGURATION ---
CHECK_INTERVAL = 10          # Seconds between checks
PING_TARGETS = ["8.8.8.8", "1.1.1.1", "208.67.222.222"]  # Multiple DNS servers
HOTSPOT_SSID = "Klipper-Setup"
HOTSPOT_PASSWORD = ""        # Leave empty for open network, or set a password (min 8 chars)
MOONRAKER_API = "http://127.0.0.1:7125"
OFFLINE_THRESHOLD = 2        # Failed checks before hotspot
ONLINE_THRESHOLD = 2         # Successful checks before disabling hotspot
FLASK_PORT = 8888            # Port for Flask (not 80 to avoid nginx conflict)
HOTSPOT_INTERFACE = "wlan0"

# State
hotspot_active = False
offline_count = 0
online_count = 0

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/var/log/wifi_autopilot.log')
    ]
)
log = logging.getLogger("wifi_autopilot")

# --- FLASK APP ---
app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Klipper Wi-Fi Setup</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, sans-serif; }
        body { padding: 20px; background: #1a1a2e; color: #eee; text-align: center; margin: 0; }
        h2 { color: #00d4ff; margin-bottom: 5px; }
        .subtitle { color: #888; margin-bottom: 20px; }
        .network { background: #16213e; border: 1px solid #0f3460; padding: 15px; margin: 8px auto; max-width: 320px; border-radius: 8px; cursor: pointer; transition: all 0.2s; }
        .network:hover { background: #0f3460; transform: scale(1.02); }
        input { padding: 14px; font-size: 16px; margin: 10px 0; width: 100%; max-width: 280px; border-radius: 6px; border: none; background: #16213e; color: #fff; }
        button { padding: 14px 30px; font-size: 16px; background: #00d4ff; color: #000; border: none; border-radius: 6px; cursor: pointer; margin: 5px; font-weight: bold; }
        button:hover { background: #00b8d4; }
        .back-btn { background: #444; color: #fff; }
        .hidden { display: none; }
        .status { padding: 12px; border-radius: 6px; margin: 15px auto; max-width: 320px; }
        .error { background: #e94560; }
        .success { background: #4ecca3; }
        .loading { color: #00d4ff; }
        #scan-results { min-height: 100px; }
    </style>
</head>
<body>
    <h2>� Klipper Wi-Fi Setup</h2>
    <p class="subtitle">Select a network to connect your printer</p>
    
    <div id="status" class="status hidden"></div>
    <div id="scan-results"><p class="loading">Scanning for networks...</p></div>
    
    <div id="connect-form" class="hidden">
        <h3 id="selected-ssid" style="color:#00d4ff;"></h3>
        <input type="password" id="password" placeholder="Enter password">
        <br>
        <button onclick="connect()">Connect</button>
        <button class="back-btn" onclick="cancel()">Back</button>
    </div>

    <script>
        let selectedSSID = "";
        
        function showStatus(msg, type) {
            const s = document.getElementById('status');
            s.innerText = msg;
            s.className = 'status ' + type;
            s.classList.remove('hidden');
        }

        function scan() {
            document.getElementById('scan-results').innerHTML = '<p class="loading">Scanning...</p>';
            fetch('/scan').then(r => r.json()).then(data => {
                const div = document.getElementById('scan-results');
                div.innerHTML = "";
                if(data.networks.length === 0) {
                    div.innerHTML = "<p>No networks found. <button onclick='scan()'>Retry</button></p>";
                    return;
                }
                data.networks.forEach(ssid => {
                    if(!ssid || ssid === 'Klipper-Setup') return;
                    let btn = document.createElement('div');
                    btn.className = 'network';
                    btn.innerText = '📶 ' + ssid;
                    btn.onclick = () => select(ssid);
                    div.appendChild(btn);
                });
            }).catch(() => {
                document.getElementById('scan-results').innerHTML = "<p>Scan failed. <button onclick='scan()'>Retry</button></p>";
            });
        }

        function select(ssid) {
            selectedSSID = ssid;
            document.getElementById('selected-ssid').innerText = ssid;
            document.getElementById('connect-form').classList.remove('hidden');
            document.getElementById('scan-results').classList.add('hidden');
            document.getElementById('status').classList.add('hidden');
            document.getElementById('password').focus();
        }

        function cancel() {
            document.getElementById('connect-form').classList.add('hidden');
            document.getElementById('scan-results').classList.remove('hidden');
            scan();
        }

        function connect() {
            const pw = document.getElementById('password').value;
            showStatus('Connecting to ' + selectedSSID + '...', 'loading');
            fetch('/connect', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ssid: selectedSSID, password: pw})
            }).then(r => r.json()).then(d => {
                if(d.success) {
                    showStatus('✅ Connected! The printer is now online. This page will close.', 'success');
                } else {
                    showStatus('❌ Failed: ' + d.message, 'error');
                }
            }).catch(() => showStatus('Connection error. Please try again.', 'error'));
        }

        scan();
    </script>
</body>
</html>
"""


def run_cmd(cmd, timeout=15):
    """Run shell command and return output."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip(), result.returncode
    except Exception as e:
        log.error(f"Command failed: {cmd} - {e}")
        return "", -1


def is_connected():
    """Check internet connectivity by pinging multiple targets."""
    for target in PING_TARGETS:
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "2", target],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5
            )
            if result.returncode == 0:
                return True
        except:
            continue
    return False


def get_current_ssid():
    """Get current connected SSID."""
    output, _ = run_cmd("iwgetid -r")
    return output if output and output != HOTSPOT_SSID else None


def klipper_msg(msg):
    """Send message to Klipper LCD."""
    try:
        response = requests.post(
            f"{MOONRAKER_API}/printer/gcode/script",
            json={"script": f'WIFI_STATUS MSG="{msg}"'},
            timeout=5
        )
        if response.status_code == 200:
            log.info(f"LCD: {msg}")
        else:
            log.warning(f"LCD failed (status {response.status_code}): {response.text}")
    except requests.exceptions.ConnectionError:
        log.debug("LCD: Moonraker not reachable (normal during boot)")
    except Exception as e:
        log.warning(f"LCD message failed: {e}")


def setup_iptables_redirect():
    """Redirect port 80 to Flask port when in hotspot mode."""
    run_cmd(f"iptables -t nat -A PREROUTING -i {HOTSPOT_INTERFACE} -p tcp --dport 80 -j REDIRECT --to-port {FLASK_PORT}")
    run_cmd(f"iptables -t nat -A PREROUTING -i {HOTSPOT_INTERFACE} -p tcp --dport 443 -j REDIRECT --to-port {FLASK_PORT}")
    log.info("iptables redirect enabled")


def remove_iptables_redirect():
    """Remove port 80 redirect."""
    run_cmd(f"iptables -t nat -D PREROUTING -i {HOTSPOT_INTERFACE} -p tcp --dport 80 -j REDIRECT --to-port {FLASK_PORT}")
    run_cmd(f"iptables -t nat -D PREROUTING -i {HOTSPOT_INTERFACE} -p tcp --dport 443 -j REDIRECT --to-port {FLASK_PORT}")
    log.info("iptables redirect removed")


def enable_hotspot():
    """Enable the Wi-Fi hotspot."""
    global hotspot_active
    
    log.info("=== ENABLING HOTSPOT ===")
    
    # Remove any existing hotspot
    run_cmd(f"nmcli con down '{HOTSPOT_SSID}' 2>/dev/null")
    run_cmd(f"nmcli con delete '{HOTSPOT_SSID}' 2>/dev/null")
    time.sleep(1)
    
    # Create hotspot
    if HOTSPOT_PASSWORD and len(HOTSPOT_PASSWORD) >= 8:
        # Protected hotspot with password
        output, code = run_cmd(
            f"nmcli dev wifi hotspot ifname {HOTSPOT_INTERFACE} ssid '{HOTSPOT_SSID}' password '{HOTSPOT_PASSWORD}'"
        )
    else:
        # Open network - must create connection manually
        # First, create an AP-mode connection without security
        run_cmd(f"nmcli con add type wifi ifname {HOTSPOT_INTERFACE} con-name '{HOTSPOT_SSID}' ssid '{HOTSPOT_SSID}' mode ap")
        run_cmd(f"nmcli con modify '{HOTSPOT_SSID}' wifi-sec.key-mgmt none")
        run_cmd(f"nmcli con modify '{HOTSPOT_SSID}' ipv4.method shared")
        run_cmd(f"nmcli con modify '{HOTSPOT_SSID}' ipv4.addresses 10.42.0.1/24")
        output, code = run_cmd(f"nmcli con up '{HOTSPOT_SSID}'")
    
    if code == 0:
        hotspot_active = True
        setup_iptables_redirect()
        klipper_msg(f"WiFi Lost! Hotspot: {HOTSPOT_SSID}")
        log.info(f"Hotspot '{HOTSPOT_SSID}' is UP (open network)")
        return True
    else:
        log.error(f"Failed to create hotspot: {output}")
        return False


def disable_hotspot():
    """Disable the hotspot and reconnect to known networks."""
    global hotspot_active
    
    log.info("=== DISABLING HOTSPOT ===")
    
    remove_iptables_redirect()
    run_cmd(f"nmcli con down '{HOTSPOT_SSID}' 2>/dev/null")
    run_cmd(f"nmcli con delete '{HOTSPOT_SSID}' 2>/dev/null")
    
    # Trigger rescan and auto-connect
    run_cmd("nmcli dev wifi rescan")
    run_cmd(f"nmcli dev set {HOTSPOT_INTERFACE} autoconnect yes")
    
    hotspot_active = False
    log.info("Hotspot disabled, attempting auto-connect")


def scan_networks():
    """Scan for available Wi-Fi networks."""
    run_cmd("nmcli dev wifi rescan")
    time.sleep(3)
    output, _ = run_cmd("nmcli -t -f SSID dev wifi list")
    ssids = list(set([x for x in output.split('\n') if x and x != HOTSPOT_SSID and x != '--']))
    return sorted(ssids)


def connect_to_network(ssid, password=""):
    """Connect to a Wi-Fi network."""
    log.info(f"Connecting to: {ssid}")
    
    # Disable hotspot first
    disable_hotspot()
    time.sleep(2)
    
    # Connect
    if password:
        cmd = f"nmcli dev wifi connect '{ssid}' password '{password}'"
    else:
        cmd = f"nmcli dev wifi connect '{ssid}'"
    
    output, code = run_cmd(cmd, timeout=30)
    
    if code == 0 or "successfully" in output.lower():
        log.info(f"Connected to {ssid}")
        klipper_msg(f"Wi-Fi: {ssid}")
        return True, "Connected!"
    else:
        log.error(f"Connection failed: {output}")
        # Re-enable hotspot since connection failed
        enable_hotspot()
        return False, output or "Connection failed"


# --- FLASK ROUTES ---
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/generate_204')
@app.route('/gen_204')
@app.route('/hotspot-detect')
@app.route('/ncsi.txt')
@app.route('/connecttest.txt')
@app.route('/success.txt')
@app.route('/canonical.html')
def captive_redirect():
    """Captive portal detection - redirect to main page."""
    return redirect('/', code=302)


@app.route('/scan')
def api_scan():
    ssids = scan_networks()
    return jsonify({"networks": ssids})


@app.route('/connect', methods=['POST'])
def api_connect():
    data = request.json
    ssid = data.get('ssid', '')
    password = data.get('password', '')
    
    if not ssid:
        return jsonify({"success": False, "message": "No network selected"})
    
    success, message = connect_to_network(ssid, password)
    return jsonify({"success": success, "message": message})


@app.route('/status')
def api_status():
    return jsonify({
        "connected": is_connected(),
        "ssid": get_current_ssid(),
        "hotspot_active": hotspot_active
    })


# --- MONITOR LOOP ---
def monitor_loop():
    """Main monitoring loop - runs in background thread."""
    global offline_count, online_count, hotspot_active
    
    log.info("Monitor starting, waiting for system boot...")
    time.sleep(20)  # Wait for system to fully boot
    
    # Check if we should clean up any existing hotspot
    current, _ = run_cmd("iwgetid -r")
    if current == HOTSPOT_SSID:
        log.info("Cleaning up existing hotspot from previous run")
        disable_hotspot()
        time.sleep(5)
    
    log.info("Monitor loop started")
    
    while True:
        try:
            connected = is_connected()
            current_ssid = get_current_ssid()
            
            if connected:
                online_count += 1
                offline_count = 0
                
                if hotspot_active and online_count >= ONLINE_THRESHOLD:
                    log.info(f"Internet restored ({online_count} checks). Disabling hotspot.")
                    disable_hotspot()
                    klipper_msg(f"Wi-Fi: {current_ssid or 'Connected'}")
                
                elif not hotspot_active and online_count == 1:
                    log.info(f"Online: {current_ssid}")
            
            else:
                offline_count += 1
                online_count = 0
                
                if not hotspot_active and offline_count >= OFFLINE_THRESHOLD:
                    log.warning(f"Offline for {offline_count} checks. Enabling hotspot.")
                    enable_hotspot()
                
                elif hotspot_active:
                    log.debug("Still offline, hotspot active")
        
        except Exception as e:
            log.error(f"Monitor error: {e}")
        
        time.sleep(CHECK_INTERVAL)


# --- MAIN ---
if __name__ == '__main__':
    log.info("=" * 50)
    log.info("  Klipper Wi-Fi Autopilot v3.0")
    log.info("=" * 50)
    log.info(f"Flask will run on port {FLASK_PORT}")
    log.info(f"Hotspot SSID: {HOTSPOT_SSID}")
    log.info(f"Hotspot Password: {'(Open Network)' if not HOTSPOT_PASSWORD else HOTSPOT_PASSWORD}")
    
    # Start monitor thread
    monitor = threading.Thread(target=monitor_loop, daemon=True)
    monitor.start()
    
    # Run Flask
    app.run(host='0.0.0.0', port=FLASK_PORT, threaded=True)
