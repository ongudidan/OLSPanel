#!/bin/bash
# Generate self-signed SSL certificate for OpenLiteSpeed if not exists

DOMAIN="chandpurtelecom.xyz"
SSL_DIR="/etc/letsencrypt/live/$DOMAIN"

# Ensure target directory exists
if [ ! -d "$SSL_DIR" ]; then
    echo "Creating SSL directory: $SSL_DIR"
    mkdir -p "$SSL_DIR"
fi

# Check if SSL cert or key already exists
if [ ! -f "$SSL_DIR/privkey.pem" ] || [ ! -f "$SSL_DIR/fullchain.pem" ]; then
    echo "No SSL cert found — generating new self-signed SSL for $DOMAIN..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$SSL_DIR/privkey.pem" \
        -out "$SSL_DIR/fullchain.pem" \
        -subj "/CN=$DOMAIN"
else
    echo "SSL cert already exists at $SSL_DIR — skipping generation."
fi

# Set permissions
chmod 600 "$SSL_DIR/privkey.pem"
chmod 644 "$SSL_DIR/fullchain.pem"
chown root:root "$SSL_DIR/privkey.pem" "$SSL_DIR/fullchain.pem"

# Restart OpenLiteSpeed
echo "Restarting OpenLiteSpeed..."
systemctl restart openlitespeed

echo "✅ SSL setup complete for $DOMAIN"
