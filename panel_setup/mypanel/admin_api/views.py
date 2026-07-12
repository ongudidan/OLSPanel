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
from whm.decorators import * 
from whm.function import * 
from whm.models import * 

@csrf_exempt
@admin_api_login_required
def home(request):
    # Ensure POST method
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=200)

    username = request.POST.get('username')  # Get username from POST data
    if not username:
        return JsonResponse({'error': 'Username is required'}, status=200)

    # Look up the user
    try:
        user_obj = User.objects.get(username=username)
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=200)

    user_id = user_obj.id
    email = user_obj.email
    full_name = f"{user_obj.first_name} {user_obj.last_name}"

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
    
    bandwidth_total(username)
    current_month_year = datetime.now().strftime('%m-%Y')
    bandwidth = Bandwidth.objects.filter(userid=request.user.id, date=current_month_year).order_by('id').first()
    total = bandwidth.total if bandwidth else 0

    if user_package:
        response = {
            'package_name': user_package.name,
            'disk_limit': check_limit(user_package.disk_space),
            'disk_used': size_display(total_bytes),
            'email_disk_used': email_disk,
            'db_disk_used': size_display(total_db_size),
            'bandwidth': check_limit(user_package.bandwidth),
            'bandwidth_use': size_display(total),
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
@admin_api_login_required
def add_user(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST method required'}, status=200)

    # Get POST data
    data = request.POST
    username = data.get('username')
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    email = data.get('email')
    pkg_id = data.get('pkg_id')
    password = data.get('password')
    domain_name = data.get('domain')
    php_name = data.get('php_version')

    if not all([username, first_name, last_name, email, pkg_id, password, domain_name, php_name]):
        return JsonResponse({'success': False, 'message': 'All fields are required'}, status=200)

    # Check if username already exists
    if User.objects.filter(username=username).exists():
        return JsonResponse({'success': False, 'message': 'A username with the same name already exists'}, status=200)

    # Create new user
    hashed_password = make_password(password)
    new_user = User(
        username=username,
        first_name=first_name,
        last_name=last_name,
        email=email,
        password=hashed_password,
    )
    new_user.save()
    last_insert_id = new_user.id

    # Save additional metadata (package, FTP, domain, etc.)
    password_save_file(username, password)
    update_user_data(last_insert_id, {'pkg_id': pkg_id})

    try:
        package = Package.objects.get(id=pkg_id)
    except (Package.DoesNotExist, ValueError):
        return JsonResponse({'success': False, 'message': 'Invalid package ID'}, status=200)

    soft_limit = package.disk_space
    hard_limit = 0 if soft_limit == 0 else soft_limit + 200
    doc_root = f'/home/{username}'

    # set_disk_quota(username, doc_root, soft_limit, hard_limit)

    # Create domain
    result = make_domains(domain_name, php_name, username, 'public_html')
    if not result['success']:
        return JsonResponse({'success': False, 'message': result['message']}, status=200)

    # Setup FTP
    hashed_password_ftp = hash_password_crypt(password)
    uid, gid = get_uid_gid(username)
    new_ftp = Ftps(
        user=username,
        dir=doc_root,
        password=hashed_password_ftp,
        userid=last_insert_id,
        QuotaSize=0,
        uid=uid,
        gid=gid,
        status=1
    )
    new_ftp.save()

    # Create index.html
    home_base_dir = f'{doc_root}/public_html'
    create_index_file(home_base_dir)
    set_permissions_and_ownership(f'{home_base_dir}/index.html', username)

    return JsonResponse({
        'success': True,
        'message': f"User {username} created successfully",
        'user_id': last_insert_id
    })
 
 
 
@csrf_exempt
@admin_api_login_required
def suspend_user(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST method required'}, status=200)

    username = request.POST.get('username')
    state = request.POST.get('state')

    if not username or not state:
        return JsonResponse({'success': False, 'message': 'Username and state are required'}, status=200)

    state = state.upper()

    try:
        usr = User.objects.get(username=username)
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'message': f"User '{username}' does not exist."}, status=200)

    profile, created = Profile.objects.get_or_create(user=usr)
    ftp_accounts = Ftps.objects.filter(userid=usr.id)
    email_accounts = Emails.objects.filter(userid=usr.id)
    domains = Domain.objects.filter(userid=usr.id)
    emf = EmailForword.objects.filter(userid=usr.id)

    if state == 'SUSPEND':
        usr.is_active = False
        usr.save()
        if ftp_accounts.exists():
            ftp_accounts.update(status=0)
        if domains.exists():
            for domain in domains:
                vhost_action(domain.domain, 'suspend')
        restart_openlitespeed()
        return JsonResponse({'success': True, 'message': f"User '{username}' and all associated accounts/domains have been suspended."})

    elif state == 'UNSUSPEND':
        usr.is_active = True
        usr.save()
        if ftp_accounts.exists():
            ftp_accounts.update(status=1)
        if domains.exists():
            for domain in domains:
                vhost_action(domain.domain, 'restore')
        restart_openlitespeed()
        return JsonResponse({'success': True, 'message': f"User '{username}' and all associated accounts/domains have been unsuspended."})

    elif state == 'DELETE':
        if usr.is_active:
            return JsonResponse({'success': False, 'message': f"User '{username}' must be suspended before deletion."}, status=200)

        if ftp_accounts.exists():
            ftp_accounts.delete()
        if email_accounts.exists():
            email_accounts.delete()
        if emf.exists():
            emf.delete()

        database_names = get_user_database_info(usr.username)
        for database in database_names:
            delete_database(usr.username, database['db_name'])

        user_list = list_users_by_prefix(usr.username)
        for user_db in user_list:
            dbx = replace_first_with_underscore(user_db)
            delete_db_user_credentials(usr.username, dbx)

        if domains.exists():
            for domain in domains:
                vhost_action(domain.domain, 'delete')
                remove_map_from_httpd_config(domain.domain)
                remove_virtual_host_from_httpd_config(domain.domain)
                remove_domain_folder(domain.domain)
                delete_record(domain.domain)
            domains.delete()

        base_dir = f'/home/{usr.username}'
        if os.path.isdir(base_dir):
            shutil.rmtree(base_dir)
        maildir_path = f"/home/vmail/{usr.username}"
        if os.path.isdir(maildir_path):
            shutil.rmtree(maildir_path)

        usr.delete()
        restart_openlitespeed()
        return JsonResponse({'success': True, 'message': f"User '{username}' and all associated FTP, email accounts, and domains have been deleted."})

    else:
        return JsonResponse({'success': False, 'message': f"Unknown state '{state}'. Use SUSPEND, UNSUSPEND or DELETE."}, status=200)
 
 

@csrf_exempt
@admin_api_login_required
def update_user(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST method required'}, status=200)

    data = request.POST
    username = data.get('username')

    if not username:
        return JsonResponse({'success': False, 'message': 'Username is required'}, status=200)

    try:
        usr = User.objects.get(username=username)
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'message': f"User with username '{username}' not found."}, status=200)

    # Update fields if provided, else keep existing
    first_name = data.get('first_name') or usr.first_name
    last_name = data.get('last_name') or usr.last_name
    email = data.get('email') or usr.email
    pkg_id = data.get('pkg_id')
    password = data.get('password')

    usr.first_name = first_name
    usr.last_name = last_name
    usr.email = email
    if password:
        usr.password = make_password(password)
        password_save_file(username, password)

    usr.save()

    profile, created = Profile.objects.get_or_create(user=usr)
    profile.bio = profile.bio or ''
    profile.save()

    if pkg_id is not None:
        update_user_data(usr.id, {'pkg_id': pkg_id})

    return JsonResponse({
        'success': True,
        'message': f"User '{username}' updated successfully.",
        'user_id': usr.id
    })
 
 
 
@csrf_exempt
@admin_api_login_required
def packages_list(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST method required'}, status=200)

    packages = Package.objects.all()
    package_list = []
    for pkg in packages:
        package_list.append({
            'id': pkg.id,
            'name': pkg.name,
            'disk_space': pkg.disk_space,
            # add other relevant fields as needed
        })

    return JsonResponse({
        'success': True,
        'packages': package_list
    }, json_dumps_params={'indent': 2})
    
    
    
    

@csrf_exempt
@admin_api_login_required
def new_package(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST method required'}, status=200)

    data = request.POST
    name = data.get('name')
    disk_space = data.get('disk_space')
    bandwidth = data.get('bandwidth')
    email_accounts = data.get('email_accounts')
    databases = data.get('databases')
    ftp_accounts = data.get('ftp_accounts')
    allowed_domains = data.get('allowed_domains')
    allowed_subdomains = data.get('allowed_subdomains')
    limit_action = data.get('limit_action')

    # Validate required field
    if not name:
        return JsonResponse({'success': False, 'message': 'Package name is required'}, status=200)

    # Check if a package with the same name exists
    if Package.objects.filter(name=name).exists():
        return JsonResponse({'success': False, 'message': 'A package with the same name already exists.'}, status=200)

    # Create new package
    new_pk = Package(
        name=name,
        disk_space=disk_space or 0,
        bandwidth=bandwidth or 0,
        email_accounts=email_accounts or 0,
        databases=databases or 0,
        ftp_accounts=ftp_accounts or 0,
        allowed_domains=allowed_domains or 0,
        allowed_subdomains=allowed_subdomains or 0,
        enforce_disk_limits=limit_action or False,
    )
    new_pk.save()

    return JsonResponse({
        'success': True,
        'message': 'Package has been added successfully.',
        'package_id': new_pk.id
    })
    
 

@csrf_exempt
@admin_api_login_required
def issue_ssl(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST method required'}, status=200)

    domain_name = request.POST.get('domain')
    if not domain_name:
        return JsonResponse({'success': False, 'message': 'Domain name is required'}, status=200)

    try:
        domain_obj = Domain.objects.get(domain=domain_name)
    except Domain.DoesNotExist:
        return JsonResponse({'success': False, 'message': f"Domain '{domain_name}' not found."}, status=200)

    # Issue SSL
    success = issue_ssl_certificate(domain_obj.domain, domain_obj.path)

    if success:
        restart_openlitespeed()
        return JsonResponse({'success': True, 'message': f"SSL issued successfully for '{domain_name}'."})
    else:
        return JsonResponse({'success': False, 'message': f"Failed to issue SSL for '{domain_name}'."})
    
    

@csrf_exempt
@admin_api_login_required
def add_domain(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST method required'}, status=200)

    username = request.POST.get('username')
    domain_name = request.POST.get('domain')
    php_version = request.POST.get('php_version')
    path = request.POST.get('path', 'public_html').lstrip('/') or 'public_html'

    if not username or not domain_name or not php_version:
        return JsonResponse({
            "success": False,
            "message": "Username, domain, and php_version are required."
        }, status=200)

    # Validate user
    try:
        cuser = User.objects.get(username=username)
    except User.DoesNotExist:
        return JsonResponse({"success": False, "message": f"User '{username}' not found."}, status=200)

    # Normalize domain
    domain_name = normalize_domain(domain_name)
    if not domain_name:
        return JsonResponse({"success": False, "message": "Invalid domain format."}, status=200)

    # Check domain exists
    if Domain.objects.filter(domain=domain_name).exists():
        return JsonResponse({"success": False, "message": f"The domain '{domain_name}' already exists."}, status=200)

    # Check package limits
    user_package = Package.objects.filter(
        id=get_user_data_by_id(cuser.id).get('pkg_id')
    ).first()
    total_domains_count = Domain.objects.filter(userid=cuser.id).count()
    if user_package.allowed_domains != 0 and total_domains_count >= user_package.allowed_domains:
        return JsonResponse({"success": False, "message": "Domain add limit exceeded."}, status=200)

    doc_root = os.path.join("/home", username, path)

    # Add listener mapping
    if not manage_listener_mapping("add", domain_name):
        return JsonResponse({"success": False, "message": f"Failed to add mapping for '{domain_name}'."}, status=200)

    # Add virtual host
    if not manage_virtual_host(domain_name, username):
        return JsonResponse({"success": False, "message": f"Failed to add virtual host for '{domain_name}'."}, status=200)

    # SSL, vhost file, permissions
    manage_ssl_listener_mapping("add", domain_name)
    create_vhost_file(domain_name, username, path)

    if not add_user_and_set_folder_permissions(username, '/home/' + username, doc_root):
        return JsonResponse({"success": False, "message": f"Failed to set folder permissions for '{domain_name}'."}, status=200)

    # Save domain
    domain_instance = Domain(
        userid=cuser,
        domain=domain_name,
        path=f"/home/{username}/{path}",
        php=php_version,
        line=1
    )
    domain_instance.save()
    last_insert_id = domain_instance.id

    # DNS, PHP, DKIM
    add_domain_dns(last_insert_id, domain_name, cuser.id)
    new_php_version = php_version.replace('.', '')
    change_php_version(domain_name, domain_name + '' + new_php_version, new_php_version)
    setup_dkim(domain_name)
    insert_dkim_record(domain_name, last_insert_id, cuser.id)

    restart_openlitespeed()
    restart_pdns()

    return JsonResponse({
        "success": True,
        "message": f"Domain '{domain_name}' added successfully!",
        "domain_id": last_insert_id
    })
    
    
    
@csrf_exempt
@admin_api_login_required
def database_add(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST method required'}, status=200)

    # Get username from POST
    username_string = request.POST.get('username')
    db = request.POST.get('db')
    db_user = request.POST.get('dbuser')
    db_pass = request.POST.get('dbpass')
    db_passc = request.POST.get('dbpassc')

    # Validate inputs
    if not all([username_string, db, db_user, db_pass, db_passc]):
        return JsonResponse({'success': False, 'error': 'All fields are required.'}, status=200)

    # Check if the username exists
    try:
        user_obj = User.objects.get(username=username_string)
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': f"Username '{username_string}' does not exist."}, status=200)

    if len(db_user) < 2:
        return JsonResponse({'success': False, 'error': 'Database username must be at least 2 characters long.'}, status=200)

    if len(db_pass) < 8:
        return JsonResponse({'success': False, 'error': 'Password must be at least 8 characters long.'}, status=200)

    if db_pass != db_passc:
        return JsonResponse({'success': False, 'error': 'Passwords do not match.'}, status=200)

    # Attempt to create the database user
    creation_result = create_database_and_user(request, username_string, db, db_user, db_pass)

    if creation_result is True:
        return JsonResponse({'success': True, 'message': f'Database and user created successfully for {username_string}.'})
    else:
        return JsonResponse({'success': False, 'error': creation_result}, status=200)    
        
        
        
@csrf_exempt
@admin_api_login_required
def sso_login(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST method required'}, status=200)

    data = request.POST
    username = data.get('username')

    if not username:
        return JsonResponse({'success': False, 'message': 'Username is required'}, status=200)

    try:
        usr = User.objects.get(username=username)
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'message': f"User with username '{username}' not found."}, status=200)
    u_password = encode(get_auto_login_password(usr.username)) 
    json_data = {"user": usr.username, "api": u_password, "port": '0000'}
    encrypted_json = encode(json.dumps(json_data))
    create_sso_token(usr.id, encrypted_json)
    full_url = request.build_absolute_uri('/')
    parsed_url = urlparse(full_url)

    scheme = parsed_url.scheme     # "http" or "https"
    netloc = request.get_host()    # includes hostname + port if needed (e.g., example.com:8080)

    # Construct return URL
    return_url = f"{scheme}://{netloc}/login/?token={encrypted_json}"

    return JsonResponse({
        'success': True,
        'message': f"User '{username}' successfully genarate sso token.",
        'url': return_url
    })        