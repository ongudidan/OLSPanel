import requests
import os
import stat
import json
import subprocess
import binascii
import zipfile
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.views import View
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from users.forms import RegisterForm, LoginForm, UpdateUserForm, UpdateProfileForm
from users.forms import DomainForm
from users.models import * 
from users.server_core import *  # Import your function
from users.database import *  # Import your function
from django.db import connection
from users.function import *  # Import your function
from users.bandwidth import *  # Import your function
from django.contrib.auth.hashers import make_password
from ftplib import FTP, error_perm
from file_manager.function_file import *
from ftplib import FTP
from urllib.parse import urlparse
from django.contrib.auth import update_session_auth_hash, authenticate, logout
from django.conf import settings
from users.decorators import * 
from .decorators import * 

@csrf_exempt
@api_login_required
def home(request):
    username = request.user.username
    user_id = request.user.id
    email = request.user.email
    full_name = f"{request.user.first_name} {request.user.last_name}"

    disk = get_disk_usage(f'/home/{username}')
    email_disk = get_disk_usage(f'/home/vmail/{username}')
    db_count = count_users_by_prefix(username)

    user_package = Package.objects.filter(id=get_user_data_by_id(user_id).get('pkg_id')).first()
    database_names = get_user_database_info(username)
    total_db_size = calculate_total_database_size(database_names)

    domain_count = Domain.objects.filter(userid=user_id).count()
    email_count = Emails.objects.filter(userid=user_id).count()
    ftp_count = Ftps.objects.filter(userid=user_id).count()

    disk_bytes = human_readable_to_bytes(disk)
    email_bytes = human_readable_to_bytes(email_disk)
    total_bytes = disk_bytes + total_db_size + email_bytes

    server_ip = get_server_ip()
    main_domain_obj = Domain.objects.filter(userid=user_id).order_by('id').first()
    main_domain = main_domain_obj.domain if main_domain_obj else None

   

    if user_package:
        response = {
            'package_name': user_package.name,
            'disk_limit': check_limit(user_package.disk_space),
            'disk_used': size_display(total_bytes),
            'email_disk_used': email_disk,
            'db_disk_used': size_display(total_db_size),
            'email_limit': check_limit(user_package.email_accounts),
            'email_used': email_count,
            'db_limit': check_limit(user_package.databases),
            'db_used': db_count,
            'ftp_limit': check_limit(user_package.ftp_accounts),
            'ftp_used': ftp_count,
            'domain_limit': check_limit(user_package.allowed_domains),
            'domain_used': domain_count,
            'server_ip': server_ip,
            'main_domain': main_domain,
            'user_id': user_id,
            'email': email,
            'full_name': full_name,
        }
    else:
        response = {'error': 'Package not found'}

    return JsonResponse(response)
    


@csrf_exempt
@api_login_required
def add_domain(request):
    try:
        # Ensure user is authenticated
        if not request.user.is_authenticated:
            return JsonResponse({"success": False, "message": "Authentication required."}, status=200)

        username_string = request.user.username

        # Ensure username exists in DB
        if not User.objects.filter(username=username_string).exists():
            return JsonResponse({"success": False, "message": f"User '{username_string}' not found."}, status=404)

        domain_name = request.POST.get('domain', '').strip()
        php_name = request.POST.get('php_version', '').strip()
        path = request.POST.get('path', 'public_html').lstrip('/') or 'public_html'

        if not domain_name or not php_name:
            return JsonResponse({"success": False, "message": "Domain and PHP version are required."}, status=200)

        # Validate and normalize domain
        domain_name = normalize_domain(domain_name)
        if not domain_name:
            return JsonResponse({"success": False, "message": "Invalid domain format."}, status=200)

        parsed_url = urlparse(domain_name)
        hostname = parsed_url.hostname if parsed_url.hostname else domain_name
        domain_parts = hostname.split('.')
        domain_type = "domain"

        if len(domain_parts) > 2:
            main_domain = ".".join(domain_parts[-2:])
            domain_obj = Domain.objects.filter(domain=main_domain, userid=request.user).first()
            if domain_obj and domain_obj.id:
                domain_type = "subdomain"

        # Package & limits
        user_package = Package.objects.filter(
            id=get_user_data_by_id(request.user.id).get('pkg_id')
        ).first()
        total_domains_count = count_domains(domain_type, request.user.id)

        if Domain.objects.filter(domain=domain_name).exists():
            return JsonResponse({"success": False, "message": f"The domain '{domain_name}' already exists."}, status=200)

        if domain_type == 'domain' and user_package.allowed_domains != 0 and total_domains_count >= user_package.allowed_domains:
            return JsonResponse({"success": False, "message": "Domain add limit exceeded."}, status=200)

        if domain_type == 'subdomain' and user_package.allowed_subdomains != 0 and total_domains_count >= user_package.allowed_subdomains:
            return JsonResponse({"success": False, "message": "Subdomain add limit exceeded."}, status=200)

        doc_root = os.path.join("/home", username_string, path)

        # Listener mapping
        if not manage_listener_mapping("add", domain_name):
            return JsonResponse({"success": False, "message": f"Failed to add mapping for '{domain_name}'."}, status=200)

        # Virtual host
        if not manage_virtual_host(domain_name, username_string):
            return JsonResponse({"success": False, "message": f"Failed to add virtual host for '{domain_name}'."}, status=200)

        manage_ssl_listener_mapping("add", domain_name)
        create_vhost_file(domain_name, username_string, path)

        if not add_user_and_set_folder_permissions(username_string, f'/home/{username_string}', doc_root):
            return JsonResponse({"success": False, "message": f"Failed to set folder permissions for '{domain_name}'."}, status=200)

        # Save domain
        domain_instance = Domain(
            userid=request.user,
            domain=domain_name,
            path=f"/home/{username_string}/{path}",
            php=php_name,
            line=1
        )
        domain_instance.save()
        last_insert_id = domain_instance.id

        # DNS, PHP, DKIM setup
        new_php_version = php_name.replace('.', '')
        add_domain_dns(last_insert_id, domain_name, request.user.id)
        change_php_version(domain_name, domain_name + '' + new_php_version, new_php_version)
        setup_dkim(domain_name)
        insert_dkim_record(domain_name, last_insert_id, request.user.id)

        if domain_type == 'subdomain':
            server_ip = get_server_ip()
            if not Dns_record.objects.filter(domain_id=domain_obj.id, name=domain_name, content=server_ip, type="A").exists():
                Dns_record.objects.create(
                    name=domain_name,
                    content=server_ip,
                    type="A",
                    ttl=3600,
                    prio=0,
                    domain_id=domain_obj.id,
                    userid=request.user
                )

        restart_openlitespeed()
        restart_pdns()

        return JsonResponse({
            "success": True,
            "message": f"Domain '{domain_name}' added successfully!",
            "domain_id": last_insert_id
        })

    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=200)




@csrf_exempt
@api_login_required
def domain_list(request):
    domains = Domain.objects.filter(userid=request.user.id)

    # Manually build a list of dicts
    data = []
    for domain in domains:
        data.append({
            'id': domain.id,
            'domain': domain.domain,
            'path': domain.path,
        })

    return JsonResponse(data, safe=False)
 




@csrf_exempt
@api_login_required
def domain_issue_ssl(request):
    try:
        # Get domain from POST data
        domain_name = request.POST.get('domain', '').strip()
        if not domain_name:
            return JsonResponse({
                "success": False,
                "message": "Domain field is required."
            }, status=200)

        # Fetch the domain object for the authenticated user
        domain = Domain.objects.filter(domain=domain_name, userid=request.user).first()
        if not domain:
            return JsonResponse({
                "success": False,
                "message": f"Domain '{domain_name}' not found for this user."
            }, status=200)

        path = domain.path

        # Attempt to issue SSL certificate
        success = issue_ssl_certificate(domain_name, path)

        if success:
            restart_openlitespeed()
            return JsonResponse({
                "success": True,
                "message": f'SSL issued successfully for "{domain_name}".'
            })

        # Fallback: create self-signed SSL if issuance fails
        create_self_signed_ssl(domain_name)
        restart_openlitespeed()
        return JsonResponse({
            "success": False,
            "message": f'Failed to issue SSL for "{domain_name}", self-signed SSL created instead.'
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": str(e)
        }, status=200)


    
@csrf_exempt
@api_login_required
def db_make(request):
    username_string = request.user.username
    db_name = request.POST.get('dbname')
    db_user = request.POST.get('dbuser')
    db_pass = request.POST.get('dbpass')
    db_passc = request.POST.get('dbpassc')

    if not db_name:
        return JsonResponse({'success': False, 'error': 'Database name is required.'}, status=200)
    
    if len(db_name) < 2:
        return JsonResponse({'success': False, 'error': 'Database name must be at least 2 characters.'}, status=200)

    # Check DB limit
    user_data = get_user_data_by_id(request.user.id)
    user_package = Package.objects.filter(id=user_data.get('pkg_id')).first()
    db_count = count_users_by_prefix(username_string)

    if user_package and user_package.databases != 0 and db_count >= user_package.databases:
        return JsonResponse({'success': False, 'error': 'Database limit exceeded.'}, status=200)

    # Create the database
    db_success, db_error = create_database(username_string, db_name)
    if not db_success:
        return JsonResponse({'success': False, 'error': db_error}, status=200)

    # If db_user fields exist, create DB user too
    if db_user or db_pass or db_passc:
        if not db_user or not db_pass or not db_passc:
            return JsonResponse({'success': False, 'error': 'All database user fields are required.'}, status=200)

        if len(db_user) < 2:
            return JsonResponse({'success': False, 'error': 'DB user name must be at least 2 characters.'}, status=200)

        if len(db_pass) < 8:
            return JsonResponse({'success': False, 'error': 'Password must be at least 8 characters.'}, status=200)

        if db_pass != db_passc:
            return JsonResponse({'success': False, 'error': 'Passwords do not match.'}, status=200)

        result = create_database_and_user(request, username_string, db_name, db_user, db_pass)
        if result is not True:
            return JsonResponse({'success': False, 'error': result}, status=200)

    return JsonResponse({'success': True, 'message': 'Database and user created successfully.'})

    
@csrf_exempt
@api_login_required
def db_user_make(request):
    db = request.POST.get('db')
    db_user = request.POST.get('dbuser')
    db_pass = request.POST.get('dbpass')
    db_passc = request.POST.get('dbpassc')

    # Validate inputs
    if not all([db, db_user, db_pass, db_passc]):
        return JsonResponse({'success': False, 'error': 'All fields are required.'}, status=200)

    if len(db_user) < 2:
        return JsonResponse({'success': False, 'error': 'Username must be at least 2 characters long.'}, status=200)

    if len(db_pass) < 8:
        return JsonResponse({'success': False, 'error': 'Password must be at least 8 characters long.'}, status=200)

    if db_pass != db_passc:
        return JsonResponse({'success': False, 'error': 'Passwords do not match.'}, status=200)

    username_string = request.user.username

    # Attempt to create the user
    creation_result = create_database_and_user(request, username_string, db, db_user, db_pass)

    if creation_result is True:
        return JsonResponse({'success': True, 'message': 'Database user created successfully.'})
    else:
        return JsonResponse({'success': False, 'error': creation_result}, status=200)

@csrf_exempt
@api_login_required
def fix_user_permission(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'}, status=405)

    full_path = request.POST.get('full_path', '').strip()

    if not full_path.startswith('/home/'):
        return JsonResponse({'success': False, 'error': 'Invalid path: must start with /home/'}, status=200)

    parts = full_path.split('/')
    if len(parts) < 3:
        return JsonResponse({'success': False, 'error': 'Invalid path: cannot extract username'}, status=200)

    username_string = request.user.username
    base_home = f'/home/{username_string}'

    # Get the relative path after /home/username/
    relative_path = full_path[len(base_home):].lstrip('/')
    rebuilt_path = os.path.join(base_home, relative_path)

    result = add_user_and_set_folder_permissions(username_string, base_home, rebuilt_path)

    if result is True:
        restart_openlitespeed()
        return JsonResponse({'success': True, 'message': 'Permission successfully set.'})
    else:
        return JsonResponse({'success': False, 'error': result}, status=200)

    
@csrf_exempt
@api_login_required
def database_list(request, db=None):
    username = request.user.username
    databases = get_user_database_info(username)

    # Extract only the db_name
    db_names = [db_info.get('db_name') for db_info in databases]

    # Optional filter if a specific db is requested
    if db:
        db_names = [name for name in db_names if name == db]

    return JsonResponse({'databases': db_names})
    

@csrf_exempt
@api_login_required
def check_db_user(request):
    db_user = request.POST.get('db_user')  # or use POST if preferred

    if not db_user:
        return JsonResponse({'status': False})  # db_user param missing

    username = request.user.username

    exists = db_user_exists(username, db_user)

    return JsonResponse({'status': exists})


@csrf_exempt
@api_login_required
def database_exists(request):
    db = request.POST.get('db')  # or use POST if preferred

    if not db:
        return JsonResponse({'status': False})  # db_user param missing

    username = request.user.username

    exists = db_user_exists(username, db)

    return JsonResponse({'status': exists})
    

@csrf_exempt
@api_login_required
def database_userlist(request):
    username = request.user.username
    user_list = list_users_by_prefix(username)

    return JsonResponse({'users': user_list})


  
@csrf_exempt
@api_login_required
def db_edit(request, db):
    username_prefix = f"{request.user.username}_"
    username_string = request.user.username

    if not db.startswith(username_prefix):
        return JsonResponse({'error': 'You are not authorized to edit this database.'}, status=200)

    dbx = replace_first_with_underscore(db)

    if request.method != 'POST':
        return JsonResponse({'db_name': dbx, 'message': 'Send POST request with action (edit/delete) and data'}, status=200)

    try:
        body = request.POST or request.body
        if hasattr(body, 'decode'):  # if request.body (bytes), decode and parse
            import json
            body = json.loads(body.decode('utf-8'))
    except Exception:
        return JsonResponse({'error': 'Invalid JSON data.'}, status=200)

    action = body.get('action')

    if action == 'edit':
        db_name = body.get('dbname')

        if not db_name:
            return JsonResponse({'error': 'Database name cannot be empty.'}, status=200)

        if len(db_name) < 2:
            return JsonResponse({'error': 'Database name must be at least 2 characters long.'}, status=200)

        old_db_name = dbx
        success_message = rename_database(username_string, old_db_name, db_name)

        if "Error" in success_message:
            return JsonResponse({'error': success_message}, status=200)
        return JsonResponse({'success': success_message}, status=200)

    elif action == 'delete':
        success_message = delete_database(username_string, db)

        if "Error" in success_message:
            return JsonResponse({'error': success_message}, status=200)
        return JsonResponse({'success': success_message}, status=200)

    else:
        return JsonResponse({'error': 'Invalid action. Must be "edit" or "delete".'}, status=200)

    


   

@csrf_exempt
@api_login_required
def cronjob_list(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method is allowed.'}, status=200)

    username_string = request.user.username
    full_line = request.POST.get('value')

    if not full_line:
        return JsonResponse({'error': 'Line is required.'}, status=200)

    full_line = full_line.strip()
    cronjobs = parse_cron_jobs(username_string)

    for index, job in enumerate(cronjobs):
        job_line = f"{job['minute']} {job['hour']} {job['day']} {job['month']} {job['weekday']} {job['command']}".strip()
        if job_line == full_line:
            return JsonResponse({'line_number': job['line_number']}, status=200)

    return JsonResponse({'error': 'Cron job not found.'}, status=200)


@csrf_exempt
@api_login_required
def cronjob_add(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=200)

    minute = request.POST.get('minute')
    hour = request.POST.get('hour')
    day = request.POST.get('day')
    month = request.POST.get('month')
    weekday = request.POST.get('weekday')
    comm = request.POST.get('comm')

    # Validate inputs
    if not all([minute, hour, day, month, weekday, comm]):
        return JsonResponse({'success': False, 'error': 'All fields are required.'}, status=200)

    username_string = request.user.username
    cron_command = f"{minute} {hour} {day} {month} {weekday} {comm}"

    try:
        added = manage_cron_jobs(username_string, cron_command)
        if added:
            return JsonResponse({'success': True, 'message': 'Cron job added successfully.'})
        else:
            return JsonResponse({'success': False, 'error': 'Cron job already exists.'}, status=200)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=200)
    
    

    
    
@csrf_exempt
@api_login_required
def cronjob_delete(request, line):
    username_string = request.user.username

    success = delete_cron_job_by_line(username_string, line)

    if success:
        return JsonResponse({'success': 'Cron job deleted successfully!'}, status=200)
    else:
        return JsonResponse({
            'error': 'Failed to delete the cron job. Please check the line number or cron file.'
        }, status=200) 
    
        
            
