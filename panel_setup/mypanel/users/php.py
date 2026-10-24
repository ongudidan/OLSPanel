import os
import subprocess
import mimetypes
import shutil
import pwd
import grp
from django.http import HttpResponse, HttpResponseRedirect, FileResponse, Http404, HttpResponseNotModified
from django.utils.http import http_date
from django.conf import settings
from http.cookies import SimpleCookie
from .database import * 
from .models import * 


def get_php_cgi_binary():
    """Detect available php-cgi binary on the system dynamically."""
    try:
        binary = AppSettings.objects.get(setting_key='cgi_bin').setting_value.strip()
        if binary and os.path.isfile(binary) and os.access(binary, os.X_OK):
            return binary
    except Exception:
        pass

    candidates = [
        '/usr/bin/php-cgi',
        '/usr/bin/php-cgi8.5',
        '/usr/bin/php-cgi8.4',
        '/usr/bin/php-cgi8.3',
        '/usr/bin/php-cgi8.2',
        '/usr/bin/php-cgi8.1',
        '/usr/bin/php-cgi7.4',
    ]
    for c in candidates:
        if os.path.isfile(c) and os.access(c, os.X_OK):
            try:
                setting, _ = AppSettings.objects.get_or_create(setting_key='cgi_bin')
                setting.setting_value = c
                setting.save()
            except Exception:
                pass
            return c

    which_bin = shutil.which('php-cgi')
    if which_bin:
        return which_bin

    return '/usr/bin/php-cgi'


def spawn_php_cgi_process(php_binary, php_script_path, env, php_user='root', php_group='root'):
    """Spawn PHP-CGI process dropping privileges cleanly without sudo -E warnings."""
    popen_kwargs = {
        'stdin': subprocess.PIPE,
        'stdout': subprocess.PIPE,
        'stderr': subprocess.PIPE,
        'env': env,
        'cwd': os.path.dirname(php_script_path)
    }

    if os.geteuid() == 0 and php_user and php_user != 'root':
        try:
            pwd.getpwnam(php_user)
            popen_kwargs['user'] = php_user
            if php_group and php_group != 'root':
                try:
                    grp.getgrnam(php_group)
                    popen_kwargs['group'] = php_group
                except Exception:
                    pass
            cmd = [php_binary]
        except Exception:
            cmd = ['sudo', '-u', php_user, php_binary]
    elif php_user and php_user != 'root':
        cmd = ['sudo', '-u', php_user, php_binary]
    else:
        cmd = [php_binary]

    return subprocess.Popen(cmd, **popen_kwargs)


def php_server(request, php_file, PHP_USER='root', PHP_GROUP='root'):
    public_folder = '3rdparty'
    if not php_file.endswith('/') and not os.path.splitext(php_file)[1]:
        return HttpResponseRedirect(request.path + '/')
        
    if not os.path.splitext(php_file)[1]:
        php_file = php_file + '/index.php'
        
    scheme = 'https' if request.is_secure() else 'http'    
    PROJECT_ROOT = str(settings.BASE_DIR)
    PHP_ROOT = os.path.join(PROJECT_ROOT, public_folder)
    PHP_BINARY = get_php_cgi_binary()

    clean_file = php_file.split('?', 1)[0]
    php_script_path = os.path.join(PHP_ROOT, clean_file)

    # === Serve static (non-PHP) files directly with HTTP caching ===
    if not clean_file.endswith('.php'):
        if os.path.isfile(php_script_path):
            stat_res = os.stat(php_script_path)
            etag = f'"{int(stat_res.st_mtime)}-{stat_res.st_size}"'
            last_modified = http_date(stat_res.st_mtime)

            if_none_match = request.META.get('HTTP_IF_NONE_MATCH')
            if_modified_since = request.META.get('HTTP_IF_MODIFIED_SINCE')

            if if_none_match == etag or if_modified_since == last_modified:
                return HttpResponseNotModified()

            mime_type, _ = mimetypes.guess_type(php_script_path)
            response = FileResponse(open(php_script_path, 'rb'), content_type=mime_type or 'application/octet-stream')
            response['ETag'] = etag
            response['Last-Modified'] = last_modified
            filename = os.path.basename(clean_file)
            if (clean_file.endswith('.js') or clean_file.endswith('.css') or clean_file.endswith('.woff2') or clean_file.endswith('.woff')) and any(c.isdigit() for c in filename):
                response['Cache-Control'] = 'public, max-age=31536000, immutable'
            else:
                response['Cache-Control'] = 'public, max-age=86400, must-revalidate'
            return response
        else:
            raise Http404()

    # === Serve PHP files through php-cgi ===
    if not os.path.exists(php_script_path):
        raise Http404()

    if getattr(request, 'user', None) and request.user.is_authenticated:
        user_data = get_user_data_by_id(request.user.id)
        whm = user_data.get('whm', 0) if user_data else (1 if request.user.is_superuser or request.user.is_staff else 0)
    elif getattr(request, 'admin_user', None):
        user_data = get_user_data_by_id(request.admin_user.id)
        whm = user_data.get('whm', 0) if user_data else (1 if request.admin_user.is_superuser or request.admin_user.is_staff else 0)
    else:
        user_data = None
        whm = 0
        
    if whm == 1:
        panel_user = 'root'
    elif getattr(request, 'user', None) and request.user.is_authenticated:    
        panel_user = request.user.username 
    else:
        panel_user = 'nobody' 
    
    env = os.environ.copy()
    env["REQUEST_METHOD"] = request.method
    env["SCRIPT_FILENAME"] = php_script_path
    env["SCRIPT_NAME"] = f"/{public_folder}/{clean_file}"
    env["REQUEST_URI"] = request.get_full_path()
    env["QUERY_STRING"] = request.META.get("QUERY_STRING", "")
    env["CONTENT_TYPE"] = request.META.get("CONTENT_TYPE", "")
    env["CONTENT_LENGTH"] = str(len(request.body)) if request.body else "0"
    env["REDIRECT_STATUS"] = "200"
    env["SERVER_SOFTWARE"] = 'OLSPanel'
    env["SERVER_PORT"] = '443' if scheme == 'https' else '80'
    env["HTTPS"] = 'on' if scheme == 'https' else 'off'
    env["REQUEST_SCHEME"] = scheme
    env["HTTP_ACCEPT"] = request.META.get("HTTP_ACCEPT", "*/*")
    env["HTTP_USER_AGENT"] = request.META.get("HTTP_USER_AGENT", "")
    env["HTTP_REFERER"] = request.META.get("HTTP_REFERER", "")
    env["HTTP_ORIGIN"] = request.META.get("HTTP_ORIGIN", "")
    env["HTTP_SEC_FETCH_DEST"] = "iframe"
    env["HTTP_SEC_FETCH_MODE"] = "navigate"
    env["HTTP_SEC_FETCH_SITE"] = "same-origin"
    env["REMOTE_ADDR"] = request.META.get('HTTP_CF_CONNECTING_IP', request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '127.0.0.1'))).split(',')[0].strip()
    env["PANEL_USERNAME"] = panel_user
    env["SERVER_ADDR"] = get_server_ip()
    env["SERVER_NAME"] = request.get_host().split(':')[0]
    env["DOCUMENT_ROOT"] = os.path.dirname(os.path.abspath(php_script_path))
    env["SERVER_PROTOCOL"] = request.META.get("SERVER_PROTOCOL", "HTTP/1.1")

    for header, value in request.META.items():
        if header.startswith("HTTP_"):
            php_header_name = header[5:].replace("_", "-").upper()
            env[f"HTTP_{php_header_name}"] = value
        elif header in ["SERVER_PORT"]:
            env[header] = str(value)

    if request.COOKIES:
        cookie_string = "; ".join([f"{k}={v}" for k, v in request.COOKIES.items()])
        env["HTTP_COOKIE"] = cookie_string

    try:
        process = spawn_php_cgi_process(PHP_BINARY, php_script_path, env, PHP_USER, PHP_GROUP)
        stdout, stderr = process.communicate(input=request.body)

        header_end = stdout.find(b"\r\n\r\n")
        delimiter_len = 4
        if header_end == -1:
            header_end = stdout.find(b"\n\n")
            delimiter_len = 2

        if header_end == -1:
            with open("/tmp/php_cgi_error.log", "a") as f:
                f.write(f"PHP-CGI Crash for {php_file} (code {process.returncode}): {stderr.decode(errors='ignore')}\n")
            err_msg = stderr.decode(errors='ignore').strip()
            return HttpResponse(f"PHP-CGI Error: {err_msg}" if err_msg else "Invalid PHP-CGI response", status=500)

        php_headers_raw = stdout[:header_end].decode("iso-8859-1")
        php_body = stdout[header_end + delimiter_len:]  # keep as bytes
        
        location = None
        status_code = 200
        
        # Parse all headers first
        for line in php_headers_raw.split("\r\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()
                
                if key.lower() == "status":
                    try:
                        status_code = int(value.split()[0])
                    except (ValueError, IndexError):
                        pass

                elif key.lower() == "location":
                    location = value
                    
                    # Process location URL
                    current_full_path = request.get_full_path()
                    base_url = request.build_absolute_uri('/').rstrip('/')

                    subpath = php_file.lstrip('/').split('/', 1)
                    app_base = subpath[0] if subpath else ''
                    prefix = f'/{public_folder}/{app_base}'

                    if location.startswith(f'/{app_base}/'):
                        location = location.replace(f'/{app_base}/', prefix + '/', 1)
                    elif not location.startswith(('http://', 'https://', '/')):
                        base_dir = os.path.dirname(current_full_path)
                        if not base_dir.endswith('/'):
                            base_dir += '/'
                        location = base_dir + location
                    elif location.startswith('/') and app_base and not location.startswith(prefix):
                        location = f'{prefix}{location}'

                    if not location.startswith(('http://', 'https://')):
                        location = f"{base_url}{location}"
        
        # Create appropriate response
        if location:
            django_response = HttpResponseRedirect(location)
        else:
            django_response = HttpResponse(content=php_body, status=status_code)
        
        # Apply all headers including cookies to the response
        for line in php_headers_raw.split("\r\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()
                
                if key.lower() == "set-cookie":
                    parts = value.split(";")
                    cookie_name_value = parts[0].split("=", 1)
                    if len(cookie_name_value) == 2:
                        cookie_name = cookie_name_value[0]
                        cookie_value = cookie_name_value[1]
                        options = {}
                        for part in parts[1:]:
                            if "=" in part:
                                opt_key, opt_val = part.split("=", 1)
                                options[opt_key.strip().lower()] = opt_val.strip()
                            else:
                                options[part.strip().lower()] = True
                                
                        max_age_raw = options.get("max-age")
                        if max_age_raw is not None:
                            try:
                                max_age = int(max_age_raw)
                            except ValueError:
                                max_age = None
                        else:
                            max_age = None
                            
                        django_response.set_cookie(
                            cookie_name,
                            cookie_value,
                            max_age=max_age if max_age != 0 else None,
                            expires=options.get("expires"),
                            path=options.get("path", "/"),
                            domain=options.get("domain"),
                            secure="secure" in options,
                            httponly="httponly" in options,
                            samesite=options.get("samesite", 'Lax')
                        )
                elif key.lower() not in ("location", "status"):
                    django_response[key] = value
        
        return django_response

    except Exception as e:
        return HttpResponse(f"Internal Server Error: {e}", status=500)
