import os
import subprocess
from django.shortcuts import render
from django.http import JsonResponse
from datetime import datetime
from django.conf import settings
import configparser
import pytz
import time
import re
import platform
import socket
import subprocess
import tempfile
import shutil
import json
import random
import string
from users.panellogger import *
from django.http import StreamingHttpResponse
import sys
import requests
import threading
logger = CpLogger()


def change_hostname(old_hostname, new_hostname):
    try:
        # Read and change the hostname in /etc/hostname
        with open("/etc/hostname", "r") as f:
            current_hostname = f.read().strip()

        # Check if the current hostname matches the old_hostname
        if current_hostname == old_hostname:
            # If the current hostname matches the old one, update it
            with open("/etc/hostname", "w") as f:
                f.write(new_hostname)
        else:
            print(f"Current hostname does not match the provided old hostname: {old_hostname}")
            return

        # Update the /etc/hosts file to reflect the new hostname
        with open("/etc/hosts", "r") as f:
            hosts_content = f.read()

        # Replace old_hostname with new_hostname in /etc/hosts
        hosts_content = hosts_content.replace(old_hostname, new_hostname)

        # Write the updated content back to /etc/hosts
        with open("/etc/hosts", "w") as f:
            f.write(hosts_content)

        if not re.match(r'^[a-zA-Z0-9.-]+$', new_hostname):
            print(f"Invalid hostname format: {new_hostname}")
            return

        # Run the hostname command to apply changes immediately
        subprocess.run(["hostnamectl", "set-hostname", new_hostname], check=True)

        print(f"Hostname successfully changed from {old_hostname} to {new_hostname}")
    except PermissionError:
        print("Permission denied. Please run this script as root.")
    except Exception as e:
        print(f"An error occurred: {e}")
        
def install_panel_update():
    """Runs upgrade.sh from the web, then downloads and extracts the update file to /usr/local/lsws/Example/html/"""
    
    upgrade_script_url = "https://ongudidan.github.io/OLSPanel/panel_updates/upgrade.sh"
    update_url = "https://ongudidan.github.io/OLSPanel/panel_updates/panel_setup.zip"
    download_path = f"{settings.BASE_DIR.parent}/panel_setup.zip"
    extract_path = settings.BASE_DIR.parent
    upgrade_script_path = f"{settings.BASE_DIR.parent}/upgrade.sh"

    try:
        print("Step 1: Downloading upgrade.sh...")
        subprocess.run(["wget", "-O", upgrade_script_path, upgrade_script_url], check=True)

        print("Step 2: Removing Windows-style line endings from upgrade.sh...")
        subprocess.run(["sed", "-i", "s/\\r$//", upgrade_script_path], check=True)

        print("Step 3: Running upgrade.sh...")
        subprocess.run(["chmod", "+x", upgrade_script_path], check=True)
        subprocess.run(["bash", upgrade_script_path], check=True)

        print("Step 4: Downloading update file...")
        cache_buster = int(time.time())
        #subprocess.run(["wget", "-O", download_path, f"{update_url}?{cache_buster}"], check=True)

        if not os.path.isfile(download_path):
            print("Error: Downloaded file not found, the download may have failed.")
            return "Error: Downloaded file not found, the download may have failed."

        print("Step 5: Extracting update file...")
        #subprocess.run(["sudo", "unzip", "-o", download_path, "-d", extract_path], check=True)

        print("Step 6: Cleaning up...")
        os.remove(download_path)
        os.remove(upgrade_script_path)
        restart_cp()

        print("Update installation complete!")
        return "Update has been successfully installed."

    except subprocess.CalledProcessError as e:
        print(f"Error during update process: {e}")
        return f"Update failed: {e}"
        
        

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return f"Unexpected error: {e}"
        
def install_softaculous_now():
    """Runs upgrade.sh from the web, then downloads and extracts the update file to /usr/local/lsws/Example/html/"""
    
    set_api_status("api_status", 1)
    upgrade_script_url = "https://ongudidan.github.io/OLSPanel/softaculous/softaculous.sh"
    extract_path = settings.BASE_DIR.parent
    upgrade_script_path = f"{settings.BASE_DIR.parent}/softaculous.sh"
    download_path = f"{settings.BASE_DIR.parent}/softaculous.zip"
    
    try:
        # Step 1: Download and run the upgrade.sh script
        print("Step 1: Downloading softaculous.sh...")
        subprocess.run(["wget", "-O", upgrade_script_path, upgrade_script_url], check=True)

        # Step 2: Remove Windows-style line endings (if any) from the upgrade.sh file
        print("Step 2: Removing Windows-style line endings from softaculous.sh...")
        subprocess.run(["sed", "-i", "s/\\r$//", upgrade_script_path], check=True)
        
        # Step 3: Running softaculous.sh
        print("Step 3: Running softaculous.sh...")
        subprocess.run(["chmod", "+x", upgrade_script_path], check=True)
        subprocess.run([upgrade_script_path], check=True)

        

        # Step 6: Clean up by removing the downloaded zip file and the upgrade script
        print("Step 6: Cleaning up...")
        os.remove(download_path)
        os.remove(upgrade_script_path)
       
        print("Installation complete!")
        return "Update has been successfully installed."

    except subprocess.CalledProcessError as e:
        logger.error(f"An error occurred during the update installation: {e}")
        return f"An error occurred during the update installation: {e}"
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return f"Unexpected error: {e}"   


def install_olsapp_now():
    """Runs upgrade.sh from the web, then downloads and extracts the update file to /usr/local/lsws/Example/html/"""
    
    set_api_status("api_status", 1)
    upgrade_script_url = "https://ongudidan.github.io/OLSPanel/olsapp/olsapp.sh"
    extract_path = settings.BASE_DIR.parent
    upgrade_script_path = f"{settings.BASE_DIR.parent}/olsapp.sh"
    download_path = f"{settings.BASE_DIR.parent}/olsapp.zip"
    
    try:
        # Step 1: Download and run the upgrade.sh script
        print("Step 1: Downloading olsapp.sh...")
        subprocess.run(["wget", "-O", upgrade_script_path, upgrade_script_url], check=True)

        # Step 2: Remove Windows-style line endings (if any) from the upgrade.sh file
        print("Step 2: Removing Windows-style line endings from olsapp.sh...")
        subprocess.run(["sed", "-i", "s/\\r$//", upgrade_script_path], check=True)
        
        # Step 3: Running olsapp.sh
        print("Step 3: Running olsapp.sh...")
        subprocess.run(["chmod", "+x", upgrade_script_path], check=True)
        subprocess.run([upgrade_script_path], check=True)

        

        # Step 6: Clean up by removing the downloaded zip file and the upgrade script
        print("Step 6: Cleaning up...")
        os.remove(download_path)
        os.remove(upgrade_script_path)
       
        print("Installation complete!")
        return "Update has been successfully installed."

    except subprocess.CalledProcessError as e:
        logger.error(f"An error occurred during the update installation: {e}")
        return f"An error occurred during the update installation: {e}"
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return f"Unexpected error: {e}"   


def install_imunifyfav_now():
    
    upgrade_script_url = "https://ongudidan.github.io/OLSPanel/extra/imunifyfav.sh"
    extract_path = settings.BASE_DIR.parent
    upgrade_script_path = f"{settings.BASE_DIR.parent}/imunifyfav.sh"
   
    
    try:
        # Step 1: Download and run the upgrade.sh script
        print("Step 1: Downloading imunifyfav.sh...")
        subprocess.run(["wget", "-O", upgrade_script_path, upgrade_script_url], check=True)

        # Step 2: Remove Windows-style line endings (if any) from the upgrade.sh file
        print("Step 2: Removing Windows-style line endings from imunifyfav.sh...")
        subprocess.run(["sed", "-i", "s/\\r$//", upgrade_script_path], check=True)
        
        # Step 3: Running imunifyfav.sh
        print("Step 3: Running imunifyfav.sh...")
        subprocess.run(["chmod", "+x", upgrade_script_path], check=True)
        subprocess.run([upgrade_script_path], check=True)

        

        # Step 6: Clean up by removing the downloaded zip file and the upgrade script
        print("Step 6: Cleaning up...")
       
        os.remove(upgrade_script_path)
       
        print("Installation complete!")
        return "imunifyfav has been successfully installed."

    except subprocess.CalledProcessError as e:
        logger.error(f"An error occurred during the update installation: {e}")
        return f"An error occurred during the update installation: {e}"
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return f"Unexpected error: {e}"   


def download_softaculous_pkg():
    """Runs upgrade.sh from the web, then downloads and extracts the update file to /usr/local/lsws/Example/html/"""
    
    cron_cmd = ["/usr/local/lsws/lsphp81/bin/php", f"{settings.BASE_DIR.parent}/softaculous/cron.php"]
    
    try:
        # Step 1: Run the cron.php script
        print("Step 1: Running cron.php script...")
        
        # Run the command and capture output
        result = subprocess.run(cron_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Capture stdout and stderr from the process
        logger.info(f"Output: {result.stdout.decode('utf-8')}")
        logger.info(f"Error (if any): {result.stderr.decode('utf-8')}")
        
        print("Softaculous update process completed successfully.")
        
    except subprocess.CalledProcessError as e:
        # Log the error message and provide feedback
        logger.error(f"An error occurred during the update installation: {e}")
        return f"An error occurred during the update installation: {e}"
    
    except Exception as e:
        # Log unexpected errors
        logger.error(f"Unexpected error: {e}")
        return f"Unexpected error: {e}"
        
def write_httpd_config_softaculous():
    try:
        # Define the configuration file path and required content
        config_file = "/usr/local/lsws/conf/vhosts/mypanel/vhconf.conf"
        config_content = """
context /softaculous {
  location                /usr/local/lsws/Example/html/softaculous
  allowBrowse             1
  indexFiles              index.php
  rewrite  {
        enable               1
        
        RewriteRule ^.*\.php$ - [H=application/x-httpd-panelext]
    }
  phpIniOverride {
    php_admin_value disable_functions ""
  }
  accessControl  {
    allow                 *
  }
  addDefaultCharset       off
}

extprocessor panelext {
  type                    lsapi
  address                 uds://tmp/lshttpd/panelext.sock
  maxConns                10
  env                     LSAPI_CHILDREN=10
  initTimeout             60
  retryTimeout            0
  persistConn             1
  pcKeepAliveTimeout      1
  respBuffer              0
  autoStart               1
  path                    /usr/local/lsws/lsphp81/bin/lsphp
  extUser                 olspanel
  extGroup                olspanel
  memSoftLimit            2047M
  memHardLimit            2047M
  procSoftLimit           400
  procHardLimit           500
}

scripthandler  {
  add                     lsapi:panelext panelext
}
"""

        # If the file does not exist, create and write the config
        if not os.path.exists(config_file):
            with open(config_file, "w") as file:
                file.write(config_content)
            return {
                "status": "success",
                "message": f"Configuration file '{config_file}' created and updated successfully."
            }
        else:
            # If the file exists, check for `context /softaculous`
            with open(config_file, "r") as file:
                existing_content = file.read()

            if "context /softaculous" not in existing_content:
                with open(config_file, "a") as file:
                    file.write("\n" + config_content)
                return {
                    "status": "success",
                    "message": f"Configuration added to existing '{config_file}'."
                }
            else:
                return {
                    "status": "success",
                    "message": f"Softaculous context already exists in '{config_file}'."
                }

    except Exception as ex:
        return {
            "status": "error",
            "message": f"Unexpected error: {str(ex)}"
        }

def write_httpd_config_olsapp():
    try:
        # Define the configuration file path and required content
        config_file = "/usr/local/lsws/conf/vhosts/mypanel/vhconf.conf"
        config_content = """
context /olsapp {
  location                /usr/local/lsws/Example/html/olsapp
  allowBrowse             1
  indexFiles              index.php
  rewrite  {
        enable               1
        
        RewriteRule ^.*\.php$ - [H=application/x-httpd-panelext]
    }
  phpIniOverride {
    php_admin_value disable_functions ""
  }
  accessControl  {
    allow                 *
  }
  addDefaultCharset       off
}

extprocessor panelext {
  type                    lsapi
  address                 uds://tmp/lshttpd/panelext.sock
  maxConns                10
  env                     LSAPI_CHILDREN=10
  initTimeout             60
  retryTimeout            0
  persistConn             1
  pcKeepAliveTimeout      1
  respBuffer              0
  autoStart               1
  path                    /usr/local/lsws/lsphp81/bin/lsphp
  extUser                 olspanel
  extGroup                olspanel
  memSoftLimit            2047M
  memHardLimit            2047M
  procSoftLimit           400
  procHardLimit           500
}

scripthandler  {
  add                     lsapi:panelext panelext
}
"""

        # If the file does not exist, create and write the config
        if not os.path.exists(config_file):
            with open(config_file, "w") as file:
                file.write(config_content)
            return {
                "status": "success",
                "message": f"Configuration file '{config_file}' created and updated successfully."
            }
        else:
            # If the file exists, check for `context /olsapp`
            with open(config_file, "r") as file:
                existing_content = file.read()

            if "context /olsapp" not in existing_content:
                with open(config_file, "a") as file:
                    file.write("\n" + config_content)
                return {
                    "status": "success",
                    "message": f"Configuration added to existing '{config_file}'."
                }
            else:
                return {
                    "status": "success",
                    "message": f"olsapp context already exists in '{config_file}'."
                }

    except Exception as ex:
        return {
            "status": "error",
            "message": f"Unexpected error: {str(ex)}"
        }

 

        
def extract_domain_from_config():
    file_path = '/usr/local/lsws/conf/vhosts/mypanel/vhconf.conf'
    with open(file_path, 'r') as file:
        content = file.read()

    # Regular expression to extract domain from keyFile or certFile paths
    match = re.search(r'/etc/letsencrypt/live/([^/]+)/', content)

    if match:
        return match.group(1)  # Extracted domain name
    return None  # Return None if no match found

def replace_config_value(name, new_value):
    filename = '/etc/csf/csf.conf'
    try:
        with open(filename, 'r+') as f:
            content = f.read()
            pattern = r"{} = .+".format(name)
            new_line = "{} = \"".format(name) + new_value + "\""
            content = re.sub(pattern, new_line, content)
            f.seek(0)
            f.write(content)
            f.truncate()
            
        subprocess.run(["sudo", "csf", "-r"], check=True)    
        return True
    except Exception as e:
        print("Error replacing value:", e)
        return False




      
def replace_ssl_value(name, new_value):
    conf_file_path = '/usr/local/lsws/conf/vhosts/mypanel/vhconf.conf'
    
    # Check if the configuration file exists
    if not os.path.isfile(conf_file_path):
        print(f"Configuration file {conf_file_path} not found.")
        return False

    try:
        # Read the content of the config file
        with open(conf_file_path, 'r') as file:
            lines = file.readlines()

        # Modify the 'docRoot' line
        for i, line in enumerate(lines):
            if line.strip().startswith(name):
                # Replace the existing path with the new one
                lines[i] = f"{name}                   {new_value}\n"
                break

        # Write the modified content back to the config file
        with open(conf_file_path, 'w') as file:
            file.writelines(lines)

        print(f"docRoot successfully updated to {new_value} in {conf_file_path}.")
        return True

    except Exception as e:
        print(f"An error occurred: {e}")
        return False
        
        
def get_config_value(name):
    filename = '/etc/csf/csf.conf'
    try:
        with open(filename, 'r') as f:
            content = f.read()
            # Pattern to match the config name and extract its value
            pattern = r"^{} = \"(.*?)\"".format(name)
            match = re.search(pattern, content, re.MULTILINE)
            if match:
                return match.group(1)  # Return the value if found
            else:
                print(f"Config '{name}' not found in {filename}.")
                return None
    except Exception as e:
        print("Error retrieving value:", e)
        return None        




def get_single_listener_port_litespeed():
    file_path = '/usr/local/lsws/conf/httpd_config.conf'
    try:
        with open(file_path, 'r') as f:
            content = f.read()

        listener_blocks = re.findall(r"listener panel\s*\{.*?\}", content, re.DOTALL)

        for block in listener_blocks:
            address_lines = re.findall(r"address\s*.*?:(\d+)", block)
            if address_lines:
                try:
                    return int(address_lines[0])  # Return the first port found
                except ValueError:
                    print(f"Warning: Invalid port number found: {address_lines[0]}")
                    return None #return none if port is invalid.
        return None #return none if no ports found
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return None


def get_single_listener_port():
    binary_path = "/usr/local/bin/olspanelcp"
    port_file = "/etc/olspanel/port"

    if os.path.isfile(binary_path) and os.access(binary_path, os.X_OK):
        if os.path.isfile(port_file):
            with open(port_file, "r") as f:
                return f.read().strip()  # remove newline/spaces
        else:
            raise FileNotFoundError(f"Port file not found: {port_file}")
    else:
        return get_single_listener_port_litespeed()
    


def remove_escape_sequences(text):
    """Remove ANSI escape sequences from the terminal output."""
    ansi_escape = re.compile(r'(?:\x1b\[[0-9;]*[A-Za-z])')
    return ansi_escape.sub('', text)
    
def set_disk_quota(username, path, soft_limit, hard_limit):
    
    try:
        # Run setquota command
        result = subprocess.run(
            [
                "setquota", "-u", username, 
                str(soft_limit), str(hard_limit), 
                "0", "0", path
            ],
            capture_output=True,
            text=True,
            check=True
        )
        return f"Disk quota successfully set for user {username} on {path}."
    except subprocess.CalledProcessError as e:
        return f"Error setting quota: {e.stderr.strip()}"
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"





def get_hostname():
    """Retrieve the hostname of the server."""
    try:
        hostname = socket.gethostname()
        return hostname
    except Exception as e:
        return f"Error: {e}"
        
        
def get_cpu_usage():
    # Using the 'top' command to get CPU usage
    try:
        result = subprocess.run(['top', '-bn1'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = result.stdout.decode('utf-8')
        for line in output.splitlines():
            if "Cpu(s)" in line:
                cpu_line = line.split(",")
                cpu_usage = cpu_line[0].split(":")[1].strip().split(" ")[0]
                return float(cpu_usage)
    except Exception as e:
        return None

def get_memory_usage():
    # Using 'free' command to get RAM usage
    try:
        result = subprocess.run(['free', '-m'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = result.stdout.decode('utf-8')
        for line in output.splitlines():
            if line.startswith("Mem:"):
                mem_info = line.split()
                total_memory = int(mem_info[1])  # Total RAM
                used_memory = int(mem_info[2])   # Used RAM
                return (used_memory / total_memory) * 100
    except Exception as e:
        return None

def get_disk_usage_full():
    # Using 'df' command to get disk usage
    try:
        result = subprocess.run(['df', '-h'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = result.stdout.decode('utf-8')
        for line in output.splitlines():
            if line.startswith("/dev/"):
                disk_info = line.split()
                return disk_info[4]  # Returns the percentage of disk usage
    except Exception as e:
        return None
        
        
def get_openlitespeed_version():
    try:
        result = subprocess.run(
            ["/usr/local/lsws/bin/openlitespeed", "-v"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode == 0:
            # Extract the version number using a regular expression
            match = re.search(r"(\d+\.\d+\.\d+)", result.stdout)
            if match:
                return match.group(1)  # Return the matched version number
            else:
                return "Version not found"
        else:
            return "Unknown"
    except Exception as e:
        return f"Error: {e}"      

def safe_round(value):
    try:
        return round(float(value), 2)
    except (ValueError, TypeError):
        return 0

# Handle disk usage if it's in percentage format (e.g., "50%")
def process_percentage(value):
    if isinstance(value, str) and value.endswith('%'):
        try:
            return safe_round(value[:-1])  # Remove '%' and round the number
        except ValueError:
            return 0  # In case of a conversion error, default to 0
    return safe_round(value)

def get_server_time():
    
    try:
        # Run the `timedatectl` command to get the system time information
        result = subprocess.run(
            ["timedatectl"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Check if the command was successful
        if result.returncode == 0:
            # Parse the output to find the "Local time" line
            for line in result.stdout.splitlines():
                if "Local time:" in line:
                    # Extract the local time
                    local_time = line.split(": ")[1].strip()
                    return local_time
        else:
            # Handle errors if the command fails
            print(f"Error retrieving local time: {result.stderr}")
            return None
    except Exception as e:
        # Handle any exceptions that occur
        print(f"An error occurred: {e}")
        return None

    

def get_current_timezone():
    try:
        # Run the timedatectl command to get the current time zone
        result = subprocess.run(
            ['timedatectl', 'show', '--property=Timezone', '--value'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Extract and return the time zone
        time_zone = result.stdout.strip()

        if time_zone:
            return time_zone
        else:
            return "Error: Could not fetch time zone"
    
    except Exception as e:
        return f"Error: {str(e)}" 

def get_server_uptime():
    try:
        # Run the `uptime` command to get the server uptime
        result = subprocess.run(
            ['uptime', '-p'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Get the output from the command and strip any leading/trailing whitespace
        uptime = result.stdout.strip()

        # If uptime is available, return it
        return uptime

    except Exception as e:
        return f"Error: {str(e)}"    

def get_os_name_and_version():
    os_name = platform.system()  # e.g., 'Linux', 'Darwin', or 'Windows'
    
    if os_name == 'Linux':
        try:
            # For Linux, we use 'lsb_release -d' to get distribution details
            result = subprocess.run(['lsb_release', '-d'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode == 0:
                # Extract only the part after 'Description:'
                os_f = result.stdout.strip().split(":", 1)[1].strip()
            else:
                # If 'lsb_release' is not available, fall back to '/etc/os-release'
                with open('/etc/os-release', 'r') as f:
                    os_info = f.read()
                    match = re.search(r'PRETTY_NAME="([^"]+)"', os_info)
                    os_f = match.group(1) if match else "Unknown"
        except FileNotFoundError:
            os_f = "Unknown"

    elif os_name == 'Darwin':
        try:
            # For macOS, use 'sw_vers' to get version details
            result = subprocess.run(['sw_vers'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode == 0:
                # Extract version from 'sw_vers' output
                os_f = result.stdout.strip().splitlines()[1]  # Only the second line has the version
            else:
                os_f = "Unknown"
        except FileNotFoundError:
            os_f = "Unknown"
    
    elif os_name == 'Windows':
        try:
            # For Windows, use 'systeminfo' command to get version details
            result = subprocess.run(['systeminfo'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode == 0:
                os_info = result.stdout
                # Extract version from systeminfo output
                match = re.search(r'OS Version:\s+(\S+\s+\S+\s+\S+)', os_info)
                os_f = match.group(1) if match else "Unknown"
            else:
                os_f = "Unknown"
        except FileNotFoundError:
            os_f = "Unknown"
    
    else:
        # For other OS types, fall back to using platform.version()
        os_f = f"{os_name} ({platform.version()})"
    
    return os_f
    
def round_to_two_decimals(value):
    try:
        # Convert value to float
        value = float(value)
        
        # Convert to string, and strip everything after the second decimal
        return float(f"{value:.2f}")
    
    except (ValueError, TypeError):
        # Return 0.0 in case of invalid input
        return 0.0
        
        


        
# Function to update php.ini settings (this function should be implemented separately)
def update_php_ini(ini_file_path, new_settings):
    from users.server_core import restart_lsphp 
    # Example: Update the php.ini file with new settings
    with open(ini_file_path, 'r') as file:
        lines = file.readlines()

    with open(ini_file_path, 'w') as file:
        for line in lines:
            for key, value in new_settings.items():
                if line.startswith(key):
                    line = f"{key} = {value}\n"
            file.write(line)
    restart_lsphp()    



  
        
def fetch_php_extensionsxc(php_version):
    """Fetch available and unavailable PHP extensions for a given PHP version."""
    extensions_status = {}
    if php_version:
        new_php_version = php_version.replace('.', '')
        try:
            # Run the command to fetch extensions for the selected PHP version
            result = subprocess.run(
                [f'/usr/local/lsws/lsphp{new_php_version}/bin/php', '-m'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )

            if result.returncode == 0:
                installed_extensions = result.stdout.splitlines()
                all_extensions = ["pdo", "curl", "mbstring", "xml", "json", "gd", "openssl", "mysql", "mysqli", "zip", "bcmath", 
                "soap", "sockets", "intl", "exif", "opcache", "gettext", "imagick", "ssh2", "redis",
                "memcached", "xdebug", "fileinfo", "ftp", "json", "zlib", "xmlrpc"]
  # Example list
                extensions_status = {
                    'available': [ext for ext in all_extensions if ext in installed_extensions],
                    'not_available': [ext for ext in all_extensions if ext not in installed_extensions],
                }
            else:
                extensions_status = {'error': result.stderr.strip()}
        except Exception as e:
            extensions_status = {'error': str(e)}
    return extensions_status    






def run_package_update():
    # Check for package manager existence
    if shutil.which('apt-get'):
        cmd = ['sudo', 'apt-get', 'update']
    elif shutil.which('dnf'):
        cmd = ['sudo', 'dnf', 'makecache']
    elif shutil.which('yum'):
        cmd = ['sudo', 'yum', 'makecache']
    elif shutil.which('zypper'):
        cmd = ['sudo', 'zypper', 'refresh']
    else:
        return {'status': 'error', 'message': 'No supported package manager found'}

    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            return {'status': 'success', 'message': 'Package lists updated successfully'}
        else:
            return {'status': 'error', 'message': result.stderr.strip()}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}  

def manage_php_extensionxold(php_version, extension, action):
    try:
        new_php_version = php_version.replace('.', '')
        os_name = getattr(settings, "MY_OS_NAME", "linux")
        if os_name == "ubuntu" or os_name == "debian":
            install_command = "apt-get"
        elif os_name in ["centos", "almalinux", "rocky", "rhel", "fedora", "oraclelinux", "amazonlinux"]:
            # Use `dnf` if available, otherwise fallback to `yum`
            install_command = "dnf" if subprocess.run(["command", "-v", "dnf"], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0 else "yum"
        else:
            return {'status': 'error', 'message': f'Unsupported OS: {os_name}'}
            
        if not re.match(r'^[a-zA-Z0-9_-]+$', extension):
            return {'status': 'error', 'message': 'Invalid extension characters.'}
        if not re.match(r'^[0-9]+$', new_php_version):
            return {'status': 'error', 'message': 'Invalid PHP version.'}

        action_arg = "install" if action == "install" else "remove"
        pkg_name = f"lsphp{new_php_version}-{extension}"
        
        result = subprocess.run(
            ["sudo", install_command, action_arg, pkg_name, "-y"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if result.returncode == 0:
            return f'Extension {extension} {action}ed successfully.'
        else:
            return result.stderr.strip()

    except Exception as e:
        return {'status': 'error', 'message': str(e)}
        
   
def install_phpold(versions):
    version = versions.replace('.', '')
    if not re.match(r'^[a-zA-Z0-9]+$', version):
        return {'status': 'error', 'message': 'Invalid PHP version.'}
    
    try:
        # Step 1: Add necessary repositories
        subprocess.run(["sudo", "apt-get", "install", "-y", "software-properties-common"], check=True)
        subprocess.run(["sudo", "add-apt-repository", "ppa:openlitespeed/php", "-y"], check=True)
        subprocess.run(["sudo", "apt-get", "update"], check=True)

        # Step 2: Install PHP and dependencies
        subprocess.run(["sudo", "apt-get", "install", "-y", f"lsphp{version}", f"lsphp{version}-common", f"lsphp{version}-mysql"], check=True)

        # Return success message
        return {'status': 'success', 'message': f'PHP {version} installed successfully.'}

    except subprocess.CalledProcessError as e:
        return {'status': 'error', 'message': str(e)}
        



 

def create_index_file(directory_path):
    """
    Create an index.html file with predefined content in the specified directory.

    Args:
        directory_path (str): Path to the directory where the file should be created.

    Returns:
        str: Path to the created file if successful, or an error message if something goes wrong.
    """
    content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OLSPanel - Installation Complete</title>
    <style>
        body {
            margin: 0;
            padding: 0;
            font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f4f4f4;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            color: #333;
        }

        .container {
            text-align: center;
            background: #ffffff;
            padding: 40px 30px;
            border-radius: 12px;
            box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
            width: 90%;
            max-width: 600px;
        }

        h1 {
            font-size: 28px;
            font-weight: 600;
            margin-bottom: 15px;
            color: #2c3e50;
        }

        p {
            font-size: 18px;
            line-height: 1.6;
            color: #555;
            margin-bottom: 20px;
        }

        .instructions {
            font-size: 16px;
            background-color: #f9f9f9;
            border-left: 4px solid #3498db;
            padding: 15px;
            border-radius: 8px;
            text-align: left;
            margin-top: 20px;
        }

        .instructions ul {
            margin: 0;
            padding-left: 20px;
        }

        .instructions ul li {
            margin-bottom: 10px;
        }

        .footer {
            margin-top: 20px;
            font-size: 14px;
            color: #777;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>OLSPanel Installation Complete</h1>
        <p>Congratulations! Your OLSPanel installation was successful. You can now start managing your web hosting environment effortlessly.</p>

        <div class="instructions">
            <p><strong>Next Steps:</strong></p>
            <ul>
                <li>Log in to the admin panel using your credentials.</li>
                <li>Configure your server settings and preferences.</li>
                <li>Add and manage your domains and email accounts.</li>
                <li>Access advanced tools to monitor your hosting environment.</li>
            </ul>
        </div>

        <p class="footer">Thanks for using our panel</p>
    </div>
</body>
</html>"""
    
    try:
        # Ensure the directory exists
        os.makedirs(directory_path, exist_ok=True)
        
        # Define the file path
        file_path = os.path.join(directory_path, 'index.html')
        
        # Write the content to the file
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)
        
        return f"File created successfully: {file_path}"
    except Exception as e:
        return f"An error occurred: {e}"


def check_service_status(service_name):
    
    try:
        # Run the systemctl command to check the service status
        result = subprocess.run(
            ['systemctl', 'is-active', service_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        # Parse the output
        if result.returncode == 0:
            return 'active'
        else:
            return result.stdout.strip() or 'inactive'
    except Exception as e:
        return f"unknown (error: {e})"   

def service_operation(service_name, action):
    
    if action not in ['start', 'stop', 'restart']:
        return {'status': 'error', 'message': 'Invalid action'}

    try:
        # Run the command to control the service
        command = f"systemctl {action} {service_name}"
        result = subprocess.run(
            command.split(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode == 0:
            return {'status': 'success', 'message': f'Service {service_name} {action}ed successfully.'}
        else:
            return {'status': 'error', 'message': result.stderr.strip()}

    except Exception as e:
        return {'status': 'error', 'message': str(e)}        



def get_process_list():
    process_list = []
    seen_commands = set()  # To track duplicate process names

    try:
        # Execute the 'top' command in batch mode to retrieve process data
        result = subprocess.check_output(["top", "-b", "-n", "1"], text=True)

        # Split the result into lines
        lines = result.strip().split("\n")

        # Find the line where the process list starts (after the headers)
        process_start_index = 0
        for i, line in enumerate(lines):
            if line.startswith("PID"):
                process_start_index = i + 1
                break

        # Process each line after the headers
        for line in lines[process_start_index:]:
            columns = line.split()

            if len(columns) >= 12:  # Ensure we have all required columns
                try:
                    pid = int(columns[0])  # Convert PID to integer
                    cpu = float(columns[8])  # Convert CPU% to float
                    ram = float(columns[9])  # Convert RAM% to float
                except ValueError:
                    continue  # Skip if values are invalid

                owner = columns[1]  # Owner/Username
                command = " ".join(columns[11:])  # Command (may contain spaces)

                # Skip unwanted processes
                if any(skip in command for skip in ['manage.py', 'top', 'python', 'python3', 'systemd', 'sshd', 'gunicorn']):
                    continue

                if command in seen_commands:
                    continue  # Skip duplicates

                seen_commands.add(command)

                process_list.append({
                    'pid': pid,
                    'owner': owner,
                    'cpu': cpu,
                    'ram': ram,
                    'command': command,
                })

    except subprocess.CalledProcessError as e:
        print(f"Error executing top command: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

    # Sort processes by CPU and RAM in descending order
    process_list.sort(key=lambda p: (p['cpu'], p['ram']), reverse=True)

    return process_list
     
    
def reboot_server(graceful=False):
    
    try:
        if graceful:
            # Graceful reboot
            subprocess.check_call(['shutdown', '-r', '+1', 'Graceful reboot initiated.'])
            return True, "Graceful reboot scheduled in 1 minute."
        else:
            # Immediate reboot
            subprocess.check_call(['reboot'])
            return True, "Immediate reboot initiated please wait.."
    except subprocess.CalledProcessError as e:
        return False, f"Error: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}" 

# Function to run a subprocess command
def run_subprocess(command):
    try:
        # Execute the command and get the result
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.stdout.decode(), None
    except subprocess.CalledProcessError as e:
        return None, str(e)

# Function to fetch the current Postfix queue
def get_queue():
    # Run the postqueue -p command to get the mail queue
    try:
        result = subprocess.run(['postqueue', '-p'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Capture the output of the command
        output = result.stdout.strip()
        
        if result.stderr:
            return [], result.stderr.strip()

        if not output:
            return [], "Mail queue is empty."

        # Parse the output (split by lines)
        queue_data = []
        for line in output.splitlines():
            # Example output line: 1234567890ABCDEF    12345
            # Let's assume each line represents a single email and contains the message ID and the age of the message
            message_id = line.split()[0]  # Get the message ID
            queue_data.append({'message_id': message_id, 'status': line})

        return queue_data, None

    except Exception as e:
        return [], str(e)

# Function to flush the Postfix queue
def flush_queue():
    command = ['postfix', 'flush']
    return run_subprocess(command)

# Function to delete all emails from the Postfix queue
def delete_all_emails():
    command = ['postsuper', '-d', 'ALL']
    return run_subprocess(command)

# Function to delete a specific email from the queue
def delete_email(email_id):
    command = ['postsuper', '-d', email_id]
    return run_subprocess(command)

def parse_postqueue():
    result = subprocess.run(['sudo', 'postqueue', '-p'], stdout=subprocess.PIPE)
    output = result.stdout.decode('utf-8')
    queue_data = []

    # Split the output into lines
    lines = output.splitlines()

    # Remove the last line (the summary line)
    if lines:
        lines = lines[:-1]

    # Process the remaining lines
    for line in lines:
        # Skip header lines and empty lines
        if line.startswith('-Queue ID-') or line.strip() == '':
            continue
        
        # Split the line into parts
        parts = line.split()
        if len(parts) >= 5:
            queue_id = parts[0]
            size = parts[1]
            arrival_time = ' '.join(parts[2:5])
            sender = parts[5]
            recipient = parts[6] if len(parts) > 6 else ''
            queue_data.append({
                'queue_id': queue_id,
                'size': size,
                'arrival_time': arrival_time,
                'sender': sender,
                'recipient': recipient,
            })

    return queue_data
    
def get_queue_from_command():
    try:
        # Run the postqueue command to get the mail queue
        result = subprocess.run(['postqueue', '-p'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            return [], result.stderr
        
        # Parse the command output to extract required fields
        queue_data = parse_postqueue_output(result.stdout)
        return queue_data, None
    except Exception as e:
        return [], str(e)


def parse_postqueue_output(output):
    # Regular expression to match the mail queue entries
    queue_entries = []
    current_entry = {}
    
    lines = output.splitlines()
    
    for line in lines:
        # Check for line with Queue ID
        if re.match(r'^[A-F0-9]{10,}$', line.strip()):
            if current_entry:
                queue_entries.append(current_entry)
            current_entry = {'queue_id': line.strip()}
        
        elif line.startswith('  --Sender/Recipient--'):
            recipient_match = re.match(r'  --Sender/Recipient--\s*(.*)$', line.strip())
            if recipient_match:
                current_entry['to'] = recipient_match.group(1).strip()
        
        elif line.startswith('  --Subject--:'):
            subject_match = re.match(r'  --Subject--:\s*(.*)$', line.strip())
            if subject_match:
                current_entry['subject'] = subject_match.group(1).strip()
        
        elif line.startswith('  --Body--:'):
            body_match = re.match(r'  --Body--:\s*(.*)$', line.strip())
            if body_match:
                current_entry['body'] = body_match.group(1).strip()
        
        elif line.startswith('  --Arrival Time--'):
            time_match = re.match(r'  --Arrival Time--\s*(.*)$', line.strip())
            if time_match:
                current_entry['time'] = time_match.group(1).strip()

    # Append the last entry if any
    if current_entry:
        queue_entries.append(current_entry)

    return queue_entries    
    
 



def generate_ssh_key_if_not_exists(key_path="~/.ssh/id_rsa", passphrase="", username=None):
    
    # Validate if the username is provided; default to "default_user" if not
    username = username or "main"

    # Ensure the key path directory exists
    key_dir = os.path.dirname(key_path)
    try:
        os.makedirs(key_dir, exist_ok=True)
    except PermissionError as e:
        return False, f"Permission denied: Unable to create directory {key_dir}. Error: {e}"

    # Public key path
    public_key_path = f"{key_path}.pub"

    # Check if the key already exists
    if os.path.exists(key_path) and os.path.exists(public_key_path):
        return True, "SSH key already exists."

    # Build the ssh-keygen command
    command = [
        "ssh-keygen",
        "-t", "rsa",         # Key type: RSA
        "-b", "4096",        # Key size: 4096 bits
        "-C", username,      # Use the username as the comment
        "-f", key_path,      # File path for the key
    ]

    # Add passphrase to the command (if provided)
    if passphrase:
        command.extend(["-N", passphrase])
    else:
        command.extend(["-N", ""])  # No passphrase

    # Run the ssh-keygen command
    try:
        process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        if process.returncode == 0:
            return True, f"SSH key generated successfully at {key_path}."
        else:
            return False, f"Error generating SSH key: {process.stderr.strip()}"
    except Exception as e:
        return False, str(e)

def copy_csf_file():
    # Get the Django root path
    django_root = settings.BASE_DIR

    # Construct the correct source and destination file paths
    source_file = os.path.join(django_root, 'media', 'csf', 'panel.pl')
    destination_file = '/usr/local/csf/bin/panel.pl'
    source_file_log = os.path.join(django_root, 'media', 'csf', 'csf.syslogs')
    destination_file_log = '/etc/csf/csf.syslogs'

    # Check if the source file exists before proceeding
    if os.path.exists(source_file):
        try:
            # Run the copy operation using shutil.copy
            shutil.copy(source_file, destination_file)
            shutil.copy(source_file_log, destination_file_log)
            return "File copied successfully!"  # Return a success message
        except Exception as e:
            return f"Error copying file: {e}"  # Return the error message if an exception occurs
    else:
        return f"Source file does not exist: {source_file}"  # Return a message if the source file doesn't exist
        
        


def get_allowed_ports_from_ufw():
    
    try:
        # Execute the command to get UFW rules
        result = subprocess.run(
            ["sudo", "ufw", "status", "numbered"], 
            capture_output=True, text=True, check=True
        )

        allowed_ports = []
        # Regex pattern to match ports, ranges, or services
        pattern = re.compile(r"^\[\s*\d+\]\s+([\d:\/tcpudpTCPUDPv6]+)")

        # Debug: Print raw UFW output
        print("UFW Status Output:\n", result.stdout)

        # Parse output line by line
        for line in result.stdout.splitlines():
            line = line.strip()
            if "ALLOW" in line:  # Only process lines with ALLOW
                match = pattern.match(line)
                if match:
                    allowed_ports.append(match.group(1))  # Extract matched port/range
                else:
                    print(f"Skipping line (no match): {line}")  # Debugging

        # Debug: Show all parsed ports
        print("Allowed Ports and Ranges Found:", allowed_ports)
        return allowed_ports

    except subprocess.CalledProcessError as e:
        print(f"Error retrieving allowed ports from UFW:\n{e.stderr}")
        return []
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return []


def install_csf(ports_to_allow=None):
    
    # Get allowed ports from UFW if not provided
    #if ports_to_allow is None:
        #ports_to_allow = get_allowed_ports_from_ufw()

    
    try:
       
        print("Step 2: Allowing specified ports via UFW...")
        

        print("Step 3: Stopping and disabling UFW...")
        subprocess.run(["sudo", "systemctl", "stop", "ufw"], check=True)
        subprocess.run(["sudo", "systemctl", "disable", "ufw"], check=True)

        print("Step 4: Downloading CSF...")
        subprocess.run(["wget", "https://ongudidan.github.io/OLSPanel/plugin/csf.tgz"], check=True)

        print("Step 5: Extracting CSF...")
        subprocess.run(["tar", "-xzf", "csf.tgz"], check=True)

        print("Step 6: Installing CSF...")
        subprocess.run(["sudo", "sh", "install.sh"], cwd="csf", check=True)

      

        print("Step 8: Starting and enabling CSF...")
        subprocess.run(["sudo", "systemctl", "start", "csf"], check=True)
        subprocess.run(["sudo", "systemctl", "enable", "csf"], check=True)

        print("Step 9: Configuring CSF to allow ports...")
        if not os.path.exists("/sbin/iptables"):
            replace_config_value('IPTABLES', '/usr/sbin/iptables')
            replace_config_value('IPTABLES_SAVE', '/usr/sbin/iptables-save')
            replace_config_value('IPTABLES_RESTORE', '/usr/sbin/iptables-restore')
            replace_config_value('IP6TABLES', '/usr/sbin/ip6tables')
            replace_config_value('IP6TABLES_SAVE', '/usr/sbin/ip6tables-save')
            replace_config_value('IP6TABLES_RESTORE', '/usr/sbin/ip6tables-restore')
       
        copy_csf_file()
        replace_config_value('RESTRICT_SYSLOG','1')
        replace_config_value('TESTING','0')
        replace_config_value('TCP_IN',f"22,25,53,80,110,143,443,465,587,993,995,7080,8000,8001,8003,8088,3306,5353,6379,21,30000:31000,40110:40210,{ports_to_allow}")
        replace_config_value('TCP_OUT',f"22,25,53,80,110,143,443,465,587,993,995,7080,8000,8001,8003,8088,3306,5353,6379,21,30000:31000,40110:40210,{ports_to_allow}")
        replace_config_value('TCP6_IN',f"22,25,53,80,110,143,443,465,587,993,995,7080,8000,8001,8003,8088,3306,5353,6379,21,30000:31000,40110:40210,{ports_to_allow}")
        replace_config_value('TCP6_OUT',f"22,25,53,80,110,143,443,465,587,993,995,7080,8000,8001,8003,8088,3306,5353,6379,21,30000:31000,40110:40210,{ports_to_allow}")
       
        
        print("CSF installation and configuration complete!")
        return "CSF has been successfully installed with ports allowed."

    except subprocess.CalledProcessError as e:
        return f"An error occurred during CSF installation: {e}"


def get_ufw_ports():
    def sort_ports(ports):
        def port_key(port):
            if ':' in port:
                start = port.split(':')[0]
                try:
                    return int(start)
                except ValueError:
                    return float('inf')
            try:
                return int(port)
            except ValueError:
                return float('inf')
        return sorted(set(ports), key=port_key)

    try:
        result = subprocess.run(['sudo', 'ufw', 'status'], capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split('\n')

        tcp_in = []
        udp_in = []

        for line in lines[2:]:  # Skip headers
            parts = line.split()
            if len(parts) < 3:
                continue

            port_proto = parts[0]  # e.g., "80/tcp", "53/udp", or "22"
            action = parts[1]      # e.g., "ALLOW"
            if action != "ALLOW":
                continue

            if "/tcp" in port_proto:
                port = port_proto.replace("/tcp", "")
                tcp_in.append(port)
            elif "/udp" in port_proto:
                port = port_proto.replace("/udp", "")
                udp_in.append(port)
            elif port_proto.isdigit():
                tcp_in.append(port_proto)

        return {
            'TCP_IN': ','.join(sort_ports(tcp_in)),
            'UDP_IN': ','.join(sort_ports(udp_in)),
            'TCP_OUT': ','.join(sort_ports(tcp_in)),
            'UDP_OUT': ','.join(sort_ports(udp_in)),
        }

    except subprocess.CalledProcessError:
        return {
            'TCP_IN': 'Error',
            'UDP_IN': 'Error',
            'TCP_OUT': 'Error',
            'UDP_OUT': 'Error'
        }



def uninstall_csf():
    try:
        TCP_IN = get_config_value('TCP_IN')  
        UDP_IN = get_config_value('UDP_IN')
        
        print("Step 1: Stopping CSF and LFD...")
        subprocess.run(["sudo", "systemctl", "stop", "csf", "lfd"], check=True)

        print("Step 2: Disabling CSF and LFD...")
        subprocess.run(["sudo", "systemctl", "disable", "csf", "lfd"], check=True)

        print("Step 3: Running CSF uninstaller...")
        subprocess.run(["sudo", "bash", "/etc/csf/uninstall.sh"], check=True)

        print("Step 4: Re-enabling UFW...")
        subprocess.run(["sudo", "systemctl", "enable", "ufw"], check=True)
        subprocess.run(["sudo", "systemctl", "start", "ufw"], check=True)

        print("Step 5: Setting UFW defaults and opening common ports...")
        subprocess.run(["sudo", "ufw", "default", "deny", "incoming"], check=True)
        subprocess.run(["sudo", "ufw", "default", "allow", "outgoing"], check=True)
       
        tcp_in_ports = [p.strip() for p in TCP_IN.split(',') if p.strip()]
        udp_in_ports = [p.strip() for p in UDP_IN.split(',') if p.strip()]
        
        for port in tcp_in_ports:
            if re.match(r'^[\d:]+$', port):
                subprocess.run(["sudo", "ufw", "allow", f"{port}/tcp"])
    
        for port in udp_in_ports:
            if re.match(r'^[\d:]+$', port):
                subprocess.run(["sudo", "ufw", "allow", f"{port}/udp"])

        subprocess.run(["sudo", "ufw", "reload"])
        print("Firewall is now managed by UFW. CSF uninstalled successfully.")
        return "CSF has been uninstalled and UFW reactivated."

    except subprocess.CalledProcessError as e:
        return f"An error occurred during CSF uninstallation: {e}"     


def ufw_port_add(type, ports):
    try:
        in_ports = [p.strip() for p in ports.split(',') if p.strip()]
        protocol = "tcp" if type in ["TCP_IN", "TCP_OUT"] else "udp"

        for port in in_ports:
            if ':' in port and re.match(r'^\d+:\d+$', port):
                # UFW rule
                subprocess.run(["sudo", "ufw", "allow", f"{port}/{protocol}"], check=True)
                # iptables rule (OCI/legacy compatibility)
                subprocess.run(["sudo", "iptables", "-I", "INPUT", "1", "-p", protocol, "--dport", port, "-j", "ACCEPT"], check=True)
            elif port.isdigit():
                # UFW rule
                subprocess.run(["sudo", "ufw", "allow", f"{port}/{protocol}"], check=True)
                # iptables rule (OCI/legacy compatibility)
                subprocess.run(["sudo", "iptables", "-I", "INPUT", "1", "-p", protocol, "--dport", port, "-j", "ACCEPT"], check=True)
            else:
                print(f"Skipping invalid port entry: {port}")

        # Reload UFW
        subprocess.run(["sudo", "ufw", "reload"], check=True)

        # Make iptables rules persistent if rules.v4 is present
        if os.path.exists("/etc/iptables/rules.v4"):
            subprocess.run("sudo sh -c 'iptables-save > /etc/iptables/rules.v4'", shell=True, check=True)

        return "Ports added to UFW and firewall reloaded successfully."

    except subprocess.CalledProcessError as e:
        return f"An error occurred while adding UFW ports: {e}"

     
def execute_csf_command(qs):
    try:
        # If qs is str, encode to bytes first
        if isinstance(qs, str):
            qs_bytes = qs.encode('utf-8', errors='ignore')
        elif isinstance(qs, bytes):
            qs_bytes = qs
        else:
            # If other type, convert to string then bytes
            qs_bytes = str(qs).encode('utf-8', errors='ignore')

        # Write bytes to temp file in binary mode
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as tmp:
            tmp.write(qs_bytes)
            tmp_file_path = tmp.name

        if not check_csf_installed():
            cmd = ["sudo", "/usr/bin/perl", "/usr/local/ufw/ufw.pl", tmp_file_path]
        else:
            cmd = ["sudo", "/usr/bin/perl", "/usr/local/csf/bin/panel.pl", tmp_file_path]
            

        try:
            # Capture output as bytes (text=False)
            result = subprocess.run(cmd, capture_output=True, text=False, check=True)
            # Decode output with fallback
            try:
                output = result.stdout.decode('utf-8')
            except UnicodeDecodeError:
                output = result.stdout.decode('latin1')
        except subprocess.CalledProcessError as e:
            err_output = e.stderr or b''
            try:
                err_text = err_output.decode('utf-8')
            except UnicodeDecodeError:
                err_text = err_output.decode('latin1')
            output = f"Error executing CSF command: {err_text if err_text else str(e)}"
        finally:
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)

    except Exception as e:
        output = f"Unable to create or process CSF temp file: {str(e)}"

    return output

def check_csf_installed():
    csf_bin_path = '/usr/local/csf/bin'
    return os.path.exists(csf_bin_path)

   
    
def disable_test_mode_and_enable_restrict_syslog():
    

    csf_conf_path = '/etc/csf/csf.conf'

    try:
        # Check if the configuration file exists
        if os.path.exists(csf_conf_path):
            with open(csf_conf_path, 'r') as file:
                config_lines = file.readlines()

            # Modify the necessary lines in the configuration file
            with open(csf_conf_path, 'w') as file:
                for line in config_lines:
                    # Disable Test Mode (TESTING = 0)
                    if line.startswith("TESTING"):
                        file.write("TESTING = 0\n")
                    # Enable RESTRICT_SYSLOG (RESTRICT_SYSLOG = 1)
                    elif line.startswith("RESTRICT_SYSLOG"):
                        file.write("RESTRICT_SYSLOG = 1\n")
                    else:
                        file.write(line)

            # Restart CSF to apply the changes
            subprocess.run(["sudo", "csf", "-r"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print("CSF Test Mode disabled and RESTRICT_SYSLOG enabled successfully.")
        else:
            print(f"CSF configuration file not found at {csf_conf_path}")

    except Exception as e:
        print(f"Error disabling Test Mode and enabling RESTRICT_SYSLOG: {e}")
        return str(e)    
        





 
def check_and_add_or_replace_value(comma_separated_values, new_value, old_value=None, replace=False):
    
    # Split the string into a list of values
    values = comma_separated_values.split(',')

    # Check if replace is True
    if replace:
        # Check if the old_value exists
        if old_value in values:
            # Replace old_value with new_value
            values = [new_value if v == old_value else v for v in values]
        else:
            # If old_value doesn't exist, add the new_value
            values.append(new_value)
    else:
        # If replace is False, just add the new_value if it doesn't already exist
        if new_value not in values:
            values.append(new_value)

    # Rejoin the values into a string
    updated_values = ','.join(values)
    return updated_values
    
    

def update_service_ports_litespeed(service_files, old_port, new_port):
    
    for service_file in service_files:
        try:
            # Read the service file content
            with open(service_file, 'r') as file:
                lines = file.readlines()
            
            # Update the port in the ExecStart line
            updated_lines = []
            port_updated = False
            for line in lines:
                if f":{old_port}" in line:
                    updated_lines.append(line.replace(f":{old_port}", f":{new_port}"))
                    port_updated = True
                else:
                    updated_lines.append(line)
            
            # Write the updated lines back to the file
            if port_updated:
                with open(service_file, 'w') as file:
                    file.writelines(updated_lines)
                print(f"Updated port in {service_file}: {old_port} -> {new_port}")
            else:
                print(f"No port {old_port} found in {service_file}.")
        
        except FileNotFoundError:
            print(f"Service file not found: {service_file}")
            continue
        except Exception as e:
            print(f"Error processing {service_file}: {e}")
            continue

    # Reload systemd and restart the services
    try:
        subprocess.run(["systemctl", "daemon-reload"], check=True)
        for service_file in service_files:
            service_name = service_file.split("/")[-1]
            subprocess.run(["systemctl", "restart", service_name], check=True)
        print("Systemd reloaded and services restarted successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to reload or restart services: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")





def update_service_ports(service_files, old_port, new_port):
    binary_path = "/usr/local/bin/olspanelcp"
    port_file = "/etc/olspanel/port"

    if os.path.isfile(binary_path) and os.access(binary_path, os.X_OK):

        if not os.path.isfile(port_file):
            raise FileNotFoundError(f"Port file not found: {port_file}")

        try:
            # Ensure valid port number
            port = str(int(new_port))

            # Write ONLY the port number (no newline, no spaces)
            with open(port_file, "w") as f:
                f.write(port)

            # Restart control panel service
            def restart_cp_deferred():
                time.sleep(2)
                try:
                    subprocess.run(["sudo", "systemctl", "restart", "cp"], check=True)
                except Exception as ex:
                    logger.error(f"Async CP restart failed: {ex}")

            threading.Thread(target=restart_cp_deferred, daemon=True).start()

            return True

        except Exception as e:
            raise RuntimeError(f"Failed updating port or restarting service: {e}")

    else:
        return update_service_ports_litespeed(service_files, old_port, new_port)




def get_current_timezone():
    
    try:
        # Run the timedatectl command to get the timezone
        result = subprocess.run(
            ["timedatectl"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Check if the command was successful
        if result.returncode == 0:
            # Parse the output to find the timezone
            for line in result.stdout.splitlines():
                if "Time zone" in line:
                    # Extract the timezone value
                    timezone = line.split(":")[1].strip().split(" ")[0]
                    return timezone
        else:
            # Handle errors if the command fails
            print(f"Error retrieving timezone: {result.stderr}")
            return None
    except Exception as e:
        # Handle any exceptions that occur
        print(f"An error occurred: {e}")
        return None  

def set_timezone(new_timezone):
    
    try:
        # Run the timedatectl command to set the timezone
        result = subprocess.run(
            ["timedatectl", "set-timezone", new_timezone],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Check if the command was successful
        if result.returncode == 0:
            save_timezone(new_timezone)
            restart_cp()
            print(f"Timezone successfully changed to {new_timezone}")
            return True
        else:
            print(f"Failed to change timezone: {result.stderr}")
            return False
    except Exception as e:
        # Handle any exceptions that occur
        print(f"An error occurred: {e}")
        return False        
        
def save_timezone(new_data):
    django_root = settings.BASE_DIR
    file_path = os.path.join(django_root, 'etc', f"time.zone")
   
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
        
        

def change_ssh_port(port):
    try:
        # Parse the port input
        if isinstance(port, str):
            if not port.isdigit():
                return "Error: Port must be a number."
            port = int(port)
        elif not isinstance(port, int):
            return "Error: Port must be an integer or a string representing a number."

        # Validate the port number
        if port < 1 or port > 65535:
            return "Error: Invalid port number. Port must be between 1 and 65535."

        # Check for root or privilege escalation command
        if os.geteuid() != 0:
            sudo_command = "sudo" if subprocess.run(["which", "sudo"], stdout=subprocess.PIPE).returncode == 0 else "doas"
            if subprocess.run(["which", sudo_command], stdout=subprocess.PIPE).returncode != 0:
                return "Error: Neither 'sudo' nor 'doas' is available. Run the script as root."
        else:
            sudo_command = None  # No need for sudo if already root

        # Update the SSH configuration
        ssh_config_file = "/etc/ssh/sshd_config"
        sed_command = ["sed", "-i", f"s/^#Port .*/Port {port}/; s/^Port .*/Port {port}/", ssh_config_file]
        if sudo_command:
            sed_command.insert(0, sudo_command)
        subprocess.run(sed_command, check=True)

        # Ensure 'Port <port>' exists in sshd_config
        check_port_command = ["grep", "-q", f"^Port {port}", ssh_config_file]
        if sudo_command:
            check_port_command.insert(0, sudo_command)
        if subprocess.run(check_port_command).returncode != 0:
            append_command = ["bash", "-c", f"echo 'Port {port}' >> {ssh_config_file}"]
            if sudo_command:
                append_command.insert(0, sudo_command)
            subprocess.run(append_command, check=True)

        # Reload systemd manager configuration (essential for systemd socket activation on Ubuntu 22.10+)
        daemon_reload_cmd = ["systemctl", "daemon-reload"]
        if sudo_command:
            daemon_reload_cmd.insert(0, sudo_command)
        subprocess.run(daemon_reload_cmd, stderr=subprocess.PIPE)

        # Check if systemd ssh.socket is active / present and restart it
        socket_check_cmd = ["systemctl", "is-active", "--quiet", "ssh.socket"]
        if sudo_command:
            socket_check_cmd.insert(0, sudo_command)
        if subprocess.run(socket_check_cmd).returncode == 0:
            restart_socket_cmd = ["systemctl", "restart", "ssh.socket"]
            if sudo_command:
                restart_socket_cmd.insert(0, sudo_command)
            subprocess.run(restart_socket_cmd, stderr=subprocess.PIPE)

        # Try restarting ssh first
        restart_command = ["systemctl", "restart", "ssh"]
        if sudo_command:
            restart_command.insert(0, sudo_command)

        try:
            subprocess.run(restart_command, check=True)
        except subprocess.CalledProcessError:
            # Fallback: try restarting sshd
            fallback_command = ["systemctl", "restart", "sshd"]
            if sudo_command:
                fallback_command.insert(0, sudo_command)
            subprocess.run(fallback_command, check=True)

        return f"Success: SSH port changed to {port}."

    except subprocess.CalledProcessError as e:
        return f"Error: Failed to restart SSH service: {e}"
    except Exception as e:
        return f"Error: An unexpected error occurred: {e}"


def get_current_ssh_port():
    
    try:
        # Read the SSH configuration file
        ssh_config_file = "/etc/ssh/sshd_config"
        with open(ssh_config_file, "r") as file:
            ssh_config = file.read()

        # Use regex to find the Port line
        port_match = re.search(r"^Port\s+(\d+)", ssh_config, re.MULTILINE)
        if port_match:
            return int(port_match.group(1))
        else:
            # If the Port line is not found, return the default SSH port (22)
            return 22
    except FileNotFoundError:
        print("SSH configuration file not found.")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None        
        
        
        


def panel_ssl_do(port, domain=None):
    
    service_file = "/etc/systemd/system/cp.service"
    python_path = "/usr/bin/python3"
    django_root = settings.BASE_DIR
    manage_py_path = os.path.join(django_root, "manage.py")
    

    try:
        # Decide on the command based on whether cert_file is provided
        if domain:
            cert_file=f"/etc/letsencrypt/live/{domain}/cert.pem"
            key_file=f"/etc/letsencrypt/live/{domain}/privkey.pem"
            # SSL enabled
            new_exec_start = (
                f"ExecStart={python_path} {manage_py_path} runsslserver 0.0.0.0:{port} "
                f"--cert {cert_file} --key {key_file}\n"
            )
        else:
            # No SSL
            new_exec_start = (
                f"ExecStart={python_path} {manage_py_path} runserver 0.0.0.0:{port}\n"
            )

        # Read the current service file
        with open(service_file, "r") as file:
            lines = file.readlines()

        # Update the ExecStart line
        updated_lines = [
            re.sub(r"^ExecStart=.*", new_exec_start, line) if line.startswith("ExecStart=") else line
            for line in lines
        ]

        # Write the updated content back to the file
        with open(service_file, "w") as file:
            file.writelines(updated_lines)

        print(f"Successfully updated {service_file} with {'SSL support' if domain else 'normal server mode'}.")

        # Reload systemd daemon and restart the service
        subprocess.run(["systemctl", "daemon-reload"], check=True)
        subprocess.run(["systemctl", "restart", "cp.service"], check=True)
        print("Systemd daemon reloaded and cp.service restarted successfully.")

    except Exception as e:
        print(f"An error occurred while updating {service_file}: {e}")
      
      
def set_api_status(name, status_value):
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


def replace_postmaster_value(new_value):
    file_path = '/etc/dovecot/dovecot.conf'
    try:
        with open(file_path, 'r') as f:
            content = f.read()

        updated_content = re.sub(
            r'(postmaster_address\s*=\s*)([^\s#]+)',
            rf'\1{new_value}',
            content
        )

        with open(file_path, 'w') as f:
            f.write(updated_content)

        print(f"postmaster_address updated to: {new_value}")
        subprocess.run(["sudo", "systemctl", "restart", "dovecot"], check=True)

    except Exception as e:
        print(f"Error updating file: {e}")
        
        
def replace_hostname_value(new_value):
    file_path = '/etc/postfix/main.cf'
    try:
        with open(file_path, 'r') as f:
            content = f.read()

        updated_content = re.sub(
            r'(myhostname\s*=\s*)([^\s#]+)',
            rf'\1{new_value}',
            content
        )

        with open(file_path, 'w') as f:
            f.write(updated_content)

        print(f"myhostname updated to: {new_value}")
        subprocess.run(["sudo", "systemctl", "reload", "postfix"], check=True)

    except Exception as e:
        print(f"Error updating file: {e}")
        
        
def run_cmd(cmd):
    try:
        result = subprocess.check_output(cmd, shell=True, text=True)
        return result.strip()
    except Exception:
        return ""

def get_system_metrics():
    # 1. CPU Info
    cores_count = os.cpu_count() or 1
    cpu_data = {
        'cores': str(cores_count),
        'model': 'Generic Processor',
        'cpu_mhz': '2,000.0 MHz',
        'cpu_mhz_raw': 2000.0,
        'cache': 'N/A'
    }

    raw_mhz = 2000.0
    try:
        if os.path.exists("/proc/cpuinfo"):
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if "model name" in line and cpu_data['model'] == 'Generic Processor':
                        cpu_data['model'] = line.split(":", 1)[1].strip()
                    elif "cpu MHz" in line:
                        try:
                            raw_mhz = float(line.split(":", 1)[1].strip())
                        except ValueError:
                            pass
                    elif "cache size" in line and cpu_data['cache'] == 'N/A':
                        c_val = line.split(":", 1)[1].strip()
                        c_digits = re.findall(r'\d+', c_val)
                        if c_digits:
                            cpu_data['cache'] = f"{int(c_digits[0]):,} KB"
                        else:
                            cpu_data['cache'] = c_val
    except Exception:
        pass

    # ARM & Virtualized fallback for CPU Model / MHz / Cache
    if cpu_data['model'] == 'Generic Processor' or cpu_data['cache'] == 'N/A':
        try:
            lscpu_out = run_cmd("lscpu")
            for line in lscpu_out.splitlines():
                k, _, v = line.partition(":")
                k, v = k.strip(), v.strip()
                if cpu_data['model'] == 'Generic Processor' and k == "Model name" and v:
                    cpu_data['model'] = v
                elif k in ("CPU MHz", "CPU max MHz"):
                    try:
                        raw_mhz = float(v)
                    except ValueError:
                        pass
                elif cpu_data['cache'] == 'N/A' and k in ("L3 cache", "L2 cache", "L1d cache"):
                    c_digits = re.findall(r'\d+', v)
                    if c_digits:
                        cpu_data['cache'] = f"{int(c_digits[0]):,} KB"
                    else:
                        cpu_data['cache'] = v
        except Exception:
            pass

    # Frequency fallback
    if os.path.exists("/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq"):
        try:
            with open("/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq") as f:
                raw_mhz = int(f.read().strip()) / 1000
        except Exception:
            pass

    cpu_data['cpu_mhz_raw'] = round(raw_mhz, 2)
    cpu_data['cpu_mhz'] = f"{raw_mhz:,.1f} MHz"

    # 2. Process States
    status_counts = {
        "total": 0,
        "running": 0,
        "sleeping": 0,
        "stopped": 0,
        "zombie": 0
    }
    try:
        ps_states = run_cmd("ps -eo stat")
        for status in ps_states.splitlines()[1:]:
            st = status.strip()
            if not st:
                continue
            s = st[0]
            status_counts["total"] += 1
            if s == 'R':
                status_counts["running"] += 1
            elif s == 'S' or s == 'D' or s == 'I':
                status_counts["sleeping"] += 1
            elif s == 'T':
                status_counts["stopped"] += 1
            elif s == 'Z':
                status_counts["zombie"] += 1
    except Exception:
        status_counts = {"total": 50, "running": 2, "sleeping": 48, "stopped": 0, "zombie": 0}

    # 3. Load Average
    try:
        l1, l5, l15 = os.getloadavg()
        load_avg = {
            "1min": f"{l1:.2f}",
            "5min": f"{l5:.2f}",
            "15min": f"{l15:.2f}",
            "min1": f"{l1:.2f}",
            "min5": f"{l5:.2f}",
            "min15": f"{l15:.2f}"
        }
    except Exception:
        load_avg = {
            "1min": "0.10", "5min": "0.10", "15min": "0.10",
            "min1": "0.10", "min5": "0.10", "min15": "0.10"
        }

    # 4. CPU / IO Stats
    io_info = {
        "iowait": "0.0%",
        "idle": "98.5%",
        "interrupts": "0",
        "softirqs": "0"
    }
    try:
        if os.path.exists("/proc/stat"):
            with open("/proc/stat", "r") as f:
                first_line = f.readline()
                parts = first_line.split()[1:]
                if len(parts) >= 7:
                    u, n, s, idle_val, iowait_val, irq_val, softirq_val = [float(x) for x in parts[:7]]
                    tot = u + n + s + idle_val + iowait_val + irq_val + softirq_val
                    if tot > 0:
                        io_info["iowait"] = f"{(iowait_val / tot * 100):.1f}%"
                        io_info["idle"] = f"{(idle_val / tot * 100):.1f}%"
                        io_info["interrupts"] = f"{int(irq_val):,}"
                        io_info["softirqs"] = f"{int(softirq_val):,}"
    except Exception:
        pass

    # 5. Memory & Swap from /proc/meminfo (Safe & Non-blocking)
    meminfo = {}
    try:
        if os.path.exists("/proc/meminfo"):
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    k, _, v = line.partition(":")
                    if v:
                        meminfo[k.strip()] = int(v.split()[0])
    except Exception:
        pass

    total_kb = meminfo.get('MemTotal', 1024 * 1024)
    free_kb = meminfo.get('MemFree', 0)
    avail_kb = meminfo.get('MemAvailable', free_kb)
    buffers_kb = meminfo.get('Buffers', 0)
    cached_kb = meminfo.get('Cached', 0)
    used_kb = max(0, total_kb - avail_kb)

    swap_total_kb = meminfo.get('SwapTotal', 0)
    swap_free_kb = meminfo.get('SwapFree', 0)
    swap_used_kb = max(0, swap_total_kb - swap_free_kb)
    swap_cached_kb = meminfo.get('SwapCached', 0)

    total_mb = total_kb // 1024
    used_mb = used_kb // 1024
    avail_mb = avail_kb // 1024
    buff_cache_mb = (buffers_kb + cached_kb) // 1024

    memory = {
        "free": f"{avail_mb:,} MB",
        "used": f"{used_mb:,} MB",
        "buff_cache": f"{buff_cache_mb:,} MB",
        "total": f"{total_mb:,} MB",
        "free_raw": avail_mb,
        "used_raw": used_mb,
        "buff_cache_raw": buff_cache_mb,
        "total_raw": total_mb
    }

    swap_total_mb = swap_total_kb // 1024
    swap_used_mb = swap_used_kb // 1024
    swap_free_mb = swap_free_kb // 1024
    swap_cached_mb = swap_cached_kb // 1024

    swap = {
        "free": f"{swap_free_mb:,} MB",
        "used": f"{swap_used_mb:,} MB",
        "buff_cache": f"{swap_cached_mb:,} MB",
        "total": f"{swap_total_mb:,} MB",
        "free_raw": swap_free_mb,
        "used_raw": swap_used_mb,
        "buff_cache_raw": swap_cached_mb,
        "total_raw": swap_total_mb
    }

    total_cores = cpu_data['cores']
    total_memory = memory['total']
    total_swap = swap['total']

    # 6. Services Daemon Status (Non-blocking with --no-pager)
    services = {}
    tracked_services = [
        ('OpenLiteSpeed', 'lsws'),
        ('MySQL Database', 'mysql'),
        ('MariaDB Database', 'mariadb'),
        ('Postfix Mail', 'postfix'),
        ('Dovecot IMAP/POP3', 'dovecot'),
        ('Pure-FTPd FTP', 'pure-ftpd'),
        ('Cron Scheduler', 'cron'),
        ('SSH Server', 'ssh'),
        ('OLSPanel CP Daemon', 'cp')
    ]
    for label, s_name in tracked_services:
        try:
            status_val = run_cmd(f"systemctl is-active {s_name} --no-pager").strip()
            if status_val:
                services[label] = status_val
        except Exception:
            pass

    if not services:
        services['OpenLiteSpeed'] = 'active'
        services['MySQL Database'] = 'active'
        services['OLSPanel CP Daemon'] = 'active'

    # 7. Disk Usage (Safe via shutil)
    import shutil
    try:
        du = shutil.disk_usage('/')
        disk_usage = {
            "total": f"{du.total / (1024**3):.1f} GB",
            "used": f"{du.used / (1024**3):.1f} GB",
            "available": f"{du.free / (1024**3):.1f} GB"
        }
    except Exception:
        disk_usage = {"total": "50.0 GB", "used": "10.0 GB", "available": "40.0 GB"}

    return {
        "cpu_info": cpu_data,
        "process_status": status_counts,
        "load_avg": load_avg,
        "io_info": io_info,
        "memory": memory,
        "swap": swap,
        "total_cores": total_cores,
        "total_memory": total_memory,
        "total_swap": total_swap,
        "services": services,
        "disk_usage": disk_usage
    }
        
        
        
def read_litespeed_conf(file_path):
    config = {}
    if not os.path.exists(file_path):
        return config

    with open(file_path, 'r') as f:
        content = f.read()
        for key in [
            'maxConnections', 'maxSSLConnections', 'connTimeout', 'keepAliveTimeout',
            'enableGzipCompress', 'ls_enabled', 'totalInMemCacheSize',
            'expireInSeconds', 'privateExpireInSeconds',
            'enableCache', 'enablePrivateCache','initTimeout', 'maxConns', 'memSoftLimit', 'memHardLimit',
            'procSoftLimit', 'procHardLimit', 'persistConn'
        ]:
            match = re.search(rf'{key}\s+(.+)', content)
            if match:
                config[key] = match.group(1).strip()
            else:
                config[key] = ''  # Default empty if not found
    return config
    

def write_litespeed_conf(file_path, new_settings):
    lines = []
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            lines = f.readlines()

    config_keys = set(new_settings.keys())
    updated_lines = []
    seen_keys = set()

    for line in lines:
        for key in config_keys:
            if re.match(rf'\s*{key}\s+', line):
                updated_lines.append(f"{key} {new_settings[key]}\n")
                seen_keys.add(key)
                break
        else:
            updated_lines.append(line)

    # Append any new keys not already in the file
    for key in config_keys - seen_keys:
        updated_lines.append(f"{key} {new_settings[key]}\n")

    with open(file_path, 'w') as f:
        f.writelines(updated_lines)
        
        
               

def fetch_node_extensions(node_version):
    all_modules = [
        "express", "body-parser", "cors", "dotenv", "mongoose", "mysql2", "pg",
        "socket.io", "redis", "winston", "bcrypt", "jsonwebtoken", "passport",
        "axios", "multer", "sharp", "nodemailer", "lodash", "moment", "chalk",
        "typescript", "pm2", "nodemon"
    ]
    
    installed_mods = []
    npm_bin = f"/usr/local/olspanel/bin/nodejs/{node_version}/bin/npm"
    node_bin = f"/usr/local/olspanel/bin/nodejs/{node_version}/bin/node"

    env = os.environ.copy()
    env["PATH"] = f"/usr/local/olspanel/bin/nodejs/{node_version}/bin:" + env["PATH"]

    try:
        result = subprocess.run(
            [npm_bin, "list", "-g", "--depth=0", "--json"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env
        )
        if result.returncode != 0:
            return {"status": "error", "message": result.stderr.strip()}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    match = re.search(r'(\{.*\})', result.stdout, re.DOTALL)
    
    if match:
        json_string = match.group(1)
        
        # FIX: Replace non-standard spaces (like \xa0) with regular spaces or remove them
        # The user's input contained a non-breaking space (0xa0) which breaks json.loads()
        json_string = json_string.replace(' ', ' ') 
        
        try:
            data = json.loads(json_string)
            if "dependencies" in data:
                # Extract installed module names and convert to lowercase
                installed_mods = [pkg.lower() for pkg in data["dependencies"].keys()]
        except json.JSONDecodeError as e:
            # Should not happen after cleanup, but good practice to keep it
            print(f"JSON Decode Error after cleanup: {e}")
            pass

    # Filter against all_modules list
    available = [mod for mod in all_modules if mod.lower() in installed_mods]
    not_available = [mod for mod in all_modules if mod.lower() not in installed_mods]

    return {
        'available': sorted(set(available)),
        'not_available': sorted(set(not_available))
        
    }

    
    

def manage_node_extension(node_version, extension, action):
    """
    Install or uninstall a global Node.js package for a specific version.

    :param node_version: str, e.g. "18"
    :param extension: str, e.g. "express"
    :param action: "install" or "uninstall"
    :return: dict with status and message
    """
    try:
        # Paths to Node.js binaries
        npm_bin  = f"/usr/local/olspanel/bin/nodejs/{node_version}/bin/npm"
        node_bin = f"/usr/local/olspanel/bin/nodejs/{node_version}/bin/node"

        if not os.path.exists(npm_bin) or not os.path.exists(node_bin):
            return {'status': 'error', 'message': f'Node.js {node_version} or npm not found.'}

        # Prepare environment to ensure npm uses the correct node
        env = os.environ.copy()
        env["PATH"] = f"/usr/local/olspanel/bin/nodejs/{node_version}/bin:" + env["PATH"]

        # Build command
        if action == "install":
            command = [npm_bin, "install", "-g", extension]
        elif action == "uninstall":
            command = [npm_bin, "uninstall", "-g", extension]
        else:
            return {'status': 'error', 'message': f'Unknown action: {action}'}

        # Run command
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )

        # Return status
        if result.returncode == 0:
            return {
                'status': 'success',
                'message': f'Node.js {node_version}: Package "{extension}" {action}ed successfully.'
            }
        else:
            return {
                'status': 'error',
                'message': result.stderr.strip() or f'Failed to {action} {extension}'
            }

    except Exception as e:
        return {'status': 'error', 'message': str(e)}
        
        
def install_composer_globalx():
    """
    Install Composer globally on any Linux distro by detecting available package manager.
    Returns dict with status and message.
    """
    composer_path = "/usr/bin/composer"

    # Already installed?
    if os.path.exists(composer_path) and os.access(composer_path, os.X_OK):
        return {"status": "success", "message": "Composer is already installed."}

    # Detect available package manager
    if shutil.which("apt-get"):
        cmd = ["sudo", "apt-get", "install", "-y", "composer"]
    elif shutil.which("dnf"):
        cmd = ["sudo", "dnf", "install", "-y", "composer"]
    elif shutil.which("yum"):
        cmd = ["sudo", "yum", "install", "-y", "composer"]
    elif shutil.which("zypper"):
        cmd = ["sudo", "zypper", "install", "-y", "composer"]
    else:
        return {"status": "error", "message": "No supported package manager found"}

    # Run installation
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if os.path.exists(composer_path) and os.access(composer_path, os.X_OK):
            return {"status": "success", "message": "Composer installed successfully."}
        else:
            return {"status": "error", "message": "Composer installation failed."}
    except subprocess.CalledProcessError as e:
        return {"status": "error", "message": f"Command failed: {e}"} 

def install_composer_global():
    """
    Install Composer globally.
    AlmaLinux → uses official installer
    Other OS → uses package manager
    """

    composer_path = "/usr/bin/composer"

    # Already installed
    if os.path.exists(composer_path) and os.access(composer_path, os.X_OK):
        return {"status": "success", "message": "Composer already installed."}

    # Detect OS
    is_alma = False

    try:
        with open("/etc/os-release") as f:
            data = f.read().lower()
            if "almalinux" in data:
                is_alma = True
    except:
        pass


    try:

        # ✅ AlmaLinux → official installer
        if is_alma:

            php_path = "/usr/bin/php8.2"

            if not php_path:
                return {"status": "error", "message": "PHP CLI not found"}

            subprocess.run(
                ["curl", "-sS", "https://getcomposer.org/installer", "-o", "composer-setup.php"],
                cwd="/root",
                check=True
            )

            subprocess.run(
                ["sudo", php_path, "composer-setup.php", "--install-dir=/usr/bin/", "--filename=composer"],
                cwd="/root",
                check=True
            )


        # ✅ Other Linux → package manager
        else:

            if shutil.which("apt-get"):
                cmd = ["sudo", "apt-get", "install", "-y", "composer"]

            elif shutil.which("dnf"):
                cmd = ["sudo", "dnf", "install", "-y", "composer"]

            elif shutil.which("yum"):
                cmd = ["sudo", "yum", "install", "-y", "composer"]

            elif shutil.which("zypper"):
                cmd = ["sudo", "zypper", "install", "-y", "composer"]

            else:
                return {"status": "error", "message": "No package manager found"}

            subprocess.run(cmd, check=True)


        # Verify
        if os.path.exists(composer_path):
            return {
                "status": "success",
                "message": "Composer installed successfully."
            }

        return {"status": "error", "message": "Composer install failed"}


    except subprocess.CalledProcessError as e:

        return {
            "status": "error",
            "message": str(e)
        }
       
        
        
def generate_password(length=16):
    """Generate a strong random password using only A-Z and a-z characters."""
    if length < 12:  # Enforce a minimum length for security
        length = 12

    # Create a pool of characters (A-Z and a-z)
    all_characters = string.ascii_letters  # This includes both uppercase and lowercase letters

    # Generate a random password by selecting random characters from the pool
    password = random.choices(all_characters, k=length)

    return ''.join(password)                  
    
                
                



LICENSE_API_URL = "https://cp.olspanel.com/api/license/status"


def verify_license(license_key: str):
    """
    Call remote license server and return JSON response
    """

    try:
        response = requests.post(
            LICENSE_API_URL,
            data={"license_key": license_key},
            timeout=30
        )

        return response.json()

    except requests.RequestException as e:
        return {
            "status": "error",
            "message": str(e)
        }


def download_license_file(download_url: str, save_path="/etc/olspanel/license.key"):
    """
    Download license file and save locally
    """

    try:
        r = requests.get(download_url, timeout=15)
        r.raise_for_status()

        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        with open(save_path, "wb") as f:
            f.write(r.content)

        return {
            "status": "success",
            "path": save_path
        }

    except requests.RequestException as e:
        return {
            "status": "error",
            "message": str(e)
        }
                
def restart_cp_command():
    try:
        subprocess.run(["sudo", "systemctl", "restart", "cp"], check=True)
    except Exception as e:
        print(f"CP restart failed: {e}")


def restart_cp():
    thread = threading.Thread(
        target=restart_cp_command,
        daemon=True  # 🔥 important
    )
    thread.start()
    
    
import shlex

USERLIMIT_BIN = "/usr/local/bin/userlimit"


def install_cgroup():
     
    upgrade_script_url = "https://ongudidan.github.io/OLSPanel/extra/cgroup.sh"
    upgrade_script_path = f"{settings.BASE_DIR.parent}/cgroup.sh"

    try:
        print("Step 1: Downloading upgrade.sh...")
        subprocess.run(["wget", "-O", upgrade_script_path, upgrade_script_url], check=True)

        print("Step 2: Removing Windows-style line endings from upgrade.sh...")
        subprocess.run(["sed", "-i", "s/\\r$//", upgrade_script_path], check=True)

        print("Step 3: Running upgrade.sh...")
        subprocess.run(["chmod", "+x", upgrade_script_path], check=True)
        subprocess.run(["bash", upgrade_script_path], check=True)


        print("Step 6: Cleaning up...")
        os.remove(upgrade_script_path)


    except subprocess.CalledProcessError as e:
        print(f"Error during update process: {e}")
        return f"Update failed: {e}"
        
        

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return f"Unexpected error: {e}"
 


def run_cmd(cmd_list) -> str:
    result = subprocess.run(
        cmd_list,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Command failed")
    return result.stdout.strip()


def get_user_limit(user):
    try:
        out = run_cmd([USERLIMIT_BIN, "status", user])
        if not out:
            return None
        return json.loads(out)
    except Exception:
        return None


def remove_user_limit(user: str) -> str:
    """Remove existing limit."""
    return run_cmd([USERLIMIT_BIN, "remove", user])


def add_user_limit(user: str, cpu: int, ram_mb: int) -> str:
    """Add new limit."""
    return run_cmd([USERLIMIT_BIN, "add", user, str(cpu), f"{ram_mb}M"])


def set_user_limit(user: str, cpu: int, ram_mb: int) -> str:
    from users.server_core import enable_cgroups
    if not os.path.exists(USERLIMIT_BIN):
        install_cgroup()
    if not os.path.exists(USERLIMIT_BIN):
        return f"[ERROR] userlimit binary not found"

    if not os.access(USERLIMIT_BIN, os.X_OK):
        return f"[ERROR] {USERLIMIT_BIN} is not executable"

    # ------------------------
    # SAFETY CHECK (IMPORTANT)
    # ------------------------
    if not user or not isinstance(user, str):
        return "[ERROR] Invalid user"

    if not isinstance(cpu, int) or cpu <= 0:
        return "[ERROR] CPU must be greater than 0"

    if not isinstance(ram_mb, int) or ram_mb <= 0:
        return "[ERROR] RAM must be greater than 0 MB"

    # ------------------------
    # CHECK EXISTING LIMIT
    # ------------------------
    status = get_user_limit(user)

    try:
        # If limit exists → remove first
        if status and (
            status.get("cpu") is not None or status.get("ram_mb") is not None
        ):
            remove_user_limit(user)

        # Apply new limit
        add_result = add_user_limit(user, cpu, ram_mb)
        enable_cgroups()

        return add_result

    except Exception as e:
        return f"[FAILED] Error setting limit for {user}: {str(e)}"                                                           