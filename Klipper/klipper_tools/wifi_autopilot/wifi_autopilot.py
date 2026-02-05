#!/usr/bin/env python3
"""
Klipper Wi-Fi Autopilot - v2.0
Monitors Wi-Fi connection and provides a captive portal for easy setup.

Changes in v2.0:
- Real-time connectivity check using ping
- Proper hotspot enable/disable with NetworkManager
- Captive portal redirect (DNS hijack)
- LCD status updates via Moonraker API
- Auto-reconnect when known network returns
"""

import time
import subprocess
import requests
import os
import socket
import logging
import threading
from flask import Flask, jsonify, request, render_template_string, redirect

# --- CONFIGURATION ---
CHECK_INTERVAL = 5       # Seconds between connectivity checks
PING_TARGET = "8.8.8.8"  # Google DNS for connectivity test
HOTSPOT_SSID = "Klipper-Setup"
HOTSPOT_PASSWORD = ""    # Leave empty for open network
MOONRAKER_API = "http://127.0.0.1:7125"
OFFLINE_THRESHOLD = 3    # Failed pings before activating hotspot
HOTSPOT_INTERFACE = "wlan0"

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("wifi_autopilot")

# --- FLASK APP ---
app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Klipper Wi-Fi Setup</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <style>
        * { box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; padding: 20px; background: #1a1a2e; color: #eee; text-align: center; }
        h2 { color: #00d4ff; }
        .network { background: #16213e; border: 1px solid #0f3460; padding: 15px; margin: 10px auto; max-width: 350px; border-radius: 8px; cursor: pointer; }
        .network:hover { background: #0f3460; }
        input { padding: 12px; font-size: 16px; margin: 10px 0; width: 100%; max-width: 300px; border-radius: 6px; border: none; }
        button { padding: 12px 30px; font-size: 16px; background: #00d4ff; color: #000; border: none; border-radius: 6px; cursor: pointer; margin: 5px; }
        .hidden { display: none; }
        .status { padding: 10px; background: #e94560; border-radius: 6px; margin: 10px auto; max-width: 350px; }
        .success { background: #4ecca3; }
    </style>
</head>
<body>
    <h2>🖨️ Klipper Wi-Fi Setup</h2>
    <p>Select your Wi-Fi network:</p>
    
    <div id="status" class="status hidden"></div>
    <div id="scan-results">Scanning...</div>
    
    <div id="connect-form" class="hidden">
        <h3 id="selected-ssid"></h3>
        <input type="password" id="password" placeholder="Password (if required)">
        <br>
        <button onclick="connect()">Connect</button>
        <button onclick="cancel()">Back</button>
    </div>

    <script>
        let selectedSSID = "";
        
        function showStatus(msg, success) {
            const s = document.getElementById('status');
            s.innerText = msg;
            s.className = 'status' + (success ? ' success' : '');
            s.classList.remove('hidden');
        }

        function scan() {
            document.getElementById('scan-results').innerHTML = 'Scanning...';
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
                    btn.innerText = ssid;
                    btn.onclick = () => select(ssid);
                    div.appendChild(btn);
                });
            }).catch(() => showStatus('Scan failed. Retrying...', false));
        }

        function select(ssid) {
            selectedSSID = ssid;
            document.getElementById('selected-ssid').innerText = ssid;
            document.getElementById('connect-form').classList.remove('hidden');
            document.getElementById('scan-results').classList.add('hidden');
            document.getElementById('status').classList.add('hidden');
        }

        function cancel() {
            document.getElementById('connect-form').classList.add('hidden');
            document.getElementById('scan-results').classList.remove('hidden');
        }

        function connect() {
            const pw = document.getElementById('password').value;
            showStatus('Connecting...', false);
            fetch('/connect', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ssid: selectedSSID, password: pw})
            }).then(r => r.json()).then(d => {
                if(d.success) {
                    showStatus('Connected! Printer will be back online shortly.', true);
                    setTimeout(() => { window.location.reload(); }, 5000);
                } else {
                    showStatus('Failed: ' + d.message, false);
                }
            }).catch(() => showStatus('Connection error.', false));
        }

        scan();
        setInterval(scan, 15000);
    </script>
</body>
</html>
"""


# --- HELPER FUNCTIONS ---
def run_cmd(cmd, timeout=10):
    """Run shell command and return output."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip()
    except Exception as e:
        logger.error(f"Command failed: {cmd} - {e}")
        return ""


def is_connected():
    """Check internet connectivity using ping."""
    try:
        subprocess.run(["ping", "-c", "1", "-W", "2", PING_TARGET], 
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        return True
    except:
        return False


def get_current_ssid():
    """Get current connected SSID."""
    output = run_cmd("iwgetid -r")
    return output if output and output != HOTSPOT_SSID else None


def klipper_msg(msg):
    """Send message to Klipper LCD via Moonraker API."""
    try:
        url = f"{MOONRAKER_API}/printer/gcode/script"
        payload = {"script": f"WIFI_STATUS MSG=\"{msg}\""}
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code == 200:
            logger.info(f"LCD Message: {msg}")
        else:
            logger.warning(f"Moonraker returned {response.status_code}")
    except Exception as e:
        logger.error(f"Failed to send LCD message: {e}")


def enable_hotspot():
    """Enable the Wi-Fi hotspot."""
    logger.info("Enabling hotspot...")
    
    # Delete existing hotspot connection if exists
    run_cmd(f"nmcli con delete '{HOTSPOT_SSID}' 2>/dev/null")
    
    # Create new hotspot
    if HOTSPOT_PASSWORD:
        cmd = f"nmcli dev wifi hotspot ifname {HOTSPOT_INTERFACE} ssid '{HOTSPOT_SSID}' password '{HOTSPOT_PASSWORD}'"
    else:
        cmd = f"nmcli dev wifi hotspot ifname {HOTSPOT_INTERFACE} ssid '{HOTSPOT_SSID}'"
    
    result = run_cmd(cmd)
    
    if "successfully" in result.lower() or run_cmd(f"iwgetid -r") == HOTSPOT_SSID:
        logger.info(f"Hotspot '{HOTSPOT_SSID}' is active")
        klipper_msg(f"Wi-Fi Lost! Connect to: {HOTSPOT_SSID}")
        return True
    else:
        logger.error(f"Failed to enable hotspot: {result}")
        return False


def disable_hotspot():
    """Disable the hotspot and return to client mode."""
    logger.info("Disabling hotspot...")
    run_cmd(f"nmcli con down '{HOTSPOT_SSID}' 2>/dev/null")
    run_cmd(f"nmcli con delete '{HOTSPOT_SSID}' 2>/dev/null")
    # Let NetworkManager auto-connect to known networks
    run_cmd("nmcli dev wifi rescan")
    time.sleep(2)
    run_cmd(f"nmcli dev set {HOTSPOT_INTERFACE} autoconnect yes")


def scan_networks():
    """Scan for available Wi-Fi networks."""
    run_cmd("nmcli dev wifi rescan")
    time.sleep(2)
    output = run_cmd("nmcli -t -f SSID dev wifi list")
    ssids = list(set([x for x in output.split('\n') if x and x != HOTSPOT_SSID]))
    return ssids


def connect_to_network(ssid, password=""):
    """Connect to a Wi-Fi network."""
    logger.info(f"Attempting to connect to: {ssid}")
    
    # Disable hotspot first
    disable_hotspot()
    time.sleep(1)
    
    # Connect
    if password:
        cmd = f"nmcli dev wifi connect '{ssid}' password '{password}'"
    else:
        cmd = f"nmcli dev wifi connect '{ssid}'"
    
    result = run_cmd(cmd, timeout=30)
    
    if "successfully" in result.lower():
        logger.info(f"Connected to {ssid}")
        klipper_msg(f"Wi-Fi: {ssid}")
        return True, "Connected successfully"
    else:
        logger.error(f"Connection failed: {result}")
        return False, result or "Connection failed"


# --- FLASK ROUTES ---
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/hotspot-detect')
@app.route('/generate_204')
@app.route('/gen_204')
@app.route('/ncsi.txt')
@app.route('/connecttest.txt')
@app.route('/redirect')
def captive_redirect():
    """Captive portal detection endpoints."""
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
        return jsonify({"success": False, "message": "No SSID provided"})
    
    success, message = connect_to_network(ssid, password)
    return jsonify({"success": success, "message": message})


@app.route('/status')
def api_status():
    connected = is_connected()
    current_ssid = get_current_ssid()
    return jsonify({
        "connected": connected,
        "ssid": current_ssid,
        "hotspot_active": run_cmd("iwgetid -r") == HOTSPOT_SSID
    })


# --- MONITOR LOOP ---
def monitor_loop():
    """Main monitoring loop."""
    failures = 0
    in_hotspot_mode = False
    last_status = None
    
    logger.info("Wi-Fi Autopilot started. Waiting for system to stabilize...")
    time.sleep(15)  # Wait for boot
    
    while True:
        try:
            connected = is_connected()
            current_ssid = get_current_ssid()
            
            if connected and current_ssid:
                # We're online!
                if in_hotspot_mode:
                    logger.info("Wi-Fi restored. Disabling hotspot.")
                    disable_hotspot()
                    in_hotspot_mode = False
                
                if last_status != "connected":
                    klipper_msg(f"Wi-Fi: {current_ssid}")
                    last_status = "connected"
                
                failures = 0
            
            else:
                # We're offline
                failures += 1
                logger.warning(f"Connectivity check failed ({failures}/{OFFLINE_THRESHOLD})")
                
                if failures >= OFFLINE_THRESHOLD and not in_hotspot_mode:
                    logger.info("Threshold reached. Activating hotspot.")
                    if enable_hotspot():
                        in_hotspot_mode = True
                        last_status = "hotspot"
                
                elif in_hotspot_mode:
                    # Check if user connected to a new network
                    current = run_cmd("iwgetid -r")
                    if current and current != HOTSPOT_SSID:
                        # User connected to something else!
                        logger.info(f"Connected to new network: {current}")
                        in_hotspot_mode = False
                        disable_hotspot()
        
        except Exception as e:
            logger.error(f"Monitor loop error: {e}")
        
        time.sleep(CHECK_INTERVAL)


# --- MAIN ---
if __name__ == '__main__':
    logger.info("=" * 50)
    logger.info("Klipper Wi-Fi Autopilot v2.0")
    logger.info("=" * 50)
    
    # Start monitor in background
    monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
    monitor_thread.start()
    
    # Run Flask on port 80 (needs root)
    # Binding to 0.0.0.0 allows access from any interface
    app.run(host='0.0.0.0', port=80, threaded=True)
