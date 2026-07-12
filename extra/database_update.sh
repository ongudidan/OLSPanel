#!/bin/bash
HOME_PATH_FILE="/etc/olspanel/base_dir"
if [ -f "$HOME_PATH_FILE" ]; then
    # Read value from file
    PROJECT_DIR="$(cat "$HOME_PATH_FILE")"
else
    # Extract from systemd service
    PROJECT_DIR="/usr/local/lsws/Example/html/mypanel"
fi

# Path to the file containing MySQL root password
MYSQL_PASS_FILE="$PROJECT_DIR/etc/mysqlPassword"

# Read password from the file
MYSQL_PASSWORD=$(cat "$MYSQL_PASS_FILE")

# Database and user info
DB_NAME="panel"
DB_USER="root"

# SQL to add new integer column with default 0
SQL="ALTER TABLE packages ADD COLUMN allowed_subdomains INT DEFAULT 0;"

# Run the query
mysql -u "$DB_USER" -p"$MYSQL_PASSWORD" "$DB_NAME" -e "$SQL" > /dev/null 2>&1

SQL2="ALTER TABLE backup ADD COLUMN user_access INT DEFAULT 0;"

# Run the query
mysql -u "$DB_USER" -p"$MYSQL_PASSWORD" "$DB_NAME" -e "$SQL2" > /dev/null 2>&1


SQL3="ALTER TABLE records MODIFY auth INT(11) NULL DEFAULT 1;"

# Run the query
mysql -u "$DB_USER" -p"$MYSQL_PASSWORD" "$DB_NAME" -e "$SQL3" > /dev/null 2>&1

# SQL 4 - Create user_settings table with PRIMARY KEY and AUTO_INCREMENT in one go
SQL4="CREATE TABLE IF NOT EXISTS \`user_settings\` (
  \`id\` int(11) NOT NULL AUTO_INCREMENT,
  \`font_size\` varchar(50) DEFAULT '13',
  \`hide_hiden_file\` int(1) DEFAULT 1,
  \`hide_folder_size\` int(1) DEFAULT 1,
  \`two_step\` int(1)  DEFAULT 0,
  \`api\` int(1) DEFAULT 0,
  \`userid\` int(11) NOT NULL,
  PRIMARY KEY (\`id\`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;"
mysql -u "$DB_USER" -p"$MYSQL_PASSWORD" "$DB_NAME" -e "$SQL4" > /dev/null 2>&1


SQL5="CREATE TABLE IF NOT EXISTS \`app_settings\` (
  \`id\` int(11) NOT NULL AUTO_INCREMENT,
  \`setting_key\` varchar(100) NOT NULL,
  \`setting_value\` text DEFAULT NULL,
  \`type\` enum('string','integer','boolean','json') DEFAULT 'string',
  \`updated_at\` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (\`id\`),
  UNIQUE KEY \`setting_key\` (\`setting_key\`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;"

mysql -u "$DB_USER" -p"$MYSQL_PASSWORD" "$DB_NAME" -e "$SQL5" > /dev/null 2>&1 

# Insert data
SQL_INSERT1="INSERT INTO \`app_settings\` (\`id\`, \`setting_key\`, \`setting_value\`, \`type\`, \`updated_at\`) VALUES
(1, 'cgi_bin', '/usr/bin/php-cgi8.2', 'string', '2025-07-27 10:28:25');"
mysql -u "$DB_USER" -p"$MYSQL_PASSWORD" "$DB_NAME" -e "$SQL_INSERT1" > /dev/null 2>&1

SQL_INSERT2="INSERT INTO \`app_settings\` (\`id\`, \`setting_key\`, \`setting_value\`, \`type\`, \`updated_at\`) VALUES
(2, 'maximum_backup', '100', 'integer', '2025-07-27 10:29:31');"

mysql -u "$DB_USER" -p"$MYSQL_PASSWORD" "$DB_NAME" -e "$SQL_INSERT2" > /dev/null 2>&1

SQL_INSERT3="INSERT INTO \`app_settings\` (\`id\`, \`setting_key\`, \`setting_value\`, \`type\`, \`updated_at\`) VALUES
(3, 'auto_update', '1', 'integer', '2025-08-07 10:29:31');"

mysql -u "$DB_USER" -p"$MYSQL_PASSWORD" "$DB_NAME" -e "$SQL_INSERT3" > /dev/null 2>&1


SQL_INSERT_s3="INSERT INTO \`app_settings\` (\`id\`, \`setting_key\`, \`setting_value\`, \`type\`, \`updated_at\`) VALUES
(4, 'api', '1', 'integer', '2025-08-13 10:29:31');"

mysql -u "$DB_USER" -p"$MYSQL_PASSWORD" "$DB_NAME" -e "$SQL_INSERT_s3" > /dev/null 2>&1

SQL6="ALTER TABLE \`user_settings\` ADD \`maximum_backup\` INT(11) NULL DEFAULT '100' AFTER \`userid\`;"
mysql -u "$DB_USER" -p"$MYSQL_PASSWORD" "$DB_NAME" -e "$SQL6" > /dev/null 2>&1 




SQL_INSERT4="
CREATE TABLE IF NOT EXISTS \`blocked_filter_ip\` (
  \`id\` int(10) UNSIGNED NOT NULL AUTO_INCREMENT,
  \`ip_address\` varchar(45) NOT NULL,
  \`first_detected\` datetime NOT NULL DEFAULT current_timestamp(),
  \`last_detected\` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  \`attempts\` int(11) NOT NULL DEFAULT 0,
  \`first_attempt_time\` datetime DEFAULT NULL,
  \`temp_block_count\` int(11) DEFAULT 0,
  PRIMARY KEY (\`id\`),
  UNIQUE KEY \`ip_unique\` (\`ip_address\`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"

mysql -u "$DB_USER" -p"$MYSQL_PASSWORD" "$DB_NAME" -e "$SQL_INSERT4" > /dev/null 2>&1

SQL_INSERT5="
CREATE TABLE IF NOT EXISTS \`blocked_ip\` (
  \`id\` int(10) UNSIGNED NOT NULL AUTO_INCREMENT,
  \`ip_address\` varchar(45) NOT NULL,
  \`block_type\` varchar(50) DEFAULT NULL,
  \`first_detected\` datetime NOT NULL DEFAULT current_timestamp(),
  \`last_detected\` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  \`attempts\` int(11) NOT NULL DEFAULT 0,
  \`temp_block_expires\` datetime DEFAULT NULL,
  \`temp_block_count\` int(11) NOT NULL DEFAULT 0,
  \`first_attempt_time\` datetime DEFAULT NULL,
  \`type\` varchar(500) DEFAULT NULL,
  PRIMARY KEY (\`id\`),
  UNIQUE KEY \`ip_unique\` (\`ip_address\`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"

mysql -u "$DB_USER" -p"$MYSQL_PASSWORD" "$DB_NAME" -e "$SQL_INSERT5" > /dev/null 2>&1


SQL_INSERT6="
CREATE TABLE IF NOT EXISTS sso_tokens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,                    -- Store WHMCS or app user ID
    token VARCHAR(500) NOT NULL UNIQUE,       -- Secure token value
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id)
);
 ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"

mysql -u "$DB_USER" -p"$MYSQL_PASSWORD" "$DB_NAME" -e "$SQL_INSERT6" > /dev/null 2>&1

SQL_INSERT7="
CREATE TABLE IF NOT EXISTS apps (
  id INT(11) NOT NULL AUTO_INCREMENT,
  userid INT(11) DEFAULT NULL,
  type VARCHAR(100) DEFAULT NULL,
  domain_id INT(11) DEFAULT NULL,
  path VARCHAR(255) DEFAULT NULL,
  version VARCHAR(50) DEFAULT NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB;
"
mysql -u "$DB_USER" -p"$MYSQL_PASSWORD" "$DB_NAME" -e "$SQL_INSERT7"


SQL23="ALTER TABLE \`apps\` ADD \`startup_file\` VARCHAR(255) NULL DEFAULT Null AFTER \`version\`;"
mysql -u "$DB_USER" -p"$MYSQL_PASSWORD" "$DB_NAME" -e "$SQL23" > /dev/null 2>&1 

SQL24="ALTER TABLE \`user_settings\` ADD \`secret\` VARCHAR(255) NULL DEFAULT Null AFTER \`maximum_backup\`;"
mysql -u "$DB_USER" -p"$MYSQL_PASSWORD" "$DB_NAME" -e "$SQL24" > /dev/null 2>&1 

SQL25="
DELETE FROM user_settings
WHERE id NOT IN (
    SELECT keep_id FROM (

        SELECT MIN(id) AS keep_id
        FROM user_settings
        WHERE secret IS NOT NULL
        GROUP BY userid

        UNION

        SELECT MIN(id) AS keep_id
        FROM user_settings
        GROUP BY userid
        HAVING SUM(secret IS NOT NULL) = 0

    ) AS t
);
"

mysql -u "$DB_USER" -p"$MYSQL_PASSWORD" "$DB_NAME" -e "$SQL25" > /dev/null 2>&1


SQL26="
ALTER TABLE user_settings
ADD UNIQUE INDEX uniq_userid (userid);
"

mysql -u "$DB_USER" -p"$MYSQL_PASSWORD" "$DB_NAME" -e "$SQL26" > /dev/null 2>&1

mysql -u "$DB_USER" -p"$MYSQL_PASSWORD" "$DB_NAME" -e "ALTER TABLE domains ADD COLUMN catalog VARCHAR(40) DEFAULT NULL;" > /dev/null 2>&1

SQL_INSERT5="INSERT INTO \`app_settings\` (\`id\`, \`setting_key\`, \`setting_value\`, \`type\`, \`updated_at\`) VALUES
(5, 'auto_restart_litespeed', '1', 'integer', '2026-03-01 10:29:31');"

mysql -u "$DB_USER" -p"$MYSQL_PASSWORD" "$DB_NAME" -e "$SQL_INSERT5" > /dev/null 2>&1

SQL_INSERT21="INSERT INTO \`app_settings\` (\`id\`, \`setting_key\`, \`setting_value\`, \`type\`, \`updated_at\`) VALUES
(7, 'hour_maximum_backup', '24', 'integer', '2025-07-27 10:29:31'),
(8, 'day_maximum_backup', '100', 'integer', '2025-07-27 10:29:31'),
(9, 'week_maximum_backup', '50', 'integer', '2025-07-27 10:29:31'),
(10, 'month_maximum_backup', '12', 'integer', '2025-07-27 10:29:31');"

mysql -u "$DB_USER" -p"$MYSQL_PASSWORD" "$DB_NAME" -e "$SQL_INSERT21" > /dev/null 2>&1

SQL66="ALTER TABLE \`user_settings\`
ADD \`hour_maximum_backup\` INT(11) NULL DEFAULT 24 AFTER \`userid\`,
ADD \`day_maximum_backup\` INT(11) NULL DEFAULT 100,
ADD \`week_maximum_backup\` INT(11) NULL DEFAULT 50,
ADD \`month_maximum_backup\` INT(11) NULL DEFAULT 12;"
mysql -u "$DB_USER" -p"$MYSQL_PASSWORD" "$DB_NAME" -e "$SQL66" > /dev/null 2>&1