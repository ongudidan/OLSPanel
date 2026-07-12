#!/bin/bash
# OLSPanel Automated Local/Offline Installer

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=================================================="
echo "🚀 Starting OLSPanel Automated Local Installer..."
echo "=================================================="

# Check if port 8000 is already in use
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "⚠️ Warning: Port 8000 is already in use. Assuming local file server is running."
else
    echo "1. Launching local file server on port 8000 in background..."
    python3 -m http.server 8000 > /dev/null 2>&1 &
    SERVER_PID=$!
    
    # Ensure the server is stopped when this script exits
    cleanup() {
        echo ""
        echo "🧹 Stopping local file server (PID: $SERVER_PID)..."
        kill $SERVER_PID 2>/dev/null
    }
    trap cleanup EXIT
    
    # Wait for the local server to start
    sleep 2
fi

echo "2. Executing patched OLSPanel installer..."
chmod +x install.sh
./install.sh

echo "=================================================="
echo "🎉 Automated installer script finished!"
echo "=================================================="
