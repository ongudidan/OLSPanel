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

# Detect Dovecot Version
RAW_VERSION=$(dovecot --version 2>/dev/null | awk '{print $1}' | cut -d'-' -f1)
VERSION=$(echo "$RAW_VERSION" | grep -oE '^[0-9]+(\.[0-9]+)+')

echo "Dovecot version detected: $VERSION (raw: $RAW_VERSION)"

# Check version >= 2.4
if echo "$VERSION" | awk -F. '{exit !($1>2 || ($1==2 && $2>=4))}'; then
    echo "Dovecot 2.4+ detected, applying 2.4 configuration..."

    wget -qO /etc/dovecot/dovecot.conf \
    https://ongudidan.github.io/OLSPanel/extra/dovecot/dovecot.conf

    chmod 644 /etc/dovecot/dovecot.conf

    # Load DB password
    PASSWORD=""
    if [ -f "/root/db_credentials_panel.txt" ]; then
        PASSWORD=$(cat /root/db_credentials_panel.txt | tr -d '[:space:]')
    elif [ -f "/etc/dovecot/dovecot-sql.conf.ext" ]; then
        PASSWORD=$(grep -oP 'password=\K\S+' /etc/dovecot/dovecot-sql.conf.ext)
    elif [ -f "/etc/postfix/mysql-virtual_domains.cf" ]; then
        PASSWORD=$(grep -oP '^password\s*=\s*\K\S+' /etc/postfix/mysql-virtual_domains.cf)
    elif [ -f "/usr/local/olspanel/mypanel/etc/mysqlPassword" ]; then
        PASSWORD=$(cat /usr/local/olspanel/mypanel/etc/mysqlPassword | tr -d '[:space:]')
    elif [ -f "/usr/local/olspanel/mypanel/user_management/settings.py" ]; then
        PASSWORD=$(python3 -c "
try:
    import sys; sys.path.append('/usr/local/olspanel/mypanel')
    from user_management.settings import DATABASES
    print(DATABASES['default']['PASSWORD'])
except:
    pass
" 2>/dev/null)
    fi

    if [ -n "$PASSWORD" ]; then
        sed -i "s|%password%|$PASSWORD|g" /etc/dovecot/dovecot.conf
    fi

    sed -i "s|%version%|$VERSION|g" /etc/dovecot/dovecot.conf

    # Ensure version string in dovecot.conf contains only numbers and dots
    sed -i -E 's/^(dovecot_(config|storage)_version\s*=\s*[0-9]+(\.[0-9]+)+).*/\1/' /etc/dovecot/dovecot.conf

    systemctl restart dovecot

    if systemctl is-active --quiet dovecot; then
        echo "Dovecot started successfully."
    else
        echo "Dovecot failed to start!"
        journalctl -u dovecot -n 50 --no-pager
    fi
else
    echo "Dovecot version is 2.3 or older ($VERSION). Ensuring service is running..."
    systemctl restart dovecot
fi