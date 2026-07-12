#!/bin/bash

# Check if Dovecot is running
if systemctl is-active --quiet dovecot; then
    echo "Dovecot is already running. No action needed."
    exit 0
fi

echo "Dovecot is NOT running. Starting auto-repair process..."

# Get IP
ip=$(hostname -I | awk '{print $1}')

if echo "$ip" | grep -Eq '^(10\.|172\.|192\.168\.)'; then
    public_ip=$(curl -4 -m 10 -s ifconfig.me)
    if [ -n "$public_ip" ]; then
        ip="$public_ip"
    fi
fi

IP="$ip"
echo "Detected IP: $IP"

# Create SSL cert if missing
if [ ! -f "/etc/dovecot/cert.pem" ]; then
    echo "Creating Dovecot SSL certificate..."

    openssl req -new -newkey rsa:2048 -days 3650 -nodes -x509 \
        -subj "/C=US/ST=State/L=City/O=OLS Panel/CN=$IP" \
        -keyout /etc/dovecot/key.pem \
        -out /etc/dovecot/cert.pem

    chmod 600 /etc/dovecot/key.pem
    chmod 644 /etc/dovecot/cert.pem
fi

wget -qO /etc/dovecot/dovecot.conf \
http://127.0.0.1:8000/extra/dovecot/dovecot.conf


# Permissions fix
chmod 644 /etc/dovecot/dovecot.conf

echo "Configs updated successfully."


# Load DB password
if [ -f "/root/db_credentials_panel.txt" ]; then
    PASSWORD=$(cat /root/db_credentials_panel.txt)

    sed -i "s|%password%|$PASSWORD|g" /etc/dovecot/dovecot.conf
fi

# Get full version
VERSION=$(dovecot --version | cut -d'-' -f1)

echo "Dovecot version: $VERSION"

sed -i "s|%version%|$VERSION|g" /etc/dovecot/dovecot.conf

# Check version >= 2.4
if echo "$VERSION" | awk -F. '{exit !($1==2 && $2>=4)}'; then
    echo "Dovecot 2.4+ detected, starting service..."

    systemctl restart dovecot

    if systemctl is-active --quiet dovecot; then
        echo "Dovecot started successfully."
    else
        echo "Dovecot failed to start!"
        journalctl -u dovecot -n 50 --no-pager
    fi
else
    echo "Dovecot version too old: $VERSION"
fi