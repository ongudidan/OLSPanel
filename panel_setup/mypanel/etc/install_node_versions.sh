#!/bin/bash
set -e

BASE_DIR="/usr/local/olspanel/bin/nodejs"

# Install NVM if not installed
if [ ! -d "$HOME/.nvm" ]; then
    echo "[INFO] Installing NVM..."
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
fi

# Load NVM
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

show_versions() {
    echo "[INFO] Fetching available Node.js versions..."
    nvm ls-remote | awk '{print $1}' | grep -E '^v[0-9]+' | tail -n +1
}

install_version() {
    VERSION=$1
    if [ -z "$VERSION" ]; then
        echo "[ERROR] No version specified."
        echo "Usage: $0 install <version>"
        exit 1
    fi

    echo "[INFO] Checking available versions..."
    AVAILABLE=$(nvm ls-remote | awk '{print $1}' | grep -E '^v[0-9]+' | sed 's/^v//')

    # If only major given, pick latest patch
    if [[ "$VERSION" =~ ^[0-9]+$ ]]; then
        MATCH=$(echo "$AVAILABLE" | grep -E "^$VERSION\." | sort -V | tail -1)
    else
        MATCH=$(echo "$AVAILABLE" | grep -x "$VERSION")
    fi

    if [ -z "$MATCH" ]; then
        echo "[ERROR] Version $VERSION not found."
        exit 1
    fi

    echo "[INFO] Installing Node.js v$MATCH ..."
    nvm install "$MATCH"

    NODE_SRC="$NVM_DIR/versions/node/v$MATCH"
    NODE_MAJOR=$( "$NODE_SRC/bin/node" -v | sed 's/v\([0-9][0-9]*\).*/\1/' )

    TARGET_DIR="$BASE_DIR/$NODE_MAJOR"

    echo "[INFO] Setting up $TARGET_DIR ..."
    sudo rm -rf "$TARGET_DIR"
    sudo mkdir -p "$TARGET_DIR"
    sudo cp -a "$NODE_SRC"/* "$TARGET_DIR/"

    echo "[SUCCESS] Node.js v$MATCH installed under $TARGET_DIR"
    echo "Usage:"
    echo "  $TARGET_DIR/bin/node -v"
    echo "  $TARGET_DIR/bin/npm -v"
}

# -------- Main --------
CMD=$1
shift || true

case "$CMD" in
    list)
        show_versions
        ;;
    install)
        install_version "$1"
        ;;
    *)
        echo "Usage: $0 {list|install <version>}"
        ;;
esac
