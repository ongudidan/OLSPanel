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

MYSQL_PASS_FILE="$PROJECT_DIR/etc/mysqlPassword"
if [ -f "$MYSQL_PASS_FILE" ]; then
    MYSQL_PASSWORD=$(cat "$MYSQL_PASS_FILE")
    mysql -u root -p"$MYSQL_PASSWORD" panel << 'EOF' > /dev/null 2>&1
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
('users', '0007_dbclusternode_channel_name_and_more', NOW());

UPDATE `app_settings` SET `setting_value` = '/usr/bin/php-cgi' WHERE `setting_key` = 'cgi_bin' AND (`setting_value` = '/usr/bin/php-cgi8.2' OR `setting_value` NOT LIKE '/%');
EOF
fi

if [ -f "/root/venv/bin/python" ] && [ -f "${PROJECT_DIR}/manage.py" ]; then
    /root/venv/bin/python "${PROJECT_DIR}/manage.py" migrate --noinput > /dev/null 2>&1
fi

# Fix Dovecot MySQL password if %password% placeholder remains
DOVECOT_CONF="/etc/dovecot/dovecot.conf"
if [ -f "$DOVECOT_CONF" ]; then
    PANEL_PASS=""
    if [ -f "/root/db_credentials_panel.txt" ]; then
        PANEL_PASS=$(cat /root/db_credentials_panel.txt | tr -d '[:space:]')
    elif [ -f "/etc/dovecot/dovecot-sql.conf.ext" ]; then
        PANEL_PASS=$(grep -oP 'password=\K\S+' /etc/dovecot/dovecot-sql.conf.ext)
    elif [ -f "/etc/postfix/mysql-virtual_domains.cf" ]; then
        PANEL_PASS=$(grep -oP '^password\s*=\s*\K\S+' /etc/postfix/mysql-virtual_domains.cf)
    elif [ -f "$MYSQL_PASS_FILE" ]; then
        PANEL_PASS=$(cat "$MYSQL_PASS_FILE" | tr -d '[:space:]')
    fi

    if [ -n "$PANEL_PASS" ]; then
        if [ ! -f "/root/db_credentials_panel.txt" ]; then
            echo "$PANEL_PASS" > /root/db_credentials_panel.txt
            chmod 600 /root/db_credentials_panel.txt
        fi
        if grep -q "%password%" "$DOVECOT_CONF"; then
            sed -i "s|%password%|$PANEL_PASS|g" "$DOVECOT_CONF"
            systemctl restart dovecot > /dev/null 2>&1 || true
        fi
    fi
fi

# Ensure Roundcube olspanellogin plugin does not crash on init()
RC_LOGIN_PLUGIN="$PROJECT_DIR/3rdparty/roundcube/plugins/olspanellogin/olspanellogin.php"
if [ -f "$RC_LOGIN_PLUGIN" ]; then
    if grep -q "kill_session" "$RC_LOGIN_PLUGIN" && grep -A 5 "function init" "$RC_LOGIN_PLUGIN" | grep -q "kill_session"; then
        sed -i '/function init/,/}/ { /kill_session/d; /logout_actions/d; /get_instance/d; /if (isset(\$_GET/d; }' "$RC_LOGIN_PLUGIN"
    fi
# Ensure mail data directories are writable for suEXEC domain users
if [ -d "$PROJECT_DIR/3rdparty/rainloop/data" ]; then
    chmod -R 777 "$PROJECT_DIR/3rdparty/rainloop/data"
fi
if [ -d "$PROJECT_DIR/3rdparty/roundcube/temp" ]; then
    chmod -R 777 "$PROJECT_DIR/3rdparty/roundcube/temp"
fi
if [ -d "$PROJECT_DIR/3rdparty/roundcube/logs" ]; then
    chmod -R 777 "$PROJECT_DIR/3rdparty/roundcube/logs"
fi


