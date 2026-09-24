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

printf "\nOLS Panel is now starting soon please wait...\n\n"

SERVER_OS=""

# Standard OS Detection via /etc/os-release
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS_ID=$(echo "$ID" | tr '[:upper:]' '[:lower:]')
    OS_ID_LIKE=$(echo "$ID_LIKE" | tr '[:upper:]' '[:lower:]')

    case "$OS_ID" in
        ubuntu)
            SERVER_OS="Ubuntu"
            ;;
        debian)
            SERVER_OS="Debian"
            ;;
        almalinux|rocky|centos|rhel|fedora|ol|amzn|cloudlinux)
            SERVER_OS="Centos"
            ;;
        *)
            if echo "$OS_ID_LIKE" | grep -q "ubuntu"; then
                SERVER_OS="Ubuntu"
            elif echo "$OS_ID_LIKE" | grep -q "debian"; then
                SERVER_OS="Debian"
            elif echo "$OS_ID_LIKE" | grep -qE "rhel|centos|fedora"; then
                SERVER_OS="Centos"
            fi
            ;;
    esac
fi

# Fallback detection if /etc/os-release was missing or inconclusive
if [ -z "$SERVER_OS" ]; then
    OUTPUT=$(cat /etc/*release 2>/dev/null)
    if echo "$OUTPUT" | grep -qi "Ubuntu"; then
        SERVER_OS="Ubuntu"
    elif echo "$OUTPUT" | grep -qi "Debian"; then
        SERVER_OS="Debian"
    elif echo "$OUTPUT" | grep -qiE "AlmaLinux|CentOS|Rocky|Red Hat|Fedora|CloudLinux|Oracle"; then
        SERVER_OS="Centos"
    fi
fi

# Check if OS is supported
if [ -z "$SERVER_OS" ]; then
    printf "\nUnsupported OS.\n\n"
    exit 1
fi

# Update package lists and install prerequisites
if [ "$SERVER_OS" = "Ubuntu" ] || [ "$SERVER_OS" = "Debian" ]; then
    wait_for_apt_lock && sudo apt update -qq && sudo apt install -y -qq wget curl unzip lsb-release
elif [ "$SERVER_OS" = "Centos" ]; then
    sudo dnf update -y && sudo dnf install -y wget curl unzip
fi

ARCH=$(uname -m)

if [[ "$ARCH" == "aarch64" || "$ARCH" == "armv7l" ]]; then
    PANEL_ARCH="arm"
else
    PANEL_ARCH="x86"
fi

if [[ "$SERVER_OS" == "Ubuntu" && "$PANEL_ARCH" == "arm" ]]; then
    PANEL_FILE="panel.sh"
else
    PANEL_FILE="panel.sh"
fi

printf "\nYour OS is %s\n\n" "$SERVER_OS"

wget -O panel.sh "https://ongudidan.github.io/OLSPanel/repo_owpanel/$SERVER_OS/$PANEL_FILE"
wget -O requirements.txt "https://ongudidan.github.io/OLSPanel/repo_owpanel/requirements.txt"

chmod +x panel.sh
sed -i 's/\r$//' panel.sh

./panel.sh