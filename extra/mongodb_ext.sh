#!/bin/bash


echo "==============================="
echo " LSHP82 MongoDB Extension Setup"
echo "==============================="

PHP_BIN="/usr/local/lsws/lsphp82/bin/php"
PECL_BIN="/usr/local/lsws/lsphp82/bin/pecl"
INI_DIR="/usr/local/lsws/lsphp82/etc/php.d"
INI_FILE="$INI_DIR/20-mongodb.ini"

# -------------------------------
# Check PHP binary
# -------------------------------
if [ ! -f "$PHP_BIN" ]; then
    echo "❌ LSHP82 PHP not found"
    exit 1
fi

echo "✅ PHP found"

# -------------------------------
# Detect package manager
# -------------------------------
if command -v dnf >/dev/null 2>&1; then
    PKG="dnf"
elif command -v yum >/dev/null 2>&1; then
    PKG="yum"
elif command -v apt >/dev/null 2>&1; then
    PKG="apt"
else
    echo "❌ Unsupported OS"
    exit 1
fi

echo "📌 Using: $PKG"

# -------------------------------
# Install dependencies
# -------------------------------
echo "📦 Installing dependencies..."

if [ "$PKG" = "dnf" ] || [ "$PKG" = "yum" ]; then
    $PKG -y install epel-release || true
    $PKG -y groupinstall "Development Tools" || true
    $PKG -y install gcc make autoconf glibc-devel pkgconfig re2c curl
	$PKG install lsphp82-devel -y
else
    apt update -y
    apt install -y build-essential autoconf pkg-config re2c curl php-pear
	apt install lsphp82-dev lsphp82-pear -y
	
fi

# -------------------------------
# Fix PECL (no go-pear)
# -------------------------------
if [ ! -f "$PECL_BIN" ]; then
    echo "⚠️ PECL not found → fixing..."

    if [ "$PKG" = "dnf" ] || [ "$PKG" = "yum" ]; then
        $PKG install -y lsphp82-pear || true
    fi

    # fallback: manual symlink from system pecl
    if [ ! -f "$PECL_BIN" ] && command -v pecl >/dev/null 2>&1; then
        ln -s $(which pecl) $PECL_BIN
    fi
fi

# final check
if [ ! -f "$PECL_BIN" ]; then
    echo "❌ PECL still missing"
    exit 1
fi

echo "✅ PECL ready"

# -------------------------------
# Update channel
# -------------------------------
$PECL_BIN channel-update pecl.php.net || true

# -------------------------------
# Install MongoDB extension
# -------------------------------
echo "⚙️ Installing mongodb..."

yes '' | $PECL_BIN install mongodb

# -------------------------------
# Enable extension
# -------------------------------
echo "🧩 Enabling extension..."

mkdir -p "$INI_DIR"
echo "extension=mongodb.so" > "$INI_FILE"

# -------------------------------
# Restart LiteSpeed
# -------------------------------
echo "🔄 Restarting LiteSpeed..."

systemctl restart lsws

# -------------------------------
# Verify
# -------------------------------



   # Target PHP ini (system PHP, NOT LSWS)
INI_FILE_PATH="/etc/php/8.2/cgi/php.ini"



echo "🔍 Finding mongodb.so inside LSWS PHP..."

SO_PATH=$(find /usr/local/lsws/lsphp82 -name "mongodb.so" 2>/dev/null | head -n 1)

if [ -z "$SO_PATH" ]; then
    echo "❌ mongodb.so not found"
    exit 1
fi

echo "✅ Found SO file: $SO_PATH"


# -------------------------------
# Add to system php.ini safely
# -------------------------------
if ! grep -q "extension=$SO_PATH" "$INI_FILE_PATH"; then
    echo "" >> "$INI_FILE_PATH"
    echo "extension=$SO_PATH" >> "$INI_FILE_PATH"
    echo "✅ Added extension=$SO_PATH to $INI_FILE_PATH"
else
    echo "ℹ️ Already exists in $INI_FILE_PATH"
fi


echo "==============================="
echo " DONE ✅"
echo "==============================="