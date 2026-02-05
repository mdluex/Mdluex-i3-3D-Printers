#!/usr/bin/env python3
import time
import subprocess
import requests
import os
import logging
from flask import Flask, jsonify, request, render_template_string

# --- CONFIGURATION ---
CHECK_INTERVAL = 10  # Seconds between connectivity checks
HOTSPOT_SSID = "Klipper-Setup"
MOONRAKER_API = "http://localhost:7125"
OFFLINE_THRESHOLD = 3  # Failures before activating hotspot

# --- FLASK APP ---
app = Flask(__name__)

# Simple HTML Template for Captive Portal
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Klipper Wi-Fi Setup</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: sans-serif; padding: 20px; text-align: center; }
        button { padding: 10px 20px; font-size: 16px; margin: 5px; width: 100%; max-width: 300px; }
        input { padding: 10px; font-size: 16px; margin: 5px; width: 100%; max-width: 280px; }
        .network { border: 1px solid #ccc; padding: 10px; margin: 5px auto; max-width: 300px; cursor: pointer; }
        .hidden { display: none; }
    </style>
</head>
<body>
    <h2>Klipper Wi-Fi Setup</h2>
    <div id="scan-results">Searching for networks...</div>
    
    <div id="connect-form" class="hidden">
        <h3 id="selected-ssid"></h3>
        <input type="password" id="password" placeholder="Password (if needed)">
        <button onclick="connect()">Connect</button>
        <button onclick="cancel()">Cancel</button>
    </div>

    <script>
        let selectedSSID = "";

        function scan() {
            fetch('/scan').then(r => r.json()).then(data => {
                const div = document.getElementById('scan-results');
                div.innerHTML = "";
                data.networks.forEach(ssid => {
                    if(!ssid) return;
                    let btn = document.createElement('div');
                    btn.className = 'network';
                    btn.innerText = ssid;
                    btn.onclick = () => select(ssid);
                    div.appendChild(btn);
                });
            });
        }

        function select(ssid) {
            selectedSSID = ssid;
            document.getElementById('selected-ssid').innerText = ssid;
            document.getElementById('connect-form').classList.remove('hidden');
            document.getElementById('scan-results').classList.add('hidden');
        }

        function cancel() {
            document.getElementById('connect-form').classList.add('hidden');
            document.getElementById('scan-results').classList.remove('hidden');
        }

        function connect() {
            const pw = document.getElementById('password').value;
            fetch('/connect', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ssid: selectedSSID, password: pw})
            }).then(r => r.json()).then(d => alert(d.status));
        }

        scan();
    </script>
</body>
</html>
"""

def klipper_msg(msg):
    try:
        requests.post(f"{MOONRAKER_API}/printer/print/script", json={"script": f"WIFI_STATUS MSG='{msg}'"})
    except:
        pass

def run_command(cmd):
    try:
        return subprocess.check_output(cmd, shell=True).decode().strip()
    except:
        return ""

def is_connected():
    # Check if we have an active connection (excluding Hotspot)
    state = run_command("nmcli -f GENERAL.STATE con show --active")
    return "activated" in state and "Klipper-Setup" not in run_command("nmcli -t -f NAME con show --active")

def enable_hotspot():
    logging.info("Enabling Hotspot...")
    klipper_msg(f"Wi-Fi Lost. Connect to {HOTSPOT_SSID}")
    # Create hotspot if not exists
    run_command(f"nmcli con add type wifi ifname wlan0 con-name {HOTSPOT_SSID} autoconnect yes ssid {HOTSPOT_SSID}")
    run_command(f"nmcli con modify {HOTSPOT_SSID} 802-11-wireless.mode ap 802-11-wireless.band bg ipv4.method shared")
    run_command(f"nmcli con up {HOTSPOT_SSID}")

def disable_hotspot():
    run_command(f"nmcli con down {HOTSPOT_SSID}")

@app.route('/')
def index():
    return HTML_TEMPLATE

@app.route('/scan')
def scan():
    raw = run_command("nmcli -t -f SSID dev wifi list")
    ssids = list(set([x for x in raw.split('\n') if x]))
    return jsonify({"networks": ssids})

@app.route('/connect', methods=['POST'])
def connect():
    data = request.json
    ssid = data.get('ssid')
    pw = data.get('password')
    
    # Simple NMCLI connection logic
    cmd = f"nmcli dev wifi connect '{ssid}'"
    if pw:
        cmd += f" password '{pw}'"
    
    res = run_command(cmd)
    if "successfully activated" in res:
        klipper_msg(f"Connected: {ssid}")
        return jsonify({"status": "Connected! System will switch networks."})
    else:
        return jsonify({"status": "Failed to connect."})

# --- MONITOR THREAD ---
import threading
def monitor_loop():
    failures = 0
    in_hotspot_mode = False
    
    time.sleep(10) # Wait for boot
    
    while True:
        if is_connected():
            if in_hotspot_mode:
                disable_hotspot()
                in_hotspot_mode = False
            klipper_msg("Wi-Fi Connected")
            failures = 0
        else:
            failures += 1
            if failures > OFFLINE_THRESHOLD and not in_hotspot_mode:
                enable_hotspot()
                in_hotspot_mode = True
        
        time.sleep(CHECK_INTERVAL)

if __name__ == '__main__':
    # Start Monitor in background
    t = threading.Thread(target=monitor_loop)
    t.daemon = True
    t.start()
    
    # Run Web Server
    app.run(host='0.0.0.0', port=80)
