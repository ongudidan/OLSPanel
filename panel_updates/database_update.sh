#!/bin/bash
# Custom Database Update / Migration Script

# Determine Project Directory
HOME_PATH_FILE="/etc/olspanel/base_dir"
if [ -f "$HOME_PATH_FILE" ]; then
    PROJECT_DIR="$(cat "$HOME_PATH_FILE")"
else
    PROJECT_DIR="/usr/local/lsws/Example/html/mypanel"
fi

echo "🔄 Running migrations..."

# Add any Django database migration or update commands here, for example:
# sudo /root/venv/bin/python ${PROJECT_DIR}/manage.py migrate --noinput
