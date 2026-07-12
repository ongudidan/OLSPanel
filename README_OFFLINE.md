# Offline OLSPanel Installation Guide

This backup has been patched to run entirely using a local web server, ensuring you do not require any connection to the developer's domains (`olspanel.com` or `github.com`).

An automated script `offline_install.sh` has been provided to completely automate this process.

## Automated Installation (Single Command)

### Step 1: Copy Backup to the Target Server
Copy the entire `olspanel_v3.0.18` folder to your fresh target server:
```bash
scp -r olspanel_v3.0.18 root@your-server-ip:/root/
```

### Step 2: Run the Automated Installer
On the target server, navigate into the folder and run the automated installer:
```bash
cd /root/olspanel_v3.0.18
./offline_install.sh
```
This script will automatically start the local web server in the background, run the patched installation process, and shut down the server when completed!

---

## Manual Installation (Alternative)

If you prefer to run it manually step-by-step:

1. Start Python's built-in HTTP server in the backup folder on the target server:
   ```bash
   cd /root/olspanel_v3.0.18
   python3 -m http.server 8000
   ```
2. Open another terminal session on the target server and execute the patched installer:
   ```bash
   bash <(curl -fsSL http://127.0.0.1:8000/install.sh)
   ```
