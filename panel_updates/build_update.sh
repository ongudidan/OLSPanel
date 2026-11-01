#!/usr/bin/env bash
# OLSPanel Custom Update Packaging Script

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UPDATES_DIR="${PROJECT_ROOT}/panel_updates"
BUILD_ZIP="${UPDATES_DIR}/panel_setup.zip"

echo "📦 Packaging Custom OLSPanel Update & Plugins..."

mkdir -p "${UPDATES_DIR}"
mkdir -p "${PROJECT_ROOT}/plugin"

# Optional: update version if passed as argument (e.g., ./build_update.sh 1.0.2)
NEW_VERSION="$1"
if [ -n "${NEW_VERSION}" ]; then
    echo "🏷️  Setting version to ${NEW_VERSION} in panel_setup/mypanel/etc/version..."
    mkdir -p "${PROJECT_ROOT}/panel_setup/mypanel/etc"
    echo "${NEW_VERSION}" > "${PROJECT_ROOT}/panel_setup/mypanel/etc/version"
fi

# Compile Tailwind CSS bundle
if command -v npx &> /dev/null && [ -d "${PROJECT_ROOT}/panel_setup/mypanel" ]; then
    echo "🎨 Compiling Tailwind CSS..."
    (cd "${PROJECT_ROOT}/panel_setup/mypanel" && npx -y tailwindcss@3.4.17 -i ./media/css/tailwind-input.css -o ./media/css/tailwind.min.css --minify)
fi

# Build panel_setup.zip and plugin zip files using Python3
PROJECT_ROOT="${PROJECT_ROOT}" python3 - <<'EOF'
import zipfile, os, re, json

base_dir = os.environ["PROJECT_ROOT"]

# 0. Synchronize centralized REPO_URL from repo_url.txt across all scripts, configs, and Django settings
repo_url_file = os.path.join(base_dir, "repo_url.txt")
repo_url = "https://ongudidan.github.io/OLSPanel"
if os.path.isfile(repo_url_file):
    with open(repo_url_file, "r", encoding="utf-8") as rf:
        val = rf.read().strip().rstrip("/")
        if val:
            repo_url = val

print(f"🔗 Synchronizing centralized repository URL: {repo_url}")

# Sync into panel_setup/mypanel/etc/repo_url
etc_dir = os.path.join(base_dir, "panel_setup", "mypanel", "etc")
os.makedirs(etc_dir, exist_ok=True)
with open(os.path.join(etc_dir, "repo_url"), "w", encoding="utf-8") as ef:
    ef.write(f"{repo_url}\n")

# Sync fallback REPO_URL in all .sh files and Python files
for root, dirs, files in os.walk(base_dir):
    if ".git" in root or "__pycache__" in root:
        continue
    for fname in files:
        fpath = os.path.join(root, fname)
        if fname.endswith(".sh") and fname != "build_update.sh":
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    text = f.read()
                new_text = re.sub(
                    r'REPO_URL="\$\{REPO_URL:-[^}]+\}"',
                    f'REPO_URL="${{REPO_URL:-{repo_url}}}"',
                    text,
                )
                if new_text != text:
                    with open(fpath, "w", encoding="utf-8") as f:
                        f.write(new_text)
            except Exception:
                pass
        elif fname.endswith(".py") and "panel_setup" in root:
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    text = f.read()
                new_text = re.sub(
                    r'getattr\(settings,\s*"OLSPANEL_REPO_URL",\s*"[^"]+"\)',
                    f'getattr(settings, "OLSPANEL_REPO_URL", "{repo_url}")',
                    text,
                )
                if fname == "settings.py":
                    new_text = re.sub(
                        r'(def get_repo_url\(\):[\s\S]*?return\s+)"[^"]+"(\s*\n\s*OLSPANEL_REPO_URL)',
                        rf'\1"{repo_url}"\2',
                        new_text,
                    )
                if new_text != text:
                    with open(fpath, "w", encoding="utf-8") as f:
                        f.write(new_text)
            except Exception:
                pass

# Sync plugins.json
plugins_json_path = os.path.join(base_dir, "plugins.json")
if os.path.isfile(plugins_json_path):
    try:
        with open(plugins_json_path, "r", encoding="utf-8") as pf:
            pdata = json.load(pf)
        changed = False
        for p in pdata.get("plugins", []):
            u = p.get("url", "")
            for suffix in ("/extra/install_mongodb.sh", "/extra/imunifyfav.sh"):
                if u.endswith(suffix) and u != f"{repo_url}{suffix}":
                    p["url"] = f"{repo_url}{suffix}"
                    changed = True
        if changed:
            with open(plugins_json_path, "w", encoding="utf-8") as pf:
                json.dump(pdata, pf, indent=2)
                pf.write("\n")
    except Exception as e:
        print(f"⚠️ Warning syncing plugins.json: {e}")

# Sync README.md install command URLs
readme_path = os.path.join(base_dir, "README.md")
if os.path.isfile(readme_path):
    try:
        with open(readme_path, "r", encoding="utf-8") as rf:
            rtext = rf.read()
        new_rtext = re.sub(r'https?://[^\s)]+/install\.sh', f'{repo_url}/install.sh', rtext)
        if new_rtext != rtext:
            with open(readme_path, "w", encoding="utf-8") as rf:
                rf.write(new_rtext)
    except Exception:
        pass

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

# 2b. Create plugin/git_deploy.zip (if olspanel-plugin-git-deploy is present)
git_deploy_src = os.path.abspath(os.path.join(base_dir, "..", "olspanel-plugin-git-deploy", "git_deploy"))
if os.path.isdir(git_deploy_src):
    git_deploy_zip = os.path.join(base_dir, "plugin", "git_deploy.zip")
    with zipfile.ZipFile(git_deploy_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(git_deploy_src):
            if '__pycache__' in root or '.git' in root:
                continue
            for f in files:
                if f.endswith('.pyc'):
                    continue
                full_p = os.path.join(root, f)
                rel_p = os.path.relpath(full_p, os.path.dirname(git_deploy_src))
                zf.write(full_p, rel_p)
    print("✅ Rebuilt plugin/git_deploy.zip")

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
