#!/bin/bash
set -e

# Sanitize Python and package manager environment so child Python processes use their own virtualenvs
unset PYTHONPATH
unset PYTHONHOME
unset VIRTUAL_ENV
export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=a
export UCF_FORCE_CONFFOLD=1

# Ensure any interrupted dpkg processes are configured cleanly first
if command -v dpkg >/dev/null 2>&1; then
    dpkg --configure -a 2>/dev/null || true
fi

# ImunifyAV architecture check (CloudLinux strictly requires x86_64)
ARCH=$(uname -m)
if [ "$ARCH" != "x86_64" ]; then
    echo "❌ Error: ImunifyAV only supports x86_64 architecture. Current server architecture is: $ARCH."
    exit 1
fi

# Detect project directory
HOME_PATH_FILE="/etc/olspanel/base_dir"
if [ -f "$HOME_PATH_FILE" ] && [ -s "$HOME_PATH_FILE" ]; then
    PROJECT_DIR="$(cat "$HOME_PATH_FILE")"
elif [ -d "/usr/local/olspanel/mypanel" ]; then
    PROJECT_DIR="/usr/local/olspanel/mypanel"
elif [ -d "/usr/local/lsws/Example/html/mypanel" ]; then
    PROJECT_DIR="/usr/local/lsws/Example/html/mypanel"
else
    PROJECT_DIR="/usr/local/olspanel/mypanel"
fi

# Detect system group for nobody (nogroup on Debian/Ubuntu, nobody on RHEL/CentOS/AlmaLinux/CloudLinux)
if getent group nogroup >/dev/null 2>&1; then
    PANEL_GROUP="nogroup"
elif getent group nobody >/dev/null 2>&1; then
    PANEL_GROUP="nobody"
else
    PANEL_GROUP="nogroup"
fi

echo "📋 Target project directory: $PROJECT_DIR"
echo "📋 System owner group: nobody:$PANEL_GROUP"

# Step 1: Clean removal of existing/broken Imunify installation if requested or broken
clean_broken_installation() {
    local broken=false

    # Check if packages are partially installed or broken
    if command -v rpm >/dev/null 2>&1; then
        if rpm -qa | grep -Ei 'imunify|defence360' >/dev/null 2>&1; then
            if [ ! -x "/opt/imunify360/venv/bin/python3" ] || ! /opt/imunify360/venv/bin/python3 -c "import defence360agent" >/dev/null 2>&1 || [ ! -f "$PROJECT_DIR/3rdparty/imunifyfav/bin/execute.py" ]; then
                broken=true
            fi
        fi
    elif command -v dpkg-query >/dev/null 2>&1; then
        if dpkg-query -W -f='${binary:Package} ${db:Status-Status}\n' 'imunify*' 2>/dev/null | grep -q 'installed'; then
            if [ ! -x "/opt/imunify360/venv/bin/python3" ] || ! /opt/imunify360/venv/bin/python3 -c "import defence360agent" >/dev/null 2>&1 || [ ! -f "$PROJECT_DIR/3rdparty/imunifyfav/bin/execute.py" ]; then
                broken=true
            fi
        fi
    fi

    # Also clean if --clean or --reinstall flag is passed
    if [ "$1" = "--clean" ] || [ "$1" = "--reinstall" ] || [ "$broken" = true ]; then
        echo "🧹 Removing broken or outdated Imunify packages..."
        if command -v dnf >/dev/null 2>&1; then
            dnf remove 'imunify*' 'defence360*' -y || true
        elif command -v yum >/dev/null 2>&1; then
            yum remove 'imunify*' 'defence360*' -y || true
        elif command -v apt-get >/dev/null 2>&1; then
            DEBIAN_FRONTEND=noninteractive apt-get purge 'imunify*' 'defence360*' -y || true
            DEBIAN_FRONTEND=noninteractive apt-get autoremove -y || true
        fi
        rm -rf /opt/imunify360/venv 2>/dev/null || true
    fi
}

# Run clean removal check
clean_broken_installation "$1"

# Critical fix for CloudLinux compatibility-check.sh:
# If ui_path exists and is non-empty without bin/execute.py, compatibility-check.sh aborts immediately!
if [ ! -f "$PROJECT_DIR/3rdparty/imunifyfav/bin/execute.py" ]; then
    echo "🧹 Ensuring $PROJECT_DIR/3rdparty/imunifyfav is clean for installer..."
    rm -rf "$PROJECT_DIR/3rdparty/imunifyfav"
fi
mkdir -p "$PROJECT_DIR/3rdparty/imunifyfav"

create_imunify_integration_conf() {
    local conf_dir="/etc/sysconfig/imunify360"
    local conf_file="$conf_dir/integration.conf"

    mkdir -p "$conf_dir"

    cat > "$conf_file" <<EOL
[paths]
ui_path = $PROJECT_DIR/3rdparty/imunifyfav
ui_path_owner = nobody:$PANEL_GROUP
EOL

    echo "✅ Created integration config: $conf_file"
}

create_imunifyfav_conf() {
    local conf_dir="$PROJECT_DIR/plugin"
    local conf_file="$conf_dir/imunifyfav.conf"

    mkdir -p "$conf_dir"

    cat > "$conf_file" <<EOL
# The Displayname.
name=Imunifyav antivirus

# The application's service.
service=both

url=/3rdparty/imunifyfav/auto_index.php
auto_login_url=/3rdparty/imunifyfav/auto_index.php

# System user and group to run process as
user=nobody
group=$PANEL_GROUP

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

header[PANEL_USERNAME]=%username%
EOL

    echo "✅ Created plugin config: $conf_file"
}

create_imunify_autologin_php() {
    local php_dir="$PROJECT_DIR/3rdparty/imunifyfav"
    local php_file="$php_dir/auto_index.php"

    mkdir -p "$php_dir"

    cat > "$php_file" <<'PHP_EOF'
<?php
// Get the username from the HTTP header
$username = $_SERVER['PANEL_USERNAME'] ?? '';
if (empty($username) || $username === 'admin') {
    $username = 'root';
}

$token = '';
$cmd = "imunify-antivirus login get --username " . escapeshellarg($username) . " 2>/dev/null";
$output = trim((string)shell_exec($cmd));

// Fallback to root if user-specific token generation failed
if (empty($output) && $username !== 'root') {
    $cmd = "imunify-antivirus login get --username root 2>/dev/null";
    $output = trim((string)shell_exec($cmd));
}

// Validate token format (JWT string without spaces or newlines)
if (!empty($output) && strpos($output, ' ') === false && strpos($output, "\n") === false) {
    $token = $output;
}

if (!empty($token)) {
    header("Location: /3rdparty/imunifyfav/#/login?token=" . urlencode($token));
} else {
    header("Location: /3rdparty/imunifyfav/");
}
exit;
PHP_EOF

    echo "✅ Created PHP auto-login file: $php_file"
}

# 1. Create integration config before deploy
create_imunify_integration_conf

# 2. Download and execute official ImunifyAV installer
echo "📥 Downloading official ImunifyAV deployment script..."
wget -q https://repo.imunify360.cloudlinux.com/defence360/imav-deploy.sh -O /tmp/imav-deploy.sh
chmod +x /tmp/imav-deploy.sh

echo "🚀 Deploying ImunifyAV (non-interactive mode)..."
env -u PYTHONPATH -u PYTHONHOME -u VIRTUAL_ENV DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a bash /tmp/imav-deploy.sh -y
rm -f /tmp/imav-deploy.sh

# 3. Configure features and permissions
if command -v imunify-antivirus >/dev/null 2>&1; then
    imunify-antivirus feature-management enable --feature av 2>/dev/null || true
    imunify-antivirus config update '{"PERMISSIONS": {"allow_malware_scan": true}}' 2>/dev/null || true
fi

# 4. Create autologin script and plugin config
create_imunify_autologin_php
create_imunifyfav_conf

# 5. Fix permissions
if [ -f "$PROJECT_DIR/3rdparty/imunifyfav/bin/execute.py" ]; then
    chmod +x "$PROJECT_DIR/3rdparty/imunifyfav/bin/execute.py"
fi
chown -R nobody:$PANEL_GROUP "$PROJECT_DIR/3rdparty/imunifyfav" 2>/dev/null || true
chmod 755 "$PROJECT_DIR/3rdparty/imunifyfav" 2>/dev/null || true
if [ -f "$PROJECT_DIR/3rdparty/imunifyfav/auto_index.php" ]; then
    chmod 644 "$PROJECT_DIR/3rdparty/imunifyfav/auto_index.php" 2>/dev/null || true
fi

# 6. Verify installation
echo "🔍 Verifying installation..."
if [ -x "/opt/imunify360/venv/bin/python3" ]; then
    DEFENCE_PATH=$(/opt/imunify360/venv/bin/python3 -c "import defence360agent; print(defence360agent.__file__)" 2>/dev/null || true)
    if [ -n "$DEFENCE_PATH" ]; then
        echo "✅ defence360agent verified: $DEFENCE_PATH"
    else
        echo "⚠️ Warning: defence360agent could not be imported in /opt/imunify360/venv"
    fi
else
    echo "⚠️ Warning: /opt/imunify360/venv/bin/python3 not found."
fi

if [ -f "$PROJECT_DIR/3rdparty/imunifyfav/bin/execute.py" ]; then
    echo "✅ Imunify FAV UI successfully installed in: $PROJECT_DIR/3rdparty/imunifyfav"
else
    echo "⚠️ Warning: Imunify FAV UI execute.py not found in: $PROJECT_DIR/3rdparty/imunifyfav"
fi

echo "🎉 ImunifyAV installation process completed!"
