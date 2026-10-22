#!/usr/bin/env bash
# OLSPanel Custom Update Packaging Script

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UPDATES_DIR="${PROJECT_ROOT}/panel_updates"
BUILD_ZIP="${UPDATES_DIR}/panel_setup.zip"

echo "📦 Packaging Custom OLSPanel Update & Plugins..."

mkdir -p "${UPDATES_DIR}"
mkdir -p "${PROJECT_ROOT}/plugin"

# Compile Tailwind CSS bundle
if command -v npx &> /dev/null && [ -d "${PROJECT_ROOT}/panel_setup/mypanel" ]; then
    echo "🎨 Compiling Tailwind CSS..."
    (cd "${PROJECT_ROOT}/panel_setup/mypanel" && npx -y tailwindcss@3.4.17 -i ./media/css/tailwind-input.css -o ./media/css/tailwind.min.css --minify)
fi

# Build panel_setup.zip and plugin zip files using Python3
python3 - <<EOF
import zipfile, os

base_dir = "${PROJECT_ROOT}"

# 1. Create plugin/ufw.zip
ufw_zip_path = os.path.join(base_dir, "plugin", "ufw.zip")
with zipfile.ZipFile(ufw_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    extra_ufw = os.path.join(base_dir, "extra", "ufw")
    if os.path.exists(extra_ufw):
        for root, dirs, files in os.walk(extra_ufw):
            rel_to_extra_ufw = os.path.relpath(root, extra_ufw)
            if rel_to_extra_ufw.startswith("config"):
                continue
            for file in files:
                full_p = os.path.join(root, file)
                arc_p = os.path.join("ufw", os.path.relpath(full_p, extra_ufw))
                zf.write(full_p, arc_p)
        print("✅ Rebuilt plugin/ufw.zip")

# 2. Create plugin/config_ufw.zip
config_zip_path = os.path.join(base_dir, "plugin", "config_ufw.zip")
with zipfile.ZipFile(config_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    config_dir = os.path.join(base_dir, "extra", "ufw", "config")
    if os.path.exists(config_dir):
        for root, dirs, files in os.walk(config_dir):
            for file in files:
                full_p = os.path.join(root, file)
                arc_p = os.path.join("config", os.path.relpath(full_p, config_dir))
                zf.write(full_p, arc_p)
        print("✅ Rebuilt plugin/config_ufw.zip")

# 3. Create panel_updates/panel_setup.zip
panel_zip_path = os.path.join(base_dir, "panel_updates", "panel_setup.zip")
mypanel_dir = os.path.join(base_dir, "panel_setup", "mypanel")
if not os.path.exists(mypanel_dir):
    mypanel_dir = os.path.join(base_dir, "mypanel")

ignored_names = {
    "update", "license.key", "mysqlPassword", "dbPassword", 
    "ip", "time.zone", "conf.ini", "db.sqlite3", "osName", "osVersion"
}

def should_ignore(filename, rel_dir):
    if filename.endswith(".pyc") or "__pycache__" in rel_dir:
        return True
    if filename in ignored_names:
        return True
    if filename.startswith("phpmyadmin_") or filename.startswith("_"):
        return True
    return False

if os.path.exists(mypanel_dir):
    with zipfile.ZipFile(panel_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(mypanel_dir):
            for file in files:
                if should_ignore(file, root):
                    continue
                full_p = os.path.join(root, file)
                arc_p = os.path.join("mypanel", os.path.relpath(full_p, mypanel_dir))
                zf.write(full_p, arc_p)
    print("✅ Created panel_updates/panel_setup.zip successfully (sensitive files excluded)!")

    # Synchronize version.txt with mypanel/etc/version
    ver_file = os.path.join(mypanel_dir, "etc", "version")
    if os.path.exists(ver_file):
        with open(ver_file, "r") as vf:
            ver = vf.read().strip()
        ver_txt = os.path.join(base_dir, "panel_updates", "version.txt")
        with open(ver_txt, "w") as out_vf:
            out_vf.write(f"{ver}\n")
        print(f"✅ Synchronized panel_updates/version.txt with version {ver}")
else:
    print("❌ Error: Panel source directory 'mypanel' not found.")

# 4. Create root panel_setup.zip (used for full fresh installations)
root_panel_zip = os.path.join(base_dir, "panel_setup.zip")
panel_setup_dir = os.path.join(base_dir, "panel_setup")
if os.path.exists(panel_setup_dir):
    with zipfile.ZipFile(root_panel_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(panel_setup_dir):
            for file in files:
                if should_ignore(file, root):
                    continue
                full_p = os.path.join(root, file)
                arc_p = os.path.relpath(full_p, panel_setup_dir)
                zf.write(full_p, arc_p)
    print("✅ Created root panel_setup.zip successfully!")
EOF

echo "🎉 Build Complete. Distribution archives are up to date."
