import subprocess
import requests
import os
import pwd
import stat
import re
import shutil
import bcrypt
import json
import random
import string
import socket
import grp
#from .database import get_server_ip
from django.core.cache import cache
import ftplib
from datetime import datetime,timedelta
from django.contrib.auth import get_user_model
from urllib.parse import urlparse, parse_qs
import base64
import json
from django.conf import settings
from users.panellogger import *
from .models import * 
import configparser
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from pathlib import Path
from datetime import datetime, timezone as dt_timezone

logger = CpLogger()

def get_license_status(request):
    return "active"


def download_script_only(script_type: str, save_path: str) -> bool:
    
    script_map = {
        'wordpress': 'https://wordpress.org/latest.zip',
        'laravel': 'https://github.com/laravel/laravel/archive/refs/heads/master.zip',
        'joomla': 'https://downloads.joomla.org/cms/joomla4/4-4-0/Joomla_4-4-0-Stable-Full_Package.zip?format=zip',
        'drupal': 'https://www.drupal.org/download-latest/zip',
        'prestashop': 'https://download.prestashop.com/download/releases/prestashop_8.1.3.zip',
    }

    if script_type not in script_map:
        return False

    url = script_map[script_type]

    try:
        subprocess.run(["wget", "-O", save_path, url], check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def ensure_group_exists_and_create_user(username, groups, groupname=None):
    """
    Ensure the user and groups exist. If not, create them.
    Add the user to the specified groups.
    """
    # Use the username as the groupname if not provided
    if groupname is None:
        groupname = username

    # Ensure the specified groups exist
    for group in groups:
        try:
            # Check if the group exists
            grp.getgrnam(group)
            print(f"Group '{group}' already exists.")
        except KeyError:
            # Create the group if it doesn't exist
            try:
                subprocess.run(['sudo', 'groupadd', group], check=True)
                print(f"Group '{group}' created successfully.")
            except subprocess.CalledProcessError as e:
                print(f"Error creating group '{group}': {e}")
                return False

    # Check if the user exists
    try:
        subprocess.run(['getent', 'passwd', username], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"User '{username}' already exists.")
    except subprocess.CalledProcessError:
        # User does not exist, so create it
        try:
            # Use the settings to detect the OS (as you originally wanted)
            if getattr(settings, "MY_OS_NAME", "linux") == "ubuntu":
                subprocess.run(['sudo', 'adduser', '--disabled-password', '--gecos', '', '--ingroup', groupname, username], check=True)
                print(f"User '{username}' created successfully on Ubuntu.")
            else:
                subprocess.run(['sudo', 'useradd', '-g', groupname, '-m', username], check=True)
                print(f"User '{username}' created successfully on non-Ubuntu system.")
        except subprocess.CalledProcessError as e:
            print(f"Error creating user '{username}': {e}")
            return False

    # Add the user to the specified groups
    for group in groups:
        try:
            subprocess.run(['sudo', 'usermod', '-aG', group, username], check=True)
            print(f"User '{username}' added to group '{group}'.")
        except subprocess.CalledProcessError as e:
            print(f"Error adding user '{username}' to group '{group}': {e}")
            return False

    return True
    
    
def get_server_ips_old():
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

def get_server_ips():
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
                        # logger.info(f"Read cached IP from file: {ip}")
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


        
def convert_to_human_readable(size_in_kb):
    if size_in_kb < 1024:
        return f"{size_in_kb:.2f} KB"
    elif size_in_kb < 1024**2:
        return f"{(size_in_kb / 1024):.2f} MB"
    elif size_in_kb < 1024**3:
        return f"{(size_in_kb / 1024**2):.2f} GB"
    else:
        return f"{(size_in_kb / 1024**3):.2f} TB"

def convert_to_kb(size_str):
    if not size_str or not isinstance(size_str, str):
        return 0  # or None, depending on your use case

    size_str = size_str.strip()
    if not size_str:
        return 0

    try:
        size = float(size_str[:-1])
        unit = size_str[-1].upper()
    except ValueError:
        return 0  # in case parsing fails
        
        
        
    # Convert to kilobytes (KB)
    if unit == 'K':  # Kilobytes
        return size
    elif unit == 'M':  # Megabytes
        return size * 1024
    elif unit == 'G':  # Gigabytes
        return size * 1024 * 1024
    elif unit == 'T':  # Terabytes
        return size * 1024 * 1024 * 1024
    else:
        return size  # Assuming size is already in KB if no unit is provided

def get_disk_usage(user_directory):
    """Calculate the disk usage of the specified user directory."""
    if not os.path.exists(user_directory):
        return 0  # Return 0 if the directory does not exist

    result = subprocess.run(['du', '-sh', user_directory], capture_output=True, text=True)

    if result.returncode != 0:
        return 0  # Return 0 in case of an error with the `du` command

    usage = result.stdout.split()[0]  # Extracts the size with unit (e.g., 1.5M, 200K)
    size_in_kb = convert_to_kb(usage)  # Convert to kilobytes
    return convert_to_human_readable(size_in_kb)
    
def calculate_total_database_size(database_names):
    total_size = 0  # Initialize total size

    for db in database_names:
        size_display = db['size_display']  # Get size display string
        numeric_part = size_display.split()[0]  # Extract numeric part (e.g., '100.8')
        unit = size_display.split()[1]  # Extract unit (e.g., 'MB')

        # Convert the numeric part to float for accurate calculations
        size_in_float = float(numeric_part)

        # Convert the size to bytes based on the unit
        if unit == 'MB':
            db_size_in_bytes = size_in_float * 1024 * 1024  # Convert MB to bytes
        elif unit == 'KB':
            db_size_in_bytes = size_in_float * 1024  # Convert KB to bytes
        elif unit == 'GB':
            db_size_in_bytes = size_in_float * 1024 * 1024 * 1024  # Convert GB to bytes
        else:
            db_size_in_bytes = 0  # Handle unknown units if necessary

        total_size += db_size_in_bytes  # Add to total size in bytes

    return total_size  # Return total size
    
    
def size_display(size_in_bytes):
    """Convert bytes into a human-readable format."""
    # Ensure size_in_bytes is an integer
    try:
        size_in_bytes = int(size_in_bytes)
    except ValueError:
        # Handle case where size_in_bytes is not a valid number
        return "Invalid size"

    if size_in_bytes >= 1024**3:
        return f"{round(size_in_bytes / 1024**3, 2)} GB"
    elif size_in_bytes >= 1024**2:
        return f"{round(size_in_bytes / 1024**2, 2)} MB"
    elif size_in_bytes >= 1024:
        return f"{round(size_in_bytes / 1024, 2)} KB"
    else:
        return f"{size_in_bytes} Bytes" 

def check_file_permission(file_path, username_string):
    
    # Check if the file exists
    if not os.path.isfile(file_path):
        return False, f"File not found {file_path}."

    # Get file's stats to check ownership and permissions
    try:
        file_stat = os.stat(file_path)
    except Exception as e:
        return False, f"Error accessing file: {e}"

    # Get the file owner's username
    file_owner = pwd.getpwuid(file_stat.st_uid).pw_name

    # Check if the logged-in user is the owner of the file
    if file_owner != username_string:
        return False, "You don't have permission to access this file."

    # Check if the user has read and write permissions to the file
    if not (file_stat.st_mode & stat.S_IWUSR and file_stat.st_mode & stat.S_IRUSR):
        return False, "You don't have the required permissions to edit this file."

    return True, "Permission granted."


def check_read_permission(file_path, username_string):
    # Check if the file exists
    if not os.path.isfile(file_path):
        return False, f"File not found: {file_path}"

    # Get file's stats to check ownership and permissions
    try:
        file_stat = os.stat(file_path)
    except Exception as e:
        return False, f"Error accessing file: {e}"

    # Get the file owner's username
    try:
        file_owner = pwd.getpwuid(file_stat.st_uid).pw_name
    except KeyError:
        return False, f"Unable to retrieve owner information for the file."

    # Check if the logged-in user is the owner of the file
    if file_owner != username_string:
        return False, "You don't have permission to access this file."

    # Check if the user has read (S_IRUSR) permission
    if not (file_stat.st_mode & stat.S_IRUSR):  # Check for read permission
        return False, "You don't have read permission for this file."

    return True, "Read permission granted."

def check_file_folder_permission(path, username_string):
    # Check if the path exists and is either a file or a directory
    if not os.path.exists(path):
        return False, f"Path not found: {path}."

    # Get the path's stats to check ownership and permissions
    try:
        path_stat = os.stat(path)
    except Exception as e:
        return False, f"Error accessing path: {e}"

    # Get the file or directory owner's username
    path_owner = pwd.getpwuid(path_stat.st_uid).pw_name

    # Check if the logged-in user is the owner of the file or directory
    if path_owner != username_string:
        return False, "You don't have permission to access this path."

    # Check if the user has read and write permissions
    if os.path.isfile(path):
        # For files: check read and write permissions for the owner
        if not (path_stat.st_mode & stat.S_IWUSR and path_stat.st_mode & stat.S_IRUSR):
            return False, "You don't have the required permissions to edit this file."
    elif os.path.isdir(path):
        # For directories: check read, write, and execute permissions for the owner
        if not (path_stat.st_mode & stat.S_IWUSR and path_stat.st_mode & stat.S_IRUSR and path_stat.st_mode & stat.S_IXUSR):
            return False, "You don't have the required permissions to access this directory."

    return True, "Permission granted."    

def check_read_file_folder_permission(path, username_string):
    # Check if the path exists (file or directory)
    if not os.path.exists(path):
        return False, f"Path not found: {path}."

    # Get the path's stats to check ownership and permissions
    try:
        path_stat = os.stat(path)
    except Exception as e:
        return False, f"Error accessing path: {e}"

    # Get the owner of the path (file or directory)
    try:
        path_owner = pwd.getpwuid(path_stat.st_uid).pw_name
    except KeyError:
        return False, f"Unable to retrieve owner information for the path."

    # Check if the logged-in user is the owner of the path
    if path_owner != username_string:
        return False, "You don't have permission to access this path."

    # Check if the user has read permission (S_IRUSR) for files and directories
    if os.path.isfile(path):
        # For files: check read permission (S_IRUSR)
        if not (path_stat.st_mode & stat.S_IRUSR):
            return False, "You don't have read permission for this file."
    elif os.path.isdir(path):
        # For directories: check read permission (S_IRUSR)
        if not (path_stat.st_mode & stat.S_IRUSR):
            return False, "You don't have read permission for this directory."

    return True, "Read permission granted."


def remove_home_anyname(file_path):
    # Check if the file path starts with /home/
    if file_path.startswith('/home/'):
        # Split the path to remove the '/home/{random_user}/' part
        parts = file_path.split('/', 3)  # Split into 4 parts, ensuring we only remove the first part of the path
        if len(parts) > 3:
            return '/' + parts[3]  # Return the path after '/home/random_user/'
    return file_path  # If it doesn't start with /home, return as-is
    
    
def ensure_user_home_prefix(file_path, username):
    if file_path is None:
        raise ValueError("file_path cannot be None")

    user_home = f"/home/{username}/"

    # Check if the path already starts with /home/{username}/
    if not file_path.startswith(user_home):
        # Add the prefix if it's missing
        file_path = os.path.join(user_home, file_path.lstrip('/'))

    return file_path
    
    
def hash_password_with_crypt(password):
    # Generate a bcrypt hash
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    # Prefix with {CRYPT}
    return f'{{CRYPT}}{hashed_password}'    


def hash_password_crypt(password):
    # Generate a bcrypt hash
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    # Prefix with {CRYPT}
    return hashed_password  


def get_uid_gid(username):
    try:
        user_info = pwd.getpwnam(username)
        uid = user_info.pw_uid
        gid = user_info.pw_gid
        return uid, gid
    except KeyError:
        print(f"User '{username}' not found.")
        return None, None   
        

def create_ini_file(domain):
    base1 = "/usr/local/olspanel/mypanel/3rdparty/rainloop/data"
    base2 = "/usr/local/lsws/Example/html/webmail/data"

    # choose base by checking ONLY the data folder
    if os.path.isdir(base1):
        base = base1
    elif os.path.isdir(base2):
        base = base2
    else:
        print("No valid data directory found.")
        return

    file_path = f"{base}/_data_/_default_/domains/{domain}.ini"

    
    # Check if the file already exists
    if os.path.exists(file_path):
        print(f"{file_path} already exists. No new file created.")
        return  # Exit the function if the file exists

    # Generate random IP addresses
    imap_host = get_server_ips()
    smtp_host = get_server_ips()

    # Define the content for the INI file
    content = f"""\
imap_host = "{imap_host}"
imap_port = 993
imap_secure = "SSL"
imap_short_login = Off
sieve_use = Off
sieve_allow_raw = Off
sieve_host = ""
sieve_port = 4190
sieve_secure = "None"
smtp_host = "{smtp_host}"
smtp_port = 587
smtp_secure = "TLS"
smtp_short_login = Off
smtp_auth = On
smtp_php_mail = Off
white_list = ""
"""

    # Write the content to the specified file
    with open(file_path, 'w') as ini_file:
        ini_file.write(content)

    print(f"{file_path} has been created.")


def is_valid_email_username(username):
    # Define the pattern for a valid username
    # Allowed: Letters, digits, underscores, periods, and hyphens
    # Length: 3-20 characters
    pattern = r'^[a-zA-Z0-9][a-zA-Z0-9._-]{1,18}[a-zA-Z0-9]$'
    
    # Check if the username matches the pattern
    return bool(re.match(pattern, username))   


def human_readable_to_bytes(size):
    if not size:
        return 0
    # Define the conversion factors
    size_mapping = {
        'B': 1,
        'KB': 1024,
        'MB': 1024**2,
        'GB': 1024**3,
        'TB': 1024**4,
        'K': 1024,
        'M': 1024**2,  # Short form for MB
        'G': 1024**3,  # Short form for GB
        'T': 1024**4   # Short form for TB
    }
    
    # Remove spaces and convert to upper case
    size = size.strip().upper()
    
    # Loop through the suffixes in descending order of length
    for suffix in sorted(size_mapping.keys(), key=len, reverse=True):
        if size.endswith(suffix):
            # Extract the numeric part and convert it to float
            number = float(size[:-len(suffix)].strip())
            return int(number * size_mapping[suffix])
    
    # If no valid suffix is found, assume it's in bytes
    return int(size)

def get_cached_disk_usage(path, timeout=300):
    # Try to get cached disk usage
    cached_usage = cache.get(path)
    if cached_usage is None:
        # If not cached, fetch and cache it
        cached_usage = get_disk_usage(path)
        cache.set(path, cached_usage, timeout)
    return cached_usage   


def check_limit(value):
    if value == 0 or value == "0" or value == "0 Bytes":
        return '∞'
    return value
    
def is_valid_email(email):
    """ Validate the destination email format. """
    regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(regex, email) is not None   

def delete_path(cpath):
    # Check if the directory exists
    if os.path.exists(cpath):
        try:
            shutil.rmtree(cpath)  # Remove the directory and all its contents
            print(f'Successfully deleted: {cpath}')
        except Exception as e:
            print(f'Error deleting directory: {e}')
    else:
        print(f'The directory does not exist: {cpath}') 

def run_command(command):
    try:
        # Run the command using subprocess
        result = subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
        
        # Check if the command was successful
        if result.returncode == 0:
            print(f"Command executed successfully: {command}")
            print(f"Output: {result.stdout}")
        else:
            print(f"Command failed with return code {result.returncode}")
            print(f"Error: {result.stderr}")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while executing the command: {e}")
        print(f"Return code: {e.returncode}")
        print(f"Output: {e.output}")
        print(f"Error: {e.stderr}")


def add_script_filter(email):
    file_path = "/etc/postfix/script_filter"
     # Construct the filter line
    virtualfilter = f"{email} FILTER {email}pipe:dummy\n"
    
    # Check if the file exists
    if not os.path.exists(file_path):
        # Create the file and write the line
        with open(file_path, 'w') as f:
            f.write(virtualfilter)
            print(f"File created and line added to {file_path}: {virtualfilter.strip()}")
    else:
        # File exists, check for the line
        with open(file_path, 'r') as f:
            contents = f.readlines()
            # Check if the line is already in the file
            if virtualfilter not in contents:
                with open(file_path, 'a') as f:
                    f.write(virtualfilter)
                    print(f"Line added to {file_path}: {virtualfilter.strip()}")
            else:
                print(f"Line already exists in {file_path}: {virtualfilter.strip()}")
                

def add_master(email, username, path):
    master_cf_path="/etc/postfix/master.cf"
    line_to_add = f"{email}pipe unix - n n - - pipe flags=Rq user={username} argv={path} -f $(sender) -- $(recipient)\n"
    
    # Check if the master.cf file exists
    if not os.path.exists(master_cf_path):
        print(f"Error: {master_cf_path} does not exist.")
        return
    
    # Check if the line already exists in the file
    with open(master_cf_path, 'r') as f:
        contents = f.readlines()
        if line_to_add not in contents:
            with open(master_cf_path, 'a') as f:
                f.write(line_to_add)
                print(f"Line added to {master_cf_path}: {line_to_add.strip()}")
        else:
            print(f"Line already exists in {master_cf_path}: {line_to_add.strip()}")


def remove_script_filter(email):
    file_path = "/etc/postfix/script_filter"
    virtualfilter = f"{email} FILTER {email}pipe:dummy\n"
    
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            contents = f.readlines()
        
        # Remove the line if it exists
        if virtualfilter in contents:
            contents.remove(virtualfilter)
            with open(file_path, 'w') as f:
                f.writelines(contents)
            print(f"Line removed from {file_path}: {virtualfilter.strip()}")
        else:
            print(f"Line not found in {file_path}: {virtualfilter.strip()}")
    else:
        print(f"File does not exist: {file_path}")  


def remove_master_line(email, username, path):
    master_cf_path = "/etc/postfix/master.cf"
    line_prefix = f"{email}pipe"

    # Check if the master.cf file exists
    if os.path.exists(master_cf_path):
        with open(master_cf_path, 'r') as f:
            contents = f.readlines()

        # Find and remove the line that starts with {email}pipe
        new_contents = [line for line in contents if not line.startswith(line_prefix)]
        
        if len(new_contents) != len(contents):
            with open(master_cf_path, 'w') as f:
                f.writelines(new_contents)
            print(f"Line(s) starting with {line_prefix} removed from {master_cf_path}")
        else:
            print(f"No line starting with {line_prefix} found in {master_cf_path}")
    else:
        print(f"File does not exist: {master_cf_path}")


def manage_cron_jobs(username, cron_command):
    # Step 1: Create a directory for cron jobs if it doesn't exist
    cron_dir = '/var/spool/cronjobs'
    if not os.path.exists(cron_dir):
        os.makedirs(cron_dir)
        print(f"Created directory: {cron_dir}")

    # Step 2: Create the cron job file path for the user
    cron_file_path = os.path.join(cron_dir, username)

    # Step 3: Check if the cron command is not empty
    if not cron_command:
        raise ValueError("Cron command cannot be empty.")

    # Step 4: Check if the command already exists in the user's cron file
    if os.path.exists(cron_file_path):
        with open(cron_file_path, 'r') as cron_file:
            if cron_command in cron_file.read():
                print(f"Cron command already exists for user '{username}': {cron_command}")
                return False  # Indicate that the command was not added because it already exists

    # Step 5: Write the new cron command to the user's cron job file
    with open(cron_file_path, 'a') as cron_file:
        cron_file.write(f"{cron_command}\n")
        print(f"Added cron command for user '{username}': {cron_command}")

    # Step 6: Set the correct permissions for the cron file
    os.chmod(cron_file_path, 0o600)
    print(f"Set permissions for: {cron_file_path}")

    # Step 7: Load the cron job from the file into the user's crontab
    try:
        subprocess.run(['sudo', 'crontab', '-u', username, cron_file_path], check=True)
        print(f"Loaded cron jobs for user: {username}")
    except subprocess.CalledProcessError as e:
        print(f"Error loading cron jobs for user '{username}': {e}")
        raise  # Re-raise the exception for further handling if needed

    # Step 8: Verify the cron jobs
    try:
        output = subprocess.run(['sudo', 'crontab', '-u', username, '-l'], capture_output=True, text=True, check=True)
        print(f"Cron jobs for user '{username}':\n{output.stdout}")
    except subprocess.CalledProcessError as e:
        print(f"Error listing cron jobs for user '{username}': {e}")

    return True  # Indicate that the command was successfully added
    
    
def parse_cron_jobs(username):
    # Path to the user's cron job file
    cron_file_path = os.path.join('/var/spool/cronjobs', username)

    if not os.path.exists(cron_file_path):
        return [f"No cron jobs found for user {username}."]

    parsed_jobs = []
    
    with open(cron_file_path, 'r') as cron_file:
        cron_jobs = cron_file.readlines()

    for line_number, job in enumerate(cron_jobs, start=1):  # Start counting from 1
        parts = job.split()
        if len(parts) < 6:
            continue  # Skip if the job doesn't have enough parts
        
        minute = parts[0]
        hour = parts[1]
        day = parts[2]
        month = parts[3]
        weekday = parts[4]
        command = ' '.join(parts[5:])  # Join the rest as command
        
        parsed_jobs.append({
            'line_number': line_number,  # Add line number
            'minute': minute,
            'hour': hour,
            'day': day,
            'month': month,
            'weekday': weekday,
            'command': command
        })
    
    return parsed_jobs
    
    
def get_cron_job_by_line_number(username, line_number):
    # Path to the user's cron job file
    cron_file_path = os.path.join('/var/spool/cronjobs', username)

    if not os.path.exists(cron_file_path):
        return f"No cron jobs found for user {username}."

    with open(cron_file_path, 'r') as cron_file:
        cron_jobs = cron_file.readlines()

    # Check if the requested line number is valid
    if line_number < 1 or line_number > len(cron_jobs):
        return f"Line number {line_number} is out of range."

    # Retrieve the specific cron job line
    job = cron_jobs[line_number - 1].strip()  # Convert to 0-based index
    parts = job.split()
    if len(parts) < 6:
        return "Invalid cron job format."

    # Parse the parts
    minute = parts[0]
    hour = parts[1]
    day = parts[2]
    month = parts[3]
    weekday = parts[4]
    command = ' '.join(parts[5:])  # Join the rest as command

    # Return a dictionary of the cron job details
    return {
        'line_number': line_number,
        'minute': minute,
        'hour': hour,
        'day': day,
        'month': month,
        'weekday': weekday,
        'command': command
    }
    
    
    
def update_cron_job(username, line_number, new_cron_command):
    cron_file_path = os.path.join('/var/spool/cronjobs', username)

    if not os.path.exists(cron_file_path):
        raise FileNotFoundError(f"No cron job file found for user: {username}")

    # Read all cron jobs
    with open(cron_file_path, 'r') as cron_file:
        cron_jobs = cron_file.readlines()

    # Check if the line_number is valid
    if line_number < 1 or line_number > len(cron_jobs):
        raise ValueError(f"Line number {line_number} is out of range.")

    # Update the specified line (adjusting for zero-based indexing)
    cron_jobs[line_number - 1] = new_cron_command + '\n'  # Append newline character

    # Write the updated cron jobs back to the file
    with open(cron_file_path, 'w') as cron_file:
        cron_file.writelines(cron_jobs)

    # Load the updated cron jobs for the user
    subprocess.run(['sudo', 'crontab', '-u', username, cron_file_path], check=True)
    
    
    
def delete_cron_job_by_line(username: str, line: int) -> bool:
    """
    Deletes a cron job from the user's cron job file based on the line number.

    Args:
        username (str): The username of the user whose cron job is being modified.
        line (int): The line number of the cron job to delete (1-based index).

    Returns:
        bool: True if the cron job was deleted successfully, False otherwise.
    """
    # Step 1: Get the cron job file path for the user
    cron_file_path = os.path.join('/var/spool/cronjobs', username)

    # Step 2: Check if the cron file exists
    if not os.path.exists(cron_file_path):
        return False  # Cron job file does not exist

    # Step 3: Read all cron jobs
    with open(cron_file_path, 'r') as cron_file:
        cron_jobs = cron_file.readlines()

    # Step 4: Check if the line number is valid
    if line < 1 or line > len(cron_jobs):
        return False  # Invalid line number

    # Step 5: Remove the specified line (adjusting for zero-based indexing)
    del cron_jobs[line - 1]  # Remove the cron job line

    # Step 6: Write the updated cron jobs back to the file
    with open(cron_file_path, 'w') as cron_file:
        cron_file.writelines(cron_jobs)

    # Step 7: Reload the updated cron jobs for the user
    try:
        subprocess.run(['sudo', 'crontab', '-u', username, cron_file_path], check=True)
    except subprocess.CalledProcessError:
        return False  # Error updating the crontab

    return True  # Cron job deleted successfully    
    
    
    
 # Function to calculate folder size recursively
def get_folder_size(path):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            if os.path.exists(file_path):
                total_size += os.path.getsize(file_path)
    return total_size
    
    
    


def encode_json_to_base64(data):
    # Convert the JSON data to a string
    json_data = json.dumps(data)

    # Encode the JSON string to Base64
    base64_encoded = base64.b64encode(json_data.encode()).decode()

    return base64_encoded
 
def decode_base64_to_json(base64_string):
    # Decode Base64 string to JSON string
    json_data = base64.b64decode(base64_string).decode()    

    return json_data   
    
def get_phpmyadmin_password(username):
    # Get the path of the project directory
    django_root = settings.BASE_DIR
    if username == 'admin':
        source_file = os.path.join(django_root, 'etc', "mysqlPassword")
    else:
        source_file = os.path.join(django_root, 'etc', f"phpmyadmin_{username}")
    
    # Check if the file exists
    if not os.path.exists(source_file):
        return f"Password file for user {username} not found."

    try:
        # Read the content of the file
        with open(source_file, 'r') as file:
            file_content = file.read()
        
        # Return the file content
        return file_content
    
    except Exception as e:
        # Handle unexpected errors and return the error message
        return f"An error occurred: {str(e)}"
    
    
def password_save_file(username, data):
    new_data = encode(data)
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
        

def encode(data: str) -> str:
    
    # Convert the string to bytes
    data_bytes = data.encode('utf-8')
    # Encode the bytes to Base64
    base64_bytes = base64.b64encode(data_bytes)
    # Convert Base64 bytes back to string
    base64_str = base64_bytes.decode('utf-8')
    # Generate a random 5-character string of lowercase letters
    random_string = ''.join(random.choices(string.ascii_lowercase, k=5))
    # Prepend the random string to the Base64 string
    return random_string + base64_str

def decode(base64_data: str) -> str:
    
    # Remove the first 5 characters (random string) from the string
    base64_str = base64_data[5:]
    # Convert Base64 string to bytes
    base64_bytes = base64_str.encode('utf-8')
    # Decode the Base64 bytes back to original bytes
    decoded_bytes = base64.b64decode(base64_bytes)
    # Convert bytes back to string
    return decoded_bytes.decode('utf-8')
    
    
def get_auto_login_password(username):
    # Get the path of the project directory
    django_root = settings.BASE_DIR
    
    source_file = os.path.join(django_root, 'etc', f"_{username}")
    
    # Check if the file exists
    if not os.path.exists(source_file):
        return f"Password file for user {username} not found."

    try:
        # Read the content of the file
        with open(source_file, 'r') as file:
            file_content = file.read()
        
        # Return the file content
        return decode(file_content)
    
    except Exception as e:
        # Handle unexpected errors and return the error message
        return f"An error occurred: {str(e)}"    
        
        
        
def replace_placeholders_in_wp_config(file_path, replacements):
    
    try:
        # Read the file content
        with open(file_path, 'r') as file:
            content = file.read()

        # Replace placeholders with actual values
        for placeholder, value in replacements.items():
            content = content.replace(placeholder, value)

        # Write the updated content back to the file
        with open(file_path, 'w') as file:
            file.write(content)

        print(f"Successfully updated {file_path} with the provided values.")
    except Exception as e:
        print(f"An error occurred: {e}")   

def generate_virtual_link(domain, path,username):
    
    # Define the default root path pattern
    default_root_path = '/home/{username}/public_html'

    # Extract the username from the path (if possible)
    if path.startswith('/home/') and '/public_html' in path:
        username = path.split('/')[2]  # Extract the username from the path
        root_path = default_root_path.format(username=username)

        # If the path matches the default root path, return only the domain
        if path == root_path:
            return domain

    # Otherwise, return the domain + relative path
    relative_path = path.replace(root_path, '').lstrip('/')
    return f"https://{domain}/{relative_path}" if relative_path else domain  

def generate_random_5_digit():
    
    return random.randint(10000, 99999)    

        
def setup_dkim(domain):
    dkim_dir = "/etc/opendkim/keys"
    domain_dir = f"{dkim_dir}/{domain}"
    key_table_file = "/etc/opendkim/key.table"
    signing_table_file = "/etc/opendkim/signing.table"
    trusted_hosts_file = "/etc/opendkim/TrustedHosts.table"
    public_key_file = f"{domain_dir}/default.txt"
    private_key_file = f"{domain_dir}/{domain}.private"

    try:
        # Create directory if it doesn't exist
        os.makedirs(domain_dir, exist_ok=True)

        # Generate DKIM keys directly in the target directory
        subprocess.run(
            ["opendkim-genkey", "-t", "-s", "default", "-d", domain, "-D", domain_dir], 
            check=True
        )

        # Rename the private key file for clarity
        os.rename(f"{domain_dir}/default.private", private_key_file)

        # Change ownership and set correct permissions for the private key
        subprocess.run(
            ["chown", "opendkim:opendkim", private_key_file], 
            check=True
        )
        subprocess.run(
            ["chmod", "400", private_key_file], 
            check=True
        )

        # Update key.table
        with open(key_table_file, "a") as kt:
            kt.write(f"default._domainkey.{domain} {domain}:default:{private_key_file}\n")

        # Update signing.table
        with open(signing_table_file, "a") as st:
            st.write(f"*@{domain} default._domainkey.{domain}\n")

        # Update TrustedHosts.table
        with open(trusted_hosts_file, "a") as th:
            th.write(f"{domain}\n")

        # Restart OpenDKIM service
        subprocess.run(["systemctl", "restart", "opendkim"], check=True)

        # Extract and display the DNS TXT record
        if os.path.exists(public_key_file):
            with open(public_key_file, "r") as pkf:
                public_key = pkf.read().strip()
            print(f"\nDNS TXT Record: {public_key}")
        else:
            print("\nWARNING: Public key file not found. Please check manually.")

        print(f"\nDKIM setup completed for {domain}")

    except Exception as e:
        print(f"Error setting up DKIM: {e}")



def insert_dkim_record(domainname,domin_id,userid):
   
    dkim_file_path = f"/etc/opendkim/keys/{domainname}/default.txt"
    domain_name = f"default._domainkey.{domainname}"

    if not os.path.exists(dkim_file_path):
        logger.error(f"DKIM file not found: {dkim_file_path}")
        return

    try:
        user_instance = User.objects.get(pk=userid) 
        # Read the DKIM public key from the file
        with open(dkim_file_path, "r") as file:
            dkim_content = file.read().strip()
        
        match = re.search(r'TXT\s*\(\s*"(.*?)"\s*\)', dkim_content, re.DOTALL)
        if not match:
            logger.error("Error: DKIM TXT record format is incorrect.")
            return
        dkim_value = match.group(1).replace('"\n"', '').replace('"\n\t"', '').replace('" "', '')

        # Check if the DKIM record already exists in PowerDNS
        if not Dns_record.objects.filter(
            domain_id=domin_id, 
            name=domain_name, 
            content=dkim_value, 
            type="TXT"
        ).exists():
            # Create a new DNS record
            new_dns = Dns_record(
                name=domain_name,
                content=dkim_value,  # Insert the actual DKIM public key
                type="TXT",
                ttl=3600,
                prio=0,
                domain_id=domin_id,
                userid=user_instance
            )
            new_dns.save()
            logger.error(f"DKIM record successfully added for {domain_name}")
        else:
            logger.error(f"DKIM record already exists for {domain_name}")
 
    except Exception as e:
        logger.error(f"Error inserting DKIM record: {e}")
        print(f"Error inserting DKIM record: {e}")
        
        
def set_api_status_u(name, status_value):
    """Sets the api_status in the conf.ini file."""

    config = configparser.ConfigParser()

    # Construct the path to conf.ini using settings.BASE_DIR
    django_root = settings.BASE_DIR
    file_path = os.path.join(django_root, 'etc', 'conf.ini')

    try:
        # Check if the file exists, if not create it
        if not os.path.exists(file_path):
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w'):
                pass  # Create an empty file

        # Read the existing config file
        config.read(file_path)

        # Ensure the 'settings' section exists
        if not config.has_section('settings'):
            config.add_section('settings')

        # Set the new api_status value
        config.set('settings', name, str(status_value))

        # Write the updated config back to the file
        with open(file_path, 'w') as config_file:
            config.write(config_file)

        return {"status": "success", "message": "updated successfully."}

    except Exception as e:
        return {"status": "error", "message": f"Error setting: {str(e)}"}  

def replace_le_webroot(domain: str, new_webroot: str) -> bool:
    acme_dir_rsa = f"/root/.acme.sh/{domain}/{domain}.conf"
    acme_dir_ecc = f"/root/.acme.sh/{domain}_ecc/{domain}.conf"

    for conf_file in [acme_dir_rsa, acme_dir_ecc]:
        if os.path.exists(conf_file):
            with open(conf_file, "r") as f:
                lines = f.readlines()

            updated = False
            with open(conf_file, "w") as f:
                for line in lines:
                    if line.strip().startswith("Le_Webroot="):
                        f.write(f"Le_Webroot='{new_webroot}'\n")
                        updated = True
                    else:
                        f.write(line)

            if updated:
                logger.info(f"Le_Webroot updated in: {conf_file}")
                return True
            else:
                logger.info(f"Le_Webroot key not found in: {conf_file}")
                return False

    logger.warning(f"Domain conf not found for: {domain}")
    return False                
    
    
def count_domains(type, userid):
    
    domains = Domain.objects.filter(userid=userid)
    root_domains = set(domains.values_list('domain', flat=True))

    domain_count = 0
    subdomain_count = 0

    for d in domains:
        d.type = 'domain'  # Default
        for root in root_domains:
            if d.domain != root and d.domain.endswith('.' + root):
                d.type = 'subdomain'
                break

        if d.type == 'domain':
            domain_count += 1
        else:
            subdomain_count += 1

    # Return count by requested type
    if type == 'domain':
        return domain_count
    elif type == 'subdomain':
        return subdomain_count
    else:
        return 0  # Invalid type fallback
        
        
    
    
    
def read_ssl_files(domain):
    domain_path = f'/etc/letsencrypt/live/{domain}'
    
    fullchain_path = os.path.join(domain_path, 'fullchain.pem')
    privkey_path = os.path.join(domain_path, 'privkey.pem')

    with open(fullchain_path, 'r') as f:
        fullchain_pem = f.read()

    with open(privkey_path, 'r') as f:
        privkey_pem = f.read()

    # Split fullchain.pem into CRT and CABUNDLE
    certs = re.findall(
        r'-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----',
        fullchain_pem,
        re.DOTALL
    )
    if not certs:
        raise ValueError("No certificates found in fullchain.pem")

    crt = certs[0]
    cabundle = '\n'.join(certs[1:]) if len(certs) > 1 else ''
    acme_folder = f'/root/.acme.sh/{domain}_ecc'
    renew_status = 'Off' if os.path.exists(acme_folder) else 'On'

    return {
        "crt": crt,
        "cabundle": cabundle,
        "privkey": privkey_pem,
        "renew": renew_status
    }        
    
    
def parse_certificate(pem_data):
    cert = x509.load_pem_x509_certificate(pem_data.encode(), default_backend())
    
    # Extract Subject domains (CN + SANs)
    domains = []
    # Common Name (CN)
    cn = cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
    if cn:
        domains.append(cn[0].value)
    
    # Subject Alternative Names (SAN)
    try:
        ext = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
        san = ext.value
        domains.extend(san.get_values_for_type(x509.DNSName))
    except x509.ExtensionNotFound:
        pass

    # Issuer
    issuer = cert.issuer.rfc4514_string()

    # Public Key Type and Size
    pubkey = cert.public_key()
    key_type = pubkey.__class__.__name__
    if hasattr(pubkey, 'key_size'):
        key_size = pubkey.key_size
    else:
        key_size = "Unknown"

    # Expiration Date
    expiration = cert.not_valid_after

    return {
        "domains": list(set(domains)),  # unique
        "issuer": issuer,
        "key_type": f"{key_type}, {key_size}-bit",
        "expiration": expiration.strftime("%b %d, %Y %I:%M:%S %p")
    }    
    
    


def save_ssl_files(domain, crt, cabundle, privkey):
    
    ssl_path = f"/etc/letsencrypt/live/{domain}"
    os.makedirs(ssl_path, exist_ok=True)

    cert_path = os.path.join(ssl_path, 'cert.pem')
    fullchain_path = os.path.join(ssl_path, 'fullchain.pem')
    privkey_path = os.path.join(ssl_path, 'privkey.pem')

    # Clean input
    crt = crt.strip()
    cabundle = cabundle.strip() if cabundle else ''
    privkey = privkey.strip()

    # Save cert.pem
    with open(cert_path, 'w') as f:
        f.write(crt)

    # Save fullchain.pem
    fullchain_content = crt
    if cabundle:
        fullchain_content += '\n\n' + cabundle

    with open(fullchain_path, 'w') as f:
        f.write(fullchain_content)

    # Save privkey.pem
    with open(privkey_path, 'w') as f:
        f.write(privkey)

    return True
    
    
def get_php_settings(php_version: str, override_path: str = None):
    # Default settings with all expected keys
    settings = {
        'memory_limit': None,
        'upload_max_filesize': None,
        'post_max_size': None,
        'max_execution_time': None,
        'max_input_time': None,
        'allow_url_fopen': None,
        'allow_url_include': None,
        'display_errors': None,
        'file_uploads': None,
        'log_errors': 'Off',
        'error_log': 'Off',
        'error_reporting': '0'
    }

    if not php_version:
        return settings

    new_php_version = php_version.replace('.', '')
    ini_file_path = f'/usr/local/lsws/lsphp{new_php_version}/etc/php/{php_version}/litespeed/php.ini'
    ini_file_path_old = f'/usr/local/lsws/lsphp{new_php_version}/etc/php.ini'

    chosen_ini_path = ini_file_path if os.path.exists(ini_file_path) else ini_file_path_old

    try:
        with open(chosen_ini_path, 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                if line and not line.startswith(';'):
                    if line.startswith('memory_limit'):
                        settings['memory_limit'] = line.split('=', 1)[1].strip()
                    elif line.startswith('upload_max_filesize'):
                        settings['upload_max_filesize'] = line.split('=', 1)[1].strip()
                    elif line.startswith('post_max_size'):
                        settings['post_max_size'] = line.split('=', 1)[1].strip()
                    elif line.startswith('max_execution_time'):
                        settings['max_execution_time'] = line.split('=', 1)[1].strip()
                    elif line.startswith('max_input_time'):
                        settings['max_input_time'] = line.split('=', 1)[1].strip()
                    elif line.startswith('allow_url_fopen'):
                        settings['allow_url_fopen'] = line.split('=', 1)[1].strip()
                    elif line.startswith('allow_url_include'):
                        settings['allow_url_include'] = line.split('=', 1)[1].strip()
                    elif line.startswith('display_errors'):
                        settings['display_errors'] = line.split('=', 1)[1].strip()
                    elif line.startswith('file_uploads'):
                        settings['file_uploads'] = line.split('=', 1)[1].strip()
    except Exception as e:
        print(f"Error reading {chosen_ini_path}: {e}")

    # Apply override if present
    if override_path:
        try:
            with open(override_path, 'r', encoding='utf-8') as f:
                in_php_override = False
                for line in f:
                    stripped = line.strip()
                    if stripped.startswith("phpIniOverride"):
                        in_php_override = True
                        continue
                    elif in_php_override and stripped == "}":
                        break
                    if in_php_override and stripped.startswith("php_admin_value"):
                        parts = stripped.split(None, 2)
                        if len(parts) == 3:
                            _, key, value = parts
                            settings[key] = value.strip('"')
        except Exception as e:
            print(f"Error reading override file {override_path}: {e}")

    return settings
    
    
def check_for_update():
    
    try:
        version_url = "https://ongudidan.github.io/FortunePanel/panel_updates/version.txt"

        os_name = getattr(settings, "MY_OS_NAME", "linux")
        os_version = getattr(settings, "MY_OS_VERSION", "0")
        panel_version = getattr(settings, "VERSION", "0")

        data = {
            "osname": os_name,
            "osversion": os_version,
            "panel": panel_version
        }

        response = requests.post(version_url, data=data, timeout=10)
        response.raise_for_status()
        latest_version = response.text.strip()

        current_version = getattr(settings, "VERSION", "0.0.0")
        django_root = settings.BASE_DIR
        update_file_path = os.path.join(django_root, 'etc', 'update')

        if current_version == latest_version:
            print(f"✅ The project is up to date (Version: {current_version})")
            if os.path.exists(update_file_path):
                os.remove(update_file_path)
                print("🗑️ Removed outdated update file.")
        else:
            print(f"⚠️ Update available! Current: {current_version}, Latest: {latest_version}")
            os.makedirs(os.path.dirname(update_file_path), exist_ok=True)
            with open(update_file_path, "w") as update_file:
                update_file.write(f"{latest_version}\n")
            print(f"📂 Update file created at: {update_file_path}")

    except requests.RequestException as e:
        print(f"❌ Error fetching version info: {e}")  


def get_plugin_headers(plugin_name):
    filename = os.path.join(settings.BASE_DIR, 'plugin', f"{plugin_name}.conf")
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()

        content = "[DEFAULT]\n" + content
        
        config = configparser.ConfigParser(interpolation=None)  # Disable interpolation
        config.optionxform = str  # preserve case
        config.read_string(content)

        logger.error(f"Config keys for {plugin_name}: {list(config['DEFAULT'].keys())}")

        headers = {}
        for key, value in config['DEFAULT'].items():
            key = key.strip()
            value = value.strip()
            match = re.match(r'header\[(.+?)\]', key, re.IGNORECASE)
            if match:
                header_key = match.group(1).strip()
                headers[header_key] = value

        return headers

    except Exception as e:
        logger.error(f"Error reading config '{plugin_name}': {e}")
        return {}
 


def get_plugin_config_value(name, plugin_name):
    filename = os.path.join(settings.BASE_DIR, 'plugin', f"{plugin_name}.conf")
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        content = "[DEFAULT]\n" + content  # Add fake section
        config = configparser.ConfigParser()
        config.optionxform = str  # preserve case
        config.read_string(content)
        return config['DEFAULT'].get(name)
    except Exception as e:
        print(f"Error reading config '{plugin_name}': {e}")
    return None



def get_all_plugin_names(features=None, service=None):
    plugin_dir = os.path.join(settings.BASE_DIR, 'plugin')

    if not os.path.isdir(plugin_dir):
        print(f"[get_all_plugin_names] Plugin directory not found: {plugin_dir}")
        return []

    plugins_with_order = []

    for filename in os.listdir(plugin_dir):
        if filename.endswith('.conf'):
            plugin_name = filename[:-5]  # remove ".conf"

            # Optional feature filtering
            if features:
                features = features.lower()
                feature_value = get_plugin_config_value('features', plugin_name)
                if feature_value:
                    feature_list = [f.strip().lower() for f in feature_value.split(',')]
                    if features not in feature_list:
                        continue

            # Optional service filtering
            if service:
                service = service.lower()
                service_value = get_plugin_config_value('service', plugin_name)
                if service_value:
                    service_list = [s.strip().lower() for s in service_value.split(',')]
                    if service not in service_list and 'both' not in service_list:
                        continue
                else:
                    # If 'service' is required but not defined in plugin config, skip
                    continue

            # Get sorder value from conf
            sorder = get_plugin_config_value('sorder', plugin_name)
            try:
                sorder = int(sorder)
            except (TypeError, ValueError):
                sorder = 9999  # Default/fallback sort order

            plugins_with_order.append((sorder, plugin_name))

    # Sort by sorder
    sorted_plugins = sorted(plugins_with_order, key=lambda x: x[0])

    # Return only plugin names
    return [name for _, name in sorted_plugins]


def get_all_plugin_link(features=None, service=None):
    
    plugin_dir = os.path.join(settings.BASE_DIR, 'plugin')

    if not os.path.isdir(plugin_dir):
        print(f"[get_all_plugin_link] Plugin directory not found: {plugin_dir}")
        return []

    plugins_with_order = []

    for filename in os.listdir(plugin_dir):
        if not filename.endswith('.json'):
            continue

        file_path = os.path.join(plugin_dir, filename)
        

        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"[get_all_plugin_link] Error reading {filename}: {e}")
            print(f"[get_all_plugin_link] Error reading {filename}: {e}")
            continue

        # Normalize to list
        if isinstance(data, dict):
            plugin_entries = [data]
        elif isinstance(data, list):
            plugin_entries = data
        else:
            print(f"[get_all_plugin_link] Invalid JSON structure in {filename}")
            continue

        # Process each entry
        for plugin in plugin_entries:
            if not isinstance(plugin, dict):
                continue
            
            
            
            # Optional filters
            if features:
                feature_value = plugin.get("features", "")
                feature_list = [f.strip().lower() for f in str(feature_value).split(',')]
                if features.lower() not in feature_list:
                    continue

            if service:
                service_value = plugin.get("service", "")
                service_list = [s.strip().lower() for s in str(service_value).split(',')]
                if service.lower() not in service_list and "both" not in service_list:
                    continue

            sorder = plugin.get("order", plugin.get("sorder", 9999))
            try:
                sorder = int(sorder)
            except (TypeError, ValueError):
                sorder = 9999

            plugins_with_order.append((sorder, plugin))

    # Sort by order
    sorted_plugins = sorted(plugins_with_order, key=lambda x: x[0])

    # Return only plugin dicts
    return [plugin for _, plugin in sorted_plugins]

    
    
    
def get_custom_cookies(request, prefix="CUSTOMCOOK_"):
    
    return {
        cookie_name[len(prefix):]: cookie_value
        for cookie_name, cookie_value in request.COOKIES.items()
        if cookie_name.startswith(prefix)
    }
    
    
    
def version_tuple(v):
    try:
        return tuple(map(int, v.strip().split(".")))
    except Exception:
        return (1, 0, 0)


def get_cgi_php_versions():
    php_versions = []
    pattern = re.compile(r'^php-cgi(\d+\.\d+)$')  # Matches filenames like 'php-cgi8.2'

    for filename in os.listdir('/usr/bin/'):
        match = pattern.match(filename)
        if match:
            version = match.group(1)
            php_versions.append('cgi ' + version)  # Format: 'cgi 8.2'

    # Sort versions numerically by their version part
    php_versions.sort(key=lambda v: list(map(int, v[4:].split('.'))))

    return php_versions  

        
def delete_old_local_backups(limit=100, backup_folder='/home/backup', schedule=None):
    try:
        # List all .tar.gz files
        files = [f for f in os.listdir(backup_folder) if f.endswith('.tar.gz')]

        # Filter by schedule prefix if specified
        if schedule:
            files = [f for f in files if f.startswith(f"{schedule}_")  and f.endswith('.tar.gz')]

        # Get full paths and modification times
        full_paths = [
            (f, os.path.getmtime(os.path.join(backup_folder, f)))
            for f in files
        ]

        # Sort by modification time (newest first)
        sorted_files = sorted(full_paths, key=lambda x: x[1], reverse=True)

        # Keep only the latest `limit` files
        files_to_delete = sorted_files[limit:]

        # Delete older files
        for file_name, _ in files_to_delete:
            try:
                os.remove(os.path.join(backup_folder, file_name))
            except Exception as e:
                print(f"Failed to delete {file_name}: {e}")

        return {
            'status': 'success',
            'schedule': schedule,
            'deleted_count': len(files_to_delete),
            'kept_count': min(limit, len(sorted_files))
        }

    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }
        
        
def validate_sso_token(token: str, user_id: int = None, expiry_minutes: int = 30) -> bool:
    
    qs = SSOToken.objects.filter(token=token)
    if user_id is not None:
        qs = qs.filter(user_id=user_id)

    if not qs.exists():
        return False

    sso_token = qs.first()
    expiry_time = sso_token.created_at + timedelta(minutes=expiry_minutes)
    return timezone.now() <= expiry_time        
    
    
def create_sso_token(user_id: int, token: str) -> str:
    
    # Delete any existing token(s) for this user
    SSOToken.objects.filter(user_id=user_id).delete()

   
    SSOToken.objects.create(user_id=user_id, token=token)

    return token            
    
    
    
def format_name(name: str) -> str:
    return " ".join(word.capitalize() for word in name.split("_"))
    
def get_app_type_from_name(name: str) -> str:
    allowed_types = {
        "node_js": "node_js",
        "python": "python",
        "ruby": "ruby",
    }
    return allowed_types.get(name, "unknown")  # unknown for anything else    
    
    
def get_node_js_versions():
    node_versions = []
    version_pattern = re.compile(r'^\d+$')  # Matches integers like 18, 19, 20

    node_path = '/usr/local/olspanel/bin/nodejs'

    if not os.path.exists(node_path):
        return []  # Return empty if path does not exist

    for folder_name in os.listdir(node_path):
        folder_path = os.path.join(node_path, folder_name)
        if os.path.isdir(folder_path) and version_pattern.match(folder_name):
            node_versions.append(folder_name)

    # Sort numerically
    node_versions.sort(key=int)
    return node_versions
    
    
def install_node(node_version):
    """
    Installs a specific Node.js version using the shell script.
    Steps:
    1. Check if the script exists.
    2. Convert Windows line endings to Unix (sed -i 's/\r$//').
    3. Ensure it is executable.
    4. Run it with sudo.
    5. Return structured output.
    """
    try:
        # 1️⃣ Path to the script
        script_path = os.path.join(settings.BASE_DIR, "etc", "install_node_versions.sh")

        # 2️⃣ Check if script exists
        if not os.path.exists(script_path):
            return {'status': 'error', 'message': f"Script not found: {script_path}"}

        # 3️⃣ Fix Windows line endings (CRLF -> LF)
        subprocess.run(['sed', '-i', 's/\r$//', script_path], check=True)

        # 4️⃣ Ensure executable
        if not os.access(script_path, os.X_OK):
            os.chmod(script_path, 0o755)

        # 5️⃣ Run the script with sudo
        result = subprocess.run(
            ['sudo', script_path, 'install', node_version],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # 6️⃣ Return result
        if result.returncode == 0:
            return {'status': 'success', 'message': result.stdout.strip()}
        else:
            return {'status': 'error', 'message': result.stderr.strip()}

    except Exception as e:
        return {'status': 'error', 'message': str(e)}
        
        
        
def restart_node(path):
    try:
        # Ensure path ends with a slash
        if not path.endswith('/'):
            path += '/'

        # 1️⃣ Path to the script
        script_path = os.path.join(settings.BASE_DIR, "etc", "restart_node_app.sh")

        # 2️⃣ Check if script exists
        if not os.path.exists(script_path):
            return {'status': 'error', 'message': f"Script not found: {script_path}"}

        # 3️⃣ Fix Windows line endings (CRLF -> LF)
        subprocess.run(['sed', '-i', 's/\r$//', script_path], check=True)

        # 4️⃣ Ensure executable
        if not os.access(script_path, os.X_OK):
            os.chmod(script_path, 0o755)

        # 5️⃣ Run the script with sudo
        result = subprocess.run(
            ['sudo', script_path, path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # 6️⃣ Return result
        if result.returncode == 0:
            return {'status': 'success', 'message': result.stdout.strip()}
        else:
            return {'status': 'error', 'message': result.stderr.strip()}

    except Exception as e:
        return {'status': 'error', 'message': str(e)}
        
        
def npm_node_install(node_version, path):
    try:
        path = path.rstrip("/")  
        npm_bin = f"/usr/local/olspanel/bin/nodejs/{node_version}/bin/npm"

        if not os.path.exists(npm_bin):
            return {'status': 'error', 'message': f"npm not found for Node.js {node_version}: {npm_bin}"}

        package_json = os.path.join(path, "package.json")
        if not os.path.exists(package_json):
            return {'status': 'error', 'message': f"No package.json found in {path}"}

        # Use correct environment
        env = os.environ.copy()
        env["PATH"] = f"/usr/local/olspanel/bin/nodejs/{node_version}/bin:" + env.get("PATH", "")

        result = subprocess.run(
            [npm_bin, "install"],
            cwd=path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )

        if result.returncode == 0:
            return {'status': 'success', 'message': result.stdout.strip() or "npm install completed"}
        else:
            return {'status': 'error', 'message': result.stderr.strip() or "npm install failed"}

    except Exception as e:
        return {'status': 'error', 'message': str(e)}
        
        
def create_app_js(target_folder,file_name):
    """
    Create a folder if it doesn't exist and generate app.js with default content.
    :param target_folder: Full path to the target folder
    :return: dict with status and message
    """
    try:
        # Ensure folder exists
        if not os.path.exists(target_folder):
            os.makedirs(target_folder, exist_ok=True)

        app_js_path = os.path.join(target_folder, file_name)

        # Only create app.js if it doesn't exist
        if not os.path.exists(app_js_path):
            content = """var http = require('http');
var server = http.createServer(function(req, res) {
    res.writeHead(200, {'Content-Type': 'text/plain'});
    var message = 'It works!\\n',
        version = 'NodeJS ' + process.versions.node + '\\n',
        response = [message, version].join('\\n');
    res.end(response);
});
server.listen();
"""
            with open(app_js_path, 'w') as f:
                f.write(content)
            return {'status': 'success', 'message': f"Created app.js in {target_folder}"}
        else:
            return {'status': 'exists', 'message': "app.js already exists"}

    except Exception as e:
        return {'status': 'error', 'message': str(e)}    





def create_ols_node_context(version, target_path, startup_file, domain, old_context=None):
    try:
        binpath = f"/usr/local/olspanel/bin/nodejs/{version}/bin/node"

        # Normalize paths
        context_path = '' if not target_path or target_path == '/' else target_path.strip('/')
        location_path = context_path

        vhost_directory = f"/usr/local/lsws/conf/vhosts/{domain}"
        os.makedirs(vhost_directory, exist_ok=True)
        vhost_file_path = os.path.join(vhost_directory, "vhost.conf")

        # Build new context content
        context_content = f"""
context /{context_path} {{
  type                    appserver
  location                $DOC_ROOT/{location_path}
  binPath                 {binpath}
  appType                 node
  startupFile             {startup_file}
  env                     NODE_ENV=production
  env                     PATH=/usr/local/olspanel/bin/nodejs/{version}/bin:$PATH
  autoStart               1
  restart                 1

  rewrite  {{

  }}
  addDefaultCharset       off
}}
"""

        # Normalize old_context if provided
        if old_context:
            context_to_remove = "/" if old_context.strip() == "/" else "/" + old_context.strip("/")
        else:
            context_to_remove = "/" if context_path == "" else "/" + context_path

        updated = False

        if os.path.exists(vhost_file_path):
            with open(vhost_file_path, 'r') as f:
                lines = f.readlines()

            new_lines = []
            inside_context = False
            brace_depth = 0

            for line in lines:
                stripped = line.strip()

                # Match only exact context start
                if not inside_context and stripped == f"context {context_to_remove} {{":
                    inside_context = True
                    brace_depth = 1
                    updated = True
                    continue

                if inside_context:
                    # Track nested braces until closing
                    brace_depth += line.count("{")
                    brace_depth -= line.count("}")
                    if brace_depth <= 0:
                        inside_context = False
                    continue

                new_lines.append(line)

            # Always append the new context
            new_lines.append(context_content)

            with open(vhost_file_path, 'w') as f:
                f.writelines(new_lines)

            return {
                'status': 'updated' if updated else 'created',
                'message': f"/{context_path or '/'} context {'updated' if updated else 'added'} in {vhost_file_path}"
            }

        else:
            # File does not exist → create with new context
            with open(vhost_file_path, 'w') as f:
                f.write(context_content)
            return {'status': 'created', 'message': f"Created {vhost_file_path} with /{context_path or '/'} context"}

    except Exception as e:
        return {'status': 'error', 'message': str(e)}



def delete_ols_node_context(domain, context_path):
    """
    Remove a Node.js app context from the vhost.conf for the given domain.
    Supports nested blocks by tracking brace depth.
    """
    try:
        vhost_directory = f"/usr/local/lsws/conf/vhosts/{domain}"
        vhost_file_path = os.path.join(vhost_directory, "vhost.conf")

        if not os.path.exists(vhost_file_path):
            return {'status': 'not_found', 'message': f"No vhost.conf found for {domain}"}

        # Normalize path
        if context_path == "/" or context_path.strip() == "":
            context_to_remove = "/"
        else:
            context_to_remove = "/" + context_path.strip("/")

        with open(vhost_file_path, 'r') as f:
            lines = f.readlines()

        new_lines = []
        inside_context = False
        brace_depth = 0
        removed = False

        for line in lines:
            stripped = line.strip()

            # Detect the start of the target context block
            if not inside_context and stripped == f"context {context_to_remove} {{":
                inside_context = True
                brace_depth = 1
                removed = True
                continue

            if inside_context:
                # Count braces inside the block
                brace_depth += line.count("{")
                brace_depth -= line.count("}")

                # If we've closed the context block, stop skipping
                if brace_depth <= 0:
                    inside_context = False
                continue

            # Keep lines outside the target context
            new_lines.append(line)

        # Write back updated file
        with open(vhost_file_path, 'w') as f:
            f.writelines(new_lines)

        if removed:
            return {'status': 'deleted', 'message': f"Removed context '{context_to_remove}' from {vhost_file_path}"}
        else:
            return {'status': 'not_found', 'message': f"Context '{context_to_remove}' not found in {vhost_file_path}"}

    except Exception as e:
        return {'status': 'error', 'message': str(e)}
        
        
def run_composer_install(full_path, timeout=300):
    """
    Executes 'composer install' in the specified directory.
    Returns a dict with {status, message, output}.
    """

    # Check directory
    if not os.path.isdir(full_path):
        return {
            "status": "error",
            "message": f"Invalid path: {full_path}"
        }

    # Check composer.json
    composer_json = os.path.join(full_path, "composer.json")
    if not os.path.isfile(composer_json):
        return {
            "status": "error",
            "message": f"'composer.json' not found in {full_path}."
        }

    try:
        # Run composer install
        result = subprocess.run(
            ["sudo", "composer", "install", "--no-interaction", "--prefer-dist"],
            cwd=full_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout
        )

        if result.returncode == 0:
            return {
                "status": "success",
                "message": "Composer install completed successfully.",
                "output": result.stdout
            }
        else:
            return {
                "status": "error",
                "message": "Composer install failed.",
                "output": result.stderr or result.stdout
            }

    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "message": "Composer install timed out."
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }        
        

def scan_module_templates(target_filename=None):
    
    base_path = os.path.join(settings.BASE_DIR, "modules")
    found_modules = []

    # ✅ Only start if 'modules' directory exists
    if not os.path.isdir(base_path):
        return []

    # Loop through each module folder
    for module_name in os.listdir(base_path):
        module_dir = os.path.join(base_path, module_name)
        templates_dir = os.path.join(module_dir, "templates")

        if not os.path.isdir(templates_dir):
            continue

        # Walk through subfolders under templates/
        for root, dirs, files in os.walk(templates_dir):
            for file_name in files:
                if not file_name.endswith(".html"):
                    continue
                if target_filename and file_name != target_filename:
                    continue

                # Example path: modules/postgresql/templates/postgresql/home_right.html
                rel_from_templates = os.path.relpath(root, templates_dir)
                template_rel_path = os.path.join(rel_from_templates, file_name).replace("\\", "/")

                found_modules.append({
                    "module": module_name,
                    "filename": file_name,
                    "template": template_rel_path,  # usable in {% include %}
                    "path": os.path.join(root, file_name),
                })

    return found_modules
    
    
    
    
def fmt_limit(value):
    return "∞" if value is None else value
    

def parse_top_cpu_ram(text: str):
    total_cpu = 0.0
    total_ram_mb = 0.0

    lines = text.splitlines()
    process_section = False

    for line in lines:
        # Detect start of process table
        if re.match(r"\s*PID\s+USER", line):
            process_section = True
            continue

        if not process_section:
            continue

        # Skip empty lines
        if not line.strip():
            continue

        parts = line.split()
        if len(parts) < 12:
            continue

        try:
            cpu = float(parts[8])   # %CPU column
            res_kb = float(parts[9])  # RES column (in KB in top)

            total_cpu += cpu
            total_ram_mb += res_kb
        except:
            continue

    

    return {
        "cpu_total_percent": round(total_cpu, 2),
        "ram_total_mb": round(total_ram_mb, 2)
    }

 
def get_top_sorted_by_cpu(user: str):
    

    result = subprocess.run(
        ["top", "-b", "-n1", "-u", user, "-o", "%CPU"],
        capture_output=True,
        text=True
    )

    return result.stdout   # <-- keep string
 
def get_user_stats(user: str, use_system_cores: bool = True):
    USERLIMIT_BIN = "/usr/local/bin/userlimit"
    cores = os.cpu_count() or 1
    new_cores = cores
    process_count=0
    cpu_limit = None
    ram_limit = None
    if os.path.exists(USERLIMIT_BIN) and os.access(USERLIMIT_BIN, os.X_OK):
        try:
            ul = subprocess.run(
                [USERLIMIT_BIN, "status", user],
                capture_output=True,
                text=True,
                timeout=2
            )
            data = json.loads(ul.stdout.strip() or "{}")
            if data.get("cpu") is not None and data.get("cpu") != "unlimited":
                cpu_limit = float(data["cpu"]) / 100.0
                cores = int(cpu_limit) if cpu_limit.is_integer() else round(cpu_limit, 2)
                new_cores = cores
            else: 
                if not use_system_cores:
                    new_cores = 0
                
            if data.get("ram_mb") is not None and data.get("ram_mb") != "unlimited":
                ram_limit = float(data["ram_mb"])
        except Exception:
            pass
    else:
        if not use_system_cores:
                    new_cores = 0
  
    lines = get_top_sorted_by_cpu(user)
    result = parse_top_cpu_ram(lines)


    

    return {
        "user": user,
        "processes": process_count,
        "ram_mb": result['ram_total_mb'],
        "cpu_percent": round(result['cpu_total_percent']/cores, 2),
        "limit": {
            "cpu": new_cores, # Assumed helper function exists
            "ram_mb": fmt_limit(ram_limit)
        }
    }