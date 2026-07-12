#!/bin/bash
# Custom OLSPanel Upgrade Installer Script

# 1. Determine Project Directory
HOME_PATH_FILE="/etc/olspanel/base_dir"
if [ -f "$HOME_PATH_FILE" ]; then
    PROJECT_DIR="$(cat "$HOME_PATH_FILE")"
else
    PROJECT_DIR="/usr/local/lsws/Example/html/mypanel"
fi

# Define your update host server URL (Replace this with your domain/IP)
UPDATE_HOST="https://YOUR_UPDATE_SERVER_DOMAIN_OR_IP"

echo "🚀 Downloading and applying custom OLSPanel update from ${UPDATE_HOST}..."

# 2. Download and unzip code
wget -O "${PROJECT_DIR%/*}/panel_setup.zip" "${UPDATE_HOST}/panel_setup.zip?$(date +%s)"
if [ $? -eq 0 ]; then
    sudo unzip -o "${PROJECT_DIR%/*}/panel_setup.zip" -d "${PROJECT_DIR%/*}"
    rm -f "${PROJECT_DIR%/*}/panel_setup.zip"
    echo "✅ Codebase updated."
else
    echo "❌ Failed to download panel_setup.zip"
    exit 1
fi

# 3. Run database migrations (optional)
curl -sSL "${UPDATE_HOST}/database_update.sh?$(date +%s)" | sed 's/\r$//' | bash

echo "🎉 Custom Update Applied Successfully!"
