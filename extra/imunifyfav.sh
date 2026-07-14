#!/bin/bash
HOME_PATH_FILE="/etc/olspanel/base_dir"
if [ -f "$HOME_PATH_FILE" ]; then
    # Read value from file
    PROJECT_DIR="$(cat "$HOME_PATH_FILE")"
else
    # Extract from systemd service
    PROJECT_DIR="/usr/local/lsws/Example/html/mypanel"
fi



create_imunify_integration_conf() {
    local conf_dir="/etc/sysconfig/imunify360"
    local conf_file="$conf_dir/integration.conf"

    # Create directory if it doesn't exist
    if [ ! -d "$conf_dir" ]; then
        mkdir -p "$conf_dir"
        echo "Created directory: $conf_dir"
    fi

    # Write the configuration
    cat > "$conf_file" <<EOL
[paths]
ui_path = $PROJECT_DIR/3rdparty/imunifyfav
ui_path_owner = nobody:nogroup
EOL

    echo "Created config file: $conf_file"
}


create_imunifyfav_conf() {
    local conf_dir="$PROJECT_DIR/plugin"
    local conf_file="$conf_dir/imunifyfav.conf"

    # Create directory if it doesn't exist
    if [ ! -d "$conf_dir" ]; then
        mkdir -p "$conf_dir"
        echo "Created directory: $conf_dir"
    fi

    # Write the configuration
    cat > "$conf_file" <<EOL
# The Displayname.
name=Imunifyav antivirus

# The application's service.
service=both


url=/3rdparty/imunifyfav/auto_index.php
auto_login_url=/3rdparty/imunifyfav/auto_index.php


# System user and group to run process as
user=nobody
group=nogroup

# Features required
features=security

# Media required
icon=/media/icon/imunifyfav.png

sorder=1
target=_blank

# System user and group to run process as second path optional
user2=root
group2=root
path2=auto_index.php
EOL

    echo "Created config file: $conf_file"
}

create_imunify_autologin_php() {
    local php_dir="$PROJECT_DIR/3rdparty/imunifyfav"
    local php_file="$php_dir/auto_index.php"

    # Create directory if it doesn't exist
    if [ ! -d "$php_dir" ]; then
        mkdir -p "$php_dir"
        echo "Created directory: $php_dir"
    fi

    # Write the PHP file
    cat > "$php_file" <<'PHP_EOF'
<?php
// Get the username from the HTTP header
$username = $_SERVER['PANEL_USERNAME'] ?? '';

// Generate token using imunify-antivirus CLI
$token = trim(shell_exec("imunify-antivirus login get --username " . escapeshellarg($username)));

// Redirect to the frontend URL with the token
header("Location: /3rdparty/imunifyfav/#/login?token=" . urlencode($token));
exit;
PHP_EOF

    echo "Created PHP auto-login file: $php_file"
}

# Run the function



# Run the function
create_imunify_integration_conf


wget https://repo.imunify360.cloudlinux.com/defence360/imav-deploy.sh -O imav-deploy.sh
bash imav-deploy.sh

imunify-antivirus feature-management enable --feature av
imunify-antivirus config update '{"PERMISSIONS": {"allow_malware_scan": true}}'

create_imunifyfav_conf
create_imunify_autologin_php
