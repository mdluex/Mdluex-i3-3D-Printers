#!/bin/bash
echo "========================================"
echo "  Klipper Wi-Fi Autopilot Uninstaller"
echo "========================================"

# 1. Stop and disable service
echo "[1/5] Stopping service..."
sudo systemctl stop wifi-autopilot.service 2>/dev/null
sudo systemctl disable wifi-autopilot.service 2>/dev/null

# 2. Remove systemd service
echo "[2/5] Removing systemd service..."
sudo rm -f /etc/systemd/system/wifi-autopilot.service
sudo systemctl daemon-reload

# 3. Remove script
echo "[3/5] Removing script..."
sudo rm -f /usr/local/bin/wifi_autopilot.py

# 4. Clean up iptables
echo "[4/5] Cleaning up iptables..."
sudo iptables -t nat -F PREROUTING 2>/dev/null

# 5. Remove hotspot connection
echo "[5/5] Removing hotspot..."
sudo nmcli con down 'Klipper-Setup' 2>/dev/null
sudo nmcli con delete 'Klipper-Setup' 2>/dev/null

# Optional: Remove config file
CURRENT_USER=${SUDO_USER:-$USER}
CONFIG_FILE="/home/$CURRENT_USER/printer_data/config/wifi_status.cfg"

if [ -f "$CONFIG_FILE" ]; then
    read -p "Remove wifi_status.cfg from Klipper config? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -f "$CONFIG_FILE"
        echo "✅ Removed wifi_status.cfg"
        echo "⚠️  Remember to remove [include wifi_status.cfg] from printer.cfg"
    fi
fi

echo ""
echo "========================================"
echo "  Uninstall Complete!"
echo "========================================"
echo "Wi-Fi Autopilot has been removed."
echo ""
