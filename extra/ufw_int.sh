#!/bin/bash
set -e

# Download and install UFW CGI Plugin
wget -O /usr/local/ufw.zip "https://ongudidan.github.io/OLSPanel/plugin/ufw.zip"
sudo unzip -o /usr/local/ufw.zip -d /usr/local

# Download and install UFW default configuration files if not present
wget -O /usr/local/config_ufw.zip "https://ongudidan.github.io/OLSPanel/plugin/config_ufw.zip"
if [ ! -d "/usr/local/ufw/config" ]; then
    sudo unzip -o /usr/local/config_ufw.zip -d /usr/local/ufw
fi

# Set executable permissions and correct ownership
sudo chmod +x /usr/local/ufw/*.pl 2>/dev/null || true
sudo chown -R root:root /usr/local/ufw 2>/dev/null || true
rm -f /usr/local/ufw.zip /usr/local/config_ufw.zip

echo "✅ UFW Firewall CGI Plugin installed successfully."