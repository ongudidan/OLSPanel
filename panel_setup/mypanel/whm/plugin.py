import requests
import os
import stat
import json
import subprocess
import binascii
import zipfile
import shutil
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse,Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy,reverse
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.views import View
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse


from django.db import connection
from users.function import *  # Import your function
from django.contrib.auth.hashers import make_password
from ftplib import FTP, error_perm
from file_manager.function_file import *
from ftplib import FTP
from urllib.parse import urlparse
from django.contrib.auth import update_session_auth_hash, authenticate, logout
from django.conf import settings
from django.http import HttpResponse, FileResponse, Http404, HttpResponseRedirect
from mimetypes import guess_type
import re
from django.views.decorators.csrf import csrf_exempt
import http.cookies
from users.panellogger import *
import time
from http.cookies import SimpleCookie
from users.php import *
from django.views.decorators.clickjacking import xframe_options_exempt


plugin_role = 'admin_panel'


def get_users_plugins_list():
    plugin_type = 'users'
    
    plugin_names = get_all_plugin_names(plugin_type, plugin_role)
    plugin_links = get_all_plugin_link(plugin_type, plugin_role)
    plugin_list = []

    # Add dynamic plugins
    for plugin_name in plugin_names:
        icon = get_plugin_config_value('icon', plugin_name)
        url = get_plugin_config_value('url', plugin_name)
        sorder = get_plugin_config_value('sorder', plugin_name)
        p_name = get_plugin_config_value('name', plugin_name)
        target = get_plugin_config_value('target', plugin_name)
        display_hide = get_plugin_config_value('display_hide', plugin_name)  # 👈 new

        # If display_hide == true → skip
        if str(display_hide).lower() == 'true':
            continue

        try:
            sorder = int(sorder)
        except (TypeError, ValueError):
            sorder = 9999

        plugin_list.append({
            'name': p_name or plugin_name,
            'icon': icon or '',
            'url': url or '#',
            'sorder': sorder,
            'target': target,
        })
        
        
    for plugin in plugin_links:
        # Skip hidden JSON entries
        if str(plugin.get('display_hide', '')).lower() == 'true':
            continue

        plugin_list.append({
            'name': plugin.get('name', ''),
            'icon': plugin.get('icon', ''),
            'url': plugin.get('url') or plugin.get('url', '#'),
            'sorder': plugin.get('order', plugin.get('sorder', 9999)),
            'target': plugin.get('target', ''),
        })
        
        
    # Add static plugins
    plugin_list.extend([
        {
            'name': 'List Users',
            'icon': '/media/icon/users.svg',
            'url': reverse('user_list_all'),
            'sorder': 1,
        },
        {
            'name': 'Add User',
            'icon': '/media/icon/person_add.svg',
            'url': reverse('add_user_all'),
            'sorder': 2,
        },
        {
            'name': 'Add Package',
            'icon': '/media/icon/package.svg',
            'url': reverse('new_package'),
            'sorder': 3,
        },
        
        {
            'name': 'Package',
            'icon': '/media/icon/package.svg',
            'url': reverse('package_list'),
            'sorder': 4,
        },
    ])

    binary_path = "/usr/local/bin/olspanelcp"
    if os.path.isfile(binary_path) and os.access(binary_path, os.X_OK):
        plugin_list.append({
            'name': 'Resource limits',
            'icon': '/media/icon/cpu.svg',
            'url': reverse('user_limit'),
            'sorder': 5,
          
        })
        
        
        
    plugin_list.sort(key=lambda x: x['sorder'])

    return plugin_list


def get_database_plugins_list():
    plugin_type = 'database'
   
    plugin_names = get_all_plugin_names(plugin_type, plugin_role)
    plugin_links = get_all_plugin_link(plugin_type, plugin_role)
    plugin_list = []

    # Add dynamic plugins
    for plugin_name in plugin_names:
        icon = get_plugin_config_value('icon', plugin_name)
        url = get_plugin_config_value('url', plugin_name)
        sorder = get_plugin_config_value('sorder', plugin_name)
        p_name = get_plugin_config_value('name', plugin_name)
        target = get_plugin_config_value('target', plugin_name)
        display_hide = get_plugin_config_value('display_hide', plugin_name)  # 👈 new

        # If display_hide == true → skip
        if str(display_hide).lower() == 'true':
            continue

        try:
            sorder = int(sorder)
        except (TypeError, ValueError):
            sorder = 9999

        plugin_list.append({
            'name': p_name or plugin_name,
            'icon': icon or '',
            'url': url or '#',
            'sorder': sorder,
            'target': target,
        })
        
    for plugin in plugin_links:
        # Skip hidden JSON entries
        if str(plugin.get('display_hide', '')).lower() == 'true':
            continue

        plugin_list.append({
            'name': plugin.get('name', ''),
            'icon': plugin.get('icon', ''),
            'url': plugin.get('url') or plugin.get('url', '#'),
            'sorder': plugin.get('order', plugin.get('sorder', 9999)),
            'target': plugin.get('target', ''),
        })
        
    # Add static plugins
    plugin_list.extend([
    
    {
        'name': 'PhpMyAdmin',
        'icon': '/media/icon/user.svg',
        'url': reverse('phpmyadmins'),
        'sorder': 1,
        'target': '_blank',
    }
    ])
    
   



    plugin_list.sort(key=lambda x: x['sorder'])

    return plugin_list



def get_domain_plugins_list():
    plugin_type = 'domain'
    
    plugin_names = get_all_plugin_names(plugin_type, plugin_role)
    plugin_links = get_all_plugin_link(plugin_type, plugin_role)
    plugin_list = []

    # Add dynamic plugins
    for plugin_name in plugin_names:
        icon = get_plugin_config_value('icon', plugin_name)
        url = get_plugin_config_value('url', plugin_name)
        sorder = get_plugin_config_value('sorder', plugin_name)
        p_name = get_plugin_config_value('name', plugin_name)
        target = get_plugin_config_value('target', plugin_name)
        display_hide = get_plugin_config_value('display_hide', plugin_name)  # 👈 new

        # If display_hide == true → skip
        if str(display_hide).lower() == 'true':
            continue

        try:
            sorder = int(sorder)
        except (TypeError, ValueError):
            sorder = 9999

        plugin_list.append({
            'name': p_name or plugin_name,
            'icon': icon or '',
            'url': url or '#',
            'sorder': sorder,
            'target': target,
        })
        
        
    for plugin in plugin_links:
        # Skip hidden JSON entries
        if str(plugin.get('display_hide', '')).lower() == 'true':
            continue

        plugin_list.append({
            'name': plugin.get('name', ''),
            'icon': plugin.get('icon', ''),
            'url': plugin.get('url') or plugin.get('url', '#'),
            'sorder': plugin.get('order', plugin.get('sorder', 9999)),
            'target': plugin.get('target', ''),
        })
        
        
    # Add static plugins
    plugin_list.extend([
        {
            'name': 'Domains',
            'icon': '/media/icon/domain.svg',
            'url': reverse('domain_list_all'),
            'sorder': 1,
        },
        {
            'name': 'DNS',
            'icon': '/media/icon/dns.svg',
            'url': reverse('dns_all'),
            'sorder': 2,
        }
    ])

    plugin_list.sort(key=lambda x: x['sorder'])

    return plugin_list


def get_file_plugins_list():
    plugin_type = 'file'
   
    plugin_names = get_all_plugin_names(plugin_type, plugin_role)
    plugin_links = get_all_plugin_link(plugin_type, plugin_role)
    plugin_list = []

    # Add dynamic plugins
    for plugin_name in plugin_names:
        icon = get_plugin_config_value('icon', plugin_name)
        url = get_plugin_config_value('url', plugin_name)
        sorder = get_plugin_config_value('sorder', plugin_name)
        p_name = get_plugin_config_value('name', plugin_name)
        target = get_plugin_config_value('target', plugin_name)
        display_hide = get_plugin_config_value('display_hide', plugin_name)  # 👈 new

        # If display_hide == true → skip
        if str(display_hide).lower() == 'true':
            continue

        try:
            sorder = int(sorder)
        except (TypeError, ValueError):
            sorder = 9999

        plugin_list.append({
            'name': p_name or plugin_name,
            'icon': icon or '',
            'url': url or '#',
            'sorder': sorder,
            'target': target,
        })
        
        
    for plugin in plugin_links:
        # Skip hidden JSON entries
        if str(plugin.get('display_hide', '')).lower() == 'true':
            continue

        plugin_list.append({
            'name': plugin.get('name', ''),
            'icon': plugin.get('icon', ''),
            'url': plugin.get('url') or plugin.get('url', '#'),
            'sorder': plugin.get('order', plugin.get('sorder', 9999)),
            'target': plugin.get('target', ''),
        })
        
        
        
    # Add static plugins
    plugin_list.extend([
    {
        'name': 'File Manager',
        'icon': '/media/icon/folder.svg',
        'url': reverse('user_file_manger'),
        'sorder': 1,
        'target': '_blank',
    },
    {
        'name': 'Backup Restore',
        'icon': '/media/icon/backup.svg',
        'url': reverse('backup_restore'),
        'sorder': 2,
    },
    {
        'name': 'Backup',
        'icon': '/media/icon/backup.svg',
        'url': reverse('backup_whm'),
        'sorder': 3,
    },
    ])


    plugin_list.sort(key=lambda x: x['sorder'])

    return plugin_list



def get_security_plugins_list():
    plugin_type = 'security'
   
    plugin_names = get_all_plugin_names(plugin_type, plugin_role)
    plugin_links = get_all_plugin_link(plugin_type, plugin_role)
    plugin_list = []

    # Add dynamic plugins
    for plugin_name in plugin_names:
        icon = get_plugin_config_value('icon', plugin_name)
        url = get_plugin_config_value('url', plugin_name)
        sorder = get_plugin_config_value('sorder', plugin_name)
        p_name = get_plugin_config_value('name', plugin_name)
        target = get_plugin_config_value('target', plugin_name)
        display_hide = get_plugin_config_value('display_hide', plugin_name)  # 👈 new

        # If display_hide == true → skip
        if str(display_hide).lower() == 'true':
            continue

        try:
            sorder = int(sorder)
        except (TypeError, ValueError):
            sorder = 9999

        plugin_list.append({
            'name': p_name or plugin_name,
            'icon': icon or '',
            'url': url or '#',
            'sorder': sorder,
            'target': target,
        })
        
    for plugin in plugin_links:
        # Skip hidden JSON entries
        if str(plugin.get('display_hide', '')).lower() == 'true':
            continue

        plugin_list.append({
            'name': plugin.get('name', ''),
            'icon': plugin.get('icon', ''),
            'url': plugin.get('url') or plugin.get('url', '#'),
            'sorder': plugin.get('order', plugin.get('sorder', 9999)),
            'target': plugin.get('target', ''),
        })
        
        
    # Add static plugins
    plugin_list.extend([
        {
            'name': 'SSL',
            'icon': '/media/icon/ssl.svg',
            'url': reverse('domain_list_ssl_all'),
            'sorder': 1,
        },
        {
            'name': 'CSF (Firewall)',
            'icon': '/media/icon/fire.svg',
            'url': reverse('configserver'),
            'sorder': 2,
        },
        {
            'name': 'UFW (Firewall)',
            'icon': '/media/icon/fire.svg',
            'url': reverse('ufw'),
            'sorder': 3,
        },
        {
            'name': 'Port (Firewall)',
            'icon': '/media/icon/port.svg',
            'url': reverse('firewall_port'),
            'sorder': 4,
        },
        {
            'name': 'ModSecurity',
            'icon': '/media/icon/modes.svg',
            'url': reverse('mode_sec'),
            'sorder': 5,
        },
        {
            'name': 'Panel Port',
            'icon': '/media/icon/admin_panel.svg',
            'url': reverse('panel_port'),
            'sorder': 6,
        },
        {
            'name': 'SSH Port',
            'icon': '/media/icon/ssh.svg',
            'url': reverse('ssh_port'),
            'sorder': 7,
        },
        
        {
            'name': 'Password',
            'icon': '/media/icon/password.svg',
            'url': reverse('whm_password_change'),
            'sorder': 10,
        },   
        {
            'name': 'Two-Factor',
            'icon': '/media/icon/2fa.svg',
            'url': reverse('whm_google_otp'),
            'sorder': 11,
        },
        {
            'name': 'Passkeys',
            'icon': '/media/icon/passkey.svg',
            'url': reverse('whm_passkeys'),
            'sorder': 12,
        },
    ])


    


    plugin_list.sort(key=lambda x: x['sorder'])

    return plugin_list



def get_server_plugins_list():
    plugin_type = 'server'
   
    plugin_names = get_all_plugin_names(plugin_type, plugin_role)
    plugin_links = get_all_plugin_link(plugin_type, plugin_role)
    plugin_list = []

    # Add dynamic plugins
    for plugin_name in plugin_names:
        icon = get_plugin_config_value('icon', plugin_name)
        url = get_plugin_config_value('url', plugin_name)
        sorder = get_plugin_config_value('sorder', plugin_name)
        p_name = get_plugin_config_value('name', plugin_name)
        target = get_plugin_config_value('target', plugin_name)
        display_hide = get_plugin_config_value('display_hide', plugin_name)  # 👈 new

        # If display_hide == true → skip
        if str(display_hide).lower() == 'true':
            continue

        try:
            sorder = int(sorder)
        except (TypeError, ValueError):
            sorder = 9999

        plugin_list.append({
            'name': p_name or plugin_name,
            'icon': icon or '',
            'url': url or '#',
            'sorder': sorder,
            'target': target,
        })
        
    for plugin in plugin_links:
        # Skip hidden JSON entries
        if str(plugin.get('display_hide', '')).lower() == 'true':
            continue

        plugin_list.append({
            'name': plugin.get('name', ''),
            'icon': plugin.get('icon', ''),
            'url': plugin.get('url') or plugin.get('url', '#'),
            'sorder': plugin.get('order', plugin.get('sorder', 9999)),
            'target': plugin.get('target', ''),
        })
    
    
    
    # Add static plugins
    plugin_list.extend([
        {
            'name': 'Services',
            'icon': '/media/icon/pc.svg',
            'url': reverse('services'),
            'sorder': 1,
        },
        {
            'name': 'Process Manager',
            'icon': '/media/icon/memory.svg',
            'url': reverse('process_manager'),
            'sorder': 2,
        },
        {
            'name': 'Time Zone',
            'icon': '/media/icon/timezone.svg',
            'url': reverse('time_zone'),
            'sorder': 3,
        },
        {
            'name': 'Restart',
            'icon': '/media/icon/reboot.svg',
            'url': reverse('reboot_server'),
            'sorder': 4,
        },
        {
            'name': 'Change Hostname',
            'icon': '/media/icon/domain.svg',
            'url': reverse('change_hostname'),
            'sorder': 5,
        },
        {
            'name': 'System Statistics',
            'icon': '/media/icon/memory.svg',
            'url': reverse('system_status_view'),
            'sorder': 6,
        },
    ])





    plugin_list.sort(key=lambda x: x['sorder'])

    return plugin_list



def get_email_plugins_list():
    plugin_type = 'email'
   
    plugin_names = get_all_plugin_names(plugin_type, plugin_role)
    plugin_links = get_all_plugin_link(plugin_type, plugin_role)
    plugin_list = []

    # Add dynamic plugins
    for plugin_name in plugin_names:
        icon = get_plugin_config_value('icon', plugin_name)
        url = get_plugin_config_value('url', plugin_name)
        sorder = get_plugin_config_value('sorder', plugin_name)
        p_name = get_plugin_config_value('name', plugin_name)
        target = get_plugin_config_value('target', plugin_name)
        display_hide = get_plugin_config_value('display_hide', plugin_name)  # 👈 new

        # If display_hide == true → skip
        if str(display_hide).lower() == 'true':
            continue

        try:
            sorder = int(sorder)
        except (TypeError, ValueError):
            sorder = 9999

        plugin_list.append({
            'name': p_name or plugin_name,
            'icon': icon or '',
            'url': url or '#',
            'sorder': sorder,
            'target': target,
        })
        
    for plugin in plugin_links:
        # Skip hidden JSON entries
        if str(plugin.get('display_hide', '')).lower() == 'true':
            continue

        plugin_list.append({
            'name': plugin.get('name', ''),
            'icon': plugin.get('icon', ''),
            'url': plugin.get('url') or plugin.get('url', '#'),
            'sorder': plugin.get('order', plugin.get('sorder', 9999)),
            'target': plugin.get('target', ''),
        })
        
    # Add static plugins
    plugin_list.extend([
        {
            'name': 'Email Queue',
            'icon': '/media/icon/mail.svg',
            'url': reverse('email_queue'),
            'sorder': 1,
        }
    ])




    plugin_list.sort(key=lambda x: x['sorder'])

    return plugin_list



def get_php_plugins_list():
    plugin_type = 'php'
   
    plugin_names = get_all_plugin_names(plugin_type, plugin_role)
    plugin_links = get_all_plugin_link(plugin_type, plugin_role)
    plugin_list = []

    # Add dynamic plugins
    for plugin_name in plugin_names:
        icon = get_plugin_config_value('icon', plugin_name)
        url = get_plugin_config_value('url', plugin_name)
        sorder = get_plugin_config_value('sorder', plugin_name)
        p_name = get_plugin_config_value('name', plugin_name)
        target = get_plugin_config_value('target', plugin_name)
        display_hide = get_plugin_config_value('display_hide', plugin_name)  # 👈 new

        # If display_hide == true → skip
        if str(display_hide).lower() == 'true':
            continue

        try:
            sorder = int(sorder)
        except (TypeError, ValueError):
            sorder = 9999

        plugin_list.append({
            'name': p_name or plugin_name,
            'icon': icon or '',
            'url': url or '#',
            'sorder': sorder,
            'target': target,
        })
        
    for plugin in plugin_links:
        # Skip hidden JSON entries
        if str(plugin.get('display_hide', '')).lower() == 'true':
            continue

        plugin_list.append({
            'name': plugin.get('name', ''),
            'icon': plugin.get('icon', ''),
            'url': plugin.get('url') or plugin.get('url', '#'),
            'sorder': plugin.get('order', plugin.get('sorder', 9999)),
            'target': plugin.get('target', ''),
        })
        
    # Add static plugins
    plugin_list.extend([
        {
            'name': 'MultiPHP INI Editor',
            'icon': '/media/icon/php.svg',
            'url': reverse('multi_php_ini'),
            'sorder': 1,
        },
        {
            'name': 'MultiPHP Manager',
            'icon': '/media/icon/php.svg',
            'url': reverse('multi_php_manager_all'),
            'sorder': 2,
        },
        {
            'name': 'PHP Extension',
            'icon': '/media/icon/php.svg',
            'url': reverse('php_ext'),
            'sorder': 3,
        },
        {
            'name': 'PHP Version',
            'icon': '/media/icon/version.svg',
            'url': reverse('php_versions'),
            'sorder': 4,
        },
        {
            'name': 'PHP Modules',
            'icon': '/media/icon/php.svg',
            'url': reverse('php_modules'),
            'sorder': 5,
        },
    ])





    plugin_list.sort(key=lambda x: x['sorder'])

    return plugin_list

def get_node_plugins_list():
    plugin_type = 'node'
   
    plugin_names = get_all_plugin_names(plugin_type, plugin_role)
    plugin_links = get_all_plugin_link(plugin_type, plugin_role)
    plugin_list = []

    # Add dynamic plugins
    for plugin_name in plugin_names:
        icon = get_plugin_config_value('icon', plugin_name)
        url = get_plugin_config_value('url', plugin_name)
        sorder = get_plugin_config_value('sorder', plugin_name)
        p_name = get_plugin_config_value('name', plugin_name)
        target = get_plugin_config_value('target', plugin_name)
        display_hide = get_plugin_config_value('display_hide', plugin_name)  # 👈 new

        # If display_hide == true → skip
        if str(display_hide).lower() == 'true':
            continue

        try:
            sorder = int(sorder)
        except (TypeError, ValueError):
            sorder = 9999

        plugin_list.append({
            'name': p_name or plugin_name,
            'icon': icon or '',
            'url': url or '#',
            'sorder': sorder,
            'target': target,
        })
        
    for plugin in plugin_links:
        # Skip hidden JSON entries
        if str(plugin.get('display_hide', '')).lower() == 'true':
            continue

        plugin_list.append({
            'name': plugin.get('name', ''),
            'icon': plugin.get('icon', ''),
            'url': plugin.get('url') or plugin.get('url', '#'),
            'sorder': plugin.get('order', plugin.get('sorder', 9999)),
            'target': plugin.get('target', ''),
        })
        
    # Add static plugins
    plugin_list.extend([
        {
            'name': 'Node JS Versions',
            'icon': '/media/icon/version.svg',
            'url': reverse('node_versions'),
            'sorder': 1,
        },
        {
            'name': 'Node JS Modules',
            'icon': '/media/icon/node.svg',
            'url': reverse('node_module_manage'),
            'sorder': 2,
        },
    ])






    plugin_list.sort(key=lambda x: x['sorder'])

    return plugin_list


def get_advance_plugins_list():
    plugin_type = 'advance'
   
    plugin_names = get_all_plugin_names(plugin_type, plugin_role)
    plugin_links = get_all_plugin_link(plugin_type, plugin_role)
    plugin_list = []

    # Add dynamic plugins
    for plugin_name in plugin_names:
        icon = get_plugin_config_value('icon', plugin_name)
        url = get_plugin_config_value('url', plugin_name)
        sorder = get_plugin_config_value('sorder', plugin_name)
        p_name = get_plugin_config_value('name', plugin_name)
        target = get_plugin_config_value('target', plugin_name)
        display_hide = get_plugin_config_value('display_hide', plugin_name)  # 👈 new

        # If display_hide == true → skip
        if str(display_hide).lower() == 'true':
            continue
        try:
            sorder = int(sorder)
        except (TypeError, ValueError):
            sorder = 9999

        plugin_list.append({
            'name': p_name or plugin_name,
            'icon': icon or '',
            'url': url or '#',
            'sorder': sorder,
            'target': target,
        })
        
        
    for plugin in plugin_links:
        # Skip hidden JSON entries
        if str(plugin.get('display_hide', '')).lower() == 'true':
            continue

        plugin_list.append({
            'name': plugin.get('name', ''),
            'icon': plugin.get('icon', ''),
            'url': plugin.get('url') or plugin.get('url', '#'),
            'sorder': plugin.get('order', plugin.get('sorder', 9999)),
            'target': plugin.get('target', ''),
        })

        
    binary_path = "/usr/local/bin/olspanelcp"
    if os.path.isfile(binary_path) and os.access(binary_path, os.X_OK):
        plugin_list.append({
            'name': 'License',
            'icon': '/media/icon/license.svg',
            'url': reverse('license'),
            'sorder': 0,
          
        })
        plugin_list.append({
            'name': 'Branding',
            'icon': '/media/icon/panel_brand.svg',
            'url': reverse('panel_brand'),
            'sorder': 0,
          
        })

    # Add static plugins
    plugin_list.extend([
        {
            'name': 'Plugin',
            'icon': '/media/icon/extension.svg',
            'url': reverse('plugin'),
            'sorder': 0,
        },
        {
            'name': 'OlsApp',
            'icon': '/media/icon/softaculous.png',
            'url': reverse('olsapp_whm'),
            'sorder': 1,
        },
        {
            'name': 'Composer',
            'icon': '/media/icon/composer.png',
            'url': reverse('composer_whm'),
            'sorder': 2,
        },
    ])





    plugin_list.sort(key=lambda x: x['sorder'])

    return plugin_list

def get_configuration_plugins_list():
    plugin_type='configuration' 
   
    plugin_names = get_all_plugin_names(plugin_type, plugin_role)
    plugin_links = get_all_plugin_link(plugin_type, plugin_role)
    plugin_list = []

    # Add dynamic plugins
    for plugin_name in plugin_names:
        icon = get_plugin_config_value('icon', plugin_name)
        url = get_plugin_config_value('url', plugin_name)
        sorder = get_plugin_config_value('sorder', plugin_name)
        p_name = get_plugin_config_value('name', plugin_name)
        target = get_plugin_config_value('target', plugin_name)
        display_hide = get_plugin_config_value('display_hide', plugin_name)  # 👈 new

        # If display_hide == true → skip
        if str(display_hide).lower() == 'true':
            continue
            
            
        try:
            sorder = int(sorder)
        except (TypeError, ValueError):
            sorder = 9999

        plugin_list.append({
            'name': p_name,
            'icon': icon,
            'url': url,
            'sorder': sorder,
            'target': target,
        })
    for plugin in plugin_links:
        # Skip hidden JSON entries
        if str(plugin.get('display_hide', '')).lower() == 'true':
            continue

        plugin_list.append({
            'name': plugin.get('name', ''),
            'icon': plugin.get('icon', ''),
            'url': plugin.get('url') or plugin.get('url', '#'),
            'sorder': plugin.get('order', plugin.get('sorder', 9999)),
            'target': plugin.get('target', ''),
        })
        
    # Add static plugins
    plugin_list.extend([
        {
            'name': 'Settings',
            'icon': '/media/icon/settings.svg',
            'url': reverse('settings'),
            'sorder': 1,
        },
        {
            'name': 'LiteSpeed Tuning',
            'icon': '/media/icon/tune.svg',
            'url': reverse('litespeed_conf'),
            'sorder': 2,
        },
        {
            'name': 'PHP Limit',
            'icon': '/media/icon/php.svg',
            'url': reverse('php_tune'),
            'sorder': 3,
        },
        {
            'name': 'Error Logs',
            'icon': '/media/icon/error.svg',
            'url': reverse('php_error_whm'),
            'sorder': 4,
        },
    ])


    

    # Sort the plugins by 'sorder'
    plugin_list.sort(key=lambda x: x['sorder'])

    return plugin_list



def get_account_plugins_list():
    plugin_type='account' 
   
    plugin_names = get_all_plugin_names(plugin_type, plugin_role)
    plugin_links = get_all_plugin_link(plugin_type, plugin_role)
    plugin_list = []

    # Add dynamic plugins
    for plugin_name in plugin_names:
        icon = get_plugin_config_value('icon', plugin_name)
        url = get_plugin_config_value('url', plugin_name)
        sorder = get_plugin_config_value('sorder', plugin_name)
        p_name = get_plugin_config_value('name', plugin_name)
        target = get_plugin_config_value('target', plugin_name)
        display_hide = get_plugin_config_value('display_hide', plugin_name)  # 👈 new

        # If display_hide == true → skip
        if str(display_hide).lower() == 'true':
            continue
            
            
        try:
            sorder = int(sorder)
        except (TypeError, ValueError):
            sorder = 9999

        plugin_list.append({
            'name': p_name,
            'icon': icon,
            'url': url,
            'sorder': sorder,
            'target': target,
        })
    for plugin in plugin_links:
        # Skip hidden JSON entries
        if str(plugin.get('display_hide', '')).lower() == 'true':
            continue

        plugin_list.append({
            'name': plugin.get('name', ''),
            'icon': plugin.get('icon', ''),
            'url': plugin.get('url') or plugin.get('url', '#'),
            'sorder': plugin.get('order', plugin.get('sorder', 9999)),
            'target': plugin.get('target', ''),
        })
        
    # Add static plugins
    plugin_list.extend([
        {
            'name': 'Profile',
            'icon': '/media/icon/user.svg',
            'url': reverse('whm-profile'),
            'sorder': 1,
        },
        {
            'name': 'Logout',
            'icon': '/media/icon/logout.svg',
            'url': reverse('whm_logout'),
            'sorder': 2,
        },
    ])



    

    # Sort the plugins by 'sorder'
    plugin_list.sort(key=lambda x: x['sorder'])

    return plugin_list
    
    

def get_support_plugins_list():
    plugin_type = 'support'
    
    plugin_names = get_all_plugin_names(plugin_type, plugin_role)
    plugin_links = get_all_plugin_link(plugin_type, plugin_role)
    plugin_list = []

    # Add dynamic plugins
    for plugin_name in plugin_names:
        icon = get_plugin_config_value('icon', plugin_name)
        url = get_plugin_config_value('url', plugin_name)
        sorder = get_plugin_config_value('sorder', plugin_name)
        p_name = get_plugin_config_value('name', plugin_name)
        target = get_plugin_config_value('target', plugin_name)
        display_hide = get_plugin_config_value('display_hide', plugin_name)  # 👈 new

        # If display_hide == true → skip
        if str(display_hide).lower() == 'true':
            continue

        try:
            sorder = int(sorder)
        except (TypeError, ValueError):
            sorder = 9999

        plugin_list.append({
            'name': p_name or plugin_name,
            'icon': icon or '',
            'url': url or '#',
            'sorder': sorder,
            'target': target,
        })
        
        
    for plugin in plugin_links:
        # Skip hidden JSON entries
        if str(plugin.get('display_hide', '')).lower() == 'true':
            continue

        plugin_list.append({
            'name': plugin.get('name', ''),
            'icon': plugin.get('icon', ''),
            'url': plugin.get('url') or plugin.get('url', '#'),
            'sorder': plugin.get('order', plugin.get('sorder', 9999)),
            'target': plugin.get('target', ''),
        })
        
        
    # Add static plugins
    plugin_list.extend([
        {
            'name': 'About Us',
            'icon': '/media/icon/info.svg',
            'url': 'https://olspanel.com/about',
            'target': '_blank',
            'sorder': 100,
        },
        {
            'name': 'Contact Us',
            'icon': '/media/icon/support.svg',
            'url': 'https://olspanel.com/contact',
            'target': '_blank',
            'sorder': 101,
        },
        {
            'name': 'Community',
            'icon': '/media/icon/forum.svg',
            'url': 'https://community.olspanel.com/',
            'target': '_blank',
            'sorder': 102,
        },
        {
            'name': 'Release Log',
            'icon': '/media/icon/history.svg',
            'url': 'https://olspanel.com/release',
            'target': '_blank',
            'sorder': 103,
        },
        
        {
            'name': 'Pricing',
            'icon': '/media/icon/pricing.svg',
            'url': 'https://olspanel.com/pricing',
            'target': '_blank',
            'sorder': 104,
        },
        {
            'name': 'Documentation',
            'icon': '/media/icon/docs.svg',
            'url': 'https://olspanel.com/introduction',
            'target': '_blank',
            'sorder': 106,
        },
        {
            'name': 'Plugin Develop',
            'icon': '/media/icon/develop.svg',
            'url': 'https://olspanel.com/plugin_develop',
            'target': '_blank',
            'sorder': 107,
        },
        {
            'name': 'WHMCS Module',
            'icon': '/media/icon/whmcs.svg',
            'url': 'https://marketplace.whmcs.com/product/7967-olspanel',
            'target': '_blank',
            'sorder': 108,
        },
        {
            'name': 'API',
            'icon': '/media/icon/api.svg',
            'url': 'https://olspanel.com/api_documents',
            'target': '_blank',
            'sorder': 110,
        },
    ])

   
        
        
        
    plugin_list.sort(key=lambda x: x['sorder'])

    return plugin_list
    
