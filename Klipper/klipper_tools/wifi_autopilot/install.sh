#!/bin/bash
echo "Installing Klipper Wi-Fi Autopilot..."

# 1. Install Dependencies
sudo apt-get update
sudo apt-get install -y network-manager python3-flask

# 2. Copy Service Script
sudo cp wifi_autopilot.py /usr/local/bin/
sudo chmod +x /usr/local/bin/wifi_autopilot.py

# 3. Create Systemd Service
sudo bash -c 'cat <<EOF > /etc/systemd/system/wifi-autopilot.service
[Unit]
Description=Klipper Wi-Fi Autopilot
After=network.target

[Service]
ExecStart=/usr/bin/python3 /usr/local/bin/wifi_autopilot.py
Restart=always
User=root

[Install]
WantedBy=multi-user.target
EOF'

# 4. Enable and Start
sudo systemctl daemon-reload
sudo systemctl enable wifi-autopilot.service
sudo systemctl start wifi-autopilot.service

echo "Installation Complete! Access the hotspot 'Klipper-Setup' if Wi-Fi is lost."
