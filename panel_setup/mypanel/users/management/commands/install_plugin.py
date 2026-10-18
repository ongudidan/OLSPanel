import os
import shutil
import subprocess
import tarfile
import zipfile
from urllib.parse import urlparse
from django.core.management.base import BaseCommand
from django.conf import settings
import requests

class Command(BaseCommand):
    help = "Installs a plugin from a local or remote file (supports .zip, .tar, .tar.gz, .rar)"

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, required=True, help='Local path or remote URL of the plugin file.')

    def handle(self, *args, **kwargs):
        file_url = kwargs['file']
        tmp_dir = '/home/tmp'
        os.makedirs(tmp_dir, exist_ok=True)

        try:
            # Download or copy logic (unchanged) ...
            parsed = urlparse(file_url)
            filename = os.path.basename(parsed.path)
            local_path = os.path.join(tmp_dir, filename)

            if parsed.scheme in ['http', 'https']:
                self.stdout.write(f"🌐 Downloading {file_url}...")
                response = requests.get(file_url, stream=True)
                response.raise_for_status()
                with open(local_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                self.stdout.write(self.style.SUCCESS(f"✅ Downloaded to {local_path}"))
            else:
                if not os.path.exists(file_url):
                    raise FileNotFoundError(f"Local file not found: {file_url}")
                shutil.copy(file_url, local_path)
                self.stdout.write(self.style.SUCCESS(f"📁 Copied local file to {local_path}"))

            # Extraction (unchanged) ...
            raw_name = os.path.splitext(filename)[0]
            extract_path = os.path.join(tmp_dir, raw_name)
            os.makedirs(extract_path, exist_ok=True)

            if filename.endswith('.zip'):
                with zipfile.ZipFile(local_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_path)
            elif filename.endswith(('.tar.gz', '.tgz', '.tar', '.tar.bz2')):
                with tarfile.open(local_path, 'r:*') as tar:
                    tar.extractall(extract_path)
            elif filename.endswith('.rar'):
                result = subprocess.run(['unrar', 'x', '-o+', local_path, extract_path], capture_output=True)
                if result.returncode != 0:
                    raise Exception(f"Error extracting RAR: {result.stderr.decode()}")
            else:
                raise Exception("Unsupported file type")

            self.stdout.write(self.style.SUCCESS(f"📦 Extracted plugin to {extract_path}"))

            # Find plugin root folder (single folder in archive root)
            top_level_items = os.listdir(extract_path)
            dirs = [d for d in top_level_items if os.path.isdir(os.path.join(extract_path, d))]
            if len(dirs) != 1:
                raise Exception(f"Expected exactly one folder inside archive root but found {len(dirs)}")

            plugin_root = os.path.join(extract_path, dirs[0])
            self.stdout.write(self.style.SUCCESS(f"📂 Plugin root folder detected: {plugin_root}"))

            # Find plugin config file
            plugin_conf_path = None
            plugin_json_path = None
            plugin_name = None
            for root, dirs, files in os.walk(plugin_root):
                for file in files:
                    if file.startswith("plugin_") and file.endswith(".conf"):
                        plugin_conf_path = os.path.join(root, file)
                        plugin_name = file.replace("plugin_", "").replace(".conf", "").strip()
                        break
                if plugin_conf_path:
                    break
                    
                    
                    
            for root, dirs, files in os.walk(plugin_root):
                for file in files:
                    if file.startswith("plugin_") and file.endswith(".json"):
                        plugin_json_path = os.path.join(root, file)
                       
                        break
                if plugin_json_path:
                    break        

            if not plugin_conf_path:
                raise Exception("❌ No 'plugin_*.conf' file found in plugin root. Plugin installation aborted.")
            if not plugin_name or '/' in plugin_name or '\\' in plugin_name:
                raise Exception("❌ Invalid plugin name extracted from config file. Installation aborted.")

            self.stdout.write(self.style.SUCCESS(f"🔍 Found plugin config: {plugin_conf_path}"))
            self.stdout.write(self.style.SUCCESS(f"📛 Plugin name: {plugin_name}"))

            # Check for icons inside plugin_root (both SVG and PNG supported)
            icon_svg_src = None
            icon_png_src = None
            conf_icon_target_name = None
            
            # Extract icon target name from conf if specified
            try:
                with open(plugin_conf_path, 'r', encoding='utf-8') as cf:
                    for line in cf:
                        line = line.strip()
                        if line.startswith('icon='):
                            raw_icon = line.split('=', 1)[1].strip()
                            if raw_icon:
                                conf_icon_target_name = os.path.basename(raw_icon)
            except Exception:
                pass

            for root, dirs, files in os.walk(plugin_root):
                for f in files:
                    lower_f = f.lower()
                    if lower_f in ('plugin_icon.svg', f"{plugin_name}.svg") or (conf_icon_target_name and lower_f == conf_icon_target_name.lower() and lower_f.endswith('.svg')):
                        if not icon_svg_src:
                            icon_svg_src = os.path.join(root, f)
                    elif lower_f in ('plugin_icon.png', f"{plugin_name}.png") or (conf_icon_target_name and lower_f == conf_icon_target_name.lower() and lower_f.endswith(('.png', '.webp', '.jpg', '.jpeg'))):
                        if not icon_png_src:
                            icon_png_src = os.path.join(root, f)

            if not icon_svg_src and not icon_png_src:
                raise Exception("❌ No plugin icon (plugin_icon.svg or plugin_icon.png) found. Plugin installation aborted.")

            # Prepare target directories
            base_3rdparty = os.path.join(settings.BASE_DIR, '3rdparty', plugin_name)
            base_plugin = os.path.join(settings.BASE_DIR, 'plugin')
            media_icon_dir = os.path.join(settings.BASE_DIR, 'media', 'icon')

            os.makedirs(base_3rdparty, exist_ok=True)
            os.makedirs(base_plugin, exist_ok=True)
            os.makedirs(media_icon_dir, exist_ok=True)
            if plugin_json_path and os.path.exists(plugin_json_path):
                plugin_json_target = os.path.join(base_plugin, f"{plugin_name}.json")
                shutil.move(plugin_json_path, plugin_json_target)
            # Move plugin files except config and icon
            icon_src_paths = {p for p in (icon_svg_src, icon_png_src) if p}
            for root, dirs, files in os.walk(plugin_root):
                for file in files:
                    full_path = os.path.join(root, file)
                    if full_path == plugin_conf_path or full_path in icon_src_paths:
                        continue  # Skip config and icon
                    if file in ('plugin_icon.png', 'plugin_icon.svg'):
                        continue

                    rel_path = os.path.relpath(full_path, plugin_root)
                    target_path = os.path.join(base_3rdparty, rel_path)

                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                    shutil.move(full_path, target_path)
                    self.stdout.write(f"📂 Moved {file} to {target_path}")

            # Move config file
            plugin_conf_target = os.path.join(base_plugin, f"{plugin_name}.conf")
            
            shutil.move(plugin_conf_path, plugin_conf_target)
            
    
            self.stdout.write(self.style.SUCCESS(f"🧩 Plugin config moved to {plugin_conf_target}"))

            # Deploy icons to media_icon_dir with appropriate permissions
            if icon_svg_src:
                svg_dest = os.path.join(media_icon_dir, f"{plugin_name}.svg")
                shutil.copy(icon_svg_src, svg_dest)
                try:
                    os.chmod(svg_dest, 0o644)
                except Exception:
                    pass
                self.stdout.write(self.style.SUCCESS(f"🖼️ SVG plugin icon deployed to {svg_dest}"))

            if icon_png_src:
                png_dest = os.path.join(media_icon_dir, f"{plugin_name}.png")
                shutil.copy(icon_png_src, png_dest)
                try:
                    os.chmod(png_dest, 0o644)
                except Exception:
                    pass
                self.stdout.write(self.style.SUCCESS(f"🖼️ PNG plugin icon deployed to {png_dest}"))

            # If conf specified a specific icon filename (e.g. icon=/media/icon/custom_name.ext), copy to that exact name as well
            if conf_icon_target_name:
                custom_dest = os.path.join(media_icon_dir, conf_icon_target_name)
                if not os.path.exists(custom_dest):
                    if conf_icon_target_name.endswith('.svg') and icon_svg_src:
                        shutil.copy(icon_svg_src, custom_dest)
                        try:
                            os.chmod(custom_dest, 0o644)
                        except Exception:
                            pass
                    elif icon_png_src:
                        shutil.copy(icon_png_src, custom_dest)
                        try:
                            os.chmod(custom_dest, 0o644)
                        except Exception:
                            pass

            # --- NEW: Look for install.cmd and run it ---
            cmd_file = os.path.join(base_3rdparty, 'plugin.cmd')
            if os.path.isfile(cmd_file):
                self.stdout.write(f"⚙️ Found plugin.cmd, rewriting paths and running...")
                try:
                    with open(cmd_file, 'r', encoding='utf-8') as f:
                        cmd_content = f.read()
                    
                    # Replace mypanel project path
                    legacy_project_path = "/usr/local/lsws/Example/html/mypanel"
                    current_project_path = str(settings.BASE_DIR).rstrip('/')
                    cmd_content = cmd_content.replace(legacy_project_path, current_project_path)
                    
                    # Replace ols parent html path
                    legacy_html_path = "/usr/local/lsws/Example/html"
                    current_html_path = str(os.path.dirname(settings.BASE_DIR)).rstrip('/')
                    cmd_content = cmd_content.replace(legacy_html_path, current_html_path)

                    with open(cmd_file, 'w', encoding='utf-8') as f:
                        f.write(cmd_content)
                except Exception as e:
                    self.stderr.write(f"⚠️ Warning: failed to rewrite paths in plugin.cmd: {e}")

                sed_cmd = f"sed -i 's/\\r$//' {cmd_file}"
                subprocess.run(sed_cmd, shell=True, check=True)

                # Make executable
                chmod_cmd = f"chmod +x {cmd_file}"
                subprocess.run(chmod_cmd, shell=True, check=True)

                # Run the command, capture output and errors
                result = subprocess.run(['bash', cmd_file], capture_output=True, text=True)
                
                if result.returncode != 0:
                    self.stderr.write(self.style.ERROR(f"❌ plugin.cmd failed:\n{result.stderr}"))
                    raise Exception("plugin.cmd script returned error.")
                else:
                    os.remove(cmd_file)
                    self.stdout.write(self.style.SUCCESS(f"✅ plugin.cmd executed successfully:\n{result.stdout}"))
                    
                    
            if os.path.exists(local_path):
                os.remove(local_path)
                self.stdout.write(f"🗑️ Removed archive: {local_path}")

            if os.path.exists(extract_path):
                shutil.rmtree(extract_path)
                self.stdout.write(f"🗑️ Removed extracted folder: {extract_path}")
            self.stdout.write(self.style.SUCCESS("🎉 Plugin installed successfully."))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Error installing plugin: {str(e)}"))
