#!/bin/bash
echo "========================================"
echo "  Klipper Wi-Fi Autopilot v3.0 Installer"
echo "========================================"

# 1. Install Dependencies
echo "[1/6] Installing dependencies..."
sudo apt-get update
sudo apt-get install -y network-manager python3-flask python3-requests wireless-tools iptables

# 2. Stop existing service if running
echo "[2/6] Stopping existing service..."
sudo systemctl stop wifi-autopilot.service 2>/dev/null

# 3. Copy Service Script
echo "[3/6] Copying service script..."
sudo cp wifi_autopilot.py /usr/local/bin/
sudo chmod +x /usr/local/bin/wifi_autopilot.py

# 4. Create Systemd Service
echo "[4/6] Creating systemd service..."
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
echo "[5/6] Enabling and starting service..."
sudo systemctl daemon-reload
sudo systemctl enable wifi-autopilot.service
sudo systemctl restart wifi-autopilot.service

# 6. Copy Klipper Macro
echo "[6/6] Copying Klipper macro..."
CURRENT_USER=${SUDO_USER:-$USER}
CONFIG_DIR="/home/$CURRENT_USER/printer_data/config"

if [ -d "$CONFIG_DIR" ]; then
    cp wifi_status.cfg "$CONFIG_DIR/"
    chown $CURRENT_USER:$CURRENT_USER "$CONFIG_DIR/wifi_status.cfg"
    echo "✅ Copied wifi_status.cfg"
    echo ""
    echo "⚠️  Add this to your printer.cfg:"
    echo "   [include wifi_status.cfg]"
else
    echo "⚠️  Copy wifi_status.cfg manually to your config folder"
fi

echo ""
echo "========================================"
echo "  Installation Complete!"
echo "========================================"
echo ""
echo "📶 Hotspot SSID: Klipper-Setup"
echo "🔓 Password: (Open Network - no password)"
echo ""
echo "📋 Check status: sudo systemctl status wifi-autopilot"
echo "📋 View logs: sudo journalctl -u wifi-autopilot -f"
echo ""
