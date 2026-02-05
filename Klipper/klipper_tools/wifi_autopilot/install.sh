#!/bin/bash
echo "========================================"
echo "  Klipper Wi-Fi Autopilot v3.2 Installer"
echo "========================================"

# 1. Install Dependencies
echo "[1/5] Installing dependencies..."
sudo apt-get update
sudo apt-get install -y network-manager python3-flask python3-requests wireless-tools iptables

# 2. Stop existing service if running
echo "[2/5] Stopping existing service..."
sudo systemctl stop wifi-autopilot.service 2>/dev/null

# 3. Copy Service Script
echo "[3/5] Copying service script..."
sudo cp wifi_autopilot.py /usr/local/bin/
sudo chmod +x /usr/local/bin/wifi_autopilot.py

# 4. Create Systemd Service
echo "[4/5] Creating systemd service..."
sudo bash -c 'cat <<EOF > /etc/systemd/system/wifi-autopilot.service
[Unit]
Description=Klipper Wi-Fi Autopilot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /usr/local/bin/wifi_autopilot.py
ExecStopPost=/sbin/iptables -t nat -F PREROUTING
Restart=always
RestartSec=10
User=root
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF'

# 5. Enable and Start
echo "[5/5] Enabling and starting service..."
sudo systemctl daemon-reload
sudo systemctl enable wifi-autopilot.service
sudo systemctl restart wifi-autopilot.service

echo ""
echo "========================================"
echo "  Installation Complete!"
echo "========================================"
echo ""
echo "📶 Hotspot SSID: Klipper-Setup"
echo "🔓 Password: (Open Network)"
echo ""
echo "📋 Check status: sudo systemctl status wifi-autopilot"
echo "📋 View logs: sudo journalctl -u wifi-autopilot -f"
echo ""
