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

OUTPUT=$(cat /etc/*release)
ARCH=$(uname -m)

if echo "$OUTPUT" | grep -q "Ubuntu 18.04"; then
    SERVER_OS="Ubuntu"
    wait_for_apt_lock && sudo apt update -qq && sudo apt install -y -qq wget curl unzip
elif echo "$OUTPUT" | grep -q "Ubuntu 20.04"; then
    SERVER_OS="Ubuntu"
    wait_for_apt_lock && sudo apt update -qq && sudo apt install -y -qq wget curl unzip
elif echo "$OUTPUT" | grep -q "Ubuntu 22.04"; then
    SERVER_OS="Ubuntu"
    wait_for_apt_lock && sudo apt update -qq && sudo apt install -y -qq wget curl unzip
elif echo "$OUTPUT" | grep -q "Ubuntu 24.04"; then
    SERVER_OS="Ubuntu"
    wait_for_apt_lock && sudo apt update -qq && sudo apt install -y -qq wget curl unzip
elif echo "$OUTPUT" | grep -q "Debian"; then
    SERVER_OS="Debian"
    wait_for_apt_lock && sudo apt update -qq && sudo apt install -y -qq wget curl unzip
elif echo "$OUTPUT" | grep -q "AlmaLinux 8"; then
    SERVER_OS="Centos"
    sudo dnf update -y && sudo dnf install -y wget curl
elif echo "$OUTPUT" | grep -q "AlmaLinux 9"; then
    SERVER_OS="Centos"
    sudo dnf update -y && sudo dnf install -y wget curl
elif echo "$OUTPUT" | grep -q "CentOS Linux 8" || echo "$OUTPUT" | grep -q "CentOS Stream 8"; then
    SERVER_OS="Centos"
    sudo dnf update -y && sudo dnf install -y wget curl
elif echo "$OUTPUT" | grep -q "CentOS Stream 9"; then
    SERVER_OS="Centos"
    sudo dnf update -y && sudo dnf install -y wget curl
elif echo "$OUTPUT" | grep -q "Rocky Linux 8"; then
    SERVER_OS="Centos"
    sudo dnf update -y && sudo dnf install -y wget curl
elif echo "$OUTPUT" | grep -q "Rocky Linux 9"; then
    SERVER_OS="Centos"
    sudo dnf update -y && sudo dnf install -y wget curl
else
    printf "\nUnsupported OS.\n\n"
    exit 1
fi

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

wget -O panel.sh "http://127.0.0.1:8000/repo_owpanel/$SERVER_OS/$PANEL_FILE"
wget -O requirements.txt "http://127.0.0.1:8000/repo_owpanel/requirements.txt"

chmod +x panel.sh
sed -i 's/\r$//' panel.sh

./panel.sh