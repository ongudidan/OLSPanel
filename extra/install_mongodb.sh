#!/bin/bash
#
# MongoDB 7.0 Secure Installer + Admin User Creator
# Works on Ubuntu, Debian, AlmaLinux, Rocky, CentOS Stream
# Author: HostBD Free
#
HOME_PATH_FILE="/etc/olspanel/base_dir"
if [ -f "$HOME_PATH_FILE" ]; then
    # Read value from file
    PROJECT_DIR="$(cat "$HOME_PATH_FILE")"
else
    # Extract from systemd service
    PROJECT_DIR="/usr/local/lsws/Example/html/mypanel"
fi

iphp_install() {
   curl -sSL https://olspanel.com/extra/mongodb_ext.sh?$(date +%s) | sed 's/\r$//' | bash
}

# === Parameters ===
ADMIN_USER="${1:-admin}"
ADMIN_PASS="${2:-admin123}"

if [ -z "$ADMIN_PASS" ]; then
    echo "Usage: sudo bash install_mongodb_secure_admin.sh <username> <password>"
    echo "Example: sudo bash install_mongodb_secure_admin.sh admin MyStrongPass123!"
    exit 1
fi

echo "=== MongoDB 7.0 Secure Installer ==="
echo "Admin user: $ADMIN_USER"
echo "Admin password: [HIDDEN]"
echo

# === Detect OS ===
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VERSION_ID=${VERSION_ID%%.*}
else
    echo "❌ Cannot detect OS version."
    exit 1
fi

echo "Detected OS: $OS $VERSION_ID"

# === Dependencies ===
if ! command -v curl &>/dev/null; then
    echo "Installing curl..."
    sudo apt-get install -y curl || sudo yum install -y curl
fi

if ! command -v gpg &>/dev/null; then
    echo "Installing gnupg..."
    sudo apt-get install -y gnupg || sudo yum install -y gnupg
fi

# === Repository Setup ===
if [[ "$OS" =~ ^(ubuntu)$ ]]; then
    echo "Setting up MongoDB repository..."

    sudo mkdir -p /usr/share/keyrings

    case "$VERSION_ID" in
        20) 
            CODENAME=focal
            KEY_URL="https://pgp.mongodb.com/server-7.0.asc"
            KEY_FILE="/usr/share/keyrings/mongodb-server-7.0.gpg"
            REPO="deb [arch=amd64,arm64 signed-by=$KEY_FILE] https://repo.mongodb.org/apt/ubuntu $CODENAME/mongodb-org/7.0 multiverse"
        ;;
        22) 
            CODENAME=jammy
            KEY_URL="https://pgp.mongodb.com/server-7.0.asc"
            KEY_FILE="/usr/share/keyrings/mongodb-server-7.0.gpg"
            REPO="deb [arch=amd64,arm64 signed-by=$KEY_FILE] https://repo.mongodb.org/apt/ubuntu $CODENAME/mongodb-org/7.0 multiverse"
        ;;
        24) 
            CODENAME=noble
            KEY_URL="https://www.mongodb.org/static/pgp/server-8.0.asc"
            KEY_FILE="/usr/share/keyrings/mongodb-server-8.0.gpg"
            REPO="deb [ arch=amd64,arm64 signed-by=$KEY_FILE ] https://repo.mongodb.org/apt/ubuntu $CODENAME/mongodb-org/8.0 multiverse"
        ;;
        *) 
            CODENAME=jammy
            KEY_URL="https://pgp.mongodb.com/server-7.0.asc"
            KEY_FILE="/usr/share/keyrings/mongodb-server-7.0.gpg"
            REPO="deb [arch=amd64,arm64 signed-by=$KEY_FILE] https://repo.mongodb.org/apt/ubuntu $CODENAME/mongodb-org/7.0 multiverse"
        ;;
    esac

    # Import correct key
    curl -fsSL "$KEY_URL" | sudo gpg --yes --batch -o "$KEY_FILE" --dearmor

    # Write repo file
    echo "$REPO" | sudo tee /etc/apt/sources.list.d/mongodb-org.list >/dev/null

    sudo apt update -y
    sudo apt install -y mongodb-org mongodb-mongosh

elif [[ "$OS" == "debian" ]]; then
    echo "Detected OS: Debian $VERSION_ID"
    sudo mkdir -p /usr/share/keyrings
    curl -fsSL https://pgp.mongodb.com/server-7.0.asc | \
    sudo gpg --yes --batch -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor

    case "$VERSION_ID" in
        11) CODENAME=bullseye ;;
        12) CODENAME=bookworm ;;
        *)  CODENAME=bookworm ;;
    esac

    echo "Setting up MongoDB repository for Debian ($CODENAME)..."
    echo "deb [arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg] \
https://repo.mongodb.org/apt/debian $CODENAME/mongodb-org/7.0 main" | \
    sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list >/dev/null

    sudo apt update -y
    sudo apt install -y mongodb-org mongodb-mongosh

elif [[ "$OS" =~ ^(almalinux|rocky|centos)$ ]]; then
    echo "Setting up MongoDB repository..."

    cat <<EOF | sudo tee /etc/yum.repos.d/mongodb-org-7.0.repo >/dev/null
[mongodb-org-7.0]
name=MongoDB Repository
baseurl=https://repo.mongodb.org/yum/redhat/\$releasever/mongodb-org/7.0/x86_64/
gpgcheck=1
enabled=1
gpgkey=https://pgp.mongodb.com/server-7.0.asc
EOF

    sudo yum install -y mongodb-org mongodb-mongosh

else
    echo "❌ Unsupported OS: $OS"
    exit 1
fi


# === Start MongoDB ===
sudo systemctl enable mongod
sudo systemctl enable mongod
sudo systemctl restart mongod || sudo systemctl start mongod

sleep 3
# === Create Admin User ===
echo "👤 Creating admin user..."
mongosh <<EOF
use admin
if (!db.getUser("$ADMIN_USER")) {
  db.createUser({
    user: "$ADMIN_USER",
    pwd: "$ADMIN_PASS",
    roles: ["root"]
  });
  print("✅ Admin user created successfully!");
} else {
  print("ℹ️ Admin user '$ADMIN_USER' already exists.");
}
EOF


sudo systemctl restart mongod
# === Secure Configuration (Modify Existing File) ===
CONF="/etc/mongod.conf"
echo "🔧 Securing MongoDB configuration: $CONF"

if [ ! -f "$CONF" ]; then
    echo "❌ $CONF not found!"
    exit 1
fi

# Clean old commented/duplicate lines
sudo sed -i 's/^[#[:space:]]*security:.*$/security:/g' "$CONF"
sudo sed -i '/^[#[:space:]]*authorization:/d' "$CONF"
sudo sed -i 's/^[#[:space:]]*setParameter:.*$/setParameter:/g' "$CONF"
sudo sed -i '/^[#[:space:]]*enableLocalhostAuthBypass:/d' "$CONF"

# Add or update security block
if ! grep -q "^security:" "$CONF"; then
    echo -e "\nsecurity:\n  authorization: enabled" | sudo tee -a "$CONF" >/dev/null
else
    sudo awk '
    /^security:/ { print; print "  authorization: enabled"; next }
    { print }
    ' "$CONF" | sudo tee "$CONF.tmp" >/dev/null && sudo mv "$CONF.tmp" "$CONF"
fi

# Add or update setParameter block
if grep -q "^setParameter:" "$CONF"; then
    sudo grep -q "enableLocalhostAuthBypass" "$CONF" || \
        sudo sed -i '/^setParameter:/a\  enableLocalhostAuthBypass: false' "$CONF"
   
else
    echo "" | sudo tee -a "$CONF" >/dev/null
    echo "setParameter:" | sudo tee -a "$CONF" >/dev/null
    echo "  enableLocalhostAuthBypass: false" | sudo tee -a "$CONF" >/dev/null
    
fi

echo "✅ MongoDB configuration secured successfully."
sudo systemctl restart mongod




MODULE_DIR="$PROJECT_DIR/modules"
sudo mkdir -p "$MODULE_DIR"
sudo wget -O "$MODULE_DIR/mongodb.zip" "https://olspanel.com/plugin/mongodb_module.zip?$(date +%s)"
sudo unzip -o "$MODULE_DIR/mongodb.zip" -d "$MODULE_DIR"
sudo rm -f "$MODULE_DIR/mongodb.zip"

iphp_install
# === Install PHP MongoDB Extension and Plugin ===
phpmymongo="$PROJECT_DIR/3rdparty/phpmymongo"
if [ ! -d "$phpmymongo" ]; then
    echo "📦 Installing phpmymongo plugin..."
    install_cp_plugin https://olspanel.com/plugin/phpmymongo.zip
fi
echo "🎉 MongoDB installation and configuration complete!"
echo "Admin user: $ADMIN_USER"
echo "Admin password: $ADMIN_PASS"
sudo systemctl restart cp
