# OLSPanel Server Wrapper (olspanelcp Replacement)

This directory contains the full source code and build tools to compile a custom, open-source server wrapper replacing the closed-source `/usr/local/bin/olspanelcp` binary.

---

## ⚙️ Features
1. **Multi-threaded HTTPS Server**: Serves the Django framework concurrently on port `6656`.
2. **WebSocket Reverse Proxy**: Intercepts `/terminal/` connections and tunnels the raw WebSocket stream directly to the internal PHP terminal server (`127.0.0.1:9090`).
3. **No External Libraries**: Relies strictly on standard Python libraries (`socket`, `ssl`, `wsgiref`, `threading`), making compilation clean and lightweight.

---

## 🛠️ How to Compile

1. Run the build script:
   ```bash
   ./build.sh
   ```
2. The compiled standalone binary will be generated at:
   ```text
   dist/olspanelcp
   ```

---

## 🚀 How to Install on Live Server

To install the new compiled binary as the active panel server:

1. Stop the current control panel daemon:
   ```bash
   sudo systemctl stop cp
   ```
2. Backup the original binary:
   ```bash
   sudo mv /usr/local/bin/olspanelcp /usr/local/bin/olspanelcp.bak
   ```
3. Copy the newly compiled `dist/olspanelcp` binary into `/usr/local/bin/olspanelcp`.
4. Ensure executable permissions:
   ```bash
   sudo chmod +x /usr/local/bin/olspanelcp
   ```
5. Restart the control panel daemon:
   ```bash
   sudo systemctl start cp
   ```
6. Check status to ensure it started successfully:
   ```bash
   sudo systemctl status cp
   ```
