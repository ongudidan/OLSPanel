#!/bin/bash

# Function to wait for apt lock to be released
wait_for_apt_lock() {
    echo "Checking for apt package manager lock..."
    local count=0
    while fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1 || fuser /var/lib/apt/lists/lock >/dev/null 2>&1 || fuser /var/lib/dpkg/lock >/dev/null 2>&1; do
        if [ $count -eq 0 ]; then
            echo "Waiting for other package manager process (like unattended-upgrades) to release the lock..."
        fi
        sleep 5
        count=$((count + 1))
        if [ $count -gt 60 ]; then
            echo "Warning: Waiting for more than 5 minutes. Attempting to force release..."
            break
        fi
    done
}

HOME_PATH_FILE="/etc/olspanel/base_dir"
if [ -f "$HOME_PATH_FILE" ]; then
    # Read value from file
    PROJECT_DIR="$(cat "$HOME_PATH_FILE")"
else
    # Extract from systemd service
    PROJECT_DIR="/usr/local/lsws/Example/html/mypanel"
fi


# Detect OS info
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS_NAME=$ID
    OS_VERSION=${VERSION_ID%%.*}
elif [ -f /etc/centos-release ]; then
    OS_NAME="centos"
    OS_VERSION=$(awk '{print $4}' /etc/centos-release | cut -d. -f1)
fi


run_py() {
    local PYTHON_CMD

    if [[ ("$OS_NAME" == "centos" || "$OS_NAME" == "almalinux") && ("$OS_VERSION" == "7" || "$OS_VERSION" == "8") ]]; then
        PYTHON_CMD="/root/venv/bin/python3.12"
    elif [[ "$OS_NAME" == "ubuntu" && "$OS_VERSION" -ge 24 ]]; then
        PYTHON_CMD="/root/venv/bin/python"
    elif [[ "$OS_NAME" == "ubuntu" && "$OS_VERSION" -lt 24 ]]; then
        PYTHON_CMD=$(which python3)
    else
        PYTHON_CMD="/root/venv/bin/python3"
    fi

    echo "Trying $PYTHON_CMD $PROJECT_DIR/manage.py install_olsapp"
    $PYTHON_CMD $PROJECT_DIR/manage.py install_olsapp
    local STATUS=$?

    if [[ $STATUS -ne 0 ]]; then
        echo "First attempt failed, trying fallback Python interpreters..."

        # Fallback Python interpreters to try if the first fails
        local FALLBACKS=(
            "/usr/bin/python3"
            "$(which python3)"
            "/usr/local/bin/python3"
            "/root/venv/bin/python"
        )

        for alt_python in "${FALLBACKS[@]}"; do
            if [[ -x "$alt_python" ]]; then
                echo "Trying fallback: $alt_python $PROJECT_DIR/manage.py install_olsapp"
                $alt_python $PROJECT_DIR/manage.py install_olsapp
                STATUS=$?
                if [[ $STATUS -eq 0 ]]; then
                    echo "Succeeded with fallback: $alt_python"
                    return 0
                fi
            else
                echo "Fallback interpreter not executable or not found: $alt_python"
            fi
        done

        echo "All fallback attempts failed."
        return 1
    fi
}


create_olsapp_conf() {
    CONF_DIR="/usr/local/olspanel/mypanel/plugin"
    CONF_FILE="$CONF_DIR/olsapp.conf"

    echo "Creating olsapp plugin config..."

    mkdir -p "$CONF_DIR"

    cat > "$CONF_FILE" <<'EOF'
# The Displayname.
name=Olsapp

# The application's service.
service=both

url=/3rdparty/olsapp/index.php 

header[HTTP_AUTOLOGINUSER]=%dbusername%
header[HTTP_AUTOLOGINPASS]=%dbuserpass% 

# System user and group to run process as
user=root
group=root 

# Features required
features=olsapp

# Media  required
icon=/media/icon/olsapp.png 

#short
sorder=99

#hide from display
display_hide = true
EOF

    echo "Config created at: $CONF_FILE"
}

install_olsapp() {
    ZIP_URL="http://127.0.0.1:8000/olsapp/olsapp.zip"

    # If project is default olspanel path
    if [ "$PROJECT_DIR" = "/usr/local/olspanel/mypanel" ]; then
        DEST_DIR="/usr/local/olspanel/mypanel/3rdparty/olsapp"
        ZIP_FILE="/usr/local/olspanel/mypanel/3rdparty/olsapp.zip"
        
    else
        DEST_DIR="${PROJECT_DIR%/*}/olsapp"
        ZIP_FILE="${PROJECT_DIR%/*}/olsapp.zip"
    fi

    echo "Downloading olsapp..."
    wget -O "$ZIP_FILE" "$ZIP_URL" --no-cache --no-cookies

    echo "Extracting olsapp..."
    mkdir -p "$DEST_DIR"
    unzip -o "$ZIP_FILE" -d "$DEST_DIR"
    rm -f "$ZIP_FILE"
if [ "$PROJECT_DIR" = "/usr/local/olspanel/mypanel" ]; then
create_olsapp_conf
#wget -O "$DEST_DIR/core/softpanel.php" "http://127.0.0.1:8000/olsapp/softpanel_for_bin.ph" --no-cache --no-cookies
wget -O "$DEST_DIR/conf.php" "http://127.0.0.1:8000/olsapp/conf_for_bin.ph" --no-cache --no-cookies
chown -R olspanel:olspanel $DEST_DIR
else
chown -R olspanel:olspanel ${PROJECT_DIR%/*}/olsapp
fi
    echo "olsapp installed at: $DEST_DIR"
}



# Run installer
#run_repo
install_olsapp
if [ "$PROJECT_DIR" != "/usr/local/olspanel/mypanel" ]; then
    run_py
else
    echo "Using default olspanel path, skipping run_py"
fi


chown -R olspanel:olspanel /usr/local/lsws/Example/html/olsapp

