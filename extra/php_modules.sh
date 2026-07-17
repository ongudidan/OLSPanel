#!/bin/bash
# ----------------------------------------------------
# PHP PECL Global Installer (WHM-style)
# Supports: OpenLiteSpeed lsphpXX, system PHP, etc.
# Usage: php-pecl-global-install <extension> <php_base> <php_ini_file>
# Example: php-pecl-global-install mongodb /usr/local/lsws/lsphp82 /usr/local/lsws/lsphp82/etc/php/8.2/litespeed/php.ini
# ----------------------------------------------------

set -e

EXT_NAME="$1"
PHP_BASE="$2"
PHP_INI_FILE="$3"

if [ -z "$EXT_NAME" ] || [ -z "$PHP_BASE" ] || [ -z "$PHP_INI_FILE" ]; then
    echo "Usage: $0 <extension> <php_base> <php_ini_file>"
    echo "Example: $0 mongodb /usr/local/lsws/lsphp82 /usr/local/lsws/lsphp82/etc/php/8.2/litespeed/php.ini"
    exit 1
fi

PECL_BIN="${PHP_BASE}/bin/pecl"
PHP_BIN="${PHP_BASE}/bin/php"

if [ ! -x "$PEAR_BIN" ]; then
    echo "⚠️  PEAR not found in ${PHP_BASE}/bin — installing..."

    if [[ "$PHP_BASE" == *"/lsphp"* ]]; then
        # Extract version number (e.g. 84 → lsphp84)
        LSPHP_VER=$(basename "$PHP_BASE" | grep -o '[0-9]\+')
        if [ -n "$LSPHP_VER" ]; then
            echo "🟢 Detected LiteSpeed PHP ${LSPHP_VER} — installing lsphp${LSPHP_VER}-pear..."
            if command -v dnf >/dev/null 2>&1; then
                dnf install -y "lsphp${LSPHP_VER}-pear"
            elif command -v yum >/dev/null 2>&1; then
                yum install -y "lsphp${LSPHP_VER}-pear"
            elif command -v apt-get >/dev/null 2>&1; then
                apt-get update -y && apt-get install -y "lsphp${LSPHP_VER}-pear"
            else
                echo "⚠️  No supported package manager found for lsphp${LSPHP_VER}-pear"
                exit 1
            fi
        else
            echo "⚠️  Could not determine LiteSpeed PHP version from ${PHP_BASE}"
            exit 1
        fi
    else
        echo "🟢 Installing system-wide php-pear..."
        if command -v apt-get >/dev/null 2>&1; then
            apt-get update -y && apt-get install -y php-pear
        elif command -v dnf >/dev/null 2>&1; then
            dnf install -y php-pear
        elif command -v yum >/dev/null 2>&1; then
            yum install -y php-pear
        else
            echo "⚠️  No package manager found — manual PEAR install"
            curl -O https://pear.php.net/go-pear.phar
            "${PHP_BIN}" go-pear.phar || {
                echo "❌ Failed to install PEAR manually."
                exit 1
            }
            rm -f go-pear.phar
        fi
    fi

    echo "✅ PEAR installation complete."
fi

if [ ! -x "$PHP_BIN" ]; then
    echo "❌ PHP binary not found at: $PHP_BIN"
    exit 1
fi

EXT_DIR=$(${PHP_BIN} -r "echo ini_get('extension_dir');")

echo "🚀 Installing PECL extension '${EXT_NAME}' using ${PECL_BIN}..."

# Non-interactive install (auto-confirm)
printf "\n" | "$PECL_BIN" install -f "$EXT_NAME" || {
    echo "❌ Failed to install extension: $EXT_NAME"
    exit 1
}

# Ensure php.ini exists
if [ ! -f "$PHP_INI_FILE" ]; then
    echo "⚠️  php.ini not found — creating a new one at ${PHP_INI_FILE}"
    mkdir -p "$(dirname "$PHP_INI_FILE")"
    echo "; Auto-generated php.ini" > "$PHP_INI_FILE"
fi

# Add extension entry if not already present
if ! grep -q "extension=${EXT_NAME}.so" "$PHP_INI_FILE"; then
    echo "extension=${EXT_NAME}.so" >> "$PHP_INI_FILE"
    echo "✅ Added 'extension=${EXT_NAME}.so' to php.ini"
else
    echo "ℹ️  Extension '${EXT_NAME}' already listed in php.ini"
fi

echo "✅ Installation complete for '${EXT_NAME}'"
echo "📁 Installed to: ${EXT_DIR}/${EXT_NAME}.so"
