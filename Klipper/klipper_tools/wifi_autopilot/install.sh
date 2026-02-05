#!/bin/bash
echo "========================================"
echo "  Klipper Wi-Fi Autopilot v2.0 Installer"
echo "========================================"

# 1. Install Dependencies
echo "[1/5] Installing dependencies..."
sudo apt-get update
sudo apt-get install -y network-manager python3-flask python3-requests wireless-tools

# 2. Copy Service Script
echo "[2/5] Copying service script..."
sudo cp wifi_autopilot.py /usr/local/bin/
sudo chmod +x /usr/local/bin/wifi_autopilot.py

# 3. Create Systemd Service
echo "[3/5] Creating systemd service..."
sudo bash -c 'cat <<EOF > /etc/systemd/system/wifi-autopilot.service
[Unit]
Description=Klipper Wi-Fi Autopilot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /usr/local/bin/wifi_autopilot.py
Restart=always
RestartSec=5
User=root
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF'

# 4. Enable and Start
echo "[4/5] Enabling service..."
sudo systemctl daemon-reload
sudo systemctl enable wifi-autopilot.service
sudo systemctl restart wifi-autopilot.service

# 5. Copy Klipper Macro (Autodetect user path)
echo "[5/5] Copying Klipper macro..."
CURRENT_USER=${SUDO_USER:-$USER}
CONFIG_DIR="/home/$CURRENT_USER/printer_data/config"

if [ -d "$CONFIG_DIR" ]; then
    echo "Detected config directory: $CONFIG_DIR"
    cp wifi_status.cfg "$CONFIG_DIR/"
    chown $CURRENT_USER:$CURRENT_USER "$CONFIG_DIR/wifi_status.cfg"
    echo "✅ Copied wifi_status.cfg to your config folder."
    echo ""
    echo "⚠️  IMPORTANT: Add this line to your printer.cfg:"
    echo "   [include wifi_status.cfg]"
else
    echo "⚠️  Could not find 'printer_data/config'."
    echo "   Please copy 'wifi_status.cfg' manually to your Klipper config folder."
fi

echo ""
echo "========================================"
echo "  Installation Complete!"
echo "========================================"
echo "If Wi-Fi is lost, connect to: 'Klipper-Setup'"
echo "Service status: sudo systemctl status wifi-autopilot"
echo ""
