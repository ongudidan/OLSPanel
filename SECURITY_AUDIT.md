# OLSPanel Security Audit Report

> **Audit Date:** July 2026
> **Codebase:** OLSPanel v3.x (Python/Django web hosting control panel)

---

## Summary

| Severity | Count |
|----------|-------|
| Critical | 5 categories (14+ SQLi, 70+ command injections, 40+ CSRF exemptions, open redirect, weak password storage) |
| High | 5 categories (path traversal, mass assignment, IDOR, auth weaknesses, missing Host validation) |
| Medium | 5 categories (secure cookie flags, plaintext DB passwords in proc, no rate limiting, firewall injection, SSRF) |
| Low | 3 categories (info disclosure, missing security headers, weak SECRET_KEY handling) |

---

## CRITICAL

### C-01: SQL Injection via F-String Queries

**File:** `panel_setup/mypanel/users/database.py`

User-controlled database names, usernames, and passwords from `request.POST` are interpolated directly into SQL via f-strings. No parameterized queries are used.

| Line | Vulnerable Code |
|------|-----------------|
| 438 | `sql = f"CREATE DATABASE {prefixed_db_name};"` |
| 504 | `create_db_sql = f"CREATE DATABASE IF NOT EXISTS \`{prefixed_db_name}\`;"` |
| 508-510 | `GRANT ALL PRIVILEGES ON \`{prefixed_db_name}\`.*` |
| 763 | `f"RENAME USER '{current_db_name}'@'localhost' TO '{new_username}'@'localhost'"` |
| 771 | `f"ALTER USER '{new_username}'@'localhost' IDENTIFIED BY '{new_password}'"` |
| 822 | `f"mysqldump -u {username} -p{password} {old_db_name}"` |
| 826 | `cursor.execute(f"CREATE DATABASE \`{new_db_name}\`;")` |
| 844 | `cursor.execute(f"DROP DATABASE \`{old_db_name}\`;")` |
| 862 | `cursor.execute(f"DROP DATABASE IF EXISTS {database_namex}")` |

**Remediation:** Replace all f-string SQL with parameterized queries using `cursor.execute(sql, params)` syntax.

---

### C-02: Command Injection via shell=True

**Files:**
- `panel_setup/mypanel/whm/function.py` (lines 73, 76, 79, 862, 887, 1086, 2069, 2645)
- `panel_setup/mypanel/users/database.py` (lines 822, 830)
- `panel_setup/mypanel/users/views.py` (lines 2683, 2691)
- `panel_setup/mypanel/users/server_core.py` (lines 2077, 2095)
- `panel_setup/mypanel/whm/views.py` (lines 2855-2906, 2022)
- `panel_setup/mypanel/users/firewall.py` (lines 91, 98, 105)

Over 70 instances use `subprocess.run(..., shell=True)` or `os.system()` with user-supplied or user-derived data. This enables arbitrary command execution if input contains shell metacharacters.

**Example (firewall.py:91):**
```python
os.system(f"ufw insert 1 deny from {ip} comment 'auto_temp_block'")
```
IP addresses parsed from firewall logs are injected directly — a spoofed IP like `1.2.3.4; rm -rf /` would execute.

**Remediation:** Use `subprocess.run([cmd, arg1, arg2, ...])` without `shell=True`. Where unavoidable, use `shlex.quote()` on all user-supplied components.

---

### C-03: CSRF Protection Entirely Disabled

**Files:**
- `panel_setup/mypanel/api/views.py` — 15 views with `@csrf_exempt` (lines 36, 94, 208, 228, 276, 325, 356, 387, 403, 418, 433, 443, 498, 521, 554)
- `panel_setup/mypanel/admin_api/views.py` — 10 views with `@csrf_exempt` (lines 39, 116, 200, 292, 340, 365, 412, 438, 524, 566)
- `panel_setup/mypanel/users/views.py` — `CustomLoginView` at line 208 is `@method_decorator(csrf_exempt, name='dispatch')`
- Additional `@csrf_exempt` in `whm/views.py:1682`, `users/views.py:3104`
- `csrf_exempt` imported but unused in `bandwidth.py`, `plugin.py`, `whm/plugin.py`, `file_manager/views.py`

**Remediation:** Implement token-based CSRF for API endpoints (e.g., Django Rest Framework's token auth) instead of blanket exemption. Restore CSRF protection on `CustomLoginView`.

---

### C-04: Weak Password Storage (Base64 Obfuscation)

**File:** `panel_setup/mypanel/users/function.py:987-998`

```python
def encode(data: str) -> str:
    data_bytes = data.encode('utf-8')
    base64_bytes = base64.b64encode(data_bytes)
    base64_str = base64_bytes.decode('utf-8')
    random_string = ''.join(random.choices(string.ascii_lowercase, k=5))
    return random_string + base64_str
```

Passwords are stored in files at `{BASE_DIR}/etc/_{username}` with this trivially reversible "encoding." Additionally, `{BASE_DIR}/etc/mysqlPassword` stores the MySQL root password in plaintext.

**Remediation:** Use Django's `Fernet` symmetric encryption or `django-cryptography` for stored credentials. Never store MySQL root password in a world-readable file.

---

### C-05: Open Redirect in Login View

**File:** `panel_setup/mypanel/users/views.py:208-218`

```python
@method_decorator(csrf_exempt, name='dispatch')
class CustomLoginView(LoginView):
    def get_success_url(self):
        next_url = self.request.GET.get("next")
        if next_url:
            return str(next_url)
```

The `?next=` parameter is used directly without validation. An attacker can craft `https://panel.example.com/login/?next=https://evil.com` for phishing.

**Remediation:** Validate the redirect URL against `ALLOWED_HOSTS` using Django's `url_has_allowed_host_and_scheme()`.

---

## HIGH

### H-01: Missing Path Traversal Guard in php_editor

**File:** `panel_setup/mypanel/users/views.py:1245-1294`

The `php_editor` view writes files using a user-controlled `file` parameter. It calls `os.path.join(base_dir, file.lstrip('/'))` but does **not** verify the resolved path starts with `base_dir` before writing. The `download` view in `file_manager/views.py:569-601` does check this, but the check may be bypassable via symlinks.

**Remediation:** Add `if not file_path.startswith(base_dir): return error` before any read/write operation.

---

### H-02: IDOR — Auto Login as Any User

**File:** `panel_setup/mypanel/whm/views.py:1136-1158`

```python
def auto_login_by_admin(request, rid):
    usr = get_object_or_404(User, id=rid)
    passw = get_auto_login_password(usr.username)
    user = authenticate(request, username=usr.username, password=passw)
    ...
    login(request, user)
    return redirect('/')
```

Any admin with access to this endpoint can impersonate any user by user ID without knowing their password.

**Remediation:** Add audit logging for all auto-login actions. Consider requiring the admin's own password confirmation.

---

### H-03: ALLOWED_HOSTS = ['*']

**File:** `panel_setup/mypanel/user_management/settings.py:33`

```python
ALLOWED_HOSTS = ['*']
```

Disables Django's Host header validation, enabling cache poisoning, password reset poisoning, and SSRF via host injection.

**Remediation:** Set to the server's actual domain name and IP: `ALLOWED_HOSTS = ['panel.yourdomain.com', 'server-ip']`.

---

### H-04: Plaintext Passwords in Command Line (proc leak)

**Files:**
- `panel_setup/mypanel/users/database.py:822` — `f"mysqldump -u {username} -p{password} {old_db_name}"`
- `panel_setup/mypanel/users/database.py:830` — `f"mysql -u {username} -p{password} {old_db_name}"`

MySQL passwords passed as CLI arguments are visible to all users via `/proc/[pid]/cmdline`.

**Remediation:** Use `--defaults-extra-file` with a temporary MySQL config file instead of inline `-p{password}`.

---

### H-05: No Rate Limiting on Authentication

All login and API authentication endpoints lack rate limiting, account lockout, or brute-force protection. The only protection is OS-level `fail2ban` parsing syslog.

**Remediation:** Implement Django middleware rate limiting (e.g., `django-ratelimit`) on all auth endpoints.

---

## MEDIUM

### M-01: Session Cookies Not Secure

**File:** `panel_setup/mypanel/user_management/settings.py:232`

```python
SESSION_COOKIE_SECURE = False
# CSRF_COOKIE_SECURE = True  (commented out)
```

Cookies are transmitted over HTTP even when HTTPS is available. Set both to `True`.

---

### M-02: Firewall IP Block Command Injection

**File:** `panel_setup/mypanel/users/firewall.py:89-108`

`os.system(f"ufw insert 1 deny from {ip}")` — IP from parsed syslog could contain shell metacharacters via crafted log entries.

**Remediation:** Validate IP format with `ipaddress` module before passing to the shell, or use the Python `ufw` API.

---

### M-03: SSRF / Arbitrary Code Execution via Plugin Install

**File:** `panel_setup/mypanel/whm/views.py:3385-3408`

Plugin URLs from user input are passed directly to `install_cp_plugin` which downloads and executes arbitrary code.

**Remediation:** Validate plugin URLs against an allowlist of known plugin sources.

---

### M-04: Insecure Session Configuration

**File:** `panel_setup/mypanel/user_management/settings.py`

Missing headers:
- `X-Frame-Options` (clickjacking)
- `X-Content-Type-Options: nosniff`
- `SECURE_HSTS_SECONDS` (commented out)

**Remediation:** Add via Django's `SECURE_*` settings or in the web server reverse proxy config.

---

## LOW

### L-01: Information Disclosure in Error Responses

Multiple endpoints return raw exception messages to the user:
- `file_manager/views.py:566` — `f"Error performing action: {str(e)}"`
- `users/database.py:849` — `f"Error occurred: {e}"`
- `whm/views.py:2807-2808` — `f"Unexpected error: {str(e)}"`

**Remediation:** Log detailed errors server-side; return generic messages to the user.

---

### L-02: Weak SECRET_KEY Handling

**File:** `panel_setup/mypanel/user_management/settings.py:28`

```python
SECRET_KEY = str(os.getenv('SECRET_KEY'))
```

No fallback or validation — if the env var is unset, Django uses an empty string, breaking all cryptographic signing.

**Remediation:** Add a startup check: `if not SECRET_KEY: raise ImproperlyConfigured(...)`.

---

### L-03: SECURE_SSL_REDIRECT = False

**File:** `panel_setup/mypanel/user_management/settings.py:35`

```python
SECURE_SSL_REDIRECT = False
```

The application does not enforce HTTPS redirect at the Django level (relies on the web server).

**Remediation:** Set to `True` if SSL termination happens before Django.

---

## Remediation Priority Matrix

| Priority | Issue | Effort | Impact |
|----------|-------|--------|--------|
| P0 | SQL injection (database.py) | Medium | Full DB compromise |
| P0 | Command injection (shell=True) | High | Full server compromise |
| P0 | CSRF exemption on LoginView | Low | Account takeover via CSRF |
| P0 | Weak password storage | Medium | Credential theft |
| P1 | ALLOWED_HOSTS = ['*'] | Low | Host header attacks |
| P1 | Path traversal in php_editor | Low | Arbitrary file write |
| P1 | Secure cookie flags | Low | Session hijacking |
| P1 | Open redirect | Low | Phishing |
| P2 | Rate limiting | Medium | Brute force |
| P2 | Security headers | Low | Clickjacking |
| P2 | Error message leakage | Low | Information disclosure |

---

## How to Run Your Own Audit

```bash
# Search for command injection
rg -n "shell=True" --include="*.py"
rg -n "os\.system\|os\.popen" --include="*.py"

# Search for SQL injection
rg -n 'f".*execute\|f".*cursor' --include="*.py" -C2

# Search for CSRF exemptions
rg -n "csrf_exempt" --include="*.py"

# Search for open redirects
rg -n 'redirect\(request\.GET\|next_url\|redirect_url' --include="*.py"

# Search for hardcoded secrets
rg -n "SECRET_KEY\|PASSWORD\|password.*=" --include="*.py" -i
```
