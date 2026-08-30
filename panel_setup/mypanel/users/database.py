import os
import re
import json
import random
import string
import socket
import requests
from django.db import connection
from django.db.utils import OperationalError
import base64
from django.conf import settings
import subprocess
from users.server_core import *
import shutil
import tarfile 
import xml.etree.ElementTree as ET
from xml.dom import minidom
from .models import * 
import zipfile
import tarfile
from django.http import JsonResponse, FileResponse
from ftplib import FTP
from users.panellogger import *
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User

logger = CpLogger()

def clean_mysql_identifier(identifier: str) -> str:
    """
    Validates and cleans MySQL database/user identifiers.
    Only allows alphanumeric characters and underscores.
    """
    if not identifier:
        raise ValueError("Identifier cannot be empty.")
    if not re.match(r'^[a-zA-Z0-9_]+$', identifier):
        raise ValueError(f"Invalid characters in database/user identifier: '{identifier}'")
    safe_name = identifier.replace("`", "``")
    return f"`{safe_name}`"

def encode2(data: str) -> str:
    from cryptography.fernet import Fernet
    import hashlib
    secret_key = getattr(settings, 'SECRET_KEY', 'default_secret_key')
    key_bytes = hashlib.sha256(secret_key.encode('utf-8')).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    f = Fernet(fernet_key)
    encrypted_bytes = f.encrypt(data.encode('utf-8'))
    random_string = ''.join(random.choices(string.ascii_lowercase, k=5))
    return random_string + encrypted_bytes.decode('utf-8')
    
    
def password_save_file2(username, data):
    new_data = encode2(data)
    django_root = settings.BASE_DIR
    file_path = os.path.join(django_root, 'etc', f"_{username}")
   
    try:
        # Check if the file exists
        if os.path.exists(file_path):
            # Replace the file content
            with open(file_path, 'w') as f:
                f.write(new_data)
            return f"Success: File '{file_path}' content replaced."
        else:
            # Create the file and write the data
            os.makedirs(os.path.dirname(file_path), exist_ok=True)  # Ensure the directory exists
            with open(file_path, 'w') as f:
                f.write(new_data)
            return f"Success: File '{file_path}' created with new content."
    except Exception as e:
        return f"Error: An unexpected error occurred: {e}"
        

def upload_to_ftp(ftp_host, ftp_user, ftp_pass, local_file, remote_path):
    try:
        # Establish FTP connection
        ftp = FTP(ftp_host)
        ftp.login(user=ftp_user, passwd=ftp_pass)
        print(f"Connected to FTP server: {ftp_host}")

        # Navigate to the target directory or create it
        remote_dir = os.path.dirname(remote_path)
        if remote_dir:
            try:
                ftp.cwd(remote_dir)
            except Exception:
                # Create directories if they don't exist
                directories = remote_dir.split('/')
                for directory in directories:
                    if directory not in ftp.nlst():
                        ftp.mkd(directory)
                    ftp.cwd(directory)

        # Open the local file in binary mode for upload
        with open(local_file, 'rb') as file:
            ftp.storbinary(f"STOR {os.path.basename(remote_path)}", file)
        print(f"File uploaded successfully to {remote_path}")
        if os.path.exists(local_file):
            os.remove(local_file)
            print(f"Local file deleted: {local_file}")

        # Close the connection
        ftp.quit()
    except Exception as e:
        logger.error(e)
        print(f"FTP upload failed: {e}")

def delete_old_ftp_backups(ftp_host, ftp_user, ftp_pass, remote_folder='/', limit=100):
    try:
        ftp = FTP(ftp_host)
        ftp.login(user=ftp_user, passwd=ftp_pass)

        ftp.cwd(remote_folder)

        # get only backup files
        files = [f for f in ftp.nlst() if f.endswith('.tar.gz')]

        # sort by filename (your timestamp format supports this)
        sorted_files = sorted(files, reverse=True)

        # keep latest `limit`
        files_to_delete = sorted_files[limit:]

        deleted_count = 0

        for file_name in files_to_delete:
            try:
                ftp.delete(file_name)
                deleted_count += 1
                print(f"Deleted: {file_name}")
            except Exception as e:
                print(f"Failed to delete {file_name}: {e}")

        ftp.quit()

        return {
            'status': 'success',
            'deleted_count': deleted_count,
            'kept_count': limit
        }

    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }


def download_ftp_file(ftp_host, ftp_user, ftp_pass, remote_file, local_dir=None):
    
    # Set the default local directory if not provided
    if local_dir is None:
        local_dir = os.path.join(settings.BASE_DIR, 'downloads')

    # Ensure the local directory exists
    os.makedirs(local_dir, exist_ok=True)

    try:
        # Connect to the FTP server
        ftp = FTP(ftp_host)
        ftp.login(ftp_user, ftp_pass)
        #ftp.set_pasv(True)  # Enable Passive Mode

        # Download the file
        local_file_path = os.path.join(local_dir, os.path.basename(remote_file))
        with open(local_file_path, 'wb') as local_file:
            ftp.retrbinary(f'RETR {remote_file}', local_file.write)

        # Close the FTP connection
        ftp.quit()

        return local_file_path
    except Exception as e:
        print(f"Error downloading file from FTP: {e}")
        return None

def gz_compress(username_string, parent, file_name=None, target_name=None, selected_items=None):
    try:
        # Validate and sanitize inputs
        if not target_name:
            return JsonResponse({'status': 'error', 'message': 'Target name is required.'}, status=400)

        base_dir = os.path.join('/home', username_string)
        source_path = os.path.join(base_dir, parent)

        # Construct the target path
        if target_name.startswith('/'):
            target_name = target_name[1:]
        target_path = os.path.join(base_dir, target_name)
        if not target_path.endswith('.tar.gz'):
            target_path += '.tar.gz'

        # Check if the target file already exists
        if os.path.exists(target_path):
            return JsonResponse({'status': 'error', 'message': f"The file '{target_path}' already exists."}, status=400)

        # Create the tar.gz archive
        with tarfile.open(target_path, "w:gz") as tar:
            if selected_items:
                for item in selected_items:
                    item_path = os.path.join(base_dir, item)
                    if not os.path.exists(item_path):
                        return JsonResponse({'status': 'error', 'message': f"The item '{item}' does not exist."}, status=404)
                    tar.add(item_path, arcname=os.path.relpath(item_path, source_path))
            elif file_name:
                file_path = os.path.join(base_dir, file_name)
                if not os.path.exists(file_path):
                    return JsonResponse({'status': 'error', 'message': f"The file '{file_name}' does not exist."}, status=404)
                tar.add(file_path, arcname=os.path.relpath(file_path, source_path))
            else:
                return JsonResponse({'status': 'error', 'message': 'No files or directories provided for compression.'}, status=400)

        # Set permissions and ownership
        set_permissions_and_ownership_all(target_path, username_string)

        return JsonResponse({'status': 'success', 'message': f'Files compressed successfully to "{target_path}".'})

    except Exception as e:
        logger.error(e)
        return JsonResponse({'status': 'error', 'message': f"Error during compression: {str(e)}"}, status=500)   

def backup_delete(username_string, file_name):
    """
    Delete a file or folder for a specific user.
    """
    try:
        # Normalize the file path
        if file_name.startswith('/'):
            file_name = file_name[1:]

        base_dir = f'/home/{username_string}/'
        file_path = os.path.join(base_dir, file_name)

        # Check if the path is a folder or file and delete accordingly
        if os.path.isdir(file_path):
            shutil.rmtree(file_path)  # Recursively delete the folder
        elif os.path.isfile(file_path):
            os.remove(file_path)  # Delete the file
        else:
            return f"Error: '{file_path}' does not exist or is not a valid file/directory."

        return f"File deleted successfully: '{file_path}'."
    except Exception as e:
        logger.error(e)
        return f"Error: {str(e)}" 

def generate_strong_random_password(length=16):
    """Generate a strong random password using only A-Z and a-z characters."""
    if length < 12:  # Enforce a minimum length for security
        length = 12

    # Create a pool of characters (A-Z and a-z)
    all_characters = string.ascii_letters  # This includes both uppercase and lowercase letters

    # Generate a random password by selecting random characters from the pool
    password = random.choices(all_characters, k=length)

    return ''.join(password)    
    
def get_server_ip_old():
    try:
        # Connect to an external server (Google's DNS server) to get the public IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('8.8.8.8', 80))  # Connect to Google's public DNS server
            public_ip = s.getsockname()[0]  # Get the IP address of the socket
        return public_ip
    except Exception as e:
        logger.error(e)
        print(f"Error retrieving public IP: {e}")
        return None
    
def get_server_ip():
    def is_private_ip(ip):
        return (
            ip.startswith('10.') or
            (ip.startswith('172.') and 16 <= int(ip.split('.')[1]) <= 31) or
            ip.startswith('192.168.')
        )

    def is_valid_ipv4(ip):
        parts = ip.split('.')
        if len(parts) != 4:
            return False
        for part in parts:
            if not part.isdigit():
                return False
            i = int(part)
            if i < 0 or i > 255:
                return False
        return True

    def get_ip_file_path():
        django_root = getattr(settings, 'BASE_DIR', None)
        if django_root:
            return os.path.join(django_root, 'etc', 'ip')
        else:
            logger.error("BASE_DIR not set in Django settings")
            return None

    def read_ip_from_file():
        ip_file = get_ip_file_path()
        try:
            if ip_file and os.path.isfile(ip_file):
                with open(ip_file, 'r') as f:
                    ip = f.read().strip()
                    if is_valid_ipv4(ip):
                        #logger.info(f"Read cached IP from file: {ip}")
                        return ip
                    else:
                        logger.warning(f"IP in file {ip_file} is invalid: {ip}")
        except Exception as e:
            logger.error(f"Error reading IP from file: {e}")
        return None

    def save_ip_to_file(ip):
        ip_file = get_ip_file_path()
        try:
            if ip_file:
                os.makedirs(os.path.dirname(ip_file), exist_ok=True)
                with open(ip_file, 'w') as f:
                    f.write(ip)
                logger.info(f"Saved IP to file: {ip}")
        except Exception as e:
            logger.error(f"Error saving IP to file: {e}")

    # Step 0: try to read IP from file
    saved_ip = read_ip_from_file()
    if saved_ip:
        return saved_ip

    # Step 1: get local IP via socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('8.8.8.8', 80))
            local_ip = s.getsockname()[0]
            logger.info(f"Detected local IP: {local_ip}")
    except Exception as e:
        logger.error(f"Error getting local IP: {e}")
        local_ip = None

    if local_ip is None:
        return None

    # Step 2: if local IP is private, get public IP from ifconfig.me with 10s timeout
    if is_private_ip(local_ip):
        try:
            response = requests.get("https://ifconfig.me/ip", timeout=10)
            response.raise_for_status()
            public_ip = response.text.strip()
            logger.info(f"ifconfig.me returned public IP: {public_ip}")

            if is_valid_ipv4(public_ip) and not is_private_ip(public_ip):
                save_ip_to_file(public_ip)
                return public_ip
            else:
                logger.warning(f"ifconfig.me returned invalid or private IP: {public_ip}, using local IP instead")
                save_ip_to_file(local_ip)
                return local_ip

        except requests.RequestException as e:
            logger.warning(f"Failed to get public IP from ifconfig.me: {e}, using local IP instead")
            save_ip_to_file(local_ip)
            return local_ip
    else:
        # local IP is public
        save_ip_to_file(local_ip)
        return local_ip    


def get_server_ipv6():
    """
    Detect a single global IPv6 address for the server and save it to file.
    If no global IPv6 is found, nothing is saved.
    """

    def get_ipv6_file_path():
        django_root = getattr(settings, 'BASE_DIR', None)
        if django_root:
            return os.path.join(django_root, 'etc', 'ipv6')
        else:
            logger.error("BASE_DIR not set in Django settings")
            return None

    def read_ipv6_from_file():
        ip_file = get_ipv6_file_path()
        try:
            if ip_file and os.path.isfile(ip_file):
                with open(ip_file, 'r') as f:
                    ip = f.read().strip()
                    if ip and not ip.startswith("fe80") and ip != "::1":
                        return ip
        except Exception as e:
            logger.error(f"Error reading IPv6 from file: {e}")
        return None

    def save_ipv6_to_file(ip):
        ip_file = get_ipv6_file_path()
        try:
            if ip_file:
                os.makedirs(os.path.dirname(ip_file), exist_ok=True)
                with open(ip_file, 'w') as f:
                    f.write(ip)
                logger.info(f"Saved IPv6 to file: {ip}")
        except Exception as e:
            logger.error(f"Error saving IPv6 to file: {e}")

    # Step 0: try reading cached IPv6
    saved_ip = read_ipv6_from_file()
    if saved_ip:
        return saved_ip

    # Step 1: detect global IPv6 using `ip -6 addr show scope global`
    global_ipv6 = None
    try:
        output = subprocess.check_output(['ip', '-6', 'addr', 'show', 'scope', 'global'], text=True)
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("inet6"):
                ip = line.split()[1].split('/')[0]
                if ip and ip != "::1":
                    global_ipv6 = ip
                    break
    except Exception as e:
        logger.error(f"Error detecting IPv6: {e}")

    # Step 2: save and return only if IPv6 found
    if global_ipv6:
        save_ipv6_to_file(global_ipv6)
        return global_ipv6
    else:
        logger.info("No global IPv6 detected, nothing saved")
        return None


def create_database(username, db_name):
    prefixed_db_name = f"{username}_{db_name}"
    try:
        safe_db_name = clean_mysql_identifier(prefixed_db_name)
    except ValueError as e:
        return False, str(e)
    with connection.cursor() as cursor:
        try:
            # Check if the database already exists
            cursor.execute("SHOW DATABASES LIKE %s;", (prefixed_db_name,))
            if cursor.fetchone():  # If the database exists
                error_message = f"Database '{prefixed_db_name}' already exists."
                print(error_message)
                return False, error_message  # Return False and the error message

            # Construct the SQL command to create a new database
            sql = f"CREATE DATABASE {safe_db_name};"
            cursor.execute(sql)
            
            # Ensure the common user exists and has privileges
            create_database_common_user(username)
            common_user = f"{username}"
            grant_common_privileges_sql = f"GRANT ALL PRIVILEGES ON {safe_db_name}.* TO %s@'localhost';"
            cursor.execute(grant_common_privileges_sql, [common_user])
            cursor.execute("FLUSH PRIVILEGES;")
            
            print(f"Database '{prefixed_db_name}' created successfully.")
            return True, None  # Return True if successful, None for no error message
        except OperationalError as e:
            logger.error(e)
            error_message = f"Error creating database '{prefixed_db_name}': {str(e)}"
            print(error_message)
            return False, error_message  # Return False and the error message

def create_mysql_user(username, db_user, db_pass):
    full_db_user = f"{username}_{replace_first_with_underscore(db_user)}"
    if not re.match(r'^[a-zA-Z0-9_]+$', full_db_user):
        return False, "Invalid database user name"
    if len(db_pass) < 8:
        return False, "Password must be at least 8 characters long"
    try:
        with connection.cursor() as cursor:
            # Check if user already exists
            cursor.execute("SELECT EXISTS(SELECT 1 FROM mysql.user WHERE user = %s);", [full_db_user])
            if cursor.fetchone()[0]:
                return False, "User already exists"
            create_query = "CREATE USER %s@'localhost' IDENTIFIED BY %s;"
            cursor.execute(create_query, [full_db_user, db_pass])
            cursor.execute("FLUSH PRIVILEGES;")
        return True, None
    except Exception as e:
        logger.error(e)
        return False, str(e)

def grant_user_privileges(username, db_user, db_name, privileges_list):
    full_db_name = f"{username}_{replace_first_with_underscore(db_name)}"
    full_db_user = f"{username}_{replace_first_with_underscore(db_user)}"
    
    if not re.match(r'^[a-zA-Z0-9_]+$', full_db_name):
        return False, "Invalid database name"
    if not re.match(r'^[a-zA-Z0-9_]+$', full_db_user):
        return False, "Invalid database user"
        
    valid_privs = {
        'select', 'insert', 'update', 'delete', 'create', 'drop',
        'references', 'index', 'alter', 'create temporary tables', 'lock tables',
        'create view', 'show view', 'create routine', 'alter routine',
        'execute', 'event', 'trigger'
    }
    
    privs_to_grant = []
    for priv in privileges_list:
        p_clean = priv.lower().strip()
        if p_clean == 'all privileges' or p_clean == 'all':
            privs_to_grant = ['ALL PRIVILEGES']
            break
        if p_clean in valid_privs:
            privs_to_grant.append(p_clean.upper())
            
    if not privs_to_grant:
        return revoke_user_privileges(username, db_user, db_name)
        
    privs_str = ", ".join(privs_to_grant)
    
    try:
        with connection.cursor() as cursor:
            try:
                cursor.execute(f"REVOKE ALL PRIVILEGES ON `{full_db_name}`.* FROM '{full_db_user}'@'localhost';")
            except Exception:
                pass
            grant_query = f"GRANT {privs_str} ON `{full_db_name}`.* TO '{full_db_user}'@'localhost';"
            cursor.execute(grant_query)
            cursor.execute("FLUSH PRIVILEGES;")
        return True, "Privileges granted successfully"
    except Exception as e:
        logger.error(e)
        return False, str(e)

def revoke_user_privileges(username, db_user, db_name):
    full_db_name = f"{username}_{replace_first_with_underscore(db_name)}"
    full_db_user = f"{username}_{replace_first_with_underscore(db_user)}"
    
    if not re.match(r'^[a-zA-Z0-9_]+$', full_db_name):
        return False, "Invalid database name"
    if not re.match(r'^[a-zA-Z0-9_]+$', full_db_user):
        return False, "Invalid database user"
        
    try:
        with connection.cursor() as cursor:
            revoke_query = f"REVOKE ALL PRIVILEGES ON `{full_db_name}`.* FROM '{full_db_user}'@'localhost';"
            cursor.execute(revoke_query)
            cursor.execute("FLUSH PRIVILEGES;")
        return True, "Privileges revoked successfully"
    except Exception as e:
        if "1141" in str(e) or "no such grant" in str(e).lower():
            return True, "Privileges revoked successfully"
        logger.error(e)
        return False, str(e)

def get_user_db_privileges(username, db_user, db_name):
    full_db_name = f"{username}_{replace_first_with_underscore(db_name)}"
    full_db_user = f"{username}_{replace_first_with_underscore(db_user)}"
    
    priv_cols = [
        'Select_priv', 'Insert_priv', 'Update_priv', 'Delete_priv', 'Create_priv', 'Drop_priv',
        'References_priv', 'Index_priv', 'Alter_priv', 'Create_tmp_table_priv', 'Lock_tables_priv',
        'Create_view_priv', 'Show_view_priv', 'Create_routine_priv', 'Alter_routine_priv',
        'Execute_priv', 'Event_priv', 'Trigger_priv'
    ]
    
    query = f"SELECT {', '.join(priv_cols)} FROM mysql.db WHERE Db = %s AND User = %s;"
    
    with connection.cursor() as cursor:
        cursor.execute(query, [full_db_name, full_db_user])
        row = cursor.fetchone()
        if row:
            return {col.lower().replace('_priv', ''): (val == 'Y') for col, val in zip(priv_cols, row)}
        
    return {col.lower().replace('_priv', ''): False for col in priv_cols}

def database_exists(username, db_name):
    prefixed_db_name = db_name
    with connection.cursor() as cursor:
        try:
            cursor.execute("SHOW DATABASES LIKE %s;", (prefixed_db_name,))
            return cursor.fetchone() is not None  # Returns True if exists, False otherwise
        except Exception as e:
            print(f"Error checking database existence: {e}")
            return False

def db_user_exists(username, db_user):
    prefixed_user = db_user
    with connection.cursor() as cursor:
        try:
            cursor.execute("SELECT User FROM mysql.user WHERE User = %s;", (prefixed_user,))
            return cursor.fetchone() is not None  # True if user exists
        except Exception as e:
            print(f"Error checking DB user existence: {e}")
            return False
           
def create_database_and_user(request, username, db_name, db_user, db_pass, is_backup=False):
    db_user = f"{username}_{db_user}"  # User with username prefix
    prefixed_db_name = f"{username}_{db_name}"  # Database with username prefix
    common_user = f"{username}"  # Common user name
    django_root = settings.BASE_DIR

    try:
        safe_db_name = clean_mysql_identifier(prefixed_db_name)
    except ValueError as e:
        return str(e)

    # Construct the correct source and destination file paths
    common_user_password_file = os.path.join(django_root, 'etc', f"phpmyadmin_{username}")

    # Ensure the password file exists and contains a password
    if not os.path.exists(common_user_password_file):
        common_user_password = generate_strong_random_password()
        with open(common_user_password_file, 'w') as f:
            f.write(common_user_password)
    else:
        with open(common_user_password_file, 'r') as f:
            common_user_password = f.read().strip()

    with connection.cursor() as cursor:
        try:
            # Check if the user already exists
            check_user_sql = "SELECT EXISTS(SELECT 1 FROM mysql.user WHERE user = %s);"
            cursor.execute(check_user_sql, [db_user])
            user_exists = cursor.fetchone()[0]

            if user_exists:
                return "User already exists."

            # Create the specified user
            if is_backup:
                create_user_sql = "CREATE USER %s@'localhost' IDENTIFIED BY PASSWORD %s;"
            else:
                create_user_sql = "CREATE USER %s@'localhost' IDENTIFIED BY %s;"
            cursor.execute(create_user_sql, [db_user, db_pass])

            # Create the database if it doesn't already exist
            create_db_sql = f"CREATE DATABASE IF NOT EXISTS {safe_db_name};"
            cursor.execute(create_db_sql)

            # Grant all privileges to the user for their specific database only
            grant_privileges_sql = f"""
                GRANT ALL PRIVILEGES 
                ON {safe_db_name}.* TO %s@'localhost';
            """
            cursor.execute(grant_privileges_sql, [db_user])

            # Create the common user if it doesn't exist
            try:
                create_common_user_sql = "CREATE USER %s@'localhost' IDENTIFIED BY %s;"
                cursor.execute(create_common_user_sql, [common_user, common_user_password])
            except OperationalError:
                pass  # Ignore error if the common user already exists

            # Grant privileges to the common user for their specific database only
            grant_common_privileges_sql = f"""
                GRANT ALL PRIVILEGES ON {safe_db_name}.* TO %s@'localhost';
            """
            cursor.execute(grant_common_privileges_sql, [common_user])

            # Apply changes
            cursor.execute("FLUSH PRIVILEGES;")  # Apply privilege changes

            return True  # Success

        except OperationalError as e:
            logger.error(e)
            return str(e)  # Return the error message as a string
            

def create_database_common_user(username):
    common_user = f"{username}"  # Common user name
    django_root = settings.BASE_DIR

    # Construct the correct source and destination file paths
    common_user_password_file = os.path.join(django_root, 'etc', f"phpmyadmin_{username}")

    # Ensure the password file exists and contains a password
    if not os.path.exists(common_user_password_file):
        common_user_password = generate_strong_random_password()
        with open(common_user_password_file, 'w') as f:
            f.write(common_user_password)
    else:
        with open(common_user_password_file, 'r') as f:
            common_user_password = f.read().strip()

    with connection.cursor() as cursor:
        try:            
            # Create the common user if it doesn't exist
            try:
                create_common_user_sql = "CREATE USER %s@'localhost' IDENTIFIED BY %s;"
                cursor.execute(create_common_user_sql, [common_user, common_user_password])
            except OperationalError:
                pass  # Ignore error if the common user already exists

           

            return True  # Success

        except OperationalError as e:
            logger.error(e)
            return str(e)  # Return the error message as a string
            
def list_db_by_prefix(username):
    database_names = []  # Initialize an empty list for database names
    prefix = f"{username}_"  # Define the prefix to match

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT SCHEMA_NAME 
            FROM INFORMATION_SCHEMA.SCHEMATA 
            WHERE SCHEMA_NAME LIKE %s
        """, [f"{prefix}%"])  # Use parameterized query for safety

        databases = cursor.fetchall()
        
        # Convert the tuples to a simple list for easier rendering
        database_names = [db[0] for db in databases]  # db[0] corresponds to SCHEMA_NAME

    return database_names
 

def total_db():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.SCHEMATA 
            WHERE SCHEMA_NAME NOT IN ('information_schema', 'panel')
        """)
        count = cursor.fetchone()[0]  # Fetch the count value
        
    return count

 
def get_user_database_info(username):
    """Retrieve a list of databases matching the user's prefix and privileged users, without the size information."""
    databases_info = []  # Initialize an empty list for databases info
    prefix = f"{username}_"  # Define the full prefix with an underscore to match

    with connection.cursor() as cursor:
        # Query to get database names and privileged users only, excluding size
        cursor.execute("""
            SELECT 
                s.SCHEMA_NAME,
                GROUP_CONCAT(DISTINCT p.GRANTEE) AS Privileged_Users
            FROM 
                INFORMATION_SCHEMA.SCHEMATA s
            LEFT JOIN 
                INFORMATION_SCHEMA.SCHEMA_PRIVILEGES p ON s.SCHEMA_NAME = p.TABLE_SCHEMA
            WHERE 
                s.SCHEMA_NAME LIKE %s
            GROUP BY 
                s.SCHEMA_NAME
        """, [f"{prefix}%"])  # Use parameterized query for safety

        databases = cursor.fetchall()

        # Process the result and customize the privileged users list
        for db in databases:
            db_name = db[0]  # Database name
            privileged_users_raw = db[1]  # Raw privileged users (with hostname)
            size_display = get_database_size_display(db[0])

            # Customize privileged users by filtering and removing hostname and single quotes
            if privileged_users_raw:
                privileged_users_list = privileged_users_raw.split(',')  # Split users by comma
                filtered_users = [
                    user.split('@')[0].strip("'")  # Remove hostname and single quotes
                    for user in privileged_users_list
                    if user.startswith(f"'{username}_")  # Only include users that match 'username_'
                ]
                
                privileged_users = ', '.join(filtered_users)  # Join the filtered users into a string
            else:
                privileged_users = ''  # Default to empty if no privileged users or no matching prefix
            
            cursor.execute("""
                    SELECT authentication_string, Host
                    FROM mysql.user
                    WHERE User = %s
                """, [privileged_users])
            password_result = cursor.fetchone()
            user_passwords = password_result[0] if password_result else None
            user_host = password_result[1] if password_result else None

            # Append the database info to the list
            databases_info.append({
                'db_name': db_name,
                'privileged_users': privileged_users,
                'size_display': size_display,
                'password': user_passwords,
                'host': user_host
            })

    return databases_info


def get_database_size_display(database_name):
    """Retrieve the total size of the specified database and return it in KB or MB format."""
    with connection.cursor() as cursor:
        # Query to get the total size of the database in bytes
        cursor.execute("""
            SELECT 
                SUM(data_length + index_length) AS total_size_bytes
            FROM 
                information_schema.TABLES
            WHERE 
                table_schema = %s
        """, [database_name])  # Use parameterized query for safety

        result = cursor.fetchone()

        # Handle the case where result is None
        total_size_bytes = result[0] if result and result[0] is not None else 0  # Default to 0 if None

        # Convert bytes to KB
        size_kb = total_size_bytes / 1024

        # Convert KB to MB if size is large enough
        if size_kb >= 1024:
            size_mb = size_kb / 1024
            return f"{round(size_mb, 2)} MB"
        else:
            return f"{round(size_kb, 2)} KB"



 
    
def list_users_by_prefix(username): 
    """Retrieve a list of users in the MySQL database that match a specific prefix."""
    user_list = []  # Initialize an empty list for user names
    prefix = f"{username}_"

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT USER, HOST 
            FROM mysql.user 
            WHERE USER LIKE %s
        """, [f"{prefix}%"])  # Use parameterized query for safety

        users = cursor.fetchall()

        # Convert the tuples to a simple list of users
        user_list = [f"{user[0]}" for user in users]  # Combine USER and HOST

    return user_list
    
def count_users_by_prefix(username):
    """Retrieve the count of users in the MySQL database that match a specific prefix."""
    prefix = f"{username}_"

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*)
            FROM mysql.user
            WHERE USER LIKE %s
        """, [f"{prefix}%"])  # Use parameterized query for safety

        user_count = cursor.fetchone()[0]  # Fetch the count

    return user_count    
    
def replace_first_with_underscore(input_string):
    
    # Check if input_string is None
    if input_string is None:
        return None

    # Split the string by the first occurrence of '_'
    parts = input_string.split('_', 1)
    
    # Check if the string contains at least one underscore
    if len(parts) > 1:
        # Return only the part after the first underscore
        return parts[1]
    else:
        # If no underscore is found, return the original string
        return input_string

    
def update_db_user_credentials(username, current_db, db_user, new_password=None):
    # Adjust the current and new database usernames by replacing the first part with an underscore
    current_db = replace_first_with_underscore(current_db)
    db_user = replace_first_with_underscore(db_user)

    # Construct the full database username for both the old and new usernames
    current_db_name = f"{username}_{current_db}"
    new_username = f"{username}_{db_user}"
    
    try:
        if not re.match(r'^[a-zA-Z0-9_]+$', current_db_name):
            raise ValueError("Invalid characters in current database user name")
        if not re.match(r'^[a-zA-Z0-9_]+$', new_username):
            raise ValueError("Invalid characters in new database user name")
    except ValueError as e:
        return False, str(e)
        
    try:
        # Use the default database connection
        with connection.cursor() as cursor:
            # Step 1: Rename the user if the username has changed
            if new_username != current_db_name:
                try:
                    # Parameterization is not supported for account management statements in MySQL,
                    # but we strictly validated identifiers using regex.
                    rename_query = f"RENAME USER '{current_db_name}'@'localhost' TO '{new_username}'@'localhost'"
                    cursor.execute(rename_query)
                except OperationalError as e:
                    return False, f"Error renaming user: {e}"
            
            # Step 2: Update the password if provided
            if new_password:
                try:
                    # Safely escape the password to prevent injection in ALTER USER statement
                    escaped_password = new_password.replace('\\', '\\\\').replace("'", "\\'")
                    if hasattr(connection, 'connection') and connection.connection:
                        try:
                            escaped_password = connection.connection.escape_string(new_password)
                            if isinstance(escaped_password, bytes):
                                escaped_password = escaped_password.decode('utf-8')
                        except Exception:
                            pass
                    password_query = f"ALTER USER '{new_username}'@'localhost' IDENTIFIED BY '{escaped_password}'"
                    cursor.execute(password_query)
                except OperationalError as e:
                    return False, f"Error updating password: {e}"

        return True, "Database user credentials updated successfully."
    
    except OperationalError as e:
        return False, f"Error connecting to the database: {e}"
        
        

def delete_db_user_credentials(username, db_user):
    db_user = replace_first_with_underscore(db_user)
    full_db_user = f"{username}_{db_user}"
    try:
        if not re.match(r'^[a-zA-Z0-9_]+$', full_db_user):
            raise ValueError("Invalid characters in database user name")
    except ValueError as e:
        return False, str(e)
    try:
        with connection.cursor() as cursor:
            # Drop the user from the database (only for localhost)
            drop_user_query = f"DROP USER IF EXISTS '{full_db_user}'@'localhost'"
            cursor.execute(drop_user_query)

        return True  # Return success

    except OperationalError as e:
        # Log the error and return False to indicate failure
        return False, f"Error deleting database user: {e}"
        

def rename_database(username_string,old_db_name, new_db_name):
    current_db = replace_first_with_underscore(old_db_name)
    new_db_name = replace_first_with_underscore(new_db_name)
    old_db_name = f"{username_string}_{current_db}"
    new_db_name = f"{username_string}_{new_db_name}"
    
    if old_db_name == new_db_name:
        return "Database renamed successfully."
    
    try:
        if not re.match(r'^[a-zA-Z0-9_]+$', old_db_name):
            raise ValueError("Invalid characters in old database name")
        if not re.match(r'^[a-zA-Z0-9_]+$', new_db_name):
            raise ValueError("Invalid characters in new database name")
    except ValueError as e:
        return f"Error: {e}"

    username = connection.settings_dict['USER']
    password = connection.settings_dict['PASSWORD']

    try:
        safe_new_db = f"`{new_db_name}`"
        safe_old_db = f"`{old_db_name}`"
    except ValueError as e:
        return f"Error: {e}"

    try:
        with connection.cursor() as cursor:
            # Step 1: Check if the old database exists
            cursor.execute("SHOW DATABASES LIKE %s;", [old_db_name])
            if not cursor.fetchone():
                return f"Error: The database '{old_db_name}' does not exist."

            # Step 2: Check if the new database already exists
            cursor.execute("SHOW DATABASES LIKE %s;", [new_db_name])
            if cursor.fetchone():
                return f"Error: The database '{new_db_name}' already exists."

            # Step 3: Backup the existing database using secure subprocess list & env MYSQL_PWD
            backup_file = f"{old_db_name}_backup.sql"
            env = os.environ.copy()
            env["MYSQL_PWD"] = password
            
            with open(backup_file, "w") as f:
                subprocess.run(
                    ["mysqldump", "-u", username, old_db_name],
                    env=env,
                    stdout=f,
                    check=True
                )

            # Step 4: Create the new database
            cursor.execute(f"CREATE DATABASE {safe_new_db};")

            # Step 5: Import the data from the old database to the new database
            with open(backup_file, "r") as f:
                subprocess.run(
                    ["mysql", "-u", username, new_db_name],
                    env=env,
                    stdin=f,
                    check=True
                )

            # Step 6: Transfer user privileges using parameterized db filtering
            cursor.execute(f"""
                SELECT CONCAT('GRANT ALL PRIVILEGES ON {safe_new_db}.* TO ''', user, '''@''', host, ''';')
                FROM mysql.db
                WHERE db = %s;
            """, [old_db_name])
            grant_queries = cursor.fetchall()

            for grant_query in grant_queries:
                cursor.execute(grant_query[0])

            # Step 7: Drop the old database
            cursor.execute(f"DROP DATABASE {safe_old_db};")

        return f"Database renamed successfully from '{old_db_name}' to '{new_db_name}' with privileges transferred."

    except Exception as e:
        logger.error(e)
        return f"Error occurred: {e}"
        
        
        
        
def delete_database(username_string,database_name):
    database_name = replace_first_with_underscore(database_name)
    database_namex = f"{username_string}_{database_name}"
    try:
        if not re.match(r'^[a-zA-Z0-9_]+$', database_namex):
            raise ValueError("Invalid characters in database name")
        safe_db_name = f"`{database_namex}`"
    except ValueError as e:
        return str(e)
    """Delete the specified database."""
    with connection.cursor() as cursor:
        try:
            # Execute the DROP DATABASE command
            cursor.execute(f"DROP DATABASE IF EXISTS {safe_db_name}")
            connection.commit()  # Commit the changes to ensure the database is deleted
            return f"Database '{database_namex}' has been deleted successfully."
        except Exception as e:
            logger.error(e)
            connection.rollback()  # Rollback in case of an error
            return f"Error deleting database '{database_namex}': {str(e)}"
            
            
            
def add_dns_records(domain_id, domain_name,userid):
    """Add DNS records for a given domain with dynamic values without using a model."""
    
    # Get the current server's IP address
    ip_address = get_server_ip()
    ip6_address = get_server_ipv6()
    if not ip_address:
        print("Failed to get the server IP address.")
        return

    # Define the records to be added
    records_data = [
        (domain_id, domain_name, 'A', ip_address, 3600, 0,  0, None,  domain_id,userid),
        (domain_id, domain_name, 'NS', f'ns1.{domain_name}', 3600, 0, 0, None,  domain_id,userid),
        (domain_id, domain_name, 'NS', f'ns2.{domain_name}', 3600, 0,  0, None,  domain_id,userid),
        (domain_id, domain_name, 'SOA', f'ns1.{domain_name} hostmaster.{domain_name} 1 10800 3600 604800 3600', 3600, 0,  0, None,  domain_id,userid),
        (domain_id, f'www.{domain_name}', 'CNAME', domain_name, 3600, 0, 0, None, domain_id,userid),
        (domain_id, f'ftp.{domain_name}', 'CNAME', domain_name, 3600, 0,  0, None,  domain_id,userid),
        (domain_id, domain_name, 'MX', f'mail.{domain_name}', 3600, 10,  0, None,  domain_id,userid),
        (domain_id, f'mail.{domain_name}', 'A', ip_address, 3600, 0,  0, None,  domain_id,userid),
        (domain_id, domain_name, 'TXT', f'v=spf1 a mx ip4:{ip_address} ~all', 3600, 0, 0, None,  domain_id,userid),
        (domain_id, f'_dmarc.{domain_name}', 'TXT', 'v=DMARC1; p=none', 3600, 0, 0, None,  domain_id,userid),
     
    ]
    
    if ip6_address:
        records_data.append(
            (domain_id, domain_name, 'AAAA', ip6_address, 3600, 0, 0, None, domain_id, userid)
        )
        
    with connection.cursor() as cursor:
        for record in records_data:
            cursor.execute("""
                INSERT INTO `records` (`domain_id`, `name`, `type`, `content`, `ttl`, `prio`,  `disabled`, `ordername`, `auth`, `userid`)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, record)
        

def get_main_domainxx(domain_name):
    """Extract the main domain from a given domain name, removing all subdomains."""
    parts = domain_name.split('.')
    # Return the last two parts as the main domain (e.g., example.com)
    if len(parts) > 2:
        return '.'.join(parts[-2:])  # Join the last two parts
    return domain_name  # Return as-is if there's no subdomain

def get_main_domain(domain_name):
    """Return main domain only if it exists in DB, otherwise return original domain."""
    try:
        parts = domain_name.split('.')

        # Extract main domain: example.com
        if len(parts) > 2:
            main_domain = '.'.join(parts[-2:])
        else:
            main_domain = domain_name

        # If main domain exists → return main domain
        if domain_check(main_domain):
            return main_domain

        # Otherwise return original domain (keep subdomain)
        return domain_name

    except Exception as e:
        print("Error:", e)
        return domain_name



def domain_check(domain_name):
    try:
        return Domain.objects.filter(domain=domain_name).exists()
    except Exception as e:
        # Log the error if needed
        print("Error:", e)
        return False


def add_domain_dns(domain_id, domain_name,userid):
    """Add a new main domain to the domains table if it doesn't exist, ignoring subdomains."""
    
    # Extract the main domain
    main_domain = get_main_domain(domain_name)
    add_dns_records(domain_id, domain_name,userid)

    # Check if the main domain already exists
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*) 
            FROM domains 
            WHERE name = %s
        """, [main_domain])
        
        count = cursor.fetchone()[0]

        # If the main domain does not exist, insert it
        if count == 0:
            cursor.execute("""
                INSERT INTO `domains` (`id`, `name`, `master`, `last_check`, `type`, `notified_serial`, `account`)
                VALUES (%s, %s, NULL, NULL, 'NATIVE', NULL, NULL)
            """, [domain_id, main_domain])
            print(f"Domain '{main_domain}' added successfully.")
        else:
            print(f"Domain '{main_domain}' already exists, not adding.")
            
            
def normalize_domain(domain_name):
    """Validate and normalize the domain name by stripping unwanted prefixes."""
    
    # Remove 'http://' or 'https://'
    domain_name = re.sub(r'^https?://', '', domain_name)
    
    # Remove 'www.' prefix
    domain_name = re.sub(r'^www\.', '', domain_name)

    # Basic validation: Ensure the domain has at least one dot and only contains valid characters
    if not re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', domain_name):
        return None  # Invalid domain format

    return domain_name  # Return the normalized domain name            
            
       
def delete_record(domain_name):
    try:
        with connection.cursor() as cursor:
            # First, get the domain ID using the domain name
            cursor.execute("SELECT id FROM domains WHERE name = %s", [domain_name])
            row = cursor.fetchone()

            if row:
                domain_id = row[0]  # Get the ID from the row

                # Delete associated records for the domain
                cursor.execute("DELETE FROM records WHERE domain_id = %s", [domain_id])

                # Now, delete the domain itself
                cursor.execute("DELETE FROM domains WHERE id = %s", [domain_id])

                print(f"Domain '{domain_name}' and associated records deleted successfully.")
            else:
                print(f"Domain '{domain_name}' not found.")
    except Exception as e:
        logger.error(e)
        print(f"An error occurred: {e}")
        
        
def get_user_data_by_id(user_id):
    """Retrieve all data for a specific user by their ID."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT * 
            FROM auth_user 
            WHERE id = %s
        """, [user_id])
        row = cursor.fetchone()

        if row:
            # Get the column names
            columns = [col[0] for col in cursor.description]  # List of column names
            
            # Create an empty dictionary to hold user data
            user_data = {}
            
            # Manually populate the dictionary
            for index in range(len(columns)):
                user_data[columns[index]] = row[index]  # Assign each column name to its corresponding value

            return user_data  # Return the dictionary
        return None  # Return None if no user is foun   

def get_user_data(criteria=None, value=None):
    """Retrieve user data by ID or search for users based on criteria like username or email with 'like'."""
    
    # If no search criteria is given, return data for all users
    if criteria is None and value is None:
        query = "SELECT * FROM auth_user where whm!=1"
        with connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            
            # Get the column names
            columns = [col[0] for col in cursor.description]
            user_data_list = []
            for row in rows:
                user_data = {columns[index]: row[index] for index in range(len(columns))}
                user_data_list.append(user_data)
            
            return user_data_list  # List of all users

    # If search criteria is provided, validate it
    allowed_criteria = ['id', 'username', 'email']  # List of valid criteria
    if criteria not in allowed_criteria:
        raise ValueError(f"Invalid criteria. Choose from {', '.join(allowed_criteria)}.")
    
    # Add % around the search term for 'like' functionality
    search_value = f"%{value}%"
    
    # Use parameterized queries to prevent SQL injection
    query = f"SELECT * FROM auth_user WHERE {criteria} LIKE %s"
    with connection.cursor() as cursor:
        cursor.execute(query, [search_value])  # Use the search term with wildcards
        rows = cursor.fetchall()

        if rows:
            # Get the column names
            columns = [col[0] for col in cursor.description]
            user_data_list = []
            for row in rows:
                user_data = {columns[index]: row[index] for index in range(len(columns))}
                user_data_list.append(user_data)
            return user_data_list  # Return matching users
        else:
            return None  # No users found for the given criteria


def update_user_data(user_id, update_fields):
    """Update user data based on the provided fields and user ID."""
    
    # Validate the fields to ensure that only allowed fields are updated
    allowed_fields = ['username', 'first_name', 'last_name', 'email', 'pkg_id']  # List of valid fields to update
    update_columns = []

    # Check if all fields in the update_fields dictionary are valid
    for field in update_fields:
        if field not in allowed_fields:
            raise ValueError(f"Invalid field '{field}'. Valid fields are: {', '.join(allowed_fields)}.")
        update_columns.append(field)

    # Build the update query dynamically
    set_clause = ", ".join([f"{field} = %s" for field in update_columns])  # Create SET part of the query
    query = f"UPDATE auth_user SET {set_clause} WHERE id = %s"  # Only update the user with the given ID

    # Prepare the values for the query
    values = [update_fields[field] for field in update_columns]
    values.append(user_id)  # Add the user ID at the end to target the correct record

    # Execute the query using parameterized inputs
    with connection.cursor() as cursor:
        cursor.execute(query, values)  # Safely pass the values to the query
        connection.commit()  # Commit the transaction to save the changes

    return True  # Indicate that the update was successful


def total_users():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*) 
            FROM auth_user 
            WHERE whm = 0
        """)
        row = cursor.fetchone()
        
        if row:
            return row[0]  # Return the count of users excluding those with whm=1
        return 0  # Return 0 if no users are found

      
def import_database(username, file_path, db_name):
    db_name = replace_first_with_underscore(db_name)
    db_name = f"{username}_{db_name}"
    db_password = settings.DATABASES['default']['PASSWORD']
    
    try:
        if not re.match(r'^[a-zA-Z0-9_]+$', db_name):
            raise ValueError("Invalid characters in database name")
    except ValueError as e:
        raise Exception(str(e))
        
    env = os.environ.copy()
    env["MYSQL_PWD"] = db_password

    try:
        if file_path.endswith('.gz'):
            # Decompress and import the .gz file without shell=True
            gunzip_proc = subprocess.Popen(["gunzip", "-c", file_path], stdout=subprocess.PIPE)
            mysql_proc = subprocess.Popen(
                ["mysql", "-u", "root", db_name],
                env=env,
                stdin=gunzip_proc.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            # Allow gunzip_proc to receive a SIGPIPE if mysql_proc exits
            gunzip_proc.stdout.close()
            stdout, stderr = mysql_proc.communicate()
            if mysql_proc.returncode != 0:
                raise subprocess.CalledProcessError(mysql_proc.returncode, "mysql", stderr)
        else:
            # Direct import if not compressed
            with open(file_path, "r") as f:
                subprocess.run(
                    ["mysql", "-u", "root", db_name],
                    env=env,
                    stdin=f,
                    check=True
                )
    except subprocess.CalledProcessError as e:
        raise Exception(f"Error importing database: {e}")
        
        
def export_database(username, file_path, db_name):
    db_name = replace_first_with_underscore(db_name)
    db_name = f"{username}_{db_name}"
    db_password = settings.DATABASES['default']['PASSWORD']
    
    try:
        if not re.match(r'^[a-zA-Z0-9_]+$', db_name):
            raise ValueError("Invalid characters in database name")
    except ValueError as e:
        raise Exception(str(e))
        
    env = os.environ.copy()
    env["MYSQL_PWD"] = db_password
    
    try:
        with open(file_path, "w") as f:
            subprocess.run(
                ["mysqldump", "-u", "root", db_name],
                env=env,
                stdout=f,
                check=True
            )
    except subprocess.CalledProcessError as e:
        raise Exception(f"Error exporting database: {e}")   

def repair_database(username, db_name):
    db_name = replace_first_with_underscore(db_name)
    db_name = f"{username}_{db_name}"
    db_password = settings.DATABASES['default']['PASSWORD']
    
    try:
        if not re.match(r'^[a-zA-Z0-9_]+$', db_name):
            raise ValueError("Invalid characters in database name")
    except ValueError as e:
        raise Exception(str(e))
        
    env = os.environ.copy()
    env["MYSQL_PWD"] = db_password
    
    try:
        subprocess.run(
            ["mysqlcheck", "-u", "root", "--repair", "--databases", db_name],
            env=env,
            check=True
        )
        print(f"Database {db_name} repaired successfully.")
    except subprocess.CalledProcessError as e:
        raise Exception(f"Error repairing database: {e}")
        
        
def create_backup(userid, backup_record,schedule=None):
    username = get_user_data_by_id(userid).get('username')
    #username = "osman"
    try:
        #db_name = "osman_88"  # db_name should be a string
        backup_folder = f"backup_{username}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
        if schedule:
            backup_file = f"{schedule}_{backup_folder}.tar.gz"
        else:
            backup_file = f"{backup_folder}.tar.gz"

        local_dirp = f"/home/{username}/backup"
        local_dir = f"/home/{username}/backup/{backup_folder}"
        if backup_record.category == 'cyberpanel':
            local_dir_home = f"/home/{username}/backup/{backup_folder}/public_html"
        elif backup_record.category == 'cpanel':
            local_dir_home = f"/home/{username}/backup/{backup_folder}/homedir"
        else:
            local_dir_home = f"/home/{username}/backup/{backup_folder}/home"


        
        home_dir = f"/home/{username}/"
        if not os.path.exists(local_dir):
            os.makedirs(local_dir)
            set_permissions_and_ownership_all(local_dir,username)
            
            
        if not os.path.exists(local_dirp):
            os.makedirs(local_dirp)
            set_permissions_and_ownership_all(local_dirp,username)       
            
        if not os.path.exists(local_dir_home):
            os.makedirs(local_dir_home)
            set_permissions_and_ownership_all(local_dir_home,username)  
              
    
        
        # Assuming export_database is a function to export the DB
        if "database" in backup_record.type or "full" in backup_record.type:
            database_names = get_user_database_info(username)
            for database in database_names:
                if backup_record.category == 'cpanel': 
                    if not os.path.exists(f"{local_dir}/mysql"):
                        os.makedirs(f"{local_dir}/mysql")
                        set_permissions_and_ownership_all(f"{local_dir}/mysql",username)   
                        
                    file_path = os.path.join(f"{local_dir}/mysql", f"{database['db_name']}.sql")
                else:
                    file_path = os.path.join(local_dir, f"{database['db_name']}.sql") 
                
                export_database(username, file_path, database['db_name'])
            # Export the database
        if "file" in backup_record.type or "full" in backup_record.type:
            exclude_dirs = ['backup', '.trash', 'logs', 'tmp']
            for item in os.listdir(home_dir):
                s = os.path.join(home_dir, item)
                
                # Skip directories that are in the exclude_dirs list
                if os.path.isdir(s) and any(exclude in item for exclude in exclude_dirs):
                    continue

                d = os.path.join(local_dir_home, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)  # Recursively copy directories
                    set_permissions_and_ownership_all(d, username)
                else:
                    shutil.copy2(s, d)  # Copy files (including metadata)
                    set_permissions_and_ownership_all(d, username)
            
        
        # Make sure the directory exists
        

        # You should include your backup logic here, for example saving the backup
        # If you are saving it to a file or handling FTP, handle that condition here
        if backup_record.category == 'cpanel':
            create_backup_cpanel(userid, backup_record,local_dir,home_dir)
        else: 
            create_backup_xml(userid, backup_record,local_dir)
            
        #gz_compress(username, local_dir, f"{local_dir}/{backup_folder}", f"{local_dir}/{backup_file}")
        #create_backup(request.user.id,'local')
        local_dirtar = f"backup/{backup_folder}"
        backup_dir = os.path.join('/home', username, local_dirtar)
        selected_items = []
        for item in os.listdir(backup_dir):
            item_path = os.path.join(local_dirtar, item)
            selected_items.append(item_path)
    
        #f_compress(username_string,parent, file_name, target_name, selected_items)
        if backup_record.category == 'cpanel':
            message = gz_compress(username, local_dirtar, backup_dir, f"backup/{backup_file}")
        else:
            message = gz_compress(username, local_dirtar, "", f"backup/{backup_file}",selected_items )            
        
        
        backup_delete(username, local_dirtar)
        if backup_record.path == "ftp":
            local_file = f"/home/{username}/backup/{backup_file}"
            
            upload_to_ftp(backup_record.host, backup_record.user, backup_record.password, local_file, backup_file)
            
        if backup_record.user_access == 1:
            src = f"/home/{username}/backup/{backup_file}"
            dst = f"/home/backup/{backup_file}"
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if os.path.isfile(src):
                shutil.copy2(src, dst)
            
        # Ensure user owns their backup directory and file in File Manager
        set_permissions_and_ownership_all(f"/home/{username}/backup", username)

        return True  # Return success
    except Exception as e:
        logger.error(e)
        print(f"Error creating backup: {e}")
        return False  # Return failure

 
  

def create_backup_xml(userid, backup_record,backup_folder):
    username = get_user_data_by_id(userid).get('username')
    main_domain = Domain.objects.filter(userid=userid).order_by('id').first()
    
    if "full" in backup_record.type:
        # Fetch child domains excluding the main domain
        child_domain = Domain.objects.filter(userid=userid).exclude(domain=main_domain.domain).order_by('id')
        
        for child in child_domain:
            # Construct the path to the vhost.conf file
            vhost_dir = f"/usr/local/lsws/conf/vhosts/{child.domain}"
            vhost_file = os.path.join(vhost_dir, "vhost.conf")
            
            if os.path.exists(vhost_file):
                # Construct new file name with folder name prefix
                folder_name = os.path.basename(vhost_dir)
                new_filename = f"{folder_name}.vhost.conf"
                
                # Destination path
                dest_path = os.path.join(backup_folder, new_filename)
                
                # Ensure the backup folder exists
                os.makedirs(backup_folder, exist_ok=True)
                
                # Copy the vhost.conf file to the backup folder with the new name
                shutil.copy(vhost_file, dest_path)
                print(f"Copied: {vhost_file} to {dest_path}")
                
                
                
        for child in child_domain:
            ssl_source_dir = f"/etc/letsencrypt/live/{child.domain}/"
            
            if os.path.exists(ssl_source_dir):
                # Ensure the backup folder exists
                os.makedirs(backup_folder, exist_ok=True)
                
                # Copy all files from the SSL directory to the backup folder with dynamic domain name as prefix
                for ssl_file in os.listdir(ssl_source_dir):
                    source_file = os.path.join(ssl_source_dir, ssl_file)
                    dest_file = os.path.join(backup_folder, f"{child.domain}.{ssl_file}")  # Add domain name as prefix dynamically
                    if os.path.isfile(source_file):  # Only copy regular files
                        shutil.copy(source_file, dest_file)
                        print(f"Copied SSL file: {source_file} to {dest_file}")
                      
                    
    
    # Root element
    root = ET.Element("metaFile")
    
    # Adding main elements
    ET.SubElement(root, "VERSION").text = "2.3"
    ET.SubElement(root, "BUILD").text = "5"
    ET.SubElement(root, "BackupWholeDir").text = "1"
    ET.SubElement(root, "masterDomain").text = str(main_domain.domain)  # Ensure it's a string
    ET.SubElement(root, "phpSelection").text = f"PHP {main_domain.php}" if main_domain else ""  # Handle None
    ET.SubElement(root, "externalApp").text = username
    ET.SubElement(root, "userName").text = username
    ET.SubElement(root, "userPassword").text = ""
    ET.SubElement(root, "firstName").text = ""
    ET.SubElement(root, "lastName").text = ""
    ET.SubElement(root, "email").text = ""
    ET.SubElement(root, "type").text = "0"
    ET.SubElement(root, "owner").text = str(userid)  # Ensure it's a string
    ET.SubElement(root, "token").text = ""
    ET.SubElement(root, "api").text = "0"
    ET.SubElement(root, "securityLevel").text = "0"
    ET.SubElement(root, "state").text = "ACTIVE"
    ET.SubElement(root, "initWebsitesLimit").text = "0"
    ET.SubElement(root, "aclName").text = username

    # Handle backup types
    if "full" in backup_record.type:
        child_domains = ET.SubElement(root, "ChildDomains")
        child_domain = Domain.objects.filter(userid=userid).exclude(domain=main_domain.domain).order_by('id')
        for child in child_domain:
        # Adding ChildDomains
            domain = ET.SubElement(child_domains, "domain")
            ET.SubElement(domain, "domain").text = child.domain
            ET.SubElement(domain, "phpSelection").text = f"PHP {child.php}"
            ET.SubElement(domain, "path").text = child.path

    if "database" in backup_record.type or "full" in backup_record.type:
        # Adding Databases
        databases = ET.SubElement(root, "Databases")
        database_names = get_user_database_info(username)
        for database in database_names:  # Correct indentation
            db = ET.SubElement(databases, "database")
            ET.SubElement(db, "dbName").text = database['db_name']
            database_users = ET.SubElement(db, "databaseUsers")
            ET.SubElement(database_users, "dbUser").text = database['privileged_users']
            ET.SubElement(database_users, "dbHost").text = database['host']
            ET.SubElement(database_users, "password").text = database['password']
    
    if "full" in backup_record.type:
        ET.SubElement(root, "Aliases")
    
    # Adding DNS Records
        dns_records = ET.SubElement(root, "dnsrecords")
        cip=ip_address = get_server_ip()
     

        dns_data = [
            {"type": "A", "name": main_domain.domain, "content": cip, "priority": "0"},
            {"type": "CNAME", "name": f"www.{main_domain.domain}", "content": main_domain.domain, "priority": "0"},
            {"type": "CNAME", "name": f"ftp.{main_domain.domain}", "content": main_domain.domain, "priority": "0"},
            {"type": "MX", "name": main_domain.domain, "content": f"mail.{main_domain.domain}", "priority": "10"},
            {"type": "A", "name": f"mail.{main_domain.domain}", "content": cip, "priority": "0"},
            {"type": "TXT", "name": main_domain.domain, "content": f"v=spf1 a mx ip4:{cip} ~all", "priority": "0"},
            {"type": "TXT", "name": f"_dmarc.{main_domain.domain}", "content": "v=DMARC1; p=none", "priority": "0"},
            {"type": "TXT", "name": f"_domainkey.{main_domain.domain}", "content": "t=y; o=~;", "priority": "0"},
        ]


        for record in dns_data:
            dns = ET.SubElement(dns_records, "dnsrecord")
            ET.SubElement(dns, "type").text = record["type"]
            ET.SubElement(dns, "name").text = record["name"]
            ET.SubElement(dns, "content").text = record["content"]
            ET.SubElement(dns, "priority").text = record["priority"]
            
    if "email" in backup_record.type or "full" in backup_record.type:
        emails_element = ET.SubElement(root, "emails")
        emails = Emails.objects.filter(userid=userid)
        for email_obj in emails:            
            email_account = ET.SubElement(emails_element, "emailAccount")
            ET.SubElement(email_account, "email").text = email_obj.email
            ET.SubElement(email_account, "password").text =email_obj.password
            ET.SubElement(email_account, "path").text =email_obj.mail
            
            
    if "email" in backup_record.type or "full" in backup_record.type:
        emails_elementf = ET.SubElement(root, "EmailForward")
        forwords = EmailForword.objects.filter(userid=userid)
        for forwords_obj in forwords:            
            email_accountf = ET.SubElement(emails_elementf, "emailAccount")
            ET.SubElement(email_accountf, "email").text = forwords_obj.source
            ET.SubElement(email_accountf, "destination").text =forwords_obj.destination
            ET.SubElement(email_accountf, "path").text =forwords_obj.path
            
            

        
        
    
    
    
    
    
    # Pretty Print XML
    xml_string = ET.tostring(root, encoding="unicode")
    parsed_xml = minidom.parseString(xml_string)
    pretty_xml = parsed_xml.toprettyxml(indent="  ")
    
    # Save to file
    with open(f"{backup_folder}/meta.xml", "w") as file:
        file.write(pretty_xml)
    
    print("Backup XML created successfully.")
    
    
    
    
def create_backup_cpanel(userid, backup_record,backup_folder,home_dir):
    username = get_user_data_by_id(userid).get('username')
    main_domain = Domain.objects.filter(userid=userid).order_by('id').first()
    with open(f"{backup_folder}/homedir_paths", 'w') as file:
            file.write(home_dir)
    
    

    # Handle backup types
    if "full" in backup_record.type:
        #child_domains = ET.SubElement(root, "ChildDomains")
        child_domain = Domain.objects.filter(userid=userid).exclude(domain=main_domain.domain).order_by('id')
        with open(f"{backup_folder}/sds2", "w") as child_file:
            for child in child_domain:
                formatted_line = f"{child.domain}={child.path}\n"
                child_file.write(formatted_line)
            
        

    if "database" in backup_record.type or "full" in backup_record.type:
        # Get database information for the user
        database_names = get_user_database_info(username)

        # Open the SQL file for writing
        with open(f"{backup_folder}/mysql.sql", "w") as sql_file:
            # Loop through each database and write SQL grant statements
            for database in database_names:
                db_name = database['db_name']
                privileged_users = database['privileged_users']
                host = database['host']
                password = database['password']

                # Write GRANT statements for the main user
                sql_file.write(f"-- Grants for database: {db_name}\n")
                sql_file.write(f"GRANT USAGE ON *.* TO '{privileged_users}'@'{host}' IDENTIFIED BY PASSWORD '{password}';\n")
                sql_file.write(f"GRANT ALL PRIVILEGES ON `{db_name}`.* TO '{privileged_users}'@'{host}';\n\n")

                # Write GRANT statements for the default user
                sql_file.write(f"-- Default user grants for database: {db_name}\n")
                sql_file.write(f"GRANT USAGE ON *.* TO '{username}'@'{host}' IDENTIFIED BY PASSWORD '{password}';\n")
                sql_file.write(f"GRANT ALL PRIVILEGES ON `{db_name}`.* TO '{username}'@'{host}';\n\n")

        
    
    if "full" in backup_record.type:
        #ET.SubElement(root, "Aliases")
    
    # Adding DNS Records
        #dns_records = ET.SubElement(root, "dnsrecords")
        cip=ip_address = get_server_ip()
     

        dns_data = [
            {"type": "A", "name": main_domain.domain, "content": cip, "priority": "0"},
            {"type": "CNAME", "name": f"www.{main_domain.domain}", "content": main_domain.domain, "priority": "0"},
            {"type": "CNAME", "name": f"ftp.{main_domain.domain}", "content": main_domain.domain, "priority": "0"},
            {"type": "MX", "name": main_domain.domain, "content": f"mail.{main_domain.domain}", "priority": "10"},
            {"type": "A", "name": f"mail.{main_domain.domain}", "content": cip, "priority": "0"},
            {"type": "TXT", "name": main_domain.domain, "content": f"v=spf1 a mx ip4:{cip} ~all", "priority": "0"},
            {"type": "TXT", "name": f"_dmarc.{main_domain.domain}", "content": "v=DMARC1; p=none", "priority": "0"},
            {"type": "TXT", "name": f"_domainkey.{main_domain.domain}", "content": "t=y; o=~;", "priority": "0"},
        ]


        for record in dns_data:
            print("must remove.")
            
            #dns = ET.SubElement(dns_records, "dnsrecord")
            #ET.SubElement(dns, "type").text = record["type"]
            #ET.SubElement(dns, "name").text = record["name"]
            #ET.SubElement(dns, "content").text = record["content"]
            #ET.SubElement(dns, "priority").text = record["priority"]
            
            

        

    
    
    print("Backup XML created successfully.")
    
    
def restore_backup(backup_file,btype,category,passwords):
    
    try:
        # Define paths
        backup_folder = backup_file.replace(".tar.gz", "")
        os.makedirs('/home/backup', exist_ok=True)
        backup_file_path = f"/home/backup/{backup_file}"

        # If not in /home/backup/, scan /home/*/backup/ to find the file
        if not os.path.exists(backup_file_path) and os.path.exists('/home'):
            for u in os.listdir('/home'):
                candidate = os.path.join('/home', u, 'backup', backup_file)
                if os.path.isfile(candidate):
                    shutil.copy2(candidate, backup_file_path)
                    break

        if category == 'cpanel':
            local_dir = f"/home/backup/{backup_folder}/{backup_folder}"
        else:
            local_dir = f"/home/backup/{backup_folder}"

        os.makedirs(local_dir, exist_ok=True)

        # Extract the backup file
        if not os.path.exists(backup_file_path):
            error_message = f"Backup file not found: {backup_file_path}"
            logger.error(error_message)
            return False, error_message

        with tarfile.open(backup_file_path, "r:gz") as tar:
            tar.extractall(path=local_dir)

        backup_types = btype.split(',')
        if "file" in backup_types or "full" in backup_types:
            if category == 'cyberpanel':
                source_dir = os.path.join(local_dir, "public_html")
            elif category == 'cpanel':
                source_dir = os.path.join(local_dir, "homedir")
            else:
                source_dir = os.path.join(local_dir, "home")
                
                
                

            if not os.path.exists(source_dir):
                error_message = f"Source directory not found: {source_dir}"
                logger.error(error_message)
                return False, error_message
             
            if category == 'cpanel':
                homedir_path = os.path.join(local_dir, "homedir_paths")
                if not os.path.exists(homedir_path):
                    error_message = f"homedir_paths file not found in {local_dir}."
                    logger.error(error_message)
                    return False, error_message
        
            
                with open(homedir_path, "r") as file:
                    home_dir = file.read().strip()
            
                username = extract_username_from_homedir_cpanel(home_dir)
                if not username:
                    error_message = f"Username not found in home directory path: {home_dir}."
                    logger.error(error_message)
                    return False, error_message
                    
            if category == 'cyberpanel' or category == 'default':
                meta_file_path = os.path.join(local_dir, "meta.xml")
                tree = ET.parse(meta_file_path)
                root = tree.getroot()
                username_element = root.find("userName")
                username = username_element.text.strip()

            
            if username:
                
                home_dir = f"/home/{username}/"
                
                # Check if the home directory exists; if not, create it
                if not os.path.exists(home_dir):
                    os.makedirs(home_dir)

                # Iterate through each item in the source directory
                for item in os.listdir(source_dir):
                    s = os.path.join(source_dir, item)  # Source path
                    d = os.path.join(home_dir, item)    # Destination path

                    try:
                        # Check if the item is a directory or file
                        if os.path.isdir(s):
                            # Copy the directory and its contents, overwriting if the destination exists
                            shutil.copytree(s, d, dirs_exist_ok=True)
                        else:
                            # Copy the file, overwriting if the destination exists
                            shutil.copy2(s, d)

                        logger.error(f"copying {s} to {d}")
                        set_permissions_and_ownership_all(d, username)

                    except Exception as e:
                        # Log any error that occurs during the copy process for the current item
                        logger.error(f"Error copying {s} to {d}: {e}")
                        continue  # Skip the current item and continue with the next item

            
        
        
        # Clean up extracted backup files
        #shutil.rmtree(local_dir)
        
        
        if category == 'cpanel':
            success, message = restore_backup_cpanel(local_dir,passwords)
            if not success:
                return False, message
            #create_backup_cpanel(userid, backup_record,local_dir,home_dir)
        else: 
            success, message = restore_backup_xml(local_dir,passwords,category)
            if not success:
                return False, message
                
                
        """        
        if "database" in backup_record.type or "full" in backup_record.type:
            database_names = get_user_database_info(username)
            for database in database_names:
                if backup_record.category == 'cpanel':
                    db_file_path = os.path.join(local_dir, "mysql", f"{database['db_name']}.sql")
                else:
                    db_file_path = os.path.join(local_dir, f"{database['db_name']}.sql")

                if not os.path.exists(db_file_path):
                    logger.error(f"Database backup file not found: {db_file_path}")
                    continue

                import_database(username, db_file_path, database['db_name'])        
            
        """
        success_message = "Restore successful"
        return True, success_message  # Restore successful
    except Exception as e:
        error_message = f"Error restoring backup: {e}"
        logger.error(error_message)
        return False, error_message  # Restore failed    

def restore_backup_xml(backup_folder,passwords,category):
    
    
    meta_file_path = os.path.join(backup_folder, "meta.xml")

    if not os.path.exists(meta_file_path):
        error_message = f"meta.xml file not found in backup folder: {backup_folder}"
        logger.error(error_message)
        return False, error_message

    try:
        
        tree = ET.parse(meta_file_path)
        root = tree.getroot()

        username_element = root.find("userName")
        if username_element is None or not username_element.text or username_element.text.strip() == "":
            error_message = "Error: 'userName' tag missing or empty in meta.xml"
            logger.error(error_message)
            return False, error_message
        username = username_element.text.strip()
        
        main_domain = root.find("masterDomain").text
        php_selection = extract_php_version(root.find("phpSelection").text)
        
        success, message = create_new_user(username, passwords, username, username, "mycp@example.com", "1", main_domain, php_selection)
        if not success:
            return False, message
        
        cuser = User.objects.get(username=username)
        userids=cuser.id

        # Restore child domains
        child_domains = root.find("ChildDomains")
        if child_domains is not None:
            for child in child_domains.findall("domain"):
                domain_name = child.find("domain").text
                php_version = extract_php_version(child.find("phpSelection").text.replace("PHP ", ""))
                domain_paths = child.find("path").text
                domain_path1 = remove_home_prefix(domain_paths)
                domain_path = f"/home/{username}/{domain_path1}"
                

                success, message = create_domain_instance(username, domain_path, php_version, domain_name)
                if success:
                    manage_virtual_host(domain_name, username)
                    manage_listener_mapping("add", domain_name)
                    manage_ssl_listener_mapping("add", domain_name)
                else:
                    return False, message
                
                

                # Restore vhost.conf files
                vhost_file = os.path.join(backup_folder, f"{domain_name}.vhost.conf")
                if os.path.exists(vhost_file):
                    vhost_dir = f"/usr/local/lsws/conf/vhosts/{domain_name}"
                    os.makedirs(vhost_dir, exist_ok=True)
                    shutil.copy(vhost_file, os.path.join(vhost_dir, "vhost.conf"))
                    
                    if category == 'cyberpanel':
                        vhost_directory = f"/usr/local/lsws/conf/vhosts/{domain_name}"
                        vhost_file_path = os.path.join(vhost_directory, "vhost.conf")
                        replace_docroot_in_virtual_conf(vhost_file_path, domain_path)
                        add_user_and_set_folder_permissions(username, f"/home/{username}", domain_path)
                    
                    
                    
                    
        
        
        
                    #set_permissions_and_ownership_all(vhost_dir, username)

                # Restore SSL certificates
                ssl_source_dir = os.path.join(backup_folder, f"{domain_name}.*")
                ssl_dest_dir = f"/etc/letsencrypt/live/{domain_name}/"
                if os.path.exists(ssl_source_dir):
                    os.makedirs(ssl_dest_dir, exist_ok=True)
                    for ssl_file in os.listdir(backup_folder):
                        if ssl_file.startswith(f"{domain_name}."):
                            source_file = os.path.join(backup_folder, ssl_file)
                            dest_file = os.path.join(ssl_dest_dir, ssl_file.replace(f"{domain_name}.", ""))
                            shutil.copy(source_file, dest_file)
                            #set_permissions_and_ownership_all(dest_file, username)

        # Restore databases
        databases = root.find("Databases")
        if databases is not None:
            for db in databases.findall("database"):
                db_name1 = db.find("dbName").text
                db_user1 = db.find("databaseUsers/dbUser").text
                db_host = db.find("databaseUsers/dbHost").text
                db_password = db.find("databaseUsers/password").text
                db_user = replace_first_with_underscore(db_user1)
                db_name = replace_first_with_underscore(db_name1)
                create_database(username, db_name)
                create_database_and_user("", username, db_name, db_user, db_password, is_backup=True)
                sql_file_path = os.path.join(backup_folder, f"{db_name1}.sql")
                if os.path.exists(sql_file_path):
                    import_database(username, sql_file_path, f"{username}_{db_name}")
                


        # Restore DNS records
        dns_records = root.find("dnsrecords")
        if dns_records is not None:
            for dns in dns_records.findall("dnsrecord"):
                dns_type = dns.find("type").text
                dns_name = dns.find("name").text
                dns_content = dns.find("content").text
                dns_priority = dns.find("priority").text

                # Add logic to restore DNS records (e.g., using an API or database)
                # Example: create_dns_record(main_domain, dns_type, dns_name, dns_content, dns_priority)

        # Restore email accounts
        emails = root.find("emails")
        if emails is not None:
            for email in emails.findall("emailAccount"):
                email_address = email.find("email").text
                email_password = email.find("password").text
                email_path = email.find("path").text

                #create_email_account(userid, email_address, email_password, email_path)

        # Restore email forwards
        email_forwards = root.find("EmailForward")
        if email_forwards is not None:
            for forward in email_forwards.findall("emailAccount"):
                source_email = forward.find("email").text
                destination_email = forward.find("destination").text
                forward_path = forward.find("path").text

                #create_email_forward(userid, source_email, destination_email, forward_path)
        suc_message = f"Successfully restored backup" 
        return True, suc_message  # Restore successful
    except Exception as e:
        error_message = f"Error restoring backup from XML: {e}"
        logger.error(error_message)
        return False, error_message 


def restore_backup_cpanel(backup_folder, passwords):
    
    try:
        # Check if the homedir_paths file exists
        homedir_path = os.path.join(backup_folder, "homedir_paths")
        if not os.path.exists(homedir_path):
            error_message = f"homedir_paths file not found in {backup_folder}."
            logger.error(error_message)
            return False, error_message

        # Read the home directory path
        with open(homedir_path, "r") as file:
            home_dir = file.read().strip()

        # Extract the username from the home directory path
        username = extract_username_from_homedir_cpanel(home_dir)
        if not username:
            error_message = f"Username not found in home directory path: {home_dir}."
            logger.error(error_message)
            return False, error_message
            
          
        success, main_domain = get_main_domain_cpanel(backup_folder)
        if not main_domain:
            return False, message
            
           
        success, message = create_new_user(username, passwords, username, username, "mycp@example.com", "1", main_domain, "8.1")
        if success:
            tls_file_path = f"{backup_folder}/apache_tls/{main_domain}"
            if os.path.exists(tls_file_path):
                tls_content = read_tls_content_from_file(tls_file_path)
                save_tls_components_by_domain(main_domain, tls_content)
               
        else:
            return False, message
                
                 
            
        restore_domains_cpanel(username, backup_folder)
        
        db_info_list = extract_db_info_from_sql_cpanel(backup_folder)
        
        for db_info in db_info_list:
            db_user1 = extract_db_user_from_sql_cpanel(backup_folder,db_info['db_name'])
            db_password = extract_db_pass_from_sql_cpanel(backup_folder,db_user1)
            db_user = replace_first_with_underscore(db_user1)
            db_name = replace_first_with_underscore(db_info['db_name'])
            logger.error(f"Database: {username}, {db_name}, {db_password}, {db_user}")
            
            create_database(username, db_name)
            if db_user and db_name and db_password:
                create_database_and_user("", username, db_name, db_user, db_password, is_backup=True)
            
            sql_file_path = os.path.join(backup_folder, "mysql", f"{db_info['db_name']}.sql")
            if os.path.exists(sql_file_path):
                import_database(username, sql_file_path, f"{username}_{db_name}")
                
                  
             
    
        
        
               
                
        
        
        # Log success
        logger.info(f"Backup restored successfully for user '{username}'.")
        success_message = "Restore successful"
        return True, success_message

    except Exception as e:
        # Log the error and return False with an error message
        error_message = f"Error restoring backup for user '{username}': {e}"
        logger.error(error_message)
        return False, error_message




def restore_domains_cpanel(username, backup_folder):
    
    try:
        # Path to the cache.json file
        cache_json_path = os.path.join(backup_folder, "userdata", "cache.json")
        if not os.path.exists(cache_json_path):
            error_message = f"cache.json file not found in {backup_folder}."
            logger.error(error_message)
            return False, error_message

        # Read the cache.json file
        with open(cache_json_path, "r") as file:
            cache_data = json.load(file)

        # Iterate through the domains in the cache data
        for domain, details in cache_data.items():
            domain_type = details[2]  # Type of domain (parked, main, sub)
            domain_paths = details[4]  # Path of the domain
            php_version = "8.1"  # PHP version (e.g., "ea-php81")

            # Skip the main domain
            if domain_type == "main":
                logger.info(f"Skipping main domain: {domain}.")
                continue
                
            domain_path1 = remove_home_prefix(domain_paths)
            #domain_path = f"/home/{username}/{domain_path1}" 
            result = make_domains(domain, php_version, username, domain_path1, restart=False)
            if result:
                tls_file_path = f"{backup_folder}/apache_tls/{domain}"
                if os.path.exists(tls_file_path):
                    tls_content = read_tls_content_from_file(tls_file_path)
                    save_tls_components_by_domain(domain, tls_content)
            else:
                error_message = f"Failed to create domain '{domain}' for user '{username}'."
                return False, error_message
              
                    
            
            logger.info(f"Domain '{domain}' restored with path '{domain_path1}' and PHP '{php_version}'.")

        # Log success
        success_message = "Domains restored successfully (excluding main domain)."
        logger.info(success_message)
        return True, success_message

    except Exception as e:
        error_message = f"Error restoring domains: {e}"
        logger.error(error_message)
        return False, error_message


def get_main_domain_cpanel(backup_folder):
    
    try:
        # Path to the cache.json file
        cache_json_path = os.path.join(backup_folder, "userdata", "cache.json")
        if not os.path.exists(cache_json_path):
            error_message = f"cache.json file not found in {backup_folder}."
            logger.error(error_message)
            return False, error_message

        # Read the cache.json file
        with open(cache_json_path, "r") as file:
            cache_data = json.load(file)

        # Iterate through the domains to find the main domain
        for domain, details in cache_data.items():
            domain_type = details[2]  # Type of domain (parked, main, sub)
            if domain_type == "main":
                logger.info(f"Main domain found: {domain}.")
                return True, domain

        # If no main domain is found
        error_message = "No main domain found in cache.json."
        logger.error(error_message)
        return False, error_message

    except Exception as e:
        error_message = f"Error retrieving main domain: {e}"
        logger.error(error_message)
        return False, error_message

 

def extract_db_info_from_sql_cpanel(backup_folder):
    
    sql_file_path = os.path.join(backup_folder, "mysql.sql")

    if not os.path.exists(sql_file_path):
        logger.error(f"SQL file does not exist: {sql_file_path}")
        return []

    db_info_list = []
    seen_db_names = set()  # Track seen database names to ignore duplicates

    try:
        with open(sql_file_path, "r") as file:
            for line in file:
                # Remove backslashes and strip whitespace
                line = line.replace("\\", "").strip()

                # Extract database name
                db_name = get_database_name(line)

                # Add to the list if the database name is not None and not a duplicate
                if db_name and db_name not in seen_db_names:
                    seen_db_names.add(db_name)  # Mark this database name as seen
                    db_info_list.append({
                        "db_name": db_name
                    })

        return db_info_list

    except Exception as e:
        logger.error(f"Error processing SQL file: {e}")
        return []
        

def extract_db_user_from_sql_cpanel(backup_folder, db_name):
    
    sql_file_path = os.path.join(backup_folder, "mysql.sql")

    if not os.path.exists(sql_file_path):
        logger.error(f"SQL file does not exist: {sql_file_path}")
        return None

    try:
        with open(sql_file_path, "r") as file:
            for line in file:
                # Remove backslashes and strip whitespace
                line = line.replace("\\", "").strip()

                # Extract username for the specified database name
                username = get_db_username(line, db_name)
                if username:
                    return username  # Return the username as soon as it's found

        # If no match is found after processing the entire file
        #logger.error(f"No username found for database: {db_name}")
        return None

    except Exception as e:
        logger.error(f"Error processing SQL file: {e}")
        return None
        
        
def extract_db_pass_from_sql_cpanel(backup_folder, db_user):
    
    sql_file_path = os.path.join(backup_folder, "mysql.sql")

    if not os.path.exists(sql_file_path):
        logger.error(f"SQL file does not exist: {sql_file_path}")
        return None

    try:
        with open(sql_file_path, "r") as file:
            for line in file:
                # Remove backslashes and strip whitespace
                line = line.replace("\\", "").strip()

                # Extract username for the specified database name
                username = get_password_hash_for_user(line, db_user)
                if username:
                    return username  # Return the username as soon as it's found

        # If no match is found after processing the entire file
        #logger.error(f"No username found for database: {db_name}")
        return None

    except Exception as e:
        logger.error(f"Error processing SQL file: {e}")
        return None        
        
def get_database_name(grant_statement):
    
    # Regex pattern to match the database name in the GRANT statement
    pattern = r"GRANT\s+ALL\s+PRIVILEGES\s+ON\s+`([^`]+)`\.\*\s+TO\s+'[^']+'@'[^']+';"
    
    # Search for the pattern in the grant statement
    match = re.search(pattern, grant_statement)
    
    if match:
        fixed_string = match.group(1).replace("\\", "")
        return fixed_string
    else:
        # Return None if no match is found
        return None

def get_password_hash_for_user(grant_statement, target_username):
    
    # Regex pattern to match the username and password hash in the GRANT statement
    pattern = r"GRANT\s+USAGE\s+ON\s+\*\.\*\s+TO\s+'([^']+)'@'[^']+'\s+IDENTIFIED\s+BY\s+PASSWORD\s+'([^']+)';"
    
    # Search for the pattern in the grant statement
    match = re.search(pattern, grant_statement)
    
    if match:
        username = match.group(1)  # Extract the username
        password_hash = match.group(2)  # Extract the password hash
        
        # Check if the extracted username matches the target username
        if username == target_username:
            return password_hash
    
    # Return None if no match is found or the username doesn't match
    return None

    
def get_db_username(grant_statement, db_name):
    
    # Regex pattern to match the database name and username in the GRANT statement
    pattern = r"GRANT\s+ALL\s+PRIVILEGES\s+ON\s+`([^`]+)`\.\*\s+TO\s+'([^']+)'@'[^']+';"
    
    # Search for the pattern in the grant statement
    match = re.search(pattern, grant_statement)
    
    if match:
        extracted_db_name = match.group(1)  # Extract the database name
        extracted_username = match.group(2)  # Extract the username
        
        # Check if the extracted database name matches the target database name
        # AND if the database name contains an underscore
        if extracted_db_name == db_name and "_" in extracted_username:
            return extracted_username
    
    # Return None if no match is found, the database name doesn't match,
    # or the database name does not contain an underscore
    return None 
        
def extract_username_from_homedir_cpanel(home_dir):
    
    # Split the path into components
    parts = home_dir.split(os.sep)

    # The username is the last component after "/home/"
    if len(parts) >= 3 and parts[1] == "home":
        return parts[2]  # Return the username
    else:
        return None  # Invalid path

def remove_home_prefix(path):
    # Split the path into components
    parts = path.split(os.sep)

    # Check if the path starts with "/home/random_string"
    if len(parts) >= 3 and parts[0] == "" and parts[1] == "home" and parts[2]:
        # Reconstruct the path without the first 3 components
        return os.sep.join(parts[3:])
    else:
        # Return the original path if the prefix is not found
        return path
        
def set_permissions_and_ownership_all(path, username, groupname=None, permissions=None):
    
    if groupname is None:
        groupname = username

    # Validate user and group
    try:
        user_info = pwd.getpwnam(username)
        group_info = grp.getgrnam(groupname)
    except KeyError as e:
        logger.error(e)
        print(f"Error: {e}")
        return False

    def apply_recursively(target_path):
        """
        Applies ownership and permissions to the target path and its contents if it's a directory.
        """
        try:
            # Set ownership
            os.chown(target_path, user_info.pw_uid, group_info.gr_gid)
            print(f"Ownership set for {target_path} to {username}:{groupname}.")

            # Determine and set permissions
            if permissions is None:
                if os.path.isdir(target_path):
                    path_permissions = stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH  # 755
                else:
                    path_permissions = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH  # 644
            else:
                path_permissions = permissions

            os.chmod(target_path, path_permissions)
            print(f"Permissions set for {target_path} to {oct(path_permissions)}.")

            # If it's a directory, recursively apply to contents
            if os.path.isdir(target_path):
                for entry in os.scandir(target_path):
                    apply_recursively(entry.path)
        except Exception as e:
            logger.error(e)
            print(f"Error applying ownership or permissions for {target_path}: {e}")
            return False

    # Start the process for the given path
    apply_recursively(path)
    return True
    

def create_new_user(username, password, first_name, last_name, email, pkg_id, domain_name, php_name):
    try:
        # Check if the username already exists
        if User.objects.filter(username=username).exists():
            error_message = f"Username '{username}' already exists."
            logger.error(error_message)
            return False, error_message

        # Hash the password
        hashed_password = make_password(password)

        # Create a new user
        new_user = User(
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=hashed_password,
        )
        new_user.save()

        # Save the password to a file (if needed)
        password_save_file2(username, password)

        # Update user fields (e.g., package ID)
        last_insert_id = new_user.id
        update_fields = {'pkg_id': pkg_id}
        update_user_data(last_insert_id, update_fields)

        # Set up disk quotas
        package = Package.objects.get(id=pkg_id)
        soft_limit = package.disk_space
        hard_limit = soft_limit + 200 if soft_limit != 0 else 0

        # Uncomment the following line if you want to set disk quotas
        # set_disk_quota(username, f"/home/{username}", soft_limit, hard_limit)

        # Create a domain for the user
        result = make_domains(domain_name, php_name, username, 'public_html', restart=False)
        if not result:
            error_message = f"Failed to create domain '{domain_name}' for user '{username}'."
            logger.error(error_message)
            return False, error_message

        # Set up FTP account
        hashed_ftp_password = hash_password_crypt(password)
        base_dir = f'/home/{username}'
        uid, gid = get_uid_gid(username)

        new_ftp = Ftps(
            user=username,
            dir=base_dir,
            password=hashed_ftp_password,
            userid=last_insert_id,
            QuotaSize=0,
            uid=uid,
            gid=gid,
            status=1
        )
        new_ftp.save()

        # Create an index file in the user's home directory
        home_base_dir = f'/home/{username}/public_html'
        

        # Log success and return True with a success message
        success_message = f"User '{username}' created successfully."
        logger.info(success_message)
        return True, success_message

    except Exception as e:
        error_message = f"Error creating new user '{username}': {e}"
        logger.error(error_message)
        return False, error_message
        
        
def create_domain_instance(username_string, path, php_name, domain_name):
    try:
        # Fetch the User instance
        user = User.objects.get(username=username_string)

        # Create a Domain instance
        domain_instance = Domain(
            userid=user,  # Assign the User instance, not the ID
            domain=domain_name,  # Set the domain name
            path=path,  # Set the domain path
            php=php_name,  # Set the PHP version
            line=1  # Set the line (you can modify this as needed)
        )

        # Save the instance to the database
        domain_instance.save()

        # Get the ID of the newly created domain
        last_insert_id = domain_instance.id

        # Add DNS records for the domain
        add_domain_dns(last_insert_id, domain_name, user.id)

        # Log success and return True with a success message
        success_message = f"Domain '{domain_name}' created successfully."
        logger.info(success_message)
        return True, success_message

    except User.DoesNotExist:
        # Handle the case where the username does not exist
        error_message = f"User '{username_string}' does not exist."
        logger.error(error_message)
        return False, error_message

    except Exception as e:
        # Log the error and return False with an error message
        error_message = f"Error creating domain '{domain_name}': {e}"
        logger.error(error_message)
        return False, error_message
        
        
        

def make_domains(domain_name, php_name, username_string, path, restart=True):
    
    # Normalize and validate inputs
    domain_name = normalize_domains(domain_name.strip())
    if not domain_name:
        return {"success": False, "message": "Invalid domain format."}

    path = path.lstrip('/') or 'public_html'  # Default to 'public_html' if no path is provided
    doc_root = os.path.join("/home", username_string, path)

    try:
        # Check if domain already exists
        if Domain.objects.filter(domain=domain_name).exists():
            return {"success": False, "message": f"The domain '{domain_name}' already exists."}

        # Get user and package information
        user = User.objects.get(username=username_string)
        user_package = Package.objects.filter(id=get_user_data_by_id(user.id).get('pkg_id')).first()
        total_domains_count = Domain.objects.filter(userid=user.id).count()

        # Check if domain limit is exceeded
        if user_package.allowed_domains != 0 and total_domains_count >= user_package.allowed_domains:
            return {"success": False, "message": "Domain add limit exceeded."}

        # Manage listener and virtual host
        if not manage_listener_mapping("add", domain_name):
            return {"success": False, "message": f"Failed to add listener mapping for '{domain_name}'."}

        if not manage_virtual_host(domain_name, username_string):
            return {"success": False, "message": f"Failed to add virtual host for '{domain_name}'."}

        # SSL listener mapping and vhost file creation
        manage_ssl_listener_mapping("add", domain_name)
        create_vhost_file(domain_name, username_string, path)

        # Set folder permissions
        if not add_user_and_set_folder_permissions(username_string, f'/home/{username_string}', doc_root):
            return {"success": False, "message": f"Failed to set folder permissions for '{domain_name}'."}

        # Save domain to database
        domain_instance = Domain(
            domain=domain_name,
            userid=user,
            path=doc_root,
            line = 1,
            php=php_name
        )
        domain_instance.save()

        # Additional configurations
        new_php_version = php_name.replace('.', '')
        add_domain_dns(domain_instance.id, domain_name, user.id)
        change_php_version(domain_name, domain_name + '' + new_php_version, new_php_version)

        # Restart services
        if restart:
            restart_openlitespeed()
            restart_pdns()
        
        
 
        return {"success": True, "message": f"Domain '{domain_name}' added successfully!"}

    except User.DoesNotExist:
        logger.error(f"User '{username_string}' does not exist.")
        return {"success": False, "message": f"User '{username_string}' does not exist."}
    except Exception as e:
        logger.error(f"An error occurred time of main domain add: {str(e)}")
        return {"success": False, "message": f"An error occurred: {str(e)}"}


def normalize_domains(domain_name):
    """Validate and normalize the domain name by stripping unwanted prefixes."""
    
    # Remove 'http://' or 'https://'
    domain_name = re.sub(r'^https?://', '', domain_name)
    
    # Remove 'www.' prefix
    domain_name = re.sub(r'^www\.', '', domain_name)

    # Basic validation: Ensure the domain has at least one dot and only contains valid characters
    if not re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', domain_name):
        return None  # Invalid domain format

    return domain_name  # Return the normalized domain name            
              
              
def extract_php_version(php_string):
    
    # Split the string by spaces
    parts = php_string.split()

    # Iterate through the parts to find the version
    for part in parts:
        if part.replace(".", "").isdigit():  # Check if the part is a version number
            return part

    # Return None if no version is found
    return None              
    
   
def save_tls_components_by_domain(domain, tls_content):
   
    try:
        # Define the base directory for Let's Encrypt
        base_dir = "/etc/letsencrypt/live"
        
        # Create the domain-specific directory
        domain_dir = os.path.join(base_dir, domain)
        os.makedirs(domain_dir, exist_ok=True)

        # Split the content into sections
        sections = tls_content.strip().split("-----BEGIN ")

        # Ensure there are enough sections to extract the private key, certificate, and full chain
        if len(sections) < 4:
            raise ValueError("Invalid TLS content: Missing required sections (private key, certificate, or full chain).")

        # Extract the private key, certificate, and full chain
        private_key = f"-----BEGIN {sections[1].strip()}-----"
        certificate = f"-----BEGIN {sections[2].strip()}-----"
        full_chain = f"-----BEGIN {sections[3].strip()}-----"

        # Save the private key to privkey.pem
        privkey_path = os.path.join(domain_dir, "privkey.pem")
        with open(privkey_path, "w") as file:
            file.write(private_key)

        # Save the certificate to cert.pem
        cert_path = os.path.join(domain_dir, "cert.pem")
        with open(cert_path, "w") as file:
            file.write(certificate)

        # Save the full chain to fullchain.pem
        fullchain_path = os.path.join(domain_dir, "fullchain.pem")
        with open(fullchain_path, "w") as file:
            file.write(tls_content)

        #print(f"Files saved successfully for domain: {domain}")
        #print(f"Private key: {privkey_path}")
        #print(f"Certificate: {cert_path}")
        #print(f"Full chain: {fullchain_path}")

    except Exception as e:
        logger.info(f"Error saving TLS components for domain '{domain}': {e}")
        # Optionally, log the error or handle it as needed


def read_tls_content_from_file(file_path):
    
    try:
        with open(file_path, "r") as file:
            return file.read()
    except Exception as e:
        logger.info(f"Error reading TLS file '{file_path}': {e}")
        return None


 