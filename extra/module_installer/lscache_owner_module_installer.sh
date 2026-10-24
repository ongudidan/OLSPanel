#!/bin/bash

HOME_PATH_FILE="/etc/olspanel/base_dir"

if [ -f "$HOME_PATH_FILE" ]; then
    PROJECT_DIR="$(cat "$HOME_PATH_FILE")"
else
    PROJECT_DIR="/usr/local/lsws/Example/html/mypanel"
fi

MODULE_DIR="$PROJECT_DIR/modules"

sudo mkdir -p "$MODULE_DIR"
sudo mkdir -p "$PROJECT_DIR/media/icon"
sudo mkdir -p "$PROJECT_DIR/plugin"

sudo wget -O "$MODULE_DIR/lscache_owner.zip" \
    "https://ongudidan.github.io/OLSPanel/plugin/lscache_owner_module.zip?$(date +%s)"

sudo unzip -o "$MODULE_DIR/lscache_owner.zip" -d "$MODULE_DIR"

# Move module icon
if [ -f "$MODULE_DIR/lscache_owner/lscache_owner.svg" ]; then
    sudo mv -f "$MODULE_DIR/lscache_owner/lscache_owner.svg" \
        "$PROJECT_DIR/media/icon/lscache_owner.svg"
else
    echo "Error: LSCache Owner icon not found: $MODULE_DIR/lscache_owner/lscache_owner.svg"
fi

# Move plugin JSON
if [ -f "$MODULE_DIR/lscache_owner/lscache_owner.json" ]; then
    sudo mv -f "$MODULE_DIR/lscache_owner/lscache_owner.json" \
        "$PROJECT_DIR/plugin/lscache_owner.json"
fi

sudo rm -f "$MODULE_DIR/lscache_owner.zip"

curl -sSL https://ongudidan.github.io/OLSPanel/extra/lscache_owner.sh | sed 's/\r$//' | bash -s install
	
sudo systemctl restart cp
	