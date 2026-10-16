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
EOF
fi

if [ -f "/root/venv/bin/python" ] && [ -f "${PROJECT_DIR}/manage.py" ]; then
    /root/venv/bin/python "${PROJECT_DIR}/manage.py" migrate --noinput > /dev/null 2>&1
fi

