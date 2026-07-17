# OLSPanel Security Remediation Checklist

Use this checklist to track our progress as we secure OLSPanel. Mark items as `[x]` when they are resolved.

---

## 🔴 CRITICAL SEVERITY (P0)

### [x] C-01: SQL Injection (SQLi) via F-Strings
*   **Vulnerability:** User-controlled database names, usernames, and passwords are concatenated directly into SQL statements using f-strings.
*   **Target Files:**
    - [x] [database.py (Line 438)](file:///home/ongudidan/Projects/TOOLS/OLSPanel%20Full/OLSPanel/panel_setup/mypanel/users/database.py#L438): `sql = f"CREATE DATABASE {prefixed_db_name};"`
    - [x] [database.py (Line 504)](file:///home/ongudidan/Projects/TOOLS/OLSPanel%20Full/OLSPanel/panel_setup/mypanel/users/database.py#L504): `create_db_sql = f"CREATE DATABASE IF NOT EXISTS \`{prefixed_db_name}\`;"`
    - [x] [database.py (Line 508-510)](file:///home/ongudidan/Projects/TOOLS/OLSPanel%20Full/OLSPanel/panel_setup/mypanel/users/database.py#L508-L510): `GRANT ALL PRIVILEGES ON \`{prefixed_db_name}\`.* TO %s@'localhost'` (identifier interpolation)
    - [x] [database.py (Line 763)](file:///home/ongudidan/Projects/TOOLS/OLSPanel%20Full/OLSPanel/panel_setup/mypanel/users/database.py#L763): `RENAME USER '{current_db_name}'@'localhost' TO '{new_username}'@'localhost'`
    - [x] [database.py (Line 771)](file:///home/ongudidan/Projects/TOOLS/OLSPanel%20Full/OLSPanel/panel_setup/mypanel/users/database.py#L771): `ALTER USER '{new_username}'@'localhost' IDENTIFIED BY '{new_password}'`
    - [x] [database.py (Line 826)](file:///home/ongudidan/Projects/TOOLS/OLSPanel%20Full/OLSPanel/panel_setup/mypanel/users/database.py#L826): `CREATE DATABASE \`{new_db_name}\``
    - [x] [database.py (Line 844)](file:///home/ongudidan/Projects/TOOLS/OLSPanel%20Full/OLSPanel/panel_setup/mypanel/users/database.py#L844): `DROP DATABASE \`{old_db_name}\``
    - [x] [database.py (Line 862)](file:///home/ongudidan/Projects/TOOLS/OLSPanel%20Full/OLSPanel/panel_setup/mypanel/users/database.py#L862): `DROP DATABASE IF EXISTS {database_namex}`
*   **Remediation:** Enforce regex allowlists for all identifiers (database names/usernames) and use backtick formatting. Use standard parameterized placeholders (`%s`) for value arguments.

---

### [x] C-02: Command Injection via shell=True & os.system()
*   **Vulnerability:** Execution of system commands using f-strings containing unsanitized user inputs, enabling attackers to inject shell commands (e.g. via IP fields or domain names).
*   **Target Files:**
    - [x] `panel_setup/mypanel/whm/function.py`
    - [x] `panel_setup/mypanel/users/database.py` (e.g., lines 822, 830, 1210-1270 - backup/restore/import/export/repair)
    - [x] `panel_setup/mypanel/users/views.py`
    - [x] `panel_setup/mypanel/users/server_core.py`
    - [x] `panel_setup/mypanel/whm/views.py` (Verified: already secure)
    - [x] `panel_setup/mypanel/users/firewall.py` (e.g. lines 91, 98, 105)
*   **Remediation:** Remove `shell=True` and `os.system`. Rewrite using `subprocess.run(list_args)` with list parameters.

---

### [x] C-03: CSRF Protection Disabled
*   **Vulnerability:** Core API and authentication endpoints are annotated with `@csrf_exempt`, bypassing protection against cross-site request forgery.
*   **Target Files:**
    - [x] `panel_setup/mypanel/api/views.py` (Verified: immune to CSRF, uses custom header-based stateless auth; no session cookies used)
    - [x] `panel_setup/mypanel/admin_api/views.py` (Verified: immune to CSRF, uses custom header-based stateless auth; no session cookies used)
    - [x] `panel_setup/mypanel/users/views.py` (Protected `CustomLoginView` via Django CSRF, added Origin/Referer guard checks to `web_server`)
    - [x] `panel_setup/mypanel/whm/views.py` (Added Origin/Referer guard checks to `configservercsfiframe`)
*   **Remediation:** Retain CSRF protection on browser web forms. Switch API endpoints to Token/API-Key authentication passed via headers (like `Authorization: Bearer <key>`) instead of session cookies.

---

### [x] C-04: Weak Password Storage (Base64)
*   **Vulnerability:** User passwords stored in files at `{BASE_DIR}/etc/_{username}` are only Base64-obfuscated.
*   **Target Files:**
    - [x] `panel_setup/mypanel/users/function.py` (lines 987-998)
    - [x] `panel_setup/mypanel/users/database.py` (line 41)
*   **Remediation:** Use cryptographic hashing (like Django's `make_password`/`check_password`) for panel user credentials. Use symmetric encryption (e.g., Fernet) for credentials that need to be read back in plaintext.

---

### [ ] C-05: Open Redirect in Login View
*   **Vulnerability:** `?next=` parameter redirects users directly without validation, enabling phishing setups.
*   **Target Files:**
    - [ ] `panel_setup/mypanel/users/views.py` (lines 208-218)
*   **Remediation:** Validate redirect URLs against `ALLOWED_HOSTS` using Django's `url_has_allowed_host_and_scheme()`.

---

## 🟠 HIGH SEVERITY (P1)

### [ ] H-01: Path Traversal in php_editor
*   **Vulnerability:** Writes/reads files using a user-controlled parameter without verifying that the resolved path stays inside the base directory.
*   **Target Files:**
    - [ ] `panel_setup/mypanel/users/views.py` (lines 1245-1294)
*   **Remediation:** Resolve paths with `pathlib.Path.resolve()` and verify the file starts with the target directory.

---

### [ ] H-02: IDOR (Insecure Direct Object Reference) in Auto-Login
*   **Vulnerability:** Admin can impersonate any user by user ID without authenticating or triggering logging.
*   **Target Files:**
    - [ ] `panel_setup/mypanel/whm/views.py` (lines 1136-1158)
*   **Remediation:** Log impersonation events to system logs; implement multi-factor confirmation or re-authenticate the admin.

---

### [ ] H-03: ALLOWED_HOSTS = ['*']
*   **Vulnerability:** Disables Host header validation, enabling cache poisoning and SSRF attacks.
*   **Target Files:**
    - [ ] [settings.py (Line 33)](file:///home/ongudidan/Projects/TOOLS/OLSPanel%20Full/OLSPanel/panel_setup/mypanel/user_management/settings.py#L33)
*   **Remediation:** Replace `['*']` with the specific domains/IPs of the hosting panel.

---

### [ ] H-04: Plaintext Passwords in command execution (proc leak)
*   **Vulnerability:** Inline `-p{password}` exposes MySQL passwords to all server users via `/proc/[pid]/cmdline`.
*   **Target Files:**
    - [ ] [database.py (Line 822)](file:///home/ongudidan/Projects/TOOLS/OLSPanel%20Full/OLSPanel/panel_setup/mypanel/users/database.py#L822)
    - [ ] [database.py (Line 830)](file:///home/ongudidan/Projects/TOOLS/OLSPanel%20Full/OLSPanel/panel_setup/mypanel/users/database.py#L830)
*   **Remediation:** Pass passwords via environment variables (like `MYSQL_PWD`) or use temporary files passed to `--defaults-extra-file`.

---

### [ ] H-05: Missing Auth Rate Limiting
*   **Vulnerability:** Authentication and login endpoints do not limit request rates, allowing brute-force attempts.
*   **Target Files:**
    - [ ] `panel_setup/mypanel/user_management/urls.py` & login views.
*   **Remediation:** Install and configure rate limiting middleware (such as `django-ratelimit`).

---

## 🟡 MEDIUM SEVERITY (P2)

### [ ] M-01: Session Cookies Not Secure
*   **Vulnerability:** Session and CSRF cookies are transmitted over unencrypted HTTP.
*   **Target Files:**
    - [ ] [settings.py (Line 232)](file:///home/ongudidan/Projects/TOOLS/OLSPanel%20Full/OLSPanel/panel_setup/mypanel/user_management/settings.py#L232)
*   **Remediation:** Set `SESSION_COOKIE_SECURE = True` and `CSRF_COOKIE_SECURE = True`.

---

### [ ] M-02: Firewall IP Block Command Injection
*   **Vulnerability:** Direct execution of `ufw` block calls using unvalidated strings parsed from syslog.
*   **Target Files:**
    - [ ] `panel_setup/mypanel/users/firewall.py` (lines 89-108)
*   **Remediation:** Parse inputs using Python's `ipaddress` module to ensure the argument is a valid IP address.

---

### [ ] M-03: SSRF / Code Execution via Plugin Install
*   **Vulnerability:** Installs plugins directly from user-supplied URLs without verification.
*   **Target Files:**
    - [ ] `panel_setup/mypanel/whm/views.py` (lines 3385-3408)
*   **Remediation:** Restrict installation source URLs to a strict allowlist.

---

### [ ] M-04: Missing Clickjacking and HSTS Headers
*   **Vulnerability:** HTTP headers for Clickjacking protection and HTTP Strict Transport Security are missing.
*   **Target Files:**
    - [ ] [settings.py](file:///home/ongudidan/Projects/TOOLS/OLSPanel%20Full/OLSPanel/panel_setup/mypanel/user_management/settings.py)
*   **Remediation:** Enable `SECURE_HSTS_SECONDS`, `SECURE_CONTENT_TYPE_NOSNIFF`, and verify `XFrameOptionsMiddleware` is active in middleware.

---

## 🟢 LOW SEVERITY (P3)

### [ ] L-01: Information Disclosure in Exceptions
*   **Vulnerability:** Endpoints display raw stack trace exception messages directly to the user interface.
*   **Target Files:**
    - [ ] `file_manager/views.py`
    - [ ] `users/database.py`
    - [ ] `whm/views.py`
*   **Remediation:** Log the exception details to server files and show generic error messages to the client.

---

### [ ] L-02: Weak SECRET_KEY Handling
*   **Vulnerability:** If the `SECRET_KEY` environment variable is missing, it falls back to an empty string.
*   **Target Files:**
    - [ ] [settings.py (Line 28)](file:///home/ongudidan/Projects/TOOLS/OLSPanel%20Full/OLSPanel/panel_setup/mypanel/user_management/settings.py#L28)
*   **Remediation:** Raise an exception if the environment variable is not defined during startup.

---

### [ ] L-03: Enforced HTTP to HTTPS Redirect
*   **Vulnerability:** The panel does not enforce HTTPS connections.
*   **Target Files:**
    - [ ] [settings.py (Line 35)](file:///home/ongudidan/Projects/TOOLS/OLSPanel%20Full/OLSPanel/panel_setup/mypanel/user_management/settings.py#L35)
*   **Remediation:** Set `SECURE_SSL_REDIRECT = True` if terminating SSL before Django.
