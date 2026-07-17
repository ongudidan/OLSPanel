# yourapp/utils.py
import os
import subprocess
import re
import shutil
import stat
import pwd
import grp
import socket
import time
from datetime import datetime
from django.contrib import messages

from django.db import connection
from .models import * 
from .function import * 
from users.panellogger import *

from django.conf import settings
# Path to the OpenLiteSpeed configuration file for listeners
LISTENER_CONFIG_FILE = "/usr/local/lsws/conf/httpd_config.conf"
logger = CpLogger()


def manage_listener_mapping(action, domain):
    """Manage domain mappings in the OpenLiteSpeed listener configuration."""
    try:
        with open(LISTENER_CONFIG_FILE, 'r') as file:
            lines = file.readlines()

        new_lines = []
        in_listener_block = False
        mapping_found = False

        for line in lines:
            if 'listener Default {' in line:
                in_listener_block = True

            # Adjust the map line format to remove extra spaces
            if in_listener_block:
                if action == "remove" and f"  map                     {domain} " in line:
                    mapping_found = True
                    continue

                if action == "add" and f"  map                     {domain} " in line:
                    mapping_found = True
                    

            new_lines.append(line)

            if '}' in line and in_listener_block:
                # Add the map if it's not found for 'add' action
                if action == "add" and not mapping_found:
                    new_lines.insert(-1, f"  map                     {domain} {domain}\n")
                in_listener_block = False

        # Write the modified lines back to the configuration file
        with open(LISTENER_CONFIG_FILE, 'w') as file:
            file.writelines(new_lines)

        # Fixing the syntax issue in the print statement
        print(f"Mapping for '{domain}' {'added' if action == 'add' else 'removed'} successfully.")
        return True

    except Exception as e:
        print(f"Error managing listener mapping: {e}")
        return False



def manage_ssl_listener_mapping(action, domain):
    """Manage domain mappings in the OpenLiteSpeed listener configuration."""
    try:
        with open(LISTENER_CONFIG_FILE, 'r') as file:
            lines = file.readlines()

        new_lines = []
        in_listener_block = False
        mapping_found = False

        for line in lines:
            if 'listener SSL {' in line:
                in_listener_block = True

            # Adjust the map line format to remove extra spaces
            if in_listener_block:
                if action == "remove" and f"  map                     {domain} " in line:
                    mapping_found = True
                    continue

                if action == "add" and f"  map                     {domain} " in line:
                    mapping_found = True
                    

            new_lines.append(line)

            if '}' in line and in_listener_block:
                # Add the map if it's not found for 'add' action
                if action == "add" and not mapping_found:
                    new_lines.insert(-1, f"  map                     {domain} {domain}\n")
                in_listener_block = False

        # Write the modified lines back to the configuration file
        with open(LISTENER_CONFIG_FILE, 'w') as file:
            file.writelines(new_lines)
            
            
        add_ipv6_ssl_listener()
        print(f"Mapping for '{domain}' {'added' if action == 'add' else 'removed'} successfully.")
        return True

    except Exception as e:
        print(f"Error managing SSL listener mapping: {e}")
        return False


    except Exception as e:
        print(f"Error managing listener mapping: {e}")
        return False


def add_ipv6_ssl_listener():
    # Read current config
    with open(LISTENER_CONFIG_FILE, "r") as f:
        config_text = f.read()

    # Remove any existing SSL IPv6 block
    config_text = re.sub(r"\n*listener\s+SSL\s+IPv6\s*{[^}]+}", "", config_text, flags=re.DOTALL)

    # Find the original SSL listener block
    pattern_ssl = r"(listener\s+SSL\s*{[^}]+})"
    match_ssl = re.search(pattern_ssl, config_text, re.DOTALL)
    if not match_ssl:
        raise ValueError("No SSL listener block found")

    old_block = match_ssl.group(1)

    # Create new SSL IPv6 block
    new_block = old_block.replace("listener SSL", "listener SSL IPv6", 1)
    new_block = new_block.replace("address                 *:", "address                 [ANY]:")

    # Insert new block immediately after old block, only once
    new_config = config_text.replace(old_block, old_block.rstrip() + "\n" + new_block.lstrip())

    # Write back updated config
    with open(LISTENER_CONFIG_FILE, "w") as f:
        f.write(new_config)
    add_ipv6_panel_listener()
    print("listener SSL IPv6 successfully overwritten in httpd_config.conf")


def add_ipv6_panel_listener():
    binary_path = "/usr/local/bin/olspanelcp"

    # 🚫 If OLS Panel binary exists → skip everything
    if os.path.isfile(binary_path) and os.access(binary_path, os.X_OK):
        print("OLS Panel binary found — skipping IPv6 listener setup.")
        return
        
        
        
    with open(LISTENER_CONFIG_FILE, "r") as f:
        config_text = f.read()

    # Remove any existing panel IPv6 block
    config_text = re.sub(r"\n*listener\s+panel\s+IPv6\s*{[^}]+}", "", config_text, flags=re.DOTALL)

    # Find the original panel listener block
    pattern_ssl = r"(listener\s+panel\s*{[^}]+})"
    match_ssl = re.search(pattern_ssl, config_text, re.DOTALL)
    if not match_ssl:
        raise ValueError("No panel listener block found")

    old_block = match_ssl.group(1)

    # Create new panel IPv6 block
    new_block = old_block.replace("listener panel", "listener panel IPv6", 1)
    new_block = new_block.replace("address                 *:", "address                 [ANY]:")

    # Insert new block immediately after old block, only once
    new_config = config_text.replace(old_block, old_block.rstrip() + "\n" + new_block.lstrip())

    # Write back updated config
    with open(LISTENER_CONFIG_FILE, "w") as f:
        f.write(new_config)

    print("listener panel IPv6 successfully overwritten in httpd_config.conf")


def preview_mapping(action, domain):
    """Manage domain mappings in the OpenLiteSpeed listener configuration."""
    try:
        with open(LISTENER_CONFIG_FILE, 'r') as file:
            lines = file.readlines()

        new_lines = []
        in_listener_block = False
        mapping_found = False

        for line in lines:
            if 'listener Default {' in line:
                in_listener_block = True

            # Adjust the map line format to remove extra spaces
            if in_listener_block:
                
                if action == "add" and f"  map                     {domain} " in line:
                    mapping_found = True
                   

            new_lines.append(line)

            if '}' in line and in_listener_block:
                # Add the map if it's not found for 'add' action
                if action == "add" and not mapping_found:
                    new_lines.insert(-1, f"  map                     {domain} *\n")
                in_listener_block = False

        # Write the modified lines back to the configuration file
        with open(LISTENER_CONFIG_FILE, 'w') as file:
            file.writelines(new_lines)

        # Fixing the syntax issue in the print statement
        print(f"Mapping for '{domain}' {'added' if action == 'add' else 'removed'} successfully.")
        return True

    except Exception as e:
        print(f"Error managing listener mapping: {e}")
        return False



def ssl_preview_mapping(action, domain):
    """Manage domain mappings in the OpenLiteSpeed listener configuration."""
    try:
        with open(LISTENER_CONFIG_FILE, 'r') as file:
            lines = file.readlines()

        new_lines = []
        in_listener_block = False
        mapping_found = False

        for line in lines:
            if 'listener SSL {' in line:
                in_listener_block = True

            # Adjust the map line format to remove extra spaces
            if in_listener_block:
                
                if action == "add" and f"  map                     {domain} " in line:
                    mapping_found = True
                    

            new_lines.append(line)

            if '}' in line and in_listener_block:
                # Add the map if it's not found for 'add' action
                if action == "add" and not mapping_found:
                    new_lines.insert(-1, f"  map                     {domain} *\n")
                in_listener_block = False

        # Write the modified lines back to the configuration file
        with open(LISTENER_CONFIG_FILE, 'w') as file:
            file.writelines(new_lines)

        # Fixing the syntax issue in the print statement
        print(f"Mapping for '{domain}' {'added' if action == 'add' else 'removed'} successfully.")
        return True

    except Exception as e:
        print(f"Error managing listener mapping: {e}")
        return False


def manage_preview_virtual_host():
   
    config_file_path = "/usr/local/lsws/conf/httpd_config.conf"
    domain_name = "preview"
    vhost_directory = f"/usr/local/lsws/conf/vhosts/{domain_name}"
    vhost_file_path = os.path.join(vhost_directory, "vhconf.conf")
    if not os.path.isfile(vhost_file_path):
        create_preview_vhost_file()
    
    
    vhost_config = f"""
virtualhost preview {{
  vhRoot                  Example/
  configFile              conf/vhosts/preview/vhconf.conf
  allowSymbolLink         1
  enableScript            1
  restrained              0
}}
"""

    # Read the existing configuration to check for the virtual host
    try:
        with open(config_file_path, "r") as config_file:
            config_content = config_file.read()

            # Check if the virtual host block exists by looking for 'virtualhost <domain_name>'
            if f"virtualhost {domain_name} " in config_content:
                print(f"Virtual host for '{domain_name}' already exists.")  # Debug message
                return True  # Indicate that the virtual host already exists

    except FileNotFoundError:
        print("Configuration file does not exist.")  # Debug message
        return False  # Indicate failure
    except Exception as e:
        print(f"Error reading config file: {str(e)}")  # Debug message
        return False  # Indicate failure

    # If not found, append the new virtual host configuration
    try:
        with open(config_file_path, "a") as config_file:
            config_file.write(vhost_config.strip() + "\n")  # Ensure a new line at the end
            print(f"Added virtual host for '{domain_name}'.")  # Debug message
            return True  # Indicate success
    except Exception as e:
        print(f"Error writing to config file: {str(e)}")  # Debug message
        return False  # Indicate failure



def create_preview_vhost_file():
    """Create a vhost directory and configuration file for the specified domain."""
    domain_name = "preview"
    vhost_directory = f"/usr/local/lsws/conf/vhosts/{domain_name}"
    vhost_file_path = os.path.join(vhost_directory, "vhconf.conf")
    
    if not os.path.exists(vhost_directory):
        try:
            os.makedirs(vhost_directory)
            print(f"Created directory: {vhost_directory}")
        except Exception as e:
            print(f"Failed to create directory: {str(e)}")
            return False

    # Check if the vhost.conf file exists
    if not os.path.isfile(vhost_file_path):
        try:
            # Create the vhost.conf file with the specified content
            vhost_content = """docRoot                   $VH_ROOT/html/default
enableGzip                1

index  {
  useServer               0
  indexFiles              index.html
  autoIndex               0
  autoIndexURI            /_autoindex/default.php
}

errorpage 404 {
  url                     /error404.html
}

expires  {
  enableExpires           1
}

accessControl  {
  allow                   *
}

context / {
  location                $DOC_ROOT/
  allowBrowse             1

  rewrite  {
    RewriteFile .htaccess
  }
}

rewrite  {
  enable                  0
  logLevel                0
}

scripthandler  {
  add                     lsapi:lsphp lsphp
}

"""
            with open(vhost_file_path, "w") as vhost_file:
                vhost_file.write(vhost_content)

            print(f"Created vhost file: {vhost_file_path}")
            return True
        except Exception as e:
            print(f"Failed to create vhost file: {str(e)}")
            return False
    else:
        print(f"Vhost file '{vhost_file_path}' already exists.")
        return False


def update_context_block(context_name, path):
    vhost_directory = "/usr/local/lsws/conf/vhosts/preview"
    conf_path = os.path.join(vhost_directory, "vhconf.conf")
    name, block = get_single_extprocessor_block(context_name)
    php_preview_mapping(name)
    context_header = f"context /~{context_name} {{"
    context_footer = "}"
    name_header = f"extprocessor {name} {{"

    new_block = f"""{context_header}
  location                {path}
  allowBrowse             1
  indexFiles              index.php, index.html
  
  accessControl  {{
    allow                 *
  }}

  rewrite  {{
  enable                  1
  autoLoadHtaccess        1
  RewriteRule ^.*\.php$ - [H=application/x-httpd-{name}]
  }}

  addDefaultCharset       off

  phpIniOverride  {{
    php_admin_value open_basedir "/tmp:{path}"
  }}
{context_footer}
"""

    try:
        # Read current file if exists
        if os.path.exists(conf_path):
            with open(conf_path, "r") as f:
                lines = f.readlines()
        else:
            lines = []

        # Remove old context block
        inside_block = False
        new_lines = []
        for line in lines:
            if line.strip().startswith(context_header):
                inside_block = True
                continue
            if inside_block and line.strip() == context_footer:
                inside_block = False
                continue
            if not inside_block:
                new_lines.append(line)

        # Remove old extprocessor block
        lines = new_lines
        inside_block = False
        final_lines = []
        for line in lines:
            if line.strip().startswith(name_header):
                inside_block = True
                continue
            if inside_block and line.strip() == context_footer:
                inside_block = False
                continue
            if not inside_block:
                final_lines.append(line)

        # Combine everything
        updated_content = "".join(final_lines).rstrip() + "\n\n" + new_block + "\n\n" + block

        # Write back to file
        with open(conf_path, "w") as f:
            f.write(updated_content)
           

        print(f"Updated context and extprocessor for /{context_name} in {conf_path}")
        return True

    except Exception as e:
        print(f"Error updating context: {str(e)}")
        return False


def get_single_extprocessor_block(domain_name):
    vhost_directory = f"/usr/local/lsws/conf/vhosts/{domain_name}" 
    vhost_file_path = os.path.join(vhost_directory, "vhost.conf")
    if not os.path.isfile(vhost_file_path):
        print(f"File not found: {vhost_file_path}")
        return None, None

    with open(vhost_file_path, "r") as f:
        content = f.read()

    match = re.search(r"extprocessor\s+(\S+)\s*\{.*?\n\}", content, re.DOTALL)
    if match:
        name = match.group(1)
        block = match.group(0).strip()
        return name, block

    return None, None



def php_preview_mapping(name):
    vhost_directory = "/usr/local/lsws/conf/vhosts/preview"
    conf_path = os.path.join(vhost_directory, "vhconf.conf")
    action = "add"

    try:
        with open(conf_path, 'r') as file:
            lines = file.readlines()

        new_lines = []
        in_listener_block = False
        mapping_found = False

        for line in lines:
            if 'scripthandler  {' in line:
                in_listener_block = True

            # Adjust the map line format to remove extra spaces
            if in_listener_block:
                
                if action == "add" and f"  add                     lsapi:{name} {name}" in line:
                    mapping_found = True
                    

            new_lines.append(line)

            if '}' in line and in_listener_block:
                # Add the map if it's not found for 'add' action
                if action == "add" and not mapping_found:
                    new_lines.insert(-1, f"  add                     lsapi:{name} {name}\n")
                in_listener_block = False

        # Write the modified lines back to the configuration file
        with open(conf_path, 'w') as file:
            file.writelines(new_lines)

        
        return True

    except Exception as e:
        print(f"Error updating scripthandler mapping: {e}")
        return False

        
def panel_listener_mapping(action, domain):
    binary_path = "/usr/local/bin/olspanelcp"

    # 🚫 If OLS Panel binary exists → skip everything
    if os.path.isfile(binary_path) and os.access(binary_path, os.X_OK):
        print("OLS Panel binary found — skipping IPv6 listener setup.")
        return
    try:
        with open(LISTENER_CONFIG_FILE, 'r') as file:
            lines = file.readlines()

        new_lines = []
        in_listener_block = False
        mapping_found = False

        for line in lines:
            if 'listener panel {' in line:
                in_listener_block = True

            # Adjust the map line format to remove extra spaces
            if in_listener_block:
                if action == "remove" and f"  map                     panel_{domain} " in line:
                    mapping_found = True
                    continue

                if action == "add" and f"  map                     panel_{domain} " in line:
                    mapping_found = True
                    

            new_lines.append(line)

            if '}' in line and in_listener_block:
                # Add the map if it's not found for 'add' action
                if action == "add" and not mapping_found:
                    new_lines.insert(-1, f"  map                     panel_{domain} {domain}\n")
                in_listener_block = False

        # Write the modified lines back to the configuration file
        with open(LISTENER_CONFIG_FILE, 'w') as file:
            file.writelines(new_lines)

        print(f"Mapping for '{domain}' {'added' if action == 'add' else 'removed'} successfully.")
        return True

    except Exception as e:
        print(f"Error managing SSL listener mapping: {e}")
        return False


    except Exception as e:
        print(f"Error managing listener mapping: {e}")
        return False



def panel_virtual_host(domain_name):
    binary_path = "/usr/local/bin/olspanelcp"

    # 🚫 If OLS Panel binary exists → skip everything
    if os.path.isfile(binary_path) and os.access(binary_path, os.X_OK):
        print("OLS Panel binary found — skipping IPv6 listener setup.")
        return
    
    
    """Check if the virtual host exists, and add it if not."""
    config_file_path = "/usr/local/lsws/conf/httpd_config.conf"
    
    # Define the virtual host configuration block
    vhost_config = f"""
virtualhost panel_{domain_name} {{
  vhRoot                  Example/
  configFile              $SERVER_ROOT/conf/vhosts/$VH_NAME/vhost.conf
  allowSymbolLink         1
  enableScript            1
  restrained              0
  setUIDMode              0
}}
"""

    # Read the existing configuration to check for the virtual host
    try:
        with open(config_file_path, "r") as config_file:
            config_content = config_file.read()

            # Check if the virtual host block exists by looking for 'virtualhost <domain_name>'
            if f"virtualhost panel_{domain_name} " in config_content:
                print(f"Virtual host for '{domain_name}' already exists.")  # Debug message
                return True  # Indicate that the virtual host already exists

    except FileNotFoundError:
        print("Configuration file does not exist.")  # Debug message
        return False  # Indicate failure
    except Exception as e:
        print(f"Error reading config file: {str(e)}")  # Debug message
        return False  # Indicate failure

    # If not found, append the new virtual host configuration
    try:
        with open(config_file_path, "a") as config_file:
            config_file.write(vhost_config.strip() + "\n")  # Ensure a new line at the end
            print(f"Added virtual host for '{domain_name}'.")  # Debug message
            return True  # Indicate success
    except Exception as e:
        print(f"Error writing to config file: {str(e)}")  # Debug message
        return False  # Indicate failure
        

def create_panel_vhost_file(domain_name):
    binary_path = "/usr/local/bin/olspanelcp"

    # 🚫 If OLS Panel binary exists → skip everything
    if os.path.isfile(binary_path) and os.access(binary_path, os.X_OK):
        print("OLS Panel binary found — skipping IPv6 listener setup.")
        return
    # Paths
    template_path = "/usr/local/lsws/conf/vhosts/mypanel/vhconf.conf"
    vhost_directory = f"/usr/local/lsws/conf/vhosts/panel_{domain_name}"
    vhost_file_path = os.path.join(vhost_directory, "vhost.conf")
    
    

    # Create vhost directory if not exists
    if not os.path.exists(vhost_directory):
        try:
            os.makedirs(vhost_directory)
            print(f"Created directory: {vhost_directory}")
        except Exception as e:
            print(f"Failed to create vhost directory: {str(e)}")
            return False

    # Read template and replace cert lines
    try:
        with open(template_path, 'r') as template_file:
            content = template_file.readlines()

        new_content = []
        for line in content:
            if "keyFile" in line:
                new_content.append(f"  keyFile                 /etc/letsencrypt/live/{domain_name}/privkey.pem\n")
            elif "certFile" in line:
                new_content.append(f"  certFile                /etc/letsencrypt/live/{domain_name}/fullchain.pem\n")
            else:
                new_content.append(line)

        with open(vhost_file_path, 'w') as new_file:
            new_file.writelines(new_content)
            print(f"Created vhost config: {vhost_file_path}")

        return True

    except Exception as e:
        print(f"Error copying or modifying vhost file: {str(e)}")
        return False
    
def get_all_panel_domains_and_create_vhosts():
    binary_path = "/usr/local/bin/olspanelcp"

    # 🚫 If OLS Panel binary exists → skip everything
    if os.path.isfile(binary_path) and os.access(binary_path, os.X_OK):
        print("OLS Panel binary found — skipping IPv6 listener setup.")
        return
        
    base_path = "/usr/local/lsws/conf/vhosts"
    try:
        with os.scandir(base_path) as entries:
            for entry in entries:
                if entry.is_dir() and entry.name.startswith("panel_"):
                    domain = entry.name.replace("panel_", "", 1)
                    create_panel_vhost_file(domain)  # Call your function
    except Exception as e:
        print(f"Error: {e}")

def create_self_signed_ssl(domain, base_ssl_dir="/etc/letsencrypt/live"):
    """
    Create a self-signed SSL certificate for a given domain and store it in the specified SSL directory.

    Args:
        domain (str): The domain for which the SSL certificate is generated.
        base_ssl_dir (str): The base directory for storing SSL certificates (default: /etc/letsencrypt/live).

    Returns:
        dict: Paths to the private key and certificate files if successful, None otherwise.
    """
    try:
        # Define the full paths for the private key and certificate
        private_key_path = f"{base_ssl_dir}/{domain}/privkey.pem"
        certificate_path = f"{base_ssl_dir}/{domain}/fullchain.pem"
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(private_key_path), exist_ok=True)
        
        # Generate the private key
        subprocess.run(["openssl", "genrsa", "-out", private_key_path, "2048"], check=True)
        
        # Generate the certificate signing request (CSR)
        subprocess.run([
            "openssl", "req", "-new", "-key", private_key_path, "-out", "/tmp/csr.pem",
            "-subj", f"/CN={domain}/O=My Pannel/C=US"  # Update this subject line as needed
        ], check=True)
        
        # Generate the self-signed certificate (valid for 365 days)
        subprocess.run([
            "openssl", "x509", "-req", "-days", "365", "-in", "/tmp/csr.pem", "-signkey", private_key_path, "-out", certificate_path
        ], check=True)
        
        # Clean up the CSR file
        os.remove("/tmp/csr.pem")
        
        print(f"SSL certificate created successfully for {domain}.")
        print(f"Private Key File: {private_key_path}")
        print(f"Certificate File: {certificate_path}")
        print("Chained Certificate: Yes")
        
        return {
            "private_key": private_key_path,
            "certificate": certificate_path,
            "chained": True
        }
    
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while creating SSL certificate: {e}")
        return None

# Usage example:
# create_self_signed_ssl('ols-example.tk')


def manage_virtual_host(domain_name, username):
    """Check if the virtual host exists, and add it if not."""
    config_file_path = "/usr/local/lsws/conf/httpd_config.conf"
    
    # Define the virtual host configuration block
    vhost_config = f"""
virtualhost {domain_name} {{
  vhRoot                  /home/{username}
  configFile              $SERVER_ROOT/conf/vhosts/$VH_NAME/vhost.conf
  allowSymbolLink         1
  enableScript            1
  restrained              1
  user                    {username}
  group                   {username}
}}
"""

    # Read the existing configuration to check for the virtual host
    try:
        with open(config_file_path, "r") as config_file:
            config_content = config_file.read()

            # Check if the virtual host block exists by looking for 'virtualhost <domain_name>'
            if f"virtualhost {domain_name} " in config_content:
                print(f"Virtual host for '{domain_name}' already exists.")  # Debug message
                return True  # Indicate that the virtual host already exists

    except FileNotFoundError:
        print("Configuration file does not exist.")  # Debug message
        return False  # Indicate failure
    except Exception as e:
        print(f"Error reading config file: {str(e)}")  # Debug message
        return False  # Indicate failure

    # If not found, append the new virtual host configuration
    try:
        with open(config_file_path, "a") as config_file:
            config_file.write(vhost_config.strip() + "\n")  # Ensure a new line at the end
            print(f"Added virtual host for '{domain_name}'.")  # Debug message
            return True  # Indicate success
    except Exception as e:
        print(f"Error writing to config file: {str(e)}")  # Debug message
        return False  # Indicate failure



def create_vhost_file(domain_name, username, document_root="public_html"):
    """Create a vhost directory and configuration file for the specified domain."""
    # Define the path for the virtual host directory and configuration file
    vhost_directory = f"/usr/local/lsws/conf/vhosts/{domain_name}"
    vhost_file_path = os.path.join(vhost_directory, "vhost.conf")
    log_directory = f"/home/{username}/logs"
    
    # Check if the virtual host directory exists
    if not os.path.exists(log_directory):
        try:
            os.makedirs(log_directory)  # Create the directory structure
            print(f"Created directory: {log_directory}")  # Debug message
        except Exception as e:
            print(f"Failed to create directory: {str(e)}")  # Debug message
            return False  # Indicate failure

    # Check if the virtual host directory exists
    if not os.path.exists(vhost_directory):
        try:
            os.makedirs(vhost_directory)  # Create the directory structure
            print(f"Created directory: {vhost_directory}")  # Debug message
        except Exception as e:
            print(f"Failed to create directory: {str(e)}")  # Debug message
            return False  # Indicate failure

    # Check if the vhost.conf file exists
    if not os.path.isfile(vhost_file_path):
        try:
            # Create the vhost.conf file with the specified content
            with open(vhost_file_path, "w") as vhost_file:
                vhost_file.write(f"""docRoot                   /home/{username}/{document_root}/
vhDomain                  $VH_NAME
vhAliases                 www.$VH_NAME
adminEmails               
enableGzip                1
enableIpGeo               1

index  {{
  useServer               0
  indexFiles              index.php, index.html
}}

errorlog $VH_ROOT/logs/{domain_name}.error_log {{
  useServer               0
  logLevel                WARN
  rollingSize             10M
}}

accesslog $VH_ROOT/logs/{domain_name}.access_log {{
  useServer               0
  logFormat               "%h %l %u %t \\"%r\\" %>s %b \\"%{{Referer}}i\\" \\"%{{User-Agent}}i\\""
  logHeaders              5
  rollingSize             10M
  keepDays                10  
  compressArchive         1
}}

phpIniOverride  {{
  php_admin_value open_basedir "/tmp:$VH_ROOT"
}}

module cache {{
 storagePath /home/{username}/lscache/$VH_NAME
}}

scripthandler  {{
  add                     lsapi:lsphp82 php
}}



rewrite  {{
  enable                  1
  autoLoadHtaccess        1
}}

context /.well-known/acme-challenge {{
  location                /home/{username}/{document_root}/.well-known/acme-challenge
  allowBrowse             1
}}

vhssl  {{
  keyFile                 /etc/letsencrypt/live/{domain_name}/privkey.pem
  certFile                /etc/letsencrypt/live/{domain_name}/fullchain.pem
  certChain               1
  sslProtocol             24
  enableECDHE             1
  renegProtection         1
  sslSessionCache         1
  enableSpdy              15
  enableStapling          1
  ocspRespMaxAge          86400
}}
extprocessor lsphp82 {{
  type                    lsapi
  address                 uds://tmp/lshttpd/lsphp82.sock
  maxConns                10
  env                     LSAPI_CHILDREN=10
  initTimeout             60
  retryTimeout            0
  persistConn             1
  pcKeepAliveTimeout      1
  respBuffer              0
  autoStart               1
  path                    /usr/local/lsws/lsphp82/bin/lsphp
  extUser                 {username}
  extGroup                {username}
  memSoftLimit            2047M
  memHardLimit            2047M
  procSoftLimit           400
  procHardLimit           500
}}
""")

            print(f"Created vhost file: {vhost_file_path}")  # Debug message
            
            # Restart OpenLiteSpeed
            try:
                subprocess.run(["sudo", "systemctl", "restart", "openlitespeed"], check=True)
                print("OpenLiteSpeed restarted successfully.")  # Debug message
            except subprocess.CalledProcessError as e:
                print(f"Failed to restart OpenLiteSpeed: {str(e)}")  # Debug message

            return True  # Indicate success
        except Exception as e:
            print(f"Failed to create vhost file: {str(e)}")  # Debug message
            return False  # Indicate failure
    else:
        print(f"Vhost file '{vhost_file_path}' already exists.")  # Debug message
        return False  # Indicate that the file already exists
        

def replace_docroot_in_virtual_conf(conf_file_path, new_docroot_path):
    
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
            if line.strip().startswith('docRoot'):
                # Replace the existing path with the new one
                lines[i] = f"docRoot                   {new_docroot_path}\n"
                break

        # Write the modified content back to the config file
        with open(conf_file_path, 'w') as file:
            file.writelines(lines)

        print(f"docRoot successfully updated to {new_docroot_path} in {conf_file_path}.")
        return True

    except Exception as e:
        print(f"An error occurred: {e}")
        return False

        
def remove_map_from_httpd_config(domain_name):
    LISTENER_CONFIG_FILE = "/usr/local/lsws/conf/httpd_config.conf"
    if not os.path.isfile(LISTENER_CONFIG_FILE):
        print(f"Configuration file {LISTENER_CONFIG_FILE} not found.")
        return False

    try:
        # Read the content of the config file
        with open(LISTENER_CONFIG_FILE, 'r') as file:
            lines = file.readlines()

        # Modify the lines to remove the mapping for the specified domain
        new_lines = []
        for line in lines:
            if not line.strip().startswith('map') or domain_name not in line:
                new_lines.append(line)

        # Write the modified content back to the config file only if changes were made
        if len(new_lines) != len(lines):
            with open(LISTENER_CONFIG_FILE, 'w') as file:
                file.writelines(new_lines)

            print(f"Mapping for domain '{domain_name}' successfully removed from {LISTENER_CONFIG_FILE}.")
            return True  # Return True if mapping was removed

        print(f"No mapping found for domain '{domain_name}' in {LISTENER_CONFIG_FILE}.")
        return False  # Return False if no mapping was found

    except Exception as e:
        print(f"An error occurred: {e}")
        return False
        
def remove_virtual_host_from_httpd_config(domain_name):
    if not os.path.isfile(LISTENER_CONFIG_FILE):
        return f"Configuration file {LISTENER_CONFIG_FILE} not found."

    try:
        with open(LISTENER_CONFIG_FILE, 'r') as file:
            lines = file.readlines()

        # Regular expression to match the start of the virtual host block for the specified domain
        virtual_host_start_pattern = re.compile(
            rf'virtualhost\s+{re.escape(domain_name)}\s*{{',
            re.DOTALL
        )

        new_lines = []
        inside_block = False

        for line in lines:
            # Check if we are entering a virtual host block
            if virtual_host_start_pattern.match(line):
                inside_block = True  # Set the flag to indicate we're inside the block
                continue  # Skip the current line that starts the block

            if inside_block:
                # Check for the closing brace of the virtual host block
                if '}' in line:
                    inside_block = False  # We found the closing brace; exit the block
                    continue  # Skip the line with the closing brace
            
            # If we are not inside a block, keep the line
            if not inside_block:
                new_lines.append(line)

        # Write the modified content back to the config file if a block was removed
        if len(new_lines) < len(lines):
            with open(LISTENER_CONFIG_FILE, 'w') as file:
                file.writelines(new_lines)
                # Restart OpenLiteSpeed
        try:
            subprocess.run(["sudo", "systemctl", "restart", "openlitespeed"], check=True)
            print("OpenLiteSpeed restarted successfully.")  # Debug message
        except subprocess.CalledProcessError as e:
            print(f"Failed to restart OpenLiteSpeed: {str(e)}")  # Debug message
        
            return f"Virtual host for '{domain_name}' and its configuration removed successfully."
        else:
            return f"No matching virtual host found for '{domain_name}'."

    except Exception as e:
        return f"An error occurred: {e}"
        
def remove_domain_folder(domain_name):
    domain_folder = f'/usr/local/lsws/conf/vhosts/{domain_name}'
    
    if os.path.exists(domain_folder):
        try:
            # Remove the domain folder and all its contents
            shutil.rmtree(domain_folder)
            return f"Domain folder '{domain_folder}' and all its contents removed successfully."
        except Exception as e:
            return f"An error occurred while removing the folder: {e}"
    else:
        return f"Domain folder '{domain_folder}' does not exist."    


def add_user_and_set_folder_permissions(username, home_dir, full_path, groupname=None):
    # Use username as groupname if not provided
    if groupname is None:
        groupname = username

    # Step 1: Check if the group exists; create it if not
    try:
        grp.getgrnam(groupname)
        logger.error(f"Group {groupname} already exists.")
    except KeyError:
        # Create the group
        try:
            subprocess.run(['sudo', 'groupadd', groupname], check=True)
            print(f"Group {groupname} added successfully.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Error adding group {groupname}: {e}")
            return False

    # Step 2: Check if the user exists; create it if not
    try:
        pwd.getpwnam(username)
        print(f"User {username} already exists.")
    except KeyError:
        # Add the user and assign it to the group
        try:
            if getattr(settings, "MY_OS_NAME", "linux") == "ubuntu":
                subprocess.run(['sudo', 'adduser', '--disabled-password', '--gecos', '', '--ingroup', groupname, username], check=True)
                
            else:
                subprocess.run(['sudo', 'useradd',  '-g', groupname, '-m', username], check=True)
                
            
            print(f"User {username} added successfully.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Error adding user {username}: {e}")
            return False

    # Step 3: Create the home directory if it does not exist
    try:
        os.makedirs(home_dir, exist_ok=True)  # Create home directory if it does not exist
        print(f"Created home directory: {home_dir}")
    except Exception as e:
        logger.error(f"Error creating home directory {home_dir}: {e}")
        return False

    # Step 4: Set home directory permissions to 711
    try:
        os.chmod(home_dir, stat.S_IRWXU | stat.S_IXGRP | stat.S_IXOTH)  # 711 (rwx--x--x)
        print(f"Permissions for {home_dir} set to 711.")
    except Exception as e:
        logger.error(f"Error setting permissions for {home_dir}: {e}")
        return False

    # Step 5: Create the document root directory if it does not exist
    try:
        os.makedirs(full_path, exist_ok=True)  # Create the directory and any necessary parent directories
        print(f"Created directory: {full_path}")
    except Exception as e:
        logger.error(f"Error creating directory {full_path}: {e}")
        return False

    # Step 6: Set ownership for the created home directory
    try:
        os.chown(home_dir, pwd.getpwnam(username).pw_uid, grp.getgrnam(groupname).gr_gid)
        print(f"Ownership for {home_dir} set to {username}:{groupname}.")
    except Exception as e:
        logger.error(f"Error setting ownership for {home_dir}: {e}")
        return False

    # Step 7: Set ownership for the created document root directory
    try:
        os.chown(full_path, pwd.getpwnam(username).pw_uid, grp.getgrnam(groupname).gr_gid)
        print(f"Ownership for {full_path} set to {username}:{groupname}.")
    except Exception as e:
        logger.error(f"Error setting ownership for {full_path}: {e}")
        return False

    # Step 8: Set permissions for the created document root directory to 755
    try:
        os.chmod(full_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)  # 755 (rwxr-xr-x)
        print(f"Permissions for {full_path} set to 755.")
    except Exception as e:
        logger.error(f"Error setting permissions for {full_path}: {e}")
        return False

    # Step 9: Ensure the "nobody" group and user exist
    try:
        grp.getgrnam('nobody')
        print("Group 'nobody' already exists.")
    except KeyError:
        # Create the group 'nobody' if it doesn't exist
        try:
            subprocess.run(['sudo', 'groupadd', 'nobody'], check=True)
            print("Group 'nobody' created successfully.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Error creating group 'nobody': {e}")
            return False

    try:
        pwd.getpwnam('nobody')
        print("User 'nobody' already exists.")
    except KeyError:
        # Create the user 'nobody' as a system user with no login shell
        try:
            subprocess.run(['sudo', 'useradd', '-r', '-s', '/usr/sbin/nologin', '-g', 'nobody', 'nobody'], check=True)
            print("User 'nobody' created successfully.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Error creating user 'nobody': {e}")
            return False

    # Step 10: Modify the full path ownership and permissions
    try:
        # Change ownership to 'username:nobody'
        subprocess.run(['sudo', 'chown', '-R', f'{username}:nobody', full_path], check=True)
        print(f"Ownership for {full_path} set to {username}:nobody.")

        # Change permissions to 775
        subprocess.run(['sudo', 'chmod', '-R', '775', full_path], check=True)
        print(f"Permissions for {full_path} set to 775.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error setting ownership/permissions for {full_path}: {e}")
        return False

    return True
    
def set_permissions_and_ownership(path, username, groupname=None, permissions=None):
    
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
            print(f"Error applying ownership or permissions for {target_path}: {e}")
            return False

    # Start the process for the given path
    apply_recursively(path)
    return True

    
def restart_openlitespeed():
    try:
        os_name = getattr(settings, "MY_OS_NAME", "linux")
        if os_name == "debian":
            subprocess.run(['sudo', 'systemctl', 'restart', 'lsws'], check=True)
        else:
            subprocess.run(['sudo', 'systemctl', 'restart', 'openlitespeed'], check=True)
            
        
        
        print("OpenLiteSpeed has been restarted successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to restart OpenLiteSpeed: {e}")


def get_php_versions():
    php_versions = []
    # Define a regex pattern to match version numbers
    version_pattern = re.compile(r'^\d+(\.\d+)?$')  # Matches versions like 8.1, 7.4, etc.

    # Get all files starting with 'php' in /usr/local/lsws/
    for filename in os.listdir('/usr/local/lsws/'):
        if filename.startswith('lsphp'):
            # Extract the version from the filename
            version = filename.replace('lsphp', '')  # Remove 'lsphp' to get the version number

            # Check if the extracted version matches the version pattern
            if version_pattern.match(version):
                # Add a dot after the first digit
                if '.' not in version:  # If the version does not contain a dot
                    version = f"{version[0]}.{version[1:]}"  # Insert a dot after the first digit
                php_versions.append(version)  # Use version as both value and display label

    # Sort the versions in ascending order
    php_versions.sort(key=lambda x: list(map(int, x.split('.'))))

    return php_versions
    
    
def replace_php_version_in_vhost(domain_name, new_php_version):
    vhost_directory = f"/usr/local/lsws/conf/vhosts/{domain_name}"
    vhost_file_path = os.path.join(vhost_directory, "vhost.conf")
    try:
        # Check if the vHost config file exists
        if not os.path.isfile(vhost_file_path):
            print(f"Configuration file {vhost_file_path} does not exist.")
            return False

        # Read the content of the vHost config file
        with open(vhost_file_path, 'r') as file:
            lines = file.readlines()

        # Define a regex pattern to find the ScriptHandler line
        script_handler_pattern = re.compile(r'^(.*?add\s+lsapi:)(\w+)(\s+php.*)$', re.MULTILINE)

        # Replace the old version in the ScriptHandler line
        for i, line in enumerate(lines):
            if script_handler_pattern.search(line):
                # Replace the version part (after lsapi:) with the new version
                lines[i] = script_handler_pattern.sub(r'\1' + f'{new_php_version}' + r'\3', line)
                print(f"Replaced PHP version in {vhost_file_path}: {line.strip()} -> {lines[i].strip()}")
                break
        else:
            print("No ScriptHandler line found to replace.")
            return False

        # Write the modified content back to the vHost config file
        with open(vhost_file_path, 'w') as file:
            file.writelines(lines)

        return True

    except Exception as e:
        print(f"Error occurred: {e}")
        return False   
        
def replace_extprocessor_socket_and_path(domain_name, new_processor_name, pure_version):
    vhost_directory = f"/usr/local/lsws/conf/vhosts/{domain_name}"
    vhost_file_path = os.path.join(vhost_directory, "vhost.conf")

    try:
        # Check if the vHost config file exists
        if not os.path.isfile(vhost_file_path):
            print(f"Configuration file {vhost_file_path} does not exist.")
            return False

        # Read the content of the vHost config file
        with open(vhost_file_path, 'r') as file:
            lines = file.readlines()

        # Define regex patterns for replacements
        processor_pattern = re.compile(r'^(extprocessor\s+)(\S+)(\s*{)', re.MULTILINE)
        socket_pattern = re.compile(r'(address\s*uds://tmp/lshttpd/)(\S+)(\.sock)', re.MULTILINE)
        # Updated path pattern to allow for multiple spaces after 'path'
        path_pattern = re.compile(r'^(path\s+)(\s*)(.*?)(/bin/lsphp)', re.MULTILINE)

        # Initialize flags to track replacements
        processor_replaced = False
        socket_replaced = False
        path_replaced = False

        # Replace the extprocessor name
        for i, line in enumerate(lines):
            if processor_pattern.search(line):
                lines[i] = processor_pattern.sub(r'\1' + new_processor_name + r'\3', line)
                print(f"Replaced extprocessor name in {vhost_file_path}: {line.strip()} -> {lines[i].strip()}")
                processor_replaced = True
                break  # Exit after the first replacement

        # Replace the socket path
        for i, line in enumerate(lines):
            if socket_pattern.search(line):
                lines[i] = socket_pattern.sub(r'\1' + new_processor_name + r'\3', line)
                print(f"Replaced socket path in {vhost_file_path}: {line.strip()} -> {lines[i].strip()}")
                socket_replaced = True
                break  # Exit after the first replacement

        # Replace the path with pure_version
        for i, line in enumerate(lines):
            if path_pattern.search(line):
                lines[i] = path_pattern.sub(r'\1' + f'\2/usr/local/lsws/{pure_version}' + r'\4', line)  # Keep spaces and update the path directly
                print(f"Replaced path in {vhost_file_path}: {line.strip()} -> {lines[i].strip()}")
                path_replaced = True
                break  # Exit after the first replacement

        # Confirm that all replacements were successful
        if not processor_replaced:
            print("No extprocessor line found to replace.")
        if not socket_replaced:
            print("No socket path line found to replace.")
        if not path_replaced:
            print("No path line found to replace.")

        # Write the modified content back to the vHost config file
        with open(vhost_file_path, 'w') as file:
            file.writelines(lines)
            print(f"Updated {vhost_file_path} successfully.")

        return True

    except Exception as e:
        print(f"Error occurred: {e}")
        return False
        

def replace_path(domain_name, pure_version): 
    vhost_directory = f"/usr/local/lsws/conf/vhosts/{domain_name}"
    vhost_file_path = os.path.join(vhost_directory, "vhost.conf")
    
    # Check if the file exists
    if not os.path.isfile(vhost_file_path):
        print(f"File not found: {vhost_file_path}")
        return

    # Read the file contents
    with open(vhost_file_path, 'r') as file:
        lines = file.readlines()

    # Replace the version in the lines
    updated_lines = []
    for line in lines:
        if "/usr/local/lsws/" in line and "/bin/lsphp" in line:
            # Split the line on '/usr/local/lsws/' and '/bin/lsphp'
            parts = line.split('/usr/local/lsws/')
            if len(parts) > 1:
                left_part = parts[0]  # Everything before the path
                right_part = parts[1]  # Everything after '/usr/local/lsws/'
                
                # Now split right_part on '/bin/lsphp'
                right_parts = right_part.split('/bin/lsphp')
                if len(right_parts) > 1:
                    # Construct the new line
                    new_line = f"{left_part}/usr/local/lsws/{pure_version}/bin/lsphp{right_parts[1]}"
                    updated_lines.append(new_line)
                else:
                    updated_lines.append(line)  # Keep original line if no match
            else:
                updated_lines.append(line)  # Keep original line if no match
        else:
            updated_lines.append(line)  # Keep original line if no match

    # Write the updated lines back to the file
    with open(vhost_file_path, 'w') as file:
        file.writelines(updated_lines)

    print(f"Replaced version in {vhost_file_path}")
    
def change_php_version(domain_name, version_name, version):
    # Construct the full PHP version string
    version_name=version_name.replace('.', '')
    version_string = f"lsphp{version}"  # Correctly construct the version string
    replace_php_version_in_vhost(domain_name, version_name)    
    replace_path(domain_name, version_string)  # Pass the constructed version string
    replace_extprocessor_socket_and_path(domain_name, version_name, version_string) 
    
  
def get_ssl_details(domain_name):
    alias = domain_name
    if domain_name.startswith("www."):
        
        domain_name = domain_name[4:]
    
        
    cert_path = f'/etc/letsencrypt/live/{domain_name}/fullchain.pem'  # Ensure the path is correct
    print(f"Checking certificate path: {cert_path}")  # Debugging line
    
    try:
        with open(cert_path, 'r') as f:
            fullchain_pem = f.read()
    except FileNotFoundError:
        return {
            "expiration_date": "Not Available",
            "certificate_type": "Unknown",
            "issuer": "Unknown",
            "certificate_validity": "Invalid or Not Found"
        }

    cert_info = parse_certificate(fullchain_pem)
    domains = cert_info.get("domains", [])

    # Check if alias matches any domain in certificate
    if alias not in domains:
        return {
            "expiration_date": "Not Available",
            "certificate_type": "Unknown",
            "issuer": "Unknown",
            "certificate_validity": "Invalid or Not Found"
        }

    
    
    try:
        # Get expiration date
        expiration_result = subprocess.run(
            ['openssl', 'x509', '-in', cert_path, '-noout', '-enddate'],
            capture_output=True,
            text=True,
            check=True
        )
        expiration_output = expiration_result.stdout.strip()
        print(f"OpenSSL expiration output: {expiration_output}")  # Debugging line

        # Extract the expiration date
        expiration_date_str = expiration_output.split('=')[1]
        expiration_date = datetime.strptime(expiration_date_str, '%b %d %H:%M:%S %Y %Z')
        formatted_date = expiration_date.strftime('%d-%m-%y %I:%M %p')

        # Get certificate type
        key_type_result = subprocess.run(
            ['openssl', 'x509', '-in', cert_path, '-noout', '-text'],
            capture_output=True,
            text=True,
            check=True
        )
        key_type_output = key_type_result.stdout.strip()
        print(f"OpenSSL key type output: {key_type_output}")  # Debugging line

        # Determine the certificate type
        if "RSA Public-Key" in key_type_output:
            cert_type = "RSA"
        elif "EC Public-Key" in key_type_output:
            cert_type = "ECC"
        else:
            cert_type = "Unknown"

        # Get certificate issuer and subject
        issuer_result = subprocess.run(
            ['openssl', 'x509', '-in', cert_path, '-noout', '-issuer'],
            capture_output=True,
            text=True,
            check=True
        )
        issuer_output = issuer_result.stdout.strip()
        print(f"OpenSSL issuer output: {issuer_output}")  # Debugging line

        subject_result = subprocess.run(
            ['openssl', 'x509', '-in', cert_path, '-noout', '-subject'],
            capture_output=True,
            text=True,
            check=True
        )
        subject_output = subject_result.stdout.strip()
        print(f"OpenSSL subject output: {subject_output}")  # Debugging line

        # Extract the issuer and subject values
        issuer_name = issuer_output.split('=')[-1].split()[0]
        subject_name = subject_output.split('=')[-1]

        # Check if the certificate is self-signed
        if issuer_name.strip() == subject_name.strip():
            cert_validity = "Self-signed certificate"
        else:
            cert_validity = get_ssl_issuer_org(cert_path)

        return {
            "expiration_date": formatted_date,
            "certificate_type": cert_type,
            "issuer": issuer_name,
            "certificate_validity": cert_validity
        }
    except subprocess.CalledProcessError as e:
        print(f"Error running OpenSSL: {e.stderr.strip()}")  # Improved error logging
    except IndexError as e:
        print(f"Error parsing output: {e}")  # Log output for parsing errors
    except Exception as e:
        print(f"An unexpected error occurred: {e}")  # General error logging

    # Default values when an error occurs
    return {
        "expiration_date": "Not Available",
        "certificate_type": "Unknown",
        "issuer": "Unknown",
        "certificate_validity": "Invalid or Not Found"
    }
 
def get_ssl_issuer_org(cert_path: str) -> str:
    
    try:
        # Run OpenSSL command to get the issuer details
        result = subprocess.run(
            ["openssl", "x509", "-in", cert_path, "-noout", "-issuer"],
            check=True,
            capture_output=True,
            text=True
        )

        # Extract 'O=' (Organization) using regex
        
        match = re.search(r"O\s*=\s*([^,]+)", result.stdout)
        return match.group(1).strip() if match else "No Organization found"
    
    except subprocess.CalledProcessError as e:
        return f"Error reading certificate: {e.stderr.strip()}"
    except Exception as e:
        return f"Error: {str(e)}"

      
def _check_domain_resolves(domain: str) -> bool:
    """Check if the domain resolves via DNS. Returns True if it resolves to any IP."""
    try:
        socket.gethostbyname(domain)
        return True
    except socket.gaierror:
        return False


def _cleanup_acme_state(domain: str):
    """Remove stale acme.sh state directories that can block retries."""
    acme_dirs = [
        f"/root/.acme.sh/{domain}_ecc",
        f"/root/.acme.sh/{domain}",
    ]
    for acme_dir in acme_dirs:
        if os.path.exists(acme_dir):
            try:
                shutil.rmtree(acme_dir)
                print(f"Cleaned up stale acme.sh state: {acme_dir}")
            except Exception as e:
                print(f"Warning: could not clean {acme_dir}: {e}")


def issue_ssl_certificate(domain: str, webroot_path: str) -> bool:
    if domain.startswith("www."):
        alias = domain
        domain = domain[4:]
        domains_list = [domain, alias]
    else:
        domains_list = [domain]

    # --- Step 1: Wait for DNS to resolve (up to ~90 seconds) ---
    max_dns_checks = 4
    dns_wait_seconds = 30
    dns_resolved = False
    for attempt in range(1, max_dns_checks + 1):
        if _check_domain_resolves(domains_list[0]):
            dns_resolved = True
            print(f"DNS resolved for {domains_list[0]} on attempt {attempt}.")
            break
        if attempt < max_dns_checks:
            print(f"DNS not resolved for {domains_list[0]}, waiting {dns_wait_seconds}s (attempt {attempt}/{max_dns_checks})...")
            time.sleep(dns_wait_seconds)

    if not dns_resolved:
        logger.error(f"DNS does not resolve for {domains_list[0]} after {max_dns_checks} attempts. Skipping SSL issuance.")
        print(f"DNS does not resolve for {domains_list[0]}. Cannot issue SSL.")
        return False

    # --- Step 2: Ensure the .well-known/acme-challenge directory exists in the webroot ---
    challenge_dir = os.path.join(webroot_path, '.well-known', 'acme-challenge')
    os.makedirs(challenge_dir, exist_ok=True)

    # --- Step 3: Build the acme.sh command ---
    domain_args = []
    for d in domains_list:
        domain_args.extend(['-d', d])

    command = [
        '/root/.acme.sh/acme.sh',
        '--issue',
        *domain_args,
        '--cert-file', f'/etc/letsencrypt/live/{domain}/cert.pem',
        '--key-file', f'/etc/letsencrypt/live/{domain}/privkey.pem',
        '--fullchain-file', f'/etc/letsencrypt/live/{domain}/fullchain.pem',
        '-w', webroot_path,
        '--reloadcmd', '/usr/local/lsws/bin/lswsctrl restart',
        '--force',
        '--debug'
    ]

    # --- Step 4: Attempt SSL issuance with retries ---
    max_retries = 3
    retry_delay = 30  # seconds between retries
    create_letsencrypt_if_not_exist(domain)

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            # Clean up stale acme.sh state before each attempt
            _cleanup_acme_state(domain)

            print(f"SSL issuance attempt {attempt}/{max_retries} for {domain}...")
            result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # Success — configure email SSL, SMTP, panel vhost, and listener
            email_ssl(domain)
            add_ssl_smtp_mail(domain)
            panel_virtual_host(domain)
            panel_listener_mapping("add", domain)
            create_panel_vhost_file(domain)
            print(result.stdout.decode())
            logger.info(f"SSL issued successfully for {domain} on attempt {attempt}:\n{result.stdout}")
            return True

        except subprocess.CalledProcessError as e:
            last_error = e
            error_output = e.stderr.decode() if e.stderr else 'No error output'
            logger.error(f"SSL attempt {attempt}/{max_retries} failed for {domain}: {error_output}")
            print(f"SSL attempt {attempt}/{max_retries} failed: {error_output}")

            if attempt < max_retries:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)

    # All retries exhausted
    logger.error(f"All {max_retries} SSL attempts failed for {domain}.")
    if last_error and last_error.stderr:
        print(f"Final error: {last_error.stderr.decode()}")
    return False


def get_dovecot_version():
    result = subprocess.run(["dovecot", "--version"], capture_output=True, text=True)
    return result.stdout.strip().split()[0].split("-")[0]

def is_dovecot_24_plus():
    version = get_dovecot_version()
    major, minor = map(int, version.split(".")[:2])
    return (major > 2) or (major == 2 and minor >= 4)

def email_ssl(domain):
    file_path = '/etc/dovecot/dovecot.conf'
    
    if is_dovecot_24_plus():
        block = f"""local_name {domain} {{
    ssl_server_cert_file = /etc/letsencrypt/live/{domain}/fullchain.pem
    ssl_server_key_file = /etc/letsencrypt/live/{domain}/privkey.pem
}}\n"""
    else:
        block = f"""local_name {domain} {{
    ssl_cert = </etc/letsencrypt/live/{domain}/fullchain.pem
    ssl_key = </etc/letsencrypt/live/{domain}/privkey.pem
}}\n"""

    try:
        with open(file_path, 'r') as f:
            content = f.read()

        if f"local_name {domain} {{" in content:
            print(f"Block for '{domain}' already exists.")
            return

        with open(file_path, 'a') as f:
            f.write('\n' + block)

        print(f"Block for '{domain}' added.")
        subprocess.run(["sudo", "systemctl", "restart", "dovecot"], check=True)
    except Exception as e:
        print(f"Error updating file: {e}")


def add_ssl_smtp_mail(domain):
    key_path = f"/etc/letsencrypt/live/{domain}/privkey.pem"
    cert_path = f"/etc/letsencrypt/live/{domain}/fullchain.pem"
    file_path="/etc/postfix/vmail_ssl.map"
    line_to_add = f"{domain} {key_path} {cert_path}\n"
    changed = False

    try:
        try:
            with open(file_path, "r") as f:
                lines = f.readlines()
                if line_to_add in lines:
                    print("Line already exists. No change made.")
                else:
                    changed = True
        except FileNotFoundError:
            changed = True  # File doesn't exist, will create

        if changed:
            with open(file_path, "a") as f:
                f.write(line_to_add)
            print("Line added.")

        # Step 3: Run postmap -F
        subprocess.run(["postmap", "-F", f"hash:{file_path}"], check=True)
        print("postmap updated.")

        # Step 4: Restart Postfix
        subprocess.run(["systemctl", "restart", "postfix"], check=True)
        print("Postfix restarted.")

    except Exception as e:
        print(f"Error: {e}")        
 


def restart_pdns():
    try:
        # Execute the command to restart PowerDNS
        subprocess.check_call(['sudo', 'systemctl', 'restart', 'pdns'])
        print("PowerDNS service restarted successfully.")
        return True  # Indicate success
    except subprocess.CalledProcessError as e:
        print(f"Failed to restart PowerDNS: {e}")
        return False  # Indicate failure   


def create_letsencrypt_if_not_exist(domain_name):
    folder_path = f"/etc/letsencrypt/live/{domain_name}"
    
    try:
        # Check if the directory exists, and create it if it doesn't
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"Folder created: {folder_path}")
        else:
            print(f"Folder already exists: {folder_path}")
    except Exception as e:
        print(f"An error occurred while creating the folder: {e}")    


def vhost_action(domain_name, action):
    vhost_directory = f"/usr/local/lsws/conf/vhosts/{domain_name}"
    conf_file_path = os.path.join(vhost_directory, "vhost.conf")
    
    # Check if the configuration file exists
    if not os.path.isfile(conf_file_path):
        print(f"Configuration file {conf_file_path} not found.")
        return False

    try:
        # Read the content of the config file
        with open(conf_file_path, 'r') as file:
            lines = file.readlines()

        old_home_path = None
        new_path = None
        current_path = None
        updated_lines = []
        docRoot_found = False
        main_docRoot_commented = False

        # Define action paths
        action_paths = {
            "suspend": '/usr/local/lsws/Example/html/blocked',
            "bandwidth": '/usr/local/lsws/Example/html/bandwidth'
        }

        # Process each line and modify accordingly
        for line in lines:
            stripped_line = line.strip()

            if 'docRoot' in stripped_line:
                # Check if this is the first occurrence of docRoot
                if not docRoot_found:
                    if stripped_line.startswith('# docRoot'):
                        current_path = stripped_line.split()[-1]
                        main_docRoot_commented = True  # Mark that main path is commented out
                    else:
                        current_path = stripped_line.split()[-1]

                    # If the path starts with /home, backup the path and don't remove it
                    if current_path.startswith("/home"):
                        old_home_path = current_path
                        # Check for current action before disabling the path
                        if action == "restore":
                            # Restore the original path
                            updated_lines.append(f"docRoot                   {old_home_path}\n")
                        else:
                            # Skip further changes if action is already applied
                            if current_path == action_paths.get(action):
                                print(f"Action '{action}' is already applied to {current_path}. Skipping.")
                                return False

                            # Comment out the current path (if it's the main /home path) and set the new action path
                            updated_lines.append(f"# {line.strip()}\n")
                            new_path = action_paths.get(action)
                            updated_lines.append(f"docRoot                   {new_path}\n")
                    elif action == "restore":
                        # If restoring, re-enable the original /home path
                        if old_home_path:
                            updated_lines.append(f"docRoot                   {old_home_path}\n")
                        else:
                            print("No valid path to restore.")
                            return False
                    else:
                        # Comment out the existing docRoot if not already commented
                        if not main_docRoot_commented:
                            updated_lines.append(f"# {line.strip()}\n")
                            main_docRoot_commented = True

                        # Apply the action path (suspend/bandwidth)
                        if action in action_paths:
                            new_path = action_paths[action]
                            updated_lines.append(f"docRoot                   {new_path}\n")
                        else:
                            print(f"Invalid action: {action}")
                            return False

                    docRoot_found = True
                else:
                    # Ignore additional docRoot lines
                    continue
            else:
                # Keep all other lines unchanged
                updated_lines.append(line)

        # If the action is restore and no /home path was found, it's an error
        if action == "restore" and old_home_path is None:
            print("No original /home path found to restore.")
            return False

        # Write the modified content back to the config file
        with open(conf_file_path, 'w') as file:
            file.writelines(updated_lines)

        print(f"docRoot successfully updated in {conf_file_path}.")
        return True

    except Exception as e:
        print(f"An error occurred: {e}")
        return False


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

def make_domain(domain_name, php_name, username_string, path):
    from users.database import get_user_data_by_id,add_domain_dns
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
        setup_dkim(domain_name)
        insert_dkim_record(domain_name,domain_instance.id,user.id)

        # Restart services
        restart_openlitespeed()
        restart_pdns()

        return {"success": True, "message": f"Domain '{domain_name}' added successfully!"}

    except User.DoesNotExist:
        return {"success": False, "message": f"User '{username_string}' does not exist."}
    except Exception as e:
        return {"success": False, "message": f"An error occurred: {str(e)}"}

def read_php_ini(ini_file_path):
    # Example: Read the php.ini file and extract necessary settings
    settings = {}
    try:
        with open(ini_file_path, 'r', encoding='utf-8') as file:
            content = file.read()  # Read full content
            for line in content.splitlines():  # Split by line for parsing
                line = line.strip()
                if line and not line.startswith(';'):  # Ignore comments and empty lines
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
            # Store full content for reference
            settings['content'] = content
    except Exception as e:
        print(f"Error reading php.ini: {e}")
    return settings


def fetch_php_settings_fun(php_version):
    
    current_settings = {}

    if php_version:
        if php_version.startswith('cgi'):
            new_php_version = php_version.replace('cgi ', '').replace('cgi', '').strip()
            ini_file_path = f'/etc/php/{new_php_version}/cgi/php.ini'
        else:    
            new_php_version = php_version.replace('.', '')
            ini_file_path = f'/usr/local/lsws/lsphp{new_php_version}/etc/php/{php_version}/litespeed/php.ini'
            ini_file_path_old = f'/usr/local/lsws/lsphp{new_php_version}/etc/php.ini'

        if os.path.exists(ini_file_path):
            current_settings = read_php_ini(ini_file_path)
        elif os.path.exists(ini_file_path_old):
            current_settings = read_php_ini(ini_file_path_old)
            
            
    
    return current_settings 
    
    
def fetch_vhost_fun(domain):
    current_settings = {}

    vhost = f'/usr/local/lsws/conf/vhosts/{domain}/vhost.conf'

    if os.path.exists(vhost):
        try:
            with open(vhost, 'r') as f:
                content = f.read()

            current_settings['status'] = 'success'
            current_settings['content'] = content
            

        except Exception as e:
            current_settings['status'] = 'error'
            current_settings['message'] = str(e)
    else:
        current_settings['status'] = 'error'
        current_settings['message'] = 'vhost.conf not found'

    return current_settings
    

def reload_openlitespeed():
    """
    Gracefully reload OpenLiteSpeed without dropping active connections.
    """
    try:
        subprocess.run(['/usr/local/lsws/bin/lswsctrl', 'reload'], check=True)
    except Exception as e:
        print(f"Error reloading OpenLiteSpeed: {e}")
    
def save_vhost_fun(domain, content):

    result = {}


    vhost = f'/usr/local/lsws/conf/vhosts/{domain}/vhost.conf'

    if not os.path.exists(vhost):
        return {
            'status': 'error',
            'message': 'vhost.conf not found'
        }

    try:
        # Optional: create backup before saving
        backup_path = vhost + ".bak"
        shutil.copy2(vhost, backup_path)

        # Write new content
        with open(vhost, 'w') as f:
            f.write(content)
        
        result['status'] = 'success'
        result['message'] = 'vhost.conf saved successfully'
        reload_openlitespeed()
    except Exception as e:
        result['status'] = 'error'
        result['message'] = str(e)

    return result    

    
def get_ini_path_fun(php_version):
    new_php_version = php_version.replace('.', '')
    ini_file_path = f'/usr/local/lsws/lsphp{new_php_version}/etc/php/{php_version}/litespeed/php.ini'
    ini_file_path_old = f'/usr/local/lsws/lsphp{new_php_version}/etc/php.ini'
            
    if os.path.exists(ini_file_path):
        current_settings = ini_file_path
    elif os.path.exists(ini_file_path_old):
        current_settings = ini_file_path_old

    return current_settings  

def get_php_version_hard():
    all_php_versions = ['7.3', '7.4', '8.0', '8.1', '8.2', '8.3','8.4','8.5']

    return all_php_versions  


    
    
def manage_php_extension(php_version, extension, action):
    try:
        os_name = getattr(settings, "MY_OS_NAME", "linux").lower()

        # Sanitize extension input
        if not re.match(r'^[a-zA-Z0-9_-]+$', extension):
            return {'status': 'error', 'message': 'Invalid extension characters.'}

        # Determine if CGI or lsphp version
        if php_version.startswith('cgi'):
            # Extract version number with dot, e.g. '7.4'
            try:
                version_num = php_version.split(' ')[1]
            except IndexError:
                return {'status': 'error', 'message': 'Invalid PHP version format.'}
            pkg_prefix = f'php{version_num}-'  # e.g. php7.4-mbstring
        else:
            # lsphp versions, remove dot for package names
            version_num = php_version.replace('.', '')
            pkg_prefix = f'lsphp{version_num}-'  # e.g. lsphp74-mbstring

        if not re.match(r'^[a-zA-Z0-9.]+$', version_num):
            return {'status': 'error', 'message': 'Invalid PHP version format.'}

        # Determine package manager & repo setup
        if os_name in ["ubuntu", "debian"]:
            # Add LiteSpeed repo only for lsphp packages (optional: skip for system php)
            if not php_version.startswith('cgi'):
                wget_proc = subprocess.Popen(["wget", "-O", "-", "https://repo.litespeed.sh"], stdout=subprocess.PIPE)
                bash_proc = subprocess.Popen(["sudo", "bash"], stdin=wget_proc.stdout)
                wget_proc.stdout.close()
                bash_proc.communicate()
                if bash_proc.returncode != 0:
                    raise subprocess.CalledProcessError(bash_proc.returncode, "sudo bash")
                from whm.function import run_package_update
                run_package_update()
            install_command = "apt-get"
        elif os_name in ["centos", "almalinux", "rocky", "rhel", "fedora", "oraclelinux", "amazonlinux"]:
            install_command = "dnf" if subprocess.run(["command", "-v", "dnf"], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0 else "yum"
        else:
            return {'status': 'error', 'message': f'Unsupported OS: {os_name}'}

        pkg_name = f"{pkg_prefix}{extension}"

        if action == "install":
            action_arg = "install"
        elif action == "uninstall":
            action_arg = "remove"
        else:
            return {'status': 'error', 'message': f'Unknown action: {action}'}

        result = subprocess.run(
            ["sudo", install_command, action_arg, pkg_name, "-y"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode == 0:
            return {'status': 'success', 'message': f'Extension {extension} {action}ed successfully.'}
        else:
            return {'status': 'error', 'message': result.stderr.strip()}

    except subprocess.CalledProcessError as e:
        return {'status': 'error', 'message': f'Command failed: {e}'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}





def fetch_php_extensions(php_version):
    all_extensions = [
        "curl", "mbstring", "xml", "json", "gd", "openssl", "mysql", "mysqli", "zip", "bcmath",
        "soap", "sockets", "intl", "exif", "opcache", "gettext", "imagick", "redis",
        "memcached", "fileinfo", "ftp", "zlib", "apcu", "imap", "ioncube",
        "ldap", "msgpack", "pgsql", "pspell", "snmp", "sqlite3", "sybase", "tidy", "pear"
    ]
    
    installed_exts = []
    installed_pkgs = []

    if php_version.startswith('cgi'):
        lsphp = 'php'
        # Extract version number with dot, e.g. '7.4' from 'cgi 7.4'
        try:
            version_num = php_version.split(' ')[1]
        except IndexError:
            version_num = ''  # fallback empty string if malformed
        new_php_version = version_num  # keep dot for package name matching
        php_bin = f'/usr/bin/php-cgi{version_num}'
    else:
        lsphp = 'lsphp'
        new_php_version = php_version.replace('.', '')  # remove dot for lsphp path & package prefix
        php_bin = f'/usr/local/lsws/lsphp{new_php_version}/bin/php'

    # Get loaded PHP modules from php -m
    try:
        result = subprocess.run([php_bin, '-m'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            installed_exts = [x.strip().lower() for x in result.stdout.splitlines()]
    except Exception:
        pass

    # Use dpkg only if version string looks valid
    if new_php_version:
        prefix = f'{lsphp}{new_php_version}-'  # e.g. php7.4- or lsphp74-
        try:
            result = subprocess.run(['dpkg', '-l'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if prefix in line and 'ii' in line:
                        parts = line.split()
                        if len(parts) >= 2:
                            ext_name = parts[1].replace(prefix, '')
                            installed_pkgs.append(ext_name.lower())
        except Exception:
            pass

    available = []
    not_available = []

    for ext in all_extensions:
        if ext in installed_exts or ext in installed_pkgs:
            available.append(ext)
        else:
            not_available.append(ext)

    return {
        'available': sorted(set(available)),
        'not_available': sorted(set(not_available))
    }


def install_php(versions):
    version = versions.replace('.', '')
    if not re.match(r'^[a-zA-Z0-9]+$', version):
        return {'status': 'error', 'message': 'Invalid PHP version input.'}
        
    os_name = getattr(settings, "MY_OS_NAME", "linux")
    os_f = getattr(settings, 'MY_OS_VERSION', 'linux')

    if os_name == "ubuntu" or os_name == "debian":
        install_command = "apt-get"
    elif os_name in ["centos", "almalinux", "rocky", "rhel", "fedora", "oraclelinux", "amazonlinux"]:
        # Use `dnf` if available, otherwise fallback to `yum`
        install_command = "dnf" if subprocess.run(["command", "-v", "dnf"], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0 else "yum"
    else:
        return {'status': 'error', 'message': f'Unsupported OS: {os_name}'}

    try:
        # Step 1: Add necessary repositories based on the OS
        if os_name == "ubuntu" or os_name == "debian":
            subprocess.run(["sudo", "apt-get", "install", "-y", "software-properties-common"], check=True)
            subprocess.run(["sudo", "add-apt-repository", "ppa:openlitespeed/php", "-y"], check=True)
            subprocess.run(["sudo", "apt-get", "update"], check=True)
        elif os_name in ["centos", "almalinux", "rocky", "rhel", "fedora", "oraclelinux", "amazonlinux"]:
            # Additional repository setup for CentOS/AlmaLinux/RHEL
            subprocess.run(["sudo", install_command, "install", "-y", "epel-release"], check=True)
            subprocess.run(["sudo", install_command, "install", "-y", f"lsphp{version}", f"lsphp{version}-common", f"lsphp{version}-mysqlnd"], check=True)

        # Step 2: Install PHP and dependencies based on the OS
        if os_name == "ubuntu":
            subprocess.run(["sudo", install_command, "install", "-y", f"lsphp{version}", f"lsphp{version}-common", f"lsphp{version}-mysqlnd"], check=True)
        elif os_name in ["centos", "almalinux", "rocky", "rhel", "fedora", "oraclelinux", "amazonlinux"]:
            subprocess.run(["sudo", install_command, "install", "-y", f"lsphp{version}", f"lsphp{version}-common", f"lsphp{version}-mysqlnd"], check=True)

        # Return success message
        return {'status': 'success', 'message': f'PHP {version} installed successfully.'}

    except subprocess.CalledProcessError as e:
        return {'status': 'error', 'message': f'Unsupported php version {versions} for OS {os_name} {os_f}'}
            
            
            
       
        
def write_httpd_config():
    try:
        # Define the configuration file path and required content
        copy_mod_file()
        copy_mod_file_rule()
        rename_exclusion_rules_file()
        config_file = "/usr/local/lsws/conf/httpd_config.conf"
        config_content = """
module mod_security {
    modsecurity  on
    modsecurity_rules `
        SecDebugLogLevel 0
        SecDebugLog /usr/local/lsws/logs/modsec.log
        SecAuditEngine on
        SecAuditLogRelevantStatus "^(?:5|4(?!04))"
        SecAuditLogParts AFH
        SecAuditLogType Serial
        SecAuditLog /usr/local/lsws/logs/auditmodsec.log
        SecRuleEngine On
        SecRule REQUEST_URI "@beginsWith /file_manager" "phase:1,allow"
    `
    modsecurity_rules_file /usr/local/lsws/conf/owasp/coreruleset/crs-setup.conf
    modsecurity_rules_file /usr/local/lsws/conf/owasp/coreruleset/arule.conf
    modsecurity_rules_file /usr/local/lsws/conf/owasp/coreruleset/owasp-master.conf
}
"""
        # Check if the file exists
        if not os.path.exists(config_file):
            # Create the file and write the content if it doesn't exist
            with open(config_file, "w") as file:
                file.write(config_content)
            return {
                "status": "success",
                "message": f"Configuration file '{config_file}' created and updated successfully."
            }
        else:
            # Check if the required configuration already exists
            with open(config_file, "r") as file:
                existing_content = file.read()
            
            if "module mod_security {" not in existing_content:
                # Append the required configuration if not present
                with open(config_file, "a") as file:
                    file.write("\n" + config_content)
                return {
                    "status": "success",
                    "message": f"Configuration added to existing '{config_file}'."
                }
            else:
                return {
                    "status": "success",
                    "message": f"Configuration already exists in '{config_file}'."
                }
    except Exception as ex:
        return {
            "status": "error",
            "message": f"Unexpected error: {str(ex)}"
        }        
        
        
        
def check_modsecurity_rule():
    config_file = "/usr/local/lsws/conf/httpd_config.conf"
    rule_line = "modsecurity_rules_file /usr/local/lsws/conf/owasp/coreruleset/owasp-master.conf"

    try:
        with open(config_file, 'r') as file:
            for line in file:
                stripped_line = line.strip()
                # Check if the line matches and is not commented out
                if stripped_line == rule_line and not stripped_line.startswith("#"):
                    return True
        return False
    except FileNotFoundError:
        print(f"Configuration file not found: {config_file}")
        return False   


def toggle_comment(comment=False):
    config_file = "/usr/local/lsws/conf/httpd_config.conf"
    rule_line = "modsecurity_rules_file /usr/local/lsws/conf/owasp/coreruleset/owasp-master.conf"
    try:
        # Read the file content
        with open(config_file, 'r') as file:
            lines = file.readlines()

        # Process the lines
        updated_lines = []
        line_found = False

        for line in lines:
            stripped_line = line.lstrip()  # Remove leading spaces for comparison
            if rule_line in stripped_line:  # Match both commented and uncommented versions
                line_found = True
                if comment and not stripped_line.startswith("#"):  # Add #
                    updated_lines.append("#" + line)  # Add a comment if not already commented
                elif not comment and stripped_line.startswith("#"):  # Remove #
                    updated_lines.append(line.lstrip()[1:])  # Uncomment by removing the first #
                else:
                    updated_lines.append(line)  # Keep the line as is
            else:
                updated_lines.append(line)  # Keep other lines unchanged

        if not line_found:
            print(f"Line not found: {rule_line}")
            return False

        # Write back the updated content
        with open(config_file, 'w') as file:
            file.writelines(updated_lines)

        return True
    except FileNotFoundError:
        print(f"Configuration file not found: {config_file}")
        return False
    except Exception as e:
        print(f"An error occurred: {e}")
        return False


def rename_exclusion_rules_file():
    try:
        # Define file paths
        rules_dir = "/usr/local/lsws/conf/owasp/coreruleset/rules"
        original_file = os.path.join(rules_dir, "REQUEST-900-EXCLUSION-RULES-BEFORE-CRS.conf.example")
        renamed_file = os.path.join(rules_dir, "REQUEST-900-EXCLUSION-RULES-BEFORE-CRS.conf")
        original_file2 = os.path.join(rules_dir, "RESPONSE-999-EXCLUSION-RULES-AFTER-CRS.conf.example")
        renamed_file2 = os.path.join(rules_dir, "RESPONSE-999-EXCLUSION-RULES-AFTER-CRS.conf")

        # Check if the original file exists
        if os.path.exists(original_file):
            os.rename(original_file, renamed_file)

        # Rename the file
        if os.path.exists(original_file2):
            os.rename(original_file2, renamed_file2)
        
        

        

    except Exception as e:
        # Handle unexpected errors
        return {
            "status": "error",
            "message": f"An error occurred: {str(e)}"
        }

            
            
def install_modsecurity_and_crs():
    try:
        # Step 1: Detect the package manager
        
        if shutil.which("yum"):
            package_manager = "yum"
        elif shutil.which("dnf"):
            package_manager = "dnf"
        elif shutil.which("apt"):
            package_manager = "apt"
        elif shutil.which("zypper"):
            package_manager = "zypper"
        else:
            return {
                "status": "error",
                "message": "Unsupported package manager. Supported: yum, dnf, apt, zypper."
            }

        # Step 2: Install ModSecurity for OpenLiteSpeed
        if package_manager in ["yum", "dnf"]:
            subprocess.run([package_manager, "install", "ols-modsecurity", "-y"], check=True)
        elif package_manager == "apt":
            subprocess.run(["apt", "update"], check=True)
            subprocess.run(["apt", "install", "ols-modsecurity", "-y"], check=True)
        elif package_manager == "zypper":
            subprocess.run(["zypper", "--non-interactive", "install", "ols-modsecurity"], check=True)
        

        # Step 3: Create the directory for OWASP CRS if it doesn't exist
        owasp_dir = "/usr/local/lsws/conf/owasp"
        if not os.path.exists(owasp_dir):
            os.makedirs(owasp_dir)

        # Step 4: Download OWASP CRS
        os.chdir(owasp_dir)
        subprocess.run(["wget", "https://github.com/coreruleset/coreruleset/archive/v3.3.2/master.zip"], check=True)
        subprocess.run(["unzip", "-qq", "master.zip"], check=True)
        subprocess.run(["rm", "-f", "master.zip"], check=True)

        # Step 5: Rename crs-setup.conf.example to crs-setup.conf
        crs_dir = os.path.join(owasp_dir, "coreruleset-3.3.2")
        crs_setup_file = os.path.join(crs_dir, "crs-setup.conf.example")
        renamed_file = os.path.join(crs_dir, "crs-setup.conf")

        if os.path.exists(crs_setup_file):
            os.rename(crs_setup_file, renamed_file)

        # Step 6: Rename the extracted CRS directory
        extracted_dir = os.path.join(owasp_dir, "coreruleset-3.3.2")
        renamed_dir = os.path.join(owasp_dir, "coreruleset")
        if os.path.exists(extracted_dir):
            os.rename(extracted_dir, renamed_dir)

        # Step 7: Write configurations to httpd config
        write_httpd_config()

        return {
            "status": "success",
            "message": "ModSecurity and OWASP CRS have been installed successfully. "
                       "The sample crs-setup.conf.example has been renamed to crs-setup.conf."
        }

    except subprocess.CalledProcessError as e:
        # Return error response for installation errors
        return {
            "status": "error",
            "message": f"Error during installation: {str(e)}"
        }
    except Exception as ex:
        # Handle unexpected errors
        return {
            "status": "error",
            "message": f"Unexpected error: {str(ex)}"
        }
            
            
def replace_config_value_mod(name, new_value):
    filename = '/usr/local/lsws/conf/httpd_config.conf'
    try:
        with open(filename, 'r+') as f:
            content = f.read()

            # Pattern to match the exact keyword and its value (case-insensitive)
            pattern = rf"\b{name}\s+(.*)"
            match = re.search(pattern, content, re.MULTILINE | re.IGNORECASE)

            if match:
                # Replace the value after the keyword
                new_line = f"{name} {new_value}"
                content = re.sub(pattern, new_line, content, flags=re.MULTILINE | re.IGNORECASE)

                # Write the updated content back to the file
                f.seek(0)
                f.write(content)
                f.truncate()

                print(f"Replaced '{name}' value to '{new_value}' in {filename}.")
            else:
                print(f"Config '{name}' not found in {filename}.")
    except Exception as e:
        print(f"Error replacing value: {e}")            
        
        
def get_config_value_mod(name):
  filename = '/usr/local/lsws/conf/httpd_config.conf'
  try:
    with open(filename, 'r') as f:
      content = f.read()
      # Match the specific line (case-insensitive) and capture any whitespace
      pattern = rf"{name}(?:\s*)(.*)"  # Match name followed by any whitespace and capture anything after
      match = re.search(pattern, content, re.MULTILINE | re.IGNORECASE)
      if match:
        return match.group(1)  # Return the captured value
      else:
        print(f"Config '{name}' not found in {filename}.")
        return None
  except Exception as e:
    print("Error retrieving value:", e)
    return None

def restart_lsphp():
    try:
        # Kill all lsphp processes
        subprocess.run(["sudo", "pkill", "lsphp"], check=True)
        print("lsphp processes killed successfully. LiteSpeed will restart them automatically.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error restarting lsphp: {e}")
        return False    

def copy_mod_file():
    # Get the Django root path
    django_root = settings.BASE_DIR

    # Construct the correct source and destination file paths
    source_file = os.path.join(django_root, 'media', 'csf', 'owasp-master.conf')
    destination_file = '/usr/local/lsws/conf/owasp/coreruleset/owasp-master.conf'

    # Check if the source file exists before proceeding
    if os.path.exists(source_file):
        try:
            # Run the copy operation using shutil.copy
            shutil.copy(source_file, destination_file)
            return "File copied successfully!"  # Return a success message
        except Exception as e:
            return f"Error copying file: {e}"  # Return the error message if an exception occurs
    else:
        return f"Source file does not exist: {source_file}"  # Return a message if the source file doesn't exist        


def copy_mod_file_rule():
    # Get the Django root path
    django_root = settings.BASE_DIR

    # Construct the correct source and destination file paths
    source_file = os.path.join(django_root, 'media', 'csf', 'arule.conf')
    destination_file = '/usr/local/lsws/conf/owasp/coreruleset/arule.conf'

    # Check if the source file exists before proceeding
    if os.path.exists(source_file):
        try:
            # Run the copy operation using shutil.copy
            shutil.copy(source_file, destination_file)
            return "File copied successfully!"  # Return a success message
        except Exception as e:
            return f"Error copying file: {e}"  # Return the error message if an exception occurs
    else:
        return f"Source file does not exist: {source_file}"  # Return a message if the source file doesn't exist 


def read_php_conf(path):
    settings = {
        'log_errors': 'Off',
        'error_log': 'Off',
        'error_reporting': '0',  # Off means no error reporting
        'display_errors': 'Off'
    }

    in_php_override = False

    try:
        with open(path, 'r') as f:
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
        print(f"Error reading {path}: {e}")

    return settings

def write_php_conf(path, new_settings: dict):
    
    try:
        with open(path, 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        # File doesn't exist, create with the block
        with open(path, 'w') as f:
            f.write("phpIniOverride  {\n")
            for k, v in new_settings.items():
                f.write(f'php_admin_value {k} {v}\n')
            f.write("}\n")
        return True

    inside_block = False
    block_start_index = None
    block_end_index = None

    # Find phpIniOverride block lines
    for i, line in enumerate(lines):
        if line.strip().startswith('phpIniOverride'):
            inside_block = True
            block_start_index = i
            continue
        if inside_block and line.strip() == '}':
            block_end_index = i
            break

    # If block not found, add it at the end
    if block_start_index is None or block_end_index is None:
        lines.append("\nphpIniOverride  {\n")
        for k, v in new_settings.items():
            lines.append(f'php_admin_value {k} {v}\n')
        lines.append("}\n")
    else:
        # Parse existing settings in block into a dict (for quick lookup)
        existing_settings = {}
        for i in range(block_start_index + 1, block_end_index):
            line = lines[i].strip()
            if line.startswith('php_admin_value'):
                parts = line.split(None, 2)
                if len(parts) == 3:
                    _, key, value = parts
                    existing_settings[key] = (value, i)

        # Update or add each new setting
        for key, value in new_settings.items():
            if key in existing_settings:
                # Update the line
                idx = existing_settings[key][1]
                lines[idx] = f'php_admin_value {key} {value}\n'
            else:
                # Insert new line before block_end_index
                lines.insert(block_end_index, f'php_admin_value {key} {value}\n')
                block_end_index += 1  # Adjust end index for subsequent inserts

    # Write back to file
    with open(path, 'w') as f:
        f.writelines(lines)

    return True


def check_mod_installed():    
    mod_bin_path = '/usr/local/lsws/conf/owasp'
    return os.path.exists(mod_bin_path)         
    
    
def get_server_conf_path():    
    CONF_FILE_PATH = '/usr/local/lsws/conf/httpd_config.conf'
    return CONF_FILE_PATH      
    
def get_vhost_directory(domain):
    vhost_directory = f"/usr/local/lsws/conf/vhosts/{domain}"

    return vhost_directory 
    
def get_vhost_file(domain):
    vhost_directory = f"/usr/local/lsws/conf/vhosts/{domain}/vhost.conf"

    return vhost_directory   


def enable_cgroups():
    import time
    with open(LISTENER_CONFIG_FILE, "r") as f:
        content = f.read()

    pattern = r"CGIRLimit\s*\{.*?\}"
    match = re.search(pattern, content, re.DOTALL)

    if not match:
        print("CGIRLimit block not found")
        return False

    block = match.group(0)

    if re.search(r"cgroups\s+\d+", block):
        new_block = re.sub(
            r"cgroups\s+\d+",
            "cgroups                 2",
            block
        )
    else:
        new_block = block[:-1] + "\n  cgroups                 2\n}"

    if block == new_block:
        print("cgroups already set correctly")
        return False

    content = content.replace(block, new_block)

    with open(LISTENER_CONFIG_FILE, "w") as f:
        f.write(content)

    print("Updated cgroups to 2")

    subprocess.run(
        ["/usr/local/lsws/bin/lswsctrl", "stop"],
        check=False
    )

    time.sleep(1)

    subprocess.run(
        ["/usr/local/lsws/bin/lswsctrl", "start"],
        check=False
    )

    print("LSWS restarted")
    return True        