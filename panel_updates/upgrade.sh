#!/bin/bash
# Custom OLSPanel Upgrade Installer Script

set -e

# 1. Determine Project Directory
HOME_PATH_FILE="/etc/olspanel/base_dir"
if [ -f "$HOME_PATH_FILE" ]; then
    PROJECT_DIR="$(cat "$HOME_PATH_FILE" | tr -d '\r\n')"
else
    PROJECT_DIR="/usr/local/olspanel/mypanel"
fi

BASE_DIR="${PROJECT_DIR%/*}" # e.g., /usr/local/olspanel
UPDATE_HOST="https://ongudidan.github.io/OLSPanel/panel_updates"
TEMP_ZIP="/tmp/panel_setup_update.zip"

echo "🚀 Downloading and applying custom OLSPanel update from ${UPDATE_HOST}..."

# 2. Download and unzip code
wget -q -O "$TEMP_ZIP" "${UPDATE_HOST}/panel_setup.zip?$(date +%s)"
if [ -s "$TEMP_ZIP" ]; then
    # Safely extract files while preserving machine-specific secrets
    unzip -o -q "$TEMP_ZIP" -d "$BASE_DIR" \
        -x "mypanel/etc/mysqlPassword" \
           "mypanel/etc/dbPassword" \
           "mypanel/etc/license.key" \
           "mypanel/etc/ip" \
           "mypanel/etc/time.zone" \
           "mypanel/etc/conf.ini" \
           "mypanel/etc/_*" \
           "mypanel/db.sqlite3" || true
    rm -f "$TEMP_ZIP"
    echo "✅ Codebase updated."
else
    echo "❌ Failed to download panel_setup.zip"
    exit 1
fi

# 3. Update version file
if curl -sSL "${UPDATE_HOST}/version.txt?$(date +%s)" -o /tmp/new_version.txt && [ -s /tmp/new_version.txt ]; then
    cp /tmp/new_version.txt "${PROJECT_DIR}/etc/version"
    rm -f /tmp/new_version.txt
    echo "✅ Version updated to $(cat "${PROJECT_DIR}/etc/version")"
fi

# 4. Remove pending update flag
rm -f "${PROJECT_DIR}/etc/update"

# 5. Run database migrations
if [ -f "/root/venv/bin/python" ] && [ -f "${PROJECT_DIR}/manage.py" ]; then
    echo "🔄 Running migrations..."
    /root/venv/bin/python "${PROJECT_DIR}/manage.py" migrate --noinput > /dev/null 2>&1 || true
elif [ -f "${PROJECT_DIR}/manage.py" ]; then
    python3 "${PROJECT_DIR}/manage.py" migrate --noinput > /dev/null 2>&1 || true
fi

# 6. Ensure correct file ownership
chown -R www-data:www-data "${PROJECT_DIR}" 2>/dev/null || true

echo "🎉 Custom Update Applied Successfully!"
