# 🚀 OLS Panel

OLS Panel is a premium, open-source web hosting control panel designed for speed, security, and maximum efficiency. Powered by **OpenLiteSpeed** and built on a robust Python/Django framework, it provides full control over your servers, websites, mailboxes, databases, and DNS.

This repository hosts the entire source code, installers, helper libraries, and release packaging tools for **OLS Panel**.

---

## 🛠️ Key Features

* **High Performance**: Native OpenLiteSpeed web server integration for lightning-fast page loads and low memory overhead.
* **Modern App Hosting**: Seamless support for PHP (versions 7.4 through 8.5) and Node.js applications.
* **Database Management**: Full support for MariaDB, PostgreSQL, and MongoDB.
* **Email & FTP Suite**: Integrated Postfix/Dovecot virtual mailboxes and Pure-FTPd database-backed user management.
* **DNS Administration**: PowerDNS server integration with automated MySQL zones.
* **Security & Firewall**: Built-in UFW and ConfigServer Security & Firewall (CSF) management.
* **One-Click SSL**: Automatic certificate generation via ACME.sh and Let's Encrypt.
* **Secure Web Terminal**: Interactive, real-time in-browser terminal console.

---

## 💾 Installation

To install **OLS Panel** on a clean VPS running **Ubuntu (20.04/22.04/24.04)**, **Debian**, or **CentOS/AlmaLinux**, connect via SSH and run:

```bash
curl -sSL https://ongudidan.github.io/OLSPanel/install.sh | bash
```

*This script downloads all required dependencies, packages, and codebase archives directly from the GitHub Pages CDN.*

---

## 📂 Repository Structure

* **[`mypanel/`](file:///home/ongudidan/Projects/TOOLS/OLSPanel%20Full/fortune_panel/panel_setup/mypanel/)**: The main Django application backend and WHM user interface templates.
* **[`panel_server/`](file:///home/ongudidan/Projects/TOOLS/OLSPanel%20Full/fortune_panel/panel_server/)**: Custom compiled HTTPS/SSL and WebSocket proxy wrapper (`olspanelcp`) written in Python.
* **[`panel_updates/`](file:///home/ongudidan/Projects/TOOLS/OLSPanel%20Full/fortune_panel/panel_updates/)**: Utility scripts and templates to package code updates and version files.
* **[`repo_owpanel/`](file:///home/ongudidan/Projects/TOOLS/OLSPanel%20Full/fortune_panel/repo_owpanel/)**: Core installation shell scripts (`panel.sh`) categorized by OS.
* **[`extra/`](file:///home/ongudidan/Projects/TOOLS/OLSPanel%20Full/fortune_panel/extra/)**: Helper scripts for configuring Dovecot mail, UFW, PHP CGI, swap, and OpenSSL libraries.

---

## 📦 How to Build and Publish Updates

### 1. Build the Code Archive
Make your customizations inside `panel_setup/mypanel/`. To package your updated codebase, run:
```bash
./panel_updates/build_update.sh
```
*This generates a compiled `panel_setup.zip` inside the `panel_updates/` directory.*

### 2. Update the Version
1. Open [`panel_updates/version.txt`](file:///home/ongudidan/Projects/TOOLS/OLSPanel%20Full/fortune_panel/panel_updates/version.txt) and increment the version string (e.g., `3.0.19`).
2. Update the corresponding `VERSION` parameter inside your Django settings: `panel_setup/mypanel/user_management/settings.py`.

### 3. Push and Deploy
Commit your changes and push to GitHub:
```bash
git add .
git commit -m "Release v3.0.19"
git push origin main
```
*Your update files will immediately deploy to GitHub Pages and be accessible to all active panels.*
