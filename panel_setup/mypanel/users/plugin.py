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
from .forms import RegisterForm, LoginForm, UpdateUserForm, UpdateProfileForm
from .forms import DomainForm
from .models import * 
from .server_core import *  # Import your function
from .database import *  # Import your function
from django.db import connection
from .function import *  # Import your function
from .bandwidth import *  # Import your function
from django.contrib.auth.hashers import make_password
from ftplib import FTP, error_perm
from file_manager.function_file import *
from ftplib import FTP
from urllib.parse import urlparse
from django.contrib.auth import update_session_auth_hash, authenticate, logout
from django.conf import settings
from .decorators import * 
from django.http import HttpResponse, FileResponse, Http404, HttpResponseRedirect
from mimetypes import guess_type
import re
from django.views.decorators.csrf import csrf_exempt
import http.cookies
from users.panellogger import *
import time
from http.cookies import SimpleCookie
from .php import *
from django.views.decorators.clickjacking import xframe_options_exempt


plugin_role = 'user_panel'


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
            'url': reverse('domain_list'),
            'sorder': 1,
        },
        {
            'name': 'Add Domain',
            'icon': '/media/icon/domain_add.svg',
            'url': reverse('users-domain'),
            'sorder': 2,
        },
        {
            'name': 'DNS',
            'icon': '/media/icon/dns.svg',
            'url': reverse('dns'),
            'sorder': 3,
        },
        {
            'name': 'Add Sub Domain',
            'icon': '/media/icon/sub_domain.svg',
            'url': reverse('sub_domain'),
            'sorder': 4,
        },
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
        'url': reverse('file_manager_home'),
        'sorder': 1,
        'target': '_blank',
    },
    {
        'name': 'FTP',
        'icon': '/media/icon/ftp.svg',
        'url': reverse('ftp_list'),
        'sorder': 2,
    },
    {
        'name': 'Backup',
        'icon': '/media/icon/backup.svg',
        'url': reverse('backup'),
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
        'url': reverse('domain_list_ssl'),
        'sorder': 1,
    },
    {
        'name': 'Custom SSL',
        'icon': '/media/icon/ssl.svg',
        'url': reverse('custom_ssl'),
        'sorder': 2,
    },
    {
        'name': 'Password',
        'icon': '/media/icon/password.svg',
        'url': reverse('password_change'),
        'sorder': 3,
    }
    ,
    {
        'name': 'Two-Factor',
        'icon': '/media/icon/2fa.svg',
        'url': reverse('google_otp'),
        'sorder': 4,
    },
    {
        'name': 'Passkeys',
        'icon': '/media/icon/passkey.svg',
        'url': reverse('users_passkeys'),
        'sorder': 5,
    },
    ])




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
        'name': 'MySQL Database',
        'icon': '/media/icon/database.svg',
        'url': reverse('database_list'),
        'sorder': 1,
    },
    {
        'name': 'MySQL Users',
        'icon': '/media/icon/user.svg',
        'url': reverse('database_userlist'),
        'sorder': 2,
    },
    {
        'name': 'Import',
        'icon': '/media/icon/database_upload.svg',
        'url': reverse('database_list_import', args=['im']),
        'sorder': 3,
    },
    {
        'name': 'Database Wizard',
        'icon': '/media/icon/databse_wizard.svg',
        'url': reverse('db_make'),
        'sorder': 4,
    },
    {
        'name': 'PhpMyAdmin',
        'icon': '/media/icon/user.svg',
        'url': reverse('phpmyadmin'),
        'sorder': 5,
        'target': '_blank',
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
            'name': 'Email account',
            'icon': '/media/icon/mail.svg',
            'url': reverse('email_accounts'),
            'sorder': 1,
        },
        {
            'name': 'Forwards',
            'icon': '/media/icon/mail_forward.svg',
            'url': reverse('email_forword_list'),
            'sorder': 2,
        },
        {
            'name': 'Email to pipe',
            'icon': '/media/icon/mail_pipe.svg',
            'url': reverse('email_pipe_list'),
            'sorder': 3,
        },
        {
            'name': 'Webmail',
            'icon': '/media/icon/webmail.svg',
            'url': reverse('webmail'),
            'sorder': 4,
            'target': '_blank',
        },
        {
            'name': 'Default Email',
            'icon': '/media/icon/mail.svg',
            'url': reverse('default_email_list'),
            'sorder': 5,
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

        

    # Add static plugins
    plugin_list.extend([
    {
        'name': 'Cronjob',
        'icon': '/media/icon/cronjob.svg',
        'url': reverse('cronjob_list'),
        'sorder': 1,
    },
    {
        'name': 'MultiPHP Manager',
        'icon': '/media/icon/php.svg',
        'url': reverse('multi_php_manager'),
        'sorder': 2,
    },
    {
        'name': 'MultiPHP INI Editor',
        'icon': '/media/icon/php.svg',
        'url': reverse('multi_php_ini_u'),
        'sorder': 3,
    },
    {
        'name': 'Visitor list',
        'icon': '/media/icon/public.svg',
        'url': reverse('visitor_list'),
        'sorder': 4,
    },
    {
        'name': 'Bandwidth',
        'icon': '/media/icon/chart.svg',
        'url': reverse('bandth'),
        'sorder': 5,
    },
    {
        'name': 'Error logs',
        'icon': '/media/icon/error.svg',
        'url': reverse('php_error'),
        'sorder': 6,
    },
    ])




    plugin_list.sort(key=lambda x: x['sorder'])

    return plugin_list

def get_software_plugins_list(softaculous):
    plugin_type='software' 
   
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
            'name': 'WordPress',
            'icon': '/media/icon/wordpress.png',
            'url': reverse('app_install_view', args=['wordpress']),
            'sorder': 1,
        },
        {
            'name': 'Joomla',
            'icon': '/media/icon/joomla.png',
            'url': reverse('app_install_view', args=['joomla']),
            'sorder': 2,
        },
        {
            'name': 'OlsApp Apps Installer',
            'icon': '/media/icon/softaculous.png',
            'url': reverse('olsapp_view'),
            'sorder': 3,
            'target': '_blank',
        },
        {
            'name': 'Node JS',
            'icon': '/media/icon/node.svg',
            'url': reverse('apps_list', args=['node_js']),
            'sorder': 4,
        },
        
        {
            'name': 'Composer',
            'icon': '/media/icon/composer.png',
            'url': reverse('composer_run'),
            'sorder': 5,
        },
    ])

    # Conditionally add Softaculous
    if softaculous == 'yes':
        plugin_list.append({
            'name': 'Softaculous',
            'icon': '/media/icon/softaculous.png',
            'url': reverse('softaculous_view'),
            'sorder': 5,
            'target': '_blank',
        })

    # Sort the plugins by 'sorder'
    plugin_list.sort(key=lambda x: x['sorder'])

    return plugin_list
