#!/bin/bash
#
# PostgreSQL Secure Installer + Admin User Creator
# Works on Ubuntu, Debian, AlmaLinux, Rocky, CentOS Stream
# Author: HostBD Free
#

if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS_NAME=$ID
    OS_VERSION=${VERSION_ID%%.*}
elif [ -f /etc/centos-release ]; then
    OS_NAME="centos"
    OS_VERSION=$(awk '{print $4}' /etc/centos-release | cut -d. -f1)
fi

HOME_PATH_FILE="/etc/olspanel/base_dir"
if [ -f "$HOME_PATH_FILE" ]; then
    # Read value from file
    PROJECT_DIR="$(cat "$HOME_PATH_FILE")"
else
    # Extract from systemd service
    PROJECT_DIR="/usr/local/lsws/Example/html/mypanel"
fi




iphp_install() {
    PHP_LIB="/etc/php/8.2"
    SO_NAME="pdo_pgsql.so"
    SO_NAME2="pgsql.so"
    INI_FILE_PATH="/etc/php/8.2/cgi/php.ini"
    MODULE_DIR="$PROJECT_DIR/modules"

    # Ensure target directory exists
    sudo mkdir -p "$MODULE_DIR"

   
    sudo wget -O "$MODULE_DIR/$SO_NAME" "https://olspanel.com/php_ext/8.2/pdo_pgsql.so?$(date +%s)"
    sudo wget -O "$MODULE_DIR/$SO_NAME2" "https://olspanel.com/php_ext/8.2/pgsql.so?$(date +%s)"

    # Verify download
    if [ -f "$MODULE_DIR/$SO_NAME" ]; then
        echo "✅ Downloaded $SO_NAME successfully."

        # Move it into PHP extension directory
        sudo mkdir -p "$PHP_LIB/modules"
        sudo mv "$MODULE_DIR/$SO_NAME" "$PHP_LIB/modules/"

        # Add extension line to php.ini if not already present
        if ! grep -q "extension=$PHP_LIB/modules/$SO_NAME" "$INI_FILE_PATH"; then
            echo -e "\nextension=$PHP_LIB/modules/$SO_NAME" | sudo tee -a "$INI_FILE_PATH" >/dev/null
            echo "✅ Added extension line to $INI_FILE_PATH"
        else
            echo "ℹ️ Extension already listed in $INI_FILE_PATH"
        fi
    else
        echo "❌ Download failed: $MODULE_DIR/$SO_NAME not found."
    fi
    
    
    
 if [ -f "$MODULE_DIR/$SO_NAME2" ]; then
        echo "Downloaded $SO_NAME2 successfully."

        # Move it into PHP extension directory
        sudo mkdir -p "$PHP_LIB/modules"
        sudo mv "$MODULE_DIR/$SO_NAME2" "$PHP_LIB/modules/"

        # Add extension line to php.ini if not already present
        if ! grep -q "extension=$PHP_LIB/modules/$SO_NAME2" "$INI_FILE_PATH"; then
            echo -e "\nextension=$PHP_LIB/modules/$SO_NAME2" | sudo tee -a "$INI_FILE_PATH" >/dev/null
            echo "✅ Added extension line to $INI_FILE_PATH"
        else
            echo "ℹ️ Extension already listed in $INI_FILE_PATH"
        fi
    else
        echo "Download failed: $MODULE_DIR/$SO_NAME2 not found."
    fi   
}

# === Parameters ===
ADMIN_USER="${1:-admin}"
ADMIN_PASS="${2:-admin123}"

if [ -z "$ADMIN_PASS" ]; then
    echo "Usage: sudo bash install_PostgreSQL_secure_admin.sh <username> <password>"
    echo "Example: sudo bash install_PostgreSQL_secure_admin.sh admin MyStrongPass123!"
    exit 1
fi

echo "=== PostgreSQL 7.0 Secure Installer ==="
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

if command -v apt >/dev/null 2>&1; then
  PKG_MANAGER="apt"
elif command -v dnf >/dev/null 2>&1; then
  PKG_MANAGER="dnf"
elif command -v yum >/dev/null 2>&1; then
  PKG_MANAGER="yum"
elif command -v pacman >/dev/null 2>&1; then
  PKG_MANAGER="pacman"
else
  err "Supported package manager not found (apt, dnf, yum, pacman). Exiting."
  exit 1
fi


install_postgres() {
  case "$PKG_MANAGER" in
    apt)
     # log "Updating apt and installing postgresql..."
      apt update -y
      DEBIAN_FRONTEND=noninteractive apt install -y postgresql postgresql-contrib || {
        err "apt installation failed."
        exit 1
      }
      ;;
    dnf|yum)
      #log "Installing postgresql server and contrib packages..."
      # On RHEL-like systems, package name might be 'postgresql-server' or 'postgresql15-server'
      # Try generic ones first.
      if ! $PKG_MANAGER -y install postgresql-server postgresql-contrib postgresql; then
        #log "Generic postgresql packages failed; trying distro packages (may already be present)."
        $PKG_MANAGER -y install postgresql-server || true
      fi
      ;;
    pacman)
      #log "Syncing pacman and installing postgresql..."
      pacman -Syu --noconfirm
      pacman -S --noconfirm postgresql || {
        err "pacman install failed."
        exit 1
      }
      ;;
  esac
}


backup_trust() {
    PGS_CONF=$(find /etc/postgresql /var/lib/pgsql /var/lib/postgresql -type f -name "postgresql.conf" 2>/dev/null | head -n1)
    BACKUPS_CONF="${PGS_CONF}.bk"
if [ ! -f "$BACKUPS_CONF" ]; then
    cp -a "$PGS_CONF" "$BACKUPS_CONF"
   
fi
 sed -i -E 's/^#password_encryption\s*=\s*md5/password_encryption = scram-sha-256/' "$PGS_CONF"


   
    PG_CONF=$(find /etc/postgresql /var/lib/pgsql /var/lib/postgresql -type f -name "pg_hba.conf" 2>/dev/null | head -n1)

   BACKUP_CONF="${PG_CONF}.bk"
    
    
    sudo mv "$PG_CONF" "$BACKUP_CONF"

  
    sudo tee "$PG_CONF" > /dev/null <<'EOF'
# TYPE  DATABASE        USER            ADDRESS                 METHOD

# "local" is for Unix domain socket connections only
local   all             all                                     trust
# IPv4 local connections:
host    all             all             127.0.0.1/32            trust
# IPv6 local connections:
host    all             all             ::1/128                 trust
# Allow replication connections from localhost, by a user with the
# replication privilege.
local   replication     all                                     trust
host    replication     all             127.0.0.1/32            trust
host    replication     all             ::1/128                 trust
EOF

   
    sudo systemctl restart postgresql
   
}

restore_original() {
    
    PG_CONF=$(find /etc/postgresql /var/lib/pgsql /var/lib/postgresql -type f -name "pg_hba.conf" 2>/dev/null | head -n1)

BACKUP_CONF="${PG_CONF}.bk"
    
    if [ -f "$BACKUP_CONF" ]; then
       
        sudo rm -f "$PG_CONF"

       
        sudo mv "$BACKUP_CONF" "$PG_CONF"

        
        sudo systemctl restart postgresql
        
    fi
}



install_postgres
# === Start MongoDB ===
sudo systemctl enable postgresql
sudo systemctl start postgresql
if [[ "$OS_NAME" =~ ^(centos|almalinux|rhel|fedora|rocky|oraclelinux)$ ]]; then
sudo /usr/bin/postgresql-setup --initdb

fi
sudo systemctl restart postgresql || sudo systemctl start postgresql

sleep 3
# === Create Admin User ===
echo "👤 Creating admin user..."

backup_trust


if [ -z "$ADMIN_PASS" ]; then
  echo "Usage: sudo $0 'NewPassword'"
  exit 1
fi

if [ "$(id -u)" -ne 0 ]; then
  echo "Please run this script as root (use sudo)."
  exit 1
fi

if ! id postgres >/dev/null 2>&1; then
  echo "PostgreSQL system user 'postgres' not found. Please install PostgreSQL first."
  exit 1
fi

echo "[+] Setting PostgreSQL superuser password..."

# Run SQL command to set password (quiet mode)
runuser -l postgres -c "psql -v ON_ERROR_STOP=1 -q -c \"ALTER USER postgres WITH PASSWORD '${ADMIN_PASS}';\"" >/dev/null 2>&1

if [ $? -eq 0 ]; then
  echo "[✓] PostgreSQL 'postgres' password set successfully."
else
  echo "[!] Failed to set password — PostgreSQL service might not be running."
  exit 1
fi
restore_original
# Try to locate pg_hba.conf to enable md5 authentication
PG_HBA=$(find /etc/postgresql /var/lib/pgsql /var/lib/postgresql -type f -name "pg_hba.conf" 2>/dev/null | head -n1)

if [ -n "$PG_HBA" ]; then
  echo "[+] Found pg_hba.conf at: $PG_HBA"
  cp -a "$PG_HBA" "${PG_HBA}.bak"
  sed -i 's/peer/scram-sha-256/g' "$PG_HBA"
  sed -i 's/ident/scram-sha-256/g' "$PG_HBA"
  echo "[+] Authentication changed to scram-sha-256"
else
  echo "[!] pg_hba.conf not found!"
fi

sudo systemctl restart postgresql

echo
echo "✅ Done. PostgreSQL superuser password set."
echo "Test with:"
echo "  psql -U postgres -h localhost -W"




echo "✅ PostgreSQL configuration secured successfully."





MODULE_DIR="$PROJECT_DIR/modules"
sudo mkdir -p "$MODULE_DIR"
sudo wget -O "$MODULE_DIR/postgresql.zip" "https://olspanel.com/plugin/postgresql_module.zip?$(date +%s)"
sudo unzip -o "$MODULE_DIR/postgresql.zip" -d "$MODULE_DIR"
sudo rm -f "$MODULE_DIR/postgresql.zip"

iphp_install
# === Install PHP MongoDB Extension and Plugin ===
phppgadmin="$PROJECT_DIR/3rdparty/phppgadmin"
if [ ! -d "$phppgadmin" ]; then
    echo "📦 Installing phppgadmin plugin..."
    install_cp_plugin https://olspanel.com/plugin/phppgadmin.zip
fi
echo "🎉 PostgreSQL installation and configuration complete!"
echo "Admin user: $ADMIN_USER"
echo "Admin password: $ADMIN_PASS"
sudo systemctl restart cp
