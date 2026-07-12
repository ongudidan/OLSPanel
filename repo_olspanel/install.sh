#!/bin/sh

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

echo -e "\nOLS Panel is now starting soon please wait...\n"
# Detect OS version
OUTPUT=$(cat /etc/*release)

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
    echo -e "\nOLS Panel is supported only on Ubuntu 18.04, 20.04, 22.04, 24.04, Debian 11, 12, AlmaLinux 8 , 9 , CentOS Stream 8, 9 and Rocky Linux 8,9 Other OS support coming soon.\n"
    exit 1
fi

echo -e "\nYour OS is $SERVER_OS\n"
# Update system and install required packages


wget -O panel.sh "https://ongudidan.github.io/OLSPanel/repo_owpanel/$SERVER_OS/panel.sh"
wget -O requirements.txt "https://ongudidan.github.io/OLSPanel/repo_owpanel/requirements.txt"

# Ensure the script is executable
chmod +x panel.sh
sed -i 's/\r$//' panel.sh

sh panel.sh
