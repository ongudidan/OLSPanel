#!/usr/bin/env bash
# OLSPanel Custom Update Packaging Script

# Paths
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UPDATES_DIR="${PROJECT_ROOT}/panel_updates"
BUILD_ZIP="${UPDATES_DIR}/panel_setup.zip"

echo "📦 Packaging Custom OLSPanel Update..."

# Ensure output directory exists
mkdir -p "${UPDATES_DIR}"

# Step 1: Zip the panel code
# The zip root must be 'mypanel/' matching the /usr/local/olspanel/ structure
if [ -d "${PROJECT_ROOT}/panel_setup/mypanel" ]; then
    echo "Using panel source directory: ${PROJECT_ROOT}/panel_setup/mypanel"
    cd "${PROJECT_ROOT}/panel_setup"
    zip -r "${BUILD_ZIP}" mypanel -x "*.pyc" "__pycache__/*" "etc/update" "etc/license.key"
    echo "✅ Created panel_setup.zip successfully!"
elif [ -d "${PROJECT_ROOT}/mypanel" ]; then
    echo "Using panel source directory: ${PROJECT_ROOT}/mypanel"
    cd "${PROJECT_ROOT}"
    zip -r "${BUILD_ZIP}" mypanel -x "*.pyc" "__pycache__/*" "etc/update" "etc/license.key"
    echo "✅ Created panel_setup.zip successfully!"
else
    echo "❌ Error: Panel source directory 'mypanel' not found."
    echo ""
    echo "💡 How to customize and build updates:"
    echo "1. Extract the base panel zip to a folder named 'panel_setup':"
    echo "   mkdir -p panel_setup && unzip olspanel_v3.0.18/panel_setup.zip -d panel_setup"
    echo "2. Make your code modifications inside 'panel_setup/mypanel/'"
    echo "3. Run this script again: ./panel_updates/build_update.sh"
    exit 1
fi

echo "🎉 Build Complete. Copy files in ${UPDATES_DIR} to your update server."
