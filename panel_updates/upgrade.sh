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

# 5. Run database schema updates and migrations
PYTHON_BIN="python3"
if [ -x "/root/venv/bin/python" ]; then
    PYTHON_BIN="/root/venv/bin/python"
elif [ -x "/root/venv/bin/python3" ]; then
    PYTHON_BIN="/root/venv/bin/python3"
fi

# Step 5a: Direct MySQL sync if credentials exist
MYSQL_PASS_FILE="${PROJECT_DIR}/etc/mysqlPassword"
if [ -f "$MYSQL_PASS_FILE" ] && command -v mysql > /dev/null 2>&1; then
    MYSQL_PASSWORD=$(cat "$MYSQL_PASS_FILE" | tr -d '\r\n')
    mysql -u root -p"$MYSQL_PASSWORD" panel << 'EOF' > /dev/null 2>&1 || true
CREATE TABLE IF NOT EXISTS `api_keys` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `name` varchar(255) NOT NULL DEFAULT 'WHMCS',
  `token` varchar(255) NOT NULL,
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `last_used` datetime(6) DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  PRIMARY KEY (`id`),
  UNIQUE KEY `token` (`token`),
  KEY `api_keys_user_id_fk_auth_user_id` (`user_id`),
  CONSTRAINT `api_keys_user_id_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT IGNORE INTO `django_migrations` (`app`, `name`, `applied`) VALUES
('users', '0005_package_profile_pkg_id_domain_dns_record', NOW()),
('users', '0006_apikey_apps_appsettings_backuplist_bandwidth_and_more', NOW()),
('users', '0007_dbclusternode_channel_name_and_more', NOW()),
('users', '0008_package_postgresql_databases', NOW());
EOF
fi

# Step 5b: Django connection schema verification and migration sync
if [ -f "${PROJECT_DIR}/manage.py" ]; then
    echo "🔄 Checking database schema and synchronizing migrations..."
    $PYTHON_BIN -c "
import sys, os
sys.path.insert(0, '$PROJECT_DIR')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'user_management.settings')
try:
    import django
    django.setup()
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute(\"SHOW TABLES LIKE 'packages'\")
        if cursor.fetchone():
            cursor.execute(\"SHOW COLUMNS FROM packages LIKE 'postgresql_databases'\")
            if not cursor.fetchone():
                cursor.execute(\"ALTER TABLE packages ADD COLUMN postgresql_databases INT(11) DEFAULT 0\")
                print('✅ Added postgresql_databases column to packages table')
            
            cursor.execute(\"SHOW COLUMNS FROM packages LIKE 'allowed_subdomains'\")
            if not cursor.fetchone():
                cursor.execute(\"ALTER TABLE packages ADD COLUMN allowed_subdomains INT(11) DEFAULT 0\")

        cursor.execute(\"SHOW TABLES LIKE 'domain'\")
        if cursor.fetchone():
            cursor.execute(\"SHOW COLUMNS FROM domain LIKE 'line'\")
            if not cursor.fetchone():
                cursor.execute(\"ALTER TABLE domain ADD COLUMN line VARCHAR(255) DEFAULT ''\")

        cursor.execute(\"SHOW TABLES LIKE 'django_migrations'\")
        if cursor.fetchone():
            cursor.execute(\"\"\"
                INSERT IGNORE INTO django_migrations (app, name, applied) VALUES
                ('users', '0005_package_profile_pkg_id_domain_dns_record', NOW()),
                ('users', '0006_apikey_apps_appsettings_backuplist_bandwidth_and_more', NOW()),
                ('users', '0007_dbclusternode_channel_name_and_more', NOW()),
                ('users', '0008_package_postgresql_databases', NOW())
            \"\"\")
            print('✅ Synchronized django_migrations table')
except Exception as e:
    print(f'⚠️ Warning during schema synchronization: {e}')
" 2>/dev/null || true

    echo "🔄 Running Django migrations..."
    $PYTHON_BIN "${PROJECT_DIR}/manage.py" migrate --noinput > /dev/null 2>&1 || true
fi

# 6. Ensure correct file ownership
chown -R www-data:www-data "${PROJECT_DIR}" 2>/dev/null || true

echo "🎉 Custom Update Applied Successfully!"
