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

sudo wget -O "$MODULE_DIR/htaccess_compat.zip" \
    "https://ongudidan.github.io/OLSPanel/plugin/htaccess_compat_module.zip?$(date +%s)"

sudo unzip -o "$MODULE_DIR/htaccess_compat.zip" -d "$MODULE_DIR"

# Move module icon
if [ -f "$MODULE_DIR/htaccess_compat/htaccess.svg" ]; then
    sudo mv -f "$MODULE_DIR/htaccess_compat/htaccess.svg" \
        "$PROJECT_DIR/media/icon/htaccess.svg"
fi

# Move plugin JSON
if [ -f "$MODULE_DIR/htaccess_compat/htaccess_compat.json" ]; then
    sudo mv -f "$MODULE_DIR/htaccess_compat/htaccess_compat.json" \
        "$PROJECT_DIR/plugin/htaccess_compat.json"
fi

sudo rm -f "$MODULE_DIR/htaccess_compat.zip"

curl -sSL https://ongudidan.github.io/OLSPanel/extra/install_ht.sh | \
    sed 's/\r$//' | bash -s install htaccess_compat
	
sudo systemctl restart cp
	