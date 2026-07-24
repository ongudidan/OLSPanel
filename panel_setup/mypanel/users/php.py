import os
import subprocess
import mimetypes
from django.http import HttpResponse, HttpResponseRedirect, FileResponse,Http404
from django.conf import settings
from http.cookies import SimpleCookie
from .database import * 
from .models import * 


def php_server(request, php_file, PHP_USER='root', PHP_GROUP='root'):
    public_folder = '3rdparty'
    if not php_file.endswith('/') and not os.path.splitext(php_file)[1]:
        return HttpResponseRedirect(request.path + '/')
        
    if not os.path.splitext(php_file)[1]:
        php_file = php_file + '/index.php'
        
    scheme = 'https' if request.is_secure() else 'http'    
    PROJECT_ROOT = str(settings.BASE_DIR)
    PHP_ROOT = os.path.join(PROJECT_ROOT, public_folder)
    try:
        PHP_BINARY = AppSettings.objects.get(setting_key='cgi_bin').setting_value.strip()
    except AppSettings.DoesNotExist:
        PHP_BINARY = '/usr/bin/php-cgi8.2'  # fallback default

    php_script_path = os.path.join(PHP_ROOT, php_file)

    # === Serve static (non-PHP) files directly ===
    if not php_file.endswith('.php'):
        if os.path.isfile(php_script_path):
            mime_type, _ = mimetypes.guess_type(php_script_path)
            return FileResponse(open(php_script_path, 'rb'), content_type=mime_type or 'application/octet-stream')
        else:
            raise Http404()

    # === Serve PHP files through php-cgi ===
    if not os.path.exists(php_script_path):
        raise Http404()

    if request.user:
        user_data = get_user_data_by_id(request.user.id)
        whm = user_data.get('whm', 0)
    elif request.admin_user:
        user_data = get_user_data_by_id(request.admin_user.id)
        whm = user_data.get('whm', 0)
    else:
        whm = 0
        
    if whm == 1:
        panel_user = 'root'
    else:    
        panel_user = request.user.username 
    
    env = os.environ.copy()
    env["REQUEST_METHOD"] = request.method
    env["SCRIPT_FILENAME"] = php_script_path
    env["SCRIPT_NAME"] = f"/{public_folder}/{php_file}"
    env["QUERY_STRING"] = request.META.get("QUERY_STRING", "")
    env["CONTENT_TYPE"] = request.META.get("CONTENT_TYPE", "")
    env["CONTENT_LENGTH"] = str(len(request.body)) if request.body else "0"
    env["REDIRECT_STATUS"] = "200"
    env["SERVER_SOFTWARE"]='OLSPanel'
    env["SERVER_PORT"]='443' if scheme == 'https' else '80'
    env["HTTPS"]= 'on' if scheme == 'https' else 'off'
    env["REQUEST_SCHEME"]= scheme
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
        process = subprocess.Popen(
            ['sudo', '-u', PHP_USER, '-E', PHP_BINARY],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            cwd=os.path.dirname(php_script_path)
        )
        stdout, stderr = process.communicate(input=request.body)

        if process.returncode != 0:
            with open("/tmp/php_cgi_error.log", "a") as f:
                f.write(f"PHP-CGI Error for {php_file}: {stderr.decode(errors='ignore')}\n")
            return HttpResponse(f"PHP-CGI Error: {stderr.decode(errors='ignore')}", status=500)

        header_end = stdout.find(b"\r\n\r\n")
        if header_end == -1:
            return HttpResponse("Invalid PHP-CGI response", status=500)

        php_headers_raw = stdout[:header_end].decode("iso-8859-1")
        php_body = stdout[header_end + 4:]  # keep as bytes
        
        location = None
        django_response = None
        
        # Parse all headers first
        for line in php_headers_raw.split("\r\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()
                
                # Store location for later use
                if key.lower() == "location":
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
        
        # Now create appropriate response
        if location:
            # For redirects, create a redirect response
            django_response = HttpResponseRedirect(location)
        else:
            # For regular responses, create a normal response with body
            django_response = HttpResponse(content=php_body)
        
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
                elif key.lower() != "location":  # Don't set Location header on response
                    django_response[key] = value
        
        return django_response

    except Exception as e:
        return HttpResponse(f"Internal Server Error: {e}", status=500)

def php_serverx(request, php_file, PHP_USER='root', PHP_GROUP='root'):
    public_folder = '3rdparty'
    if not php_file.endswith('/') and not os.path.splitext(php_file)[1]:
        return HttpResponseRedirect(request.path + '/')
        
    if not os.path.splitext(php_file)[1]:
        php_file = php_file + '/index.php'
        
    scheme = 'https' if request.is_secure() else 'http'    
    PROJECT_ROOT = str(settings.BASE_DIR)
    PHP_ROOT = os.path.join(PROJECT_ROOT, public_folder)
    try:
        PHP_BINARY = AppSettings.objects.get(setting_key='cgi_bin').setting_value.strip()
    except AppSettings.DoesNotExist:
        PHP_BINARY = '/usr/bin/php-cgi8.2'  # fallback default
    #PHP_USER = 'root'
    #PHP_GROUP = 'root'

    # Full path to the requested file
    php_script_path = os.path.join(PHP_ROOT, php_file)

    # === Serve static (non-PHP) files directly ===
    if not php_file.endswith('.php'):
        if os.path.isfile(php_script_path):
            mime_type, _ = mimetypes.guess_type(php_script_path)
            return FileResponse(open(php_script_path, 'rb'), content_type=mime_type or 'application/octet-stream')
        else:
            raise Http404()

    # === Serve PHP files through php-cgi ===
    if not os.path.exists(php_script_path):
        raise Http404()


    if request.user:
        user_data = get_user_data_by_id(request.user.id)
        whm = user_data.get('whm', 0)
    elif request.admin_user:
        user_data = get_user_data_by_id(request.admin_user.id)
        whm = user_data.get('whm', 0)
    else:
        whm = 0
        
        
    if whm == 1:
        panel_user = 'root'
    else:    
        panel_user = request.user.username 
    
    env = os.environ.copy()
    env["REQUEST_METHOD"] = request.method
    env["SCRIPT_FILENAME"] = php_script_path
    env["SCRIPT_NAME"] = f"/{public_folder}/{php_file}"
    env["QUERY_STRING"] = request.META.get("QUERY_STRING", "")
    env["CONTENT_TYPE"] = request.META.get("CONTENT_TYPE", "")
    env["CONTENT_LENGTH"] = str(len(request.body)) if request.body else "0"
    env["REDIRECT_STATUS"] = "200"
    env["SERVER_SOFTWARE"]='OLSPanel'
    env["SERVER_PORT"]='443' if scheme == 'https' else '80'
    env["HTTPS"]= 'on' if scheme == 'https' else 'off'
    env["REQUEST_SCHEME"]= scheme
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
        process = subprocess.Popen(
            ['sudo', '-u', PHP_USER, '-E', PHP_BINARY],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            cwd=os.path.dirname(php_script_path)
        )
        stdout, stderr = process.communicate(input=request.body)

        if process.returncode != 0:
            with open("/tmp/php_cgi_error.log", "a") as f:
                f.write(f"PHP-CGI Error for {php_file}: {stderr.decode(errors='ignore')}\n")
            return HttpResponse(f"PHP-CGI Error: {stderr.decode(errors='ignore')}", status=500)

        header_end = stdout.find(b"\r\n\r\n")
        if header_end == -1:
            return HttpResponse("Invalid PHP-CGI response", status=500)

        php_headers_raw = stdout[:header_end].decode("iso-8859-1")
        php_body = stdout[header_end + 4:]  # keep as bytes
        
        

        django_response = HttpResponse(content=php_body)
        location = None  
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
                             
                
                else:
                    django_response[key] = value
                    
                if key.lower() == "location":
                    
                    location = value
                            
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

                               
                    
        if location:
            return HttpResponseRedirect(location)
        return django_response

    except Exception as e:
        return HttpResponse(f"Internal Server Error: {e}", status=500)
