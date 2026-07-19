import os
import zipfile
import shutil
import platform
import ftplib
import json
from django.conf import settings
from django.utils.timezone import now
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.views import View
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from .models import * 
from users.models import * 
from .decorators import * 
from .function import * 
from users.server_core import *  # Import your function
from users.database import *  # Import your function
from django.db import connection
from users.function import *  # Import your function
from django.contrib.auth.hashers import make_password
from django.http import JsonResponse, FileResponse
from django.core.files.storage import FileSystemStorage
from users.forms import *
from django.contrib.auth.views import LoginView, PasswordResetView, PasswordChangeView
import subprocess
from django.views.decorators.clickjacking import xframe_options_exempt
from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from users.panellogger import *
from django.contrib.auth import update_session_auth_hash
from .plugin import * 
from django.http import StreamingHttpResponse
from file_manager.models import * 
from users.google_authenticator import GoogleAuthenticator
from django.utils import timezone
from datetime import datetime, timezone as dt_timezone
from users.decorators import * 


authenticator = GoogleAuthenticator()

logger = CpLogger()

@alogin_required
def home(request):
    
    ols_version = get_openlitespeed_version()
    os_f = f"{getattr(settings, 'MY_OS_NAME', 'linux')} {getattr(settings, 'MY_OS_VERSION', '0')}"
    load_avg = os.getloadavg()  # Retu
    load_avg_1 = round_to_two_decimals(load_avg[0])  # 1-minute load average
    load_avg_5 = round_to_two_decimals(load_avg[1])  # 5-minute load average
    load_avg_15 = round_to_two_decimals(load_avg[2]) 
    loadavg=f"{load_avg_1} {load_avg_5} {load_avg_15}"
    server_ip = get_server_ip()
    server_time = get_server_time()
    timezone = get_current_timezone()
    timenow=f"{server_time} ({timezone})"
    uptime = get_server_uptime()
    total_domain = Domain.objects.count()
    total_pkg = Package.objects.count()
    total_user = total_users
    total_dbx=total_db()
    hostname=get_hostname()
    current_version = getattr(settings, "VERSION", "0.0.0")
    update_file_path = os.path.join(settings.BASE_DIR, 'etc', 'update')
    if os.path.exists(update_file_path):
        with open(update_file_path, "r") as f:
            latest_version = f.read().strip()
        if version_tuple(latest_version) > version_tuple(current_version):
            update_available=True
        else:
            update_available=False
            
    else:
        latest_version=current_version
        update_available=False        
            
    modules = scan_module_templates("admin_home_top.html")           
    users_plugin = get_users_plugins_list()
    database_plugin = get_database_plugins_list()
    domain_plugin = get_domain_plugins_list()
    file_plugin = get_file_plugins_list()
    security_plugin = get_security_plugins_list()
    service_plugin = get_server_plugins_list()
    email_plugin = get_email_plugins_list()
    php_plugin = get_php_plugins_list()
    node_plugin = get_node_plugins_list()
    advance_plugin = get_advance_plugins_list()
    configuration_plugin = get_configuration_plugins_list()
    account_plugin = get_account_plugins_list()
     
    return render(request, 'whm/index.html',{'osz': os_f,
    'load': load_avg,
    'lite': ols_version,
    'ip': server_ip,
    'time': timenow,
    'uptime': uptime,
    'total_user': total_user,
    'total_domain': total_domain,
    'total_db': total_dbx,
    'total_pkg': total_pkg,
    'host_name': hostname,
    "update_available": update_available,
    "current_version": current_version,
    "latest_version": latest_version,
    'users_plugin': users_plugin,
    'database_plugin': database_plugin,
    'domain_plugin': domain_plugin,
    'file_plugin': file_plugin,
    'security_plugin': security_plugin,
    'service_plugin': service_plugin,
    'email_plugin': email_plugin,
    'php_plugin': php_plugin,
    'node_plugin': node_plugin,
    'advance_plugin': advance_plugin,
    'configuration_plugin': configuration_plugin,
    'account_plugin': account_plugin,
    'modules': modules
    
    })
  
@alogin_required
def update_check(request):
    check_for_update()
    current_version = getattr(settings, "VERSION", "0.0.0")
    update_file_path = os.path.join(settings.BASE_DIR, 'etc', 'update')
    if os.path.exists(update_file_path):
        with open(update_file_path, "r") as f:
            latest_version = f.read().strip()
        if version_tuple(latest_version) > version_tuple(current_version):
            update_available=True
        else:
            update_available=False    
    else:
        latest_version=current_version
        update_available=False
        

    return render(request, 'whm/version.html', {"update_available": update_available,
    "current_version": current_version,
    "latest_version": latest_version,})

@alogin_required
def install_update(request):
    
    try:
        install_panel_update()
        restart_openlitespeed()

        # Return success response
        response_data = {
            "status": "success",
            "message": f"Service updated successfully with ."
        }
        return JsonResponse(response_data, status=200)

    except Exception as e:
        # Handle errors and return error response
        return JsonResponse({"status": "error", "message": str(e)}, status=200)      
    
@alogin_required    
def system_status(request):
    # Get CPU, RAM, and Disk usage
    cpu_usage = get_cpu_usage()
    ram_usage = get_memory_usage()
    disk_usage = get_disk_usage_full()  # Assuming this returns a percentage string like "50%"

    # Function to safely convert to float and round to 2 decimal places
    

    # Round values to 2 decimal places, using 0 if the value is invalid
    cpu_usage = safe_round(cpu_usage)
    ram_usage = safe_round(ram_usage)
    disk_usage = process_percentage(disk_usage)  # Process the disk usage as a percentage
    load_avg = os.getloadavg()  # Retu

    # Return the data as a JSON response
    return JsonResponse({
        'cpu_percent': cpu_usage,
        'ram_percent': ram_usage,
        'disk_percent': disk_usage,
        'load_avg': load_avg,
    })
    
    
@alogin_required
def change_password_all(request):
    """
    Function-based view to handle password change with a custom form.
    """
    if request.method == 'POST':
        # Get form data from the request
        old_password = request.POST.get('old_password')
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')
        
        # Validate the old password
        user = authenticate(username=request.admin_user.username, password=old_password)
        if user is None:
            messages.error(request, "Your old password was entered incorrectly. Please enter it again.")
            return render(request, 'users/change_password.html')
        
        # Validate the new passwords
        if new_password1 != new_password2:
            messages.error(request, "The new passwords do not match. Please enter them again.")
            return render(request, 'users/change_password.html')
        
        if len(new_password1) < 6:
            messages.error(request, "The new password must be at least 6 characters long.")
            return render(request, 'users/change_password.html')
        
        # Update the user's password
        user.set_password(new_password1)
        user.save()
        
        # Update the session to prevent the user from being logged out
        update_session_auth_hash(request, user)
        
        # Save the new password to a file
        password_save_file(request.admin_user.username, new_password1)
        
        # Show a success message
        messages.success(request, "Successfully Changed Your Password")
        
        # Redirect to the success URL
        return redirect(reverse_lazy('users-home'))
    else:
        # Render the change password template for GET requests
        return render(request, 'whm/change_password.html')   

@alogin_required
def domain_list_all(request):
    all_users = User.objects.exclude(id=1)

    domains = Domain.objects.all()  # Start with all domains
    user_filter = ''
    search_query = ''

    if request.method == 'POST':
        search_query = request.POST.get('search', '').strip()
        user_filter = request.POST.get('user', '').strip()

        # Case 1: Both search and user selected
        if search_query and user_filter:
            domains = domains.filter(domain__icontains=search_query, userid=user_filter)

        # Case 2: Only search
        elif search_query:
            domains = domains.filter(domain__icontains=search_query)

        # Case 3: Only user
        elif user_filter:
            domains = domains.filter(userid=user_filter)

        # Else: nothing selected, domains = all
    binary_path = "/usr/local/bin/olspanelcp"
    if os.path.isfile(binary_path) and os.access(binary_path, os.X_OK):
        domain_pre = False
    else: 
        domain_pre = True
        
        
    return render(request, 'whm/domain_list.html', {
        'domains': domains,
        'allusers': all_users,
        'selected_user': user_filter,
        'search_query': search_query,
        'domain_pre': domain_pre
    })
 

@alogin_required
def domain_list_ssl_all(request):
    domains = []  # Initialize domains to avoid UnboundLocalError

    if request.method == 'POST':
        if 'search' in request.POST:
            search_query = request.POST.get('search', '')
            domains = Domain.objects.filter(domain__icontains=search_query)
        elif 'id' in request.POST:
            # Handle the task when 'id' is present in POST data
            rid = request.POST.get('id', '')
            domain_obj = Domain.objects.get(id=rid)  # Fetch the domain object by ID
            domain_name = domain_obj.domain
            path = domain_obj.path
            success = issue_ssl_certificate(domain_name, path)  # Using dynamic domain and path

            if success:
                restart_openlitespeed()
                messages.success(request, f'SSL issue for "{domain_name}" has been successful.')
            else:
                messages.error(request, f'Failed to issue SSL for "{domain_name}".')

            return redirect('/whm/domain_list_ssl_all')  # Redirect after the action completes

    else:
        domains = Domain.objects.all()

    if domains:

        new_domains = []

        for domain in domains:

            # main domain SSL
            ssl_details = get_ssl_details(domain.domain)

            domain.ssl = ssl_details['expiration_date']
            domain.type = ssl_details['certificate_validity']

            new_domains.append(domain)


            # create www / non-www version for display
            if domain.domain.startswith("www."):

                alt = domain.domain[4:]
                alt_id = str(domain.id)

            else:

                alt = "www." + domain.domain
                alt_id = "w"+str(domain.id)


            fake = Domain()

            fake.id = alt_id   # example 10w

            fake.domain = alt

            fake.path = domain.path

            ssl_details = get_ssl_details(alt)

            fake.ssl = ssl_details['expiration_date']

            fake.type = ssl_details['certificate_validity']

            new_domains.append(fake)


        domains = new_domains
            

    return render(request, 'whm/domain_list_ssl.html', {
        'domains': domains,
    })

 
@alogin_required
def domain_list_ssl_first_all(request, pk):
    # Fetch the domain based on the provided primary key (pk)
    pk = str(pk)
    if str(pk).startswith("w"):
        
        real_id = str(pk)[1:]   # remove w

        domain = get_object_or_404(Domain, pk=real_id)

        domain_name = "www." + domain.domain

    else:
        domain = get_object_or_404(Domain, pk=pk)
        domain_name = domain.domain
        
        
    path = domain.path

    # Call the function to issue the SSL certificate
    success = issue_ssl_certificate(domain_name, path)
    
    # Check if the SSL was issued successfully and return the appropriate message
    if success:
        restart_openlitespeed()  # Restart OpenLiteSpeed after issuing the SSL
        return HttpResponse(f'SSL issued for "{domain_name}" successfully.', content_type='text/plain')
    else:
        create_self_signed_ssl(domain_name)
        restart_openlitespeed()
        return HttpResponse(f'Failed to issue SSL for "{domain_name}".', content_type='text/plain')
 
@alogin_required
def add_domain(request):
    php_versions = get_php_versions()  # Fetch the PHP versions
    users = User.objects.exclude(id=1)
    if request.method == 'POST':
        form = DomainForm(request.POST)
        if form.is_valid():
            domain_name = form.cleaned_data['domain'].strip()  # Get the domain name and strip whitespace

            # Validate and normalize the domain name
            domain_name = normalize_domain(domain_name)

            if not domain_name:
                messages.error(request, "Invalid domain format. Please enter a valid domain.")
                return redirect('/whm/add_domain')

            php_name = request.POST.get('php_version')  # Get the PHP version from the form
            new_php_version = php_name.replace('.', '')
            username_string = request.POST.get('user')
            if not username_string:
                messages.error(request, "Invalid username.")
                return redirect('/whm/add_domain')
                
            cuser = User.objects.get(username=username_string)
            # Get the path from the form; default to 'public_html' if empty
            path = form.cleaned_data['path'].lstrip('/') or 'public_html'
            doc_root = os.path.join("/home", username_string, path)  # Construct the full path
            user_package = Package.objects.filter(id=get_user_data_by_id(cuser.id).get('pkg_id')).first()
            total_domains_count = Domain.objects.filter(userid=cuser.id).count()
            

            # Check if the domain already exists in the database
            if Domain.objects.filter(domain=domain_name).exists():
                messages.error(request, f"The domain '{domain_name}' already exists.")
                return redirect('/whm/add_domain')  # Redirect back to the form
                
            if user_package.allowed_domains != 0 and total_domains_count >= user_package.allowed_domains:
                messages.error(request, 'Domain add limit exceeded.')
                return redirect('/whm/add_domain')
                   
                

            # Manage the listener mapping
            success = manage_listener_mapping("add", domain_name)

            if success:  # Check if the listener mapping was successful
                vhost_success = manage_virtual_host(domain_name, username_string)  # Call to manage_virtual_host
                if vhost_success:  # Ensure the virtual host was added successfully
                    manage_ssl_listener_mapping("add", domain_name)
                    create_vhost_file(domain_name, username_string, path)

                    # Call to create the document root and set permissions
                    if add_user_and_set_folder_permissions(username_string, '/home/' + username_string, doc_root):
                        # Create Domain instance and save it to the database
                        domain_instance = form.save(commit=False)  # Create a Domain instance without saving to DB yet
                        domain_instance.userid = request.admin_user  # Set the current user as the owner of the domain
                        domain_instance.path = f"/home/{username_string}/{path}"
                        domain_instance.php = php_name
                        domain_instance.line = 1
                        domain_instance.save()  # Save the instance to the database
                        last_insert_id = domain_instance.id
                        add_domain_dns(last_insert_id, domain_name,cuser.id)
                        change_php_version(domain_name, domain_name + '' + new_php_version, new_php_version)
                        setup_dkim(domain_name)
                        insert_dkim_record(domain_name,last_insert_id,cuser.id)
                        restart_openlitespeed()
                        restart_pdns()
                        messages.success(request, f"Domain '{domain_name}' added successfully!")
                    else:
                        messages.error(request, f"Failed to set folder permissions for '{domain_name}'.")
                else:
                    messages.error(request, f"Failed to add virtual host for '{domain_name}'.")
            else:
                messages.error(request, f"Failed to add mapping for '{domain_name}'.")

            return redirect('/whm/domain_list_all?id=' + str(last_insert_id))  # Redirect to a success page
    else:
        form = DomainForm()  # Initialize the form for GET requests

    return render(request, 'whm/domain.html', {'user_form': form, 'php_versions': php_versions, 'all_user' : users})
    


@alogin_required    
def domain_delete_all(request, pk):
    domain = get_object_or_404(Domain, pk=pk)
    
    # Check if the current user is the owner of the domain
    if domain.userid != request.admin_user:
        return redirect('domain_list')  # Redirect to home if not authorized
    
    if request.method == 'POST':
        # Remove the domain mapping from the HTTPD configuration
        success = remove_map_from_httpd_config(domain.domain)  # Update with actual config file path
        remove_virtual_host_from_httpd_config(domain.domain)
        remove_domain_folder(domain.domain)
        delete_record(domain.domain)
        domain.delete()  # Delete the domain from the database
        restart_pdns()
        messages.success(request, f'Domain "{domain.domain}" has been deleted successfully.')
        
        
        return redirect('/whm/domain_list_all')  # Redirect to the domain list after deletion
    
    # Render the confirmation delete page
    return render(request, 'whm/domain_confirm_delete.html', {'domain': domain})

    
@alogin_required
def domain_edit_all(request, pk):
    # Fetch the domain based on the provided primary key (pk) and check user
    domain = get_object_or_404(Domain, pk=pk)
    dm = User.objects.get(id=domain.userid_id)
    username_string = dm.username
    # If the domain's user ID doesn't match the current user, redirect to the domain list
    

    if request.method == 'POST':
        # Extract relevant path from form input
        relevant_path = request.POST['path']
        
        # Add back the base path
        base_path = f"/home/{username_string}/"
        full_path = base_path + relevant_path

        # Update the domain path and save it
        domain.path = full_path
        domain.save()
         
         # Update the virtual host configuration
        vhost_directory = get_vhost_directory(domain.domain)
        vhost_file_path = os.path.join(vhost_directory, "vhost.conf")
        replace_docroot_in_virtual_conf(vhost_file_path, full_path)
        add_user_and_set_folder_permissions(username_string, '/home/' + username_string, full_path)
        replace_le_webroot(domain.domain,full_path)
        restart_openlitespeed()


        # Display a success message after saving
        messages.success(request, f'Domain "{domain.domain}" has been updated successfully.')
        return redirect('/whm/domain_list_all')
    
    else:
        # Remove the base path from the existing domain path
        base_path = f"/home/{username_string}/"
        relevant_path = domain.path.replace(base_path, '', 1)
        
    return render(request, 'whm/edit_domain.html', {'domain': domain, 'relevant_path': relevant_path})  
    

    
@alogin_required
def dns_all(request):
    if request.method == 'POST':
        search_query = request.POST.get('search', '')
        # Use __icontains for case-insensitive partial match
        domains = Domain.objects.filter(domain__icontains=search_query)
    else:
        domains = Domain.objects.all()

    return render(request, 'whm/dns.html', {'domains': domains})


@alogin_required
def dns_list_all(request,rid):
    if request.method == 'POST':
        search_query = request.POST.get('search', '')
        # Use __icontains for case-insensitive partial match
        dnss = Dns_record.objects.filter( name__icontains=search_query,domain_id=rid)
    else:
        dnss = Dns_record.objects.filter(domain_id=rid)

    return render(request, 'whm/dns_list.html', {'dnss': dnss,'rid': rid})


@alogin_required
def dns_edit_all(request, rid):
    # Fetch the DNS record based on the provided id (rid) and ensure it belongs to the logged-in user
    dns = get_object_or_404(Dns_record, id=rid)

    # Check if the record belongs to the current user
    if dns.userid != request.admin_user:
        return redirect('/whm/dns')

    if request.method == 'POST':
        # Extract form input
        dns_name = request.POST.get('dns_name')
        dns_value = request.POST.get('dns_value')
        ptype = request.POST.get('type')
        ttl = request.POST.get('ttl')
        prio = request.POST.get('prio', 0)  # prio might be optional if not an MX record

        # Check if a record with the same name and content already exists in the same domain
        if Dns_record.objects.filter(domain_id=dns.domain_id, name=dns_name, content=dns_value,type=ptype).exclude(id=rid).exists():
            messages.error(request, 'A DNS record with the same name and content already exists in this domain.')
            return redirect('/dns_edit', rid=rid)  # Redirect back to the edit page

        # Update DNS fields
        dns.name = dns_name
        dns.content = dns_value
        dns.type = ptype
        dns.ttl = ttl

        # Handle 'prio' field if the DNS type is MX
       
        dns.prio = prio

        # Save the updated DNS record
        dns.save()

        # Display a success message after saving
        messages.success(request, 'DNS record has been updated successfully.')
        return redirect(f'/whm/dns/list/{dns.domain_id}')

    return render(request, 'whm/dns_record_edit.html', {'dns': dns})
    
    
@alogin_required
def dns_delete_all(request, rid):
    # Fetch the DNS record based on the provided id (rid) and ensure it belongs to the logged-in user
    dns = get_object_or_404(Dns_record, id=rid)

    # Check if the record belongs to the current user
    if dns.userid != request.admin_user:
        return redirect('/whm/dns')

    if request.method == 'POST':
        # Delete the DNS record
        dns.delete()

        # Display a success message after deletion
        messages.success(request, 'DNS record has been deleted successfully.')

        # Redirect to the list page after deletion
        return redirect(f'/whm/dns/list/{dns.domain_id}')   


@alogin_required
def dns_create_all(request, domain_id=None):
    # Handle form submission
    if request.method == 'POST':
        dns_name = request.POST.get('dns_name')
        dns_value = request.POST.get('dns_value')

        # Check if domain_id is provided, if not get it from the POST data
        if domain_id is None:
            domain_id = request.POST.get('id')

        dm = Domain.objects.get(id=domain_id)
        ptype = request.POST.get('type')  # Fix indentation here
        ttl = request.POST.get('ttl')
        prio = request.POST.get('prio', 0)  # Optional for non-MX types
        
        # Check if a record with the same name, content, and type already exists in the domain
        if Dns_record.objects.filter(domain_id=domain_id, name=dns_name, content=dns_value, type=ptype).exists():
            messages.error(request, 'A DNS record with the same name and content already exists in this domain.')
            return redirect(f'/whm/dns/list/{domain_id}')

        # Create a new DNS record
        new_dns = Dns_record(
            name=dns_name,
            content=dns_value,
            type=ptype,
            ttl=ttl,
            prio=prio,
            domain_id=domain_id,
            userid=dm.userid
        )
        new_dns.save()

        # Display a success message and redirect to the list page
        messages.success(request, 'DNS record has been added successfully.')
        return redirect(f'/whm/dns/list/{domain_id}')

    return render(request, 'whm/dns_create.html', {'domain_id': domain_id})

    

@alogin_required
def user_list_all(request):
    # Initialize an empty users list
    users = []

    # Handle POST request for searching users
    if request.method == 'POST':
        search_query = request.POST.get('search', '')
        if search_query:
            # Use the get_user_data function to search for users based on username
            users = get_user_data('username', search_query)  # Get users matching the search query
    else:
        # For GET requests, fetch all users
        users = get_user_data()

    # If users are found, process them
    if users:
        for user in users:
            # Make sure pkg_id exists in the user data before fetching the Package
            if 'pkg_id' in user and user['pkg_id']:
                try:
                    pkg = Package.objects.get(id=user['pkg_id'])  # Fetch the package
                    user['pkg'] = pkg.name  # Add the package name to the user data
                    user['quota'] = pkg.disk_space 
                except Package.DoesNotExist:
                    user['pkg'] = 'Unknown'  # Handle case where the package does not exist
                    user['quota'] = 'Unknown' 
            else:
                user['pkg'] = 'Unknown'
                user['quota'] = 'Unknown' 
                
            username_string = user['username']   
           
            current_month_year = datetime.now().strftime('%m-%Y')
            bandwidth = Bandwidth.objects.filter(userid=user['id'], date=current_month_year).order_by('id').first()
            total = bandwidth.total if bandwidth else 0
            
            user['bandwidth_use'] = size_display(total)

            
                        
            user['main_domain'] = Domain.objects.filter(userid=user['id']).order_by('id').first()    

    # Render the user list template with the processed users data
    return render(request, 'whm/user_list.html', {'users': users})
 
 
@alogin_required
def disk_users_view(request):

    users = get_user_data()
    result = []

    if users:
        for user in users:

            username = user['username']

            disk = get_disk_usage(f'/home/{username}')
            email_disk = get_disk_usage(f'/home/vmail/{username}')

            disk_bytes = human_readable_to_bytes(disk)
            email_bytes = human_readable_to_bytes(email_disk)

            database_names = get_user_database_info(username)
            db_size = calculate_total_database_size(database_names)

            total_bytes = disk_bytes + email_bytes + db_size
            total_usage = size_display(total_bytes)

            result.append({
                "username": username,
                "total_usage": total_usage
            })

    return JsonResponse({
        "status": "success",
        "data": result
    })

 

@alogin_required
def add_user_all(request):
    pkg = Package.objects.all()
    php_versions = get_php_versions()  # Fetch the PHP versions
    
    # Handle form submission
    if request.method == 'POST':
        username = request.POST.get('username')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        pkg_id = request.POST.get('pkg_id')
        password = request.POST.get('password')
        domain_name = request.POST.get('domain')
        php_name = request.POST.get('php_version')
        
        
        # Check if a record with the same name, content, and type already exists in the domain
        if User.objects.filter(username=username).exists():
            messages.error(request, 'A username with the same name and content already exists.')
            return redirect(f'/whm/user_list_all/')
            
        hashed_password = make_password(password)    

        # Create a new DNS record
        new_user = User(
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=hashed_password,
            
        )
        new_user.save()
        password_save_file(username,password)
        last_insert_id = new_user.id
        create_database_common_user(username)
        update_fields = {
        'pkg_id': pkg_id
        }
        update_user_data(last_insert_id, update_fields)
        doc_root = os.path.join("/home", username)
        package = Package.objects.get(id=pkg_id)
        soft_limit = package.disk_space
        if soft_limit == 0:
            hard_limit = 0
        else:
            hard_limit = soft_limit + 200
            
        #set_disk_quota(username, doc_root, soft_limit, hard_limit)
       
        result = make_domain(domain_name, php_name, username, 'public_html')
        if not result['success']:
            messages.error(request, result['message'])
            return redirect(f'/whm/user_list_all')
            
            
        hashed_password = hash_password_crypt(password)
        base_dir = f'/home/{username}'
        uid, gid = get_uid_gid(username)
        new_ftp = Ftps(
            user=username,
            dir=base_dir,  # Use the correct field name
            password=hashed_password,  # Assuming you have a password field in the Emails model
            userid=last_insert_id,  # Assuming userid is a ForeignKey to the User model
            QuotaSize=0,  # Assuming you have a domain_id field in your Emails model
            uid=uid,
            gid=gid,
            status=1
        )
        new_ftp.save()
        home_base_dir = f'/home/{username}/public_html'
        create_index_file(home_base_dir)
        set_permissions_and_ownership(f'{home_base_dir}/index.html',username)
 
        if result['success']:
            messages.success(request, result['message'])
            #return redirect(f'/whm/user_list_all')
            
            return redirect(f"/whm/account_details/{last_insert_id}/")  # Redirect to a success page
        else: 
            messages.error(request, result['message'])
    
        



        # Display a success message and redirect to the list page
        #messages.success(request, 'User has been added successfully.')
        

    return render(request, 'whm/user_create.html', {'php_versions': php_versions, 'pkg': pkg})    

@alogin_required
def package_list(request):
    if request.method == 'POST':
        search_query = request.POST.get('search', '')
        # Use __icontains for case-insensitive partial match
        pkg = Package.objects.filter( name__icontains=search_query)
    else:
        pkg = Package.objects.all()

    return render(request, 'whm/pkg_list.html', {'package': pkg})
    
    
    
    
@alogin_required
def new_package(request):
   
    
    # Handle form submission
    if request.method == 'POST':
        name = request.POST.get('name')
        disk_space = request.POST.get('disk_space')
        bandwidth = request.POST.get('bandwidth')
        email_accounts = request.POST.get('email_accounts')
        databases = request.POST.get('databases')
        ftp_accounts = request.POST.get('ftp_accounts')
        allowed_domains = request.POST.get('allowed_domains')
        allowed_subdomains = request.POST.get('allowed_subdomains')
        limit_action = request.POST.get('limit_action')
        
        
        
        # Check if a record with the same name, content, and type already exists in the domain
        if Package.objects.filter(name=name).exists():
            messages.error(request, 'A Package with the same name and content already exists.')
            return redirect(f'/whm/package_list/')
            
         

        # Create a new DNS record
        new_pk = Package(
            name=name,
            disk_space=disk_space,
            bandwidth=bandwidth,
            email_accounts=email_accounts,
            databases=databases,
            ftp_accounts=ftp_accounts,
            allowed_domains=allowed_domains,
            allowed_subdomains=allowed_subdomains,
            enforce_disk_limits=limit_action,
            
            
        )
        new_pk.save()
        

        # Display a success message and redirect to the list page
        messages.success(request, 'Package has been added successfully.')
        return redirect('/whm/package_list/')
        

    return render(request, 'whm/new_package.html',{'title': 'Add'})    
    

@alogin_required
def update_package(request, rid):
    # Fetch the package to be updated
    pkg = get_object_or_404(Package, id=rid)
    
    if request.method == 'POST':
        # Retrieve form data
        name = request.POST.get('name')
        disk_space = request.POST.get('disk_space')
        bandwidth = request.POST.get('bandwidth')
        email_accounts = request.POST.get('email_accounts')
        databases = request.POST.get('databases')
        ftp_accounts = request.POST.get('ftp_accounts')
        allowed_domains = request.POST.get('allowed_domains')
        allowed_subdomains = request.POST.get('allowed_subdomains')
        limit_action = request.POST.get('limit_action')
        
        # Check if a package with the same name already exists (excluding the current package)
        if Package.objects.filter(name=name).exclude(id=rid).exists():
            messages.error(request, 'A package with the same name already exists.')
            return redirect('/whm/package_list/')
        
        # Update the package's fields
        pkg.name = name
        pkg.disk_space = disk_space
        pkg.bandwidth = bandwidth
        pkg.email_accounts = email_accounts
        pkg.databases = databases
        pkg.ftp_accounts = ftp_accounts
        pkg.allowed_domains = allowed_domains
        pkg.allowed_subdomains = allowed_subdomains
        pkg.enforce_disk_limits=limit_action
        pkg.save()

        # Display a success message and redirect to the package list
        messages.success(request, 'Package has been updated successfully.')
        return redirect('/whm/package_list/')
    
    # Render the form with existing package data
    return render(request, 'whm/new_package.html', {'pk': pkg,'title': 'Update'})

    
    

@alogin_required
def suspend_user(request, rid):
    # Retrieve the user to update
    usr = get_object_or_404(User, id=rid)
    profile, created = Profile.objects.get_or_create(user=usr)  # Ensure Profile exists
    ftp_accounts = Ftps.objects.filter(userid=usr.id)  # Retrieve all FTP accounts for this user
    email_accounts = Emails.objects.filter(userid=usr.id)  # Retrieve all email accounts for this user
    domains = Domain.objects.filter(userid=usr.id)  # Retrieve all domains for this user
    emf=EmailForword.objects.filter(userid=usr.id)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'suspend':
            usr.is_active = 0
            usr.save()

            # Suspend all FTP accounts
            if ftp_accounts.exists():
                ftp_accounts.update(status=0)  # Set all FTP accounts to inactive
            
            
            
            # Suspend all domains (using vhost_action)
            if domains.exists():
                for domain in domains:
                    vhost_action(domain.domain, 'suspend')  # Suspend the virtual host
                    
            restart_openlitespeed()
            messages.success(request, f'User {usr.username}, all associated FTP, email accounts, and domains have been suspended.')
        
        elif action == 'unsuspend':
            usr.is_active = 1
            usr.save()

            # Activate all FTP accounts
            if ftp_accounts.exists():
                ftp_accounts.update(status=1)  # Set all FTP accounts to active
            
            
            
            # Restore all domains (using vhost_action)
            if domains.exists():
                for domain in domains:
                    vhost_action(domain.domain, 'restore')  # Restore the virtual host
            
            # Optionally restart OpenLiteSpeed or web server
            restart_openlitespeed()
            
            messages.success(request, f'User {usr.username}, all associated FTP, email accounts, and domains have been unsuspended.')
        
        elif action == 'delete':
            # Check if user is suspended
            if usr.is_active == 1:
                messages.error(request, f'User {usr.username} must be suspended before deletion.')
            else:
                # Delete all associated FTP accounts
                if ftp_accounts.exists():
                    ftp_accounts.delete()
                
                # Delete all associated email accounts
                if email_accounts.exists():
                    email_accounts.delete()
                    
                if emf.exists():
                    emf.delete()
                    
                
                database_names = get_user_database_info(usr.username)
                for database in database_names:
                    delete_database(usr.username,database['db_name'])
                    
                user_list = list_users_by_prefix(usr.username)
                for user_db in user_list:
                    dbx = replace_first_with_underscore(user_db)
                    delete_db_user_credentials(usr.username, dbx)
                    
 
                
                # Delete all associated domains
                if domains.exists():
                    for domain in domains:
                        vhost_action(domain.domain, 'delete')  # Delete the virtual host
                        success = remove_map_from_httpd_config(domain.domain)  # Update with actual config file path
                        remove_virtual_host_from_httpd_config(domain.domain)
                        remove_domain_folder(domain.domain)
                        delete_record(domain.domain)
        
                    domains.delete()  # Delete domain records from the database
                    
                
                if usr.username:
                    # Delete the user's home directory
                    base_dir = f'/home/{usr.username}'
                    if os.path.isdir(base_dir):
                        shutil.rmtree(base_dir)
                        
                    
                    # Delete the user's mail directory
                    maildir_path = f"/home/vmail/{usr.username}"
                    if os.path.isdir(maildir_path):
                        shutil.rmtree(maildir_path)
                        

                
                BackupList.objects.filter(userid=usr.id).delete()
                usr.delete()
                restart_openlitespeed()
                messages.success(request, f'User {usr.username}, all associated FTP, email accounts, and domains have been deleted.')

        # Redirect after processing the action
        
        return redirect('/whm/user_list_all/')
    
    # Render form with the existing user data
    return render(request, 'whm/edit_user.html', {'usr': usr})




@alogin_required
def update_user(request, rid):
    # Retrieve the user to update
    usr = get_object_or_404(User, id=rid)
    profile, created = Profile.objects.get_or_create(user=usr)  # Ensure Profile exists
    packages = Package.objects.all()  # Fetch all packages

    # Fetch user data (assumes `get_user_data` returns a list of dictionaries)
    users = get_user_data('username', usr.username)
    for user in users:
        # Add package name to user data if `pkg_id` exists
        pkg_id = user.get('pkg_id')
        if pkg_id:
            try:
                package = Package.objects.get(id=pkg_id)
                user['pkg'] = package.name
            except Package.DoesNotExist:
                user['pkg'] = 'Unknown'
        else:
            user['pkg'] = 'Unknown'

    if request.method == 'POST':
        # Retrieve form data
        username = request.POST.get('username', usr.username)
        first_name = request.POST.get('first_name', usr.first_name)
        last_name = request.POST.get('last_name', usr.last_name)
        email = request.POST.get('email', usr.email)
        pkg_id = request.POST.get('pkg_id')
        password = request.POST.get('password', '')

        # Check if a username already exists (excluding the current user)
        if User.objects.filter(username=username).exclude(id=rid).exists():
            messages.error(request, 'A username with the same name already exists.')
            return redirect('/whm/user_list_all/')

        # Update user fields
        #usr.username = username
        usr.first_name = first_name
        usr.last_name = last_name
        usr.email = email
        if password:  # Update password only if provided
            usr.password = make_password(password)
            password_save_file(username, password)
        usr.save()

        # Update profile bio
        profile.bio = profile.bio or ''
        profile.save()

        # Update related fields (e.g., package or custom fields)
        update_fields = {'pkg_id': pkg_id}
        update_user_data(usr.id, update_fields)

        # Display a success message and redirect
        messages.success(request, 'User has been updated successfully.')
        return redirect('/whm/user_list_all/')

    # Render form with the existing user data
    return render(request, 'whm/edit_user.html', {
        'pkg': packages,
        'usr': usr,  # Pass the User instance
        'users': users,
        'pkg_id':pkg_id,
    })


@alogin_required
def auto_login_by_admin(request, rid):
    # Retrieve the user to update
    usr = get_object_or_404(User, id=rid)
    
    passw=get_auto_login_password(usr.username)
          

       
            

        # Authenticate the user
    user = authenticate(request, username=usr.username, password=passw)

    if user is not None:
        if request.admin_user.is_authenticated:
            logout(request)
            
            
        login(request, user)
        request.session.set_expiry(0)
        request.session.modified = True
        return redirect('/')  # Redirect to home or any desired page
    else:
        messages.warning(request, "Invalid username or password")
            #return redirect('/login')
            

    # Generate CSRF token for the for

    

    # Render form with the existing user data
    return render(request, 'whm/auto_login.html', {
        'username': usr.username,
        
        
    })
    
    
@alogin_required
def multi_php_manager_all(request):
    php_versions = get_php_versions()  # Fetch the PHP versions

    # Initialize the domain list
    domains = Domain.objects.all()

    # Handle POST request
    if request.method == 'POST':
        # Search functionality
        if 'search' in request.POST:
            search_query = request.POST.get('search', '')
            domains = Domain.objects.filter(domain__icontains=search_query)
        # PHP version update functionality
        elif 'php_version' in request.POST:
            php_version = request.POST.get('php_version', None)
            selected_domains = request.POST.getlist('selected_domains')

            # Validate PHP version and selected domains
            if php_version and selected_domains:
                new_php_version = php_version.replace('.', '')  # Format the version for OpenLiteSpeed
                # Update the PHP version for selected domains
                Domain.objects.filter(id__in=selected_domains).update(php=php_version)
                
                # Perform additional actions related to PHP version change
                for domain_id in selected_domains:
                    domain_name = Domain.objects.get(id=domain_id).domain  # Fetch the domain name by ID
                    change_php_version(domain_name, domain_name+'' + new_php_version, new_php_version)

                # Restart OpenLiteSpeed after the change, outside the loop
                restart_openlitespeed()
                messages.success(request, "Selected domains updated successfully.")
            else:
                messages.warning(request, "Please select at least one domain to update.")

            # Retrieve updated domain list after updates
            domains = Domain.objects.all()

    # Render the template with the current domain list and PHP versions
    return render(request, 'whm/multi_php_manager.html', {'domains': domains, 'php_versions': php_versions})  



@alogin_required
def multi_php_ini(request):
    # Fetch available PHP versions (implement this function to retrieve the versions)
    php_versions_only = get_php_versions() 
    php_cgi_versions = get_cgi_php_versions()
    php_versions = php_versions_only + [v for v in php_cgi_versions if v not in php_versions_only]
  
    current_settings = {}

    # Check if a PHP version is selected or posted
    php_version = request.POST.get('php_version')
    if php_version:
        if php_version.startswith('cgi'):
            new_php_version = php_version.replace('cgi ', '').replace('cgi', '').strip()
            ini_file_path = f'/etc/php/{new_php_version}/cgi/php.ini'
        else:         
            new_php_version = php_version.replace('.', '')
        # Define the path to the php.ini file for the selected PHP version
            ini_file_path = get_ini_path_fun(php_version)
            
            

    # Handle POST request for saving settings
    if request.method == 'POST' and php_version:
        new_settings = {
            'memory_limit': request.POST.get('memory_limit'),
            'upload_max_filesize': request.POST.get('upload_max_filesize'),
            'post_max_size': request.POST.get('post_max_size'),
            'max_execution_time': request.POST.get('max_execution_time'),
            'max_input_time': request.POST.get('max_input_time'),
            'allow_url_fopen': 'On' if request.POST.get('allow_url_fopen') else 'Off',
            'allow_url_include': 'On' if request.POST.get('allow_url_include') else 'Off',
            'display_errors': 'On' if request.POST.get('display_errors') else 'Off',
            'file_uploads': 'On' if request.POST.get('file_uploads') else 'Off',
        }
        try:
            if os.path.exists(ini_file_path):
                update_php_ini(ini_file_path, new_settings)
            
                
            messages.success(request, "Selected php updated successfully.")
        except Exception as e:
            messages.warning(request, f"Error: {str(e)}")
        return redirect('/whm/multi_php_ini/')
        
        
    return render(request, 'whm/multi_php_ini.html', {
        'php_versions': php_versions
    })

    
@alogin_required
def fetch_php_settings(request):
    # Get PHP version from the request
    php_version = request.GET.get('php_version')  
    if not php_version:
        return JsonResponse({'status': 'error', 'message': 'php_version missing'})
        
    data=fetch_php_settings_fun(php_version)    
    return JsonResponse(data)   
    
@alogin_required
def fetch_vhost(request):
    domain = request.GET.get('domain')

    if not domain:
        return JsonResponse({'status': 'error', 'message': 'Domain missing'})

    data = fetch_vhost_fun(domain)
    return JsonResponse(data) 


@alogin_required
def save_vhost(request):

    if request.method != "POST":
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

    domain = request.POST.get('domain')
    content = request.POST.get('content')

    if not domain or content is None:
        return JsonResponse({'status': 'error', 'message': 'Missing parameters'})

    result = save_vhost_fun(domain, content)

    return JsonResponse(result)
    
    
@alogin_required
def ini_editor(request):
    ini_file_path = None
    php_version = request.POST.get('php_version')
    
    if php_version:
        if php_version.startswith('cgi'):
            new_php_version = php_version.replace('cgi ', '').replace('cgi', '').strip()
            ini_file_path = f'/etc/php/{new_php_version}/cgi/php.ini'
        else:                
            ini_file_path = get_ini_path_fun(php_version)
    
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        if not ini_file_path:
            return JsonResponse({'status': 'error', 'message': 'Invalid PHP version or file path.'}, status=400)
        
        new_content = request.POST.get('content')
        if new_content is None:
            return JsonResponse({'status': 'error', 'message': 'No content provided.'}, status=400)
        
        try:
            if os.path.exists(ini_file_path):
                with open(ini_file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
            
                
            restart_lsphp()    
            return JsonResponse({'status': 'success', 'message': 'File saved successfully.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f"Error saving file: {str(e)}"}, status=500)

    # Handle GET request (optional, if required)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)



@alogin_required
def php_ext(request):
    php_versions_only = get_php_versions() 
    php_cgi_versions = get_cgi_php_versions()
    php_versions = php_versions_only + [v for v in php_cgi_versions if v not in php_versions_only]
    
    # Check for POST request to manage PHP extensions
    if request.method == 'POST':
        php_version = request.POST.get('php_version')
        extension = request.POST.get('extension')
        action = request.POST.get('action')

        if php_version and extension and action:
            # Call the manage_php_extension function for install/uninstall action
            result = manage_php_extension(php_version, extension, action)
            restart_lsphp()
            restart_openlitespeed()
            messages.success(request, result)
        else:
            messages.error(request, 'Failed.')
            
        return redirect('/whm/php_ext/')    

    # Render the template with the PHP versions
    return render(request, 'whm/php_ext.html', {'php_versions': php_versions})

@alogin_required
def php_ext_manage(request):
    php_versions = get_php_versions()  # Fetch PHP versions

    if request.method == 'POST':
        php_version = request.POST.get('php_version')
        extension = request.POST.get('extension')
        action = request.POST.get('action')

        if php_version and extension and action:
            # Perform install/uninstall action
            result = manage_php_extension(php_version, extension, action)
            restart_lsphp()
            restart_openlitespeed()
            return JsonResponse({'success': True, 'message': result})
        else:
            return JsonResponse({'success': False, 'message': 'Missing parameters.'})

    # GET request: render template
    return render(request, 'whm/php_ext.html', {'php_versions': php_versions})

@alogin_required
def php_ext_load(request):
    php_version = request.POST.get('php_version')
    extensions_status = fetch_php_extensions(php_version)

    return JsonResponse({
        'extensions_status': extensions_status,
        'selected_version': php_version,
    })

  
@alogin_required
def php_versions(request):
    # Full list of PHP versions
    all_php_versions = get_php_version_hard()
    
    # Get installed PHP versions
    installed_php_versions = get_php_versions() 

    # Compare installed versions with all available versions
    php_versions_status = {}
    for version in all_php_versions:
        if version in installed_php_versions:
            php_versions_status[version] = 'installed'
        else:
            php_versions_status[version] = 'uninstall'

    # Pass to template
    return render(request, 'whm/php_versions.html', {'php_versions_status': php_versions_status})
    
    
@alogin_required
def php_install_now(request):
    if request.method == "POST":
        php_version = request.POST.get('php_version')
        if php_version:
            extensions_status = install_php(php_version)
            message = extensions_status.get('message', 'Installation status not available')
            return JsonResponse({
                'status': extensions_status['status'],
                'message': message,
                'selected_version': php_version,
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'PHP version is required.'
            })
    
    
    
@alogin_required    
def services(request):
    
    os_name = getattr(settings, "MY_OS_NAME", "linux")
    if os_name == "ubuntu" or os_name == "debian":
        ftpserver = "pure-ftpd-mysql"
    else:
        ftpserver = "pure-ftpd"
        
    if os_name == "debian":
        openlitespeed = "lsws"
    else:
        openlitespeed = "openlitespeed"    
    
    services_to_check = {
        'mariadb': 'MariaDB',
        openlitespeed: 'OpenLiteSpeed',
        'pdns': 'DNS',
        'dovecot': 'IMAP',
        'postfix': 'Mail server',
        ftpserver: 'FTP Server',
        'opendkim': 'OpenDkim'
    }

    # Check the status of each service and create a dictionary with both custom names and statuses
    service_statuses = {
        custom_name: {
            'status': check_service_status(system_name),  # Get the service status
            'system_name': system_name  # Keep the system name for reference
        }
        for system_name, custom_name in services_to_check.items()
    }

    # Render the template with the services and their statuses
    return render(request, 'whm/services.html', {'services': service_statuses})

    
@alogin_required       
def service_action(request, service_name, action):
    
    result = service_operation(service_name, action)

    # Return the result as a JSON response
    return JsonResponse(result)    
  
  
@alogin_required       
def process_manager(request):
    
    process_list = get_process_list()  # Get process data from the main function
    return render(request, 'whm/processmanager.html', {
        'process': process_list,  # Pass the process data to the template
    })  
    
     
@alogin_required       
def kill_process(request):
    if request.method == 'POST':
        pid = request.POST.get('pid')
        try:
            os.kill(int(pid), 9)  # Send SIGKILL to the process
            return JsonResponse({'success': True, 'message': f'Process {pid} killed successfully.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})  

@alogin_required    
def reboot(request):
    
    if request.method == 'POST':
        reboot_type = request.POST.get('type', 'immediate')  # Default to immediate if type is not provided
        if reboot_type == 'graceful':
            success, message = reboot_server(graceful=True)
        else:
            success, message = reboot_server(graceful=False)
        return JsonResponse({'success': success, 'message': message})
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})

@alogin_required       
def reboot_view(request):
    
   
    return render(request, 'whm/reboot.html', {
       
    }) 


@alogin_required
def email_queue(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'flush':
            output, error = flush_queue()
            if error:
                messages.warning(request, f'Error flushing queue: {error}')
            else:
                messages.success(request, 'Queue flushed successfully.')
        
        elif action == 'delete_all':
            output, error = delete_all_emails()
            if error:
                messages.warning(request, f'Error deleting emails: {error}')
            else:
                messages.success(request, 'All emails deleted from the queue.')
        
        elif action == 'delete_email':
            email_id = request.POST.get('email_id')
            output, error = delete_email(email_id)
            if error:
                messages.warning(request, f'Error deleting email {email_id}: {error}')
            else:
                messages.success(request, f'Email {email_id} deleted successfully.')
    
    # Get the output from 'postqueue -p' command
    #output, error = get_queue_from_command()
    output = parse_postqueue()
    
        
    
    # Render the template with the parsed output
    return render(request, 'whm/email_queue.html', {'queue_data': output})
    
@alogin_required       
def csf_install(request):
    if request.method == "POST":
        current_port = get_single_listener_port()
        install_output = install_csf(current_port)
        
    return JsonResponse({'output': install_output}, status=200)
    
    
@alogin_required       
def csf_remove(request):
    if request.method == "POST":
        uninstall_result = uninstall_csf()  # No argument needed unless modified
        #messages.success(request, uninstall_result)  # optional: show success message
    
    return JsonResponse({'output': uninstall_result}, status=200)
    
    
@alogin_required       
def mod_install(request):
    if request.method == "POST":
        install_output = install_modsecurity_and_crs()
        restart_openlitespeed()
        
    return JsonResponse({'output': install_output["message"]}, status=200)    
    
@alogin_required
def configserver(request):
    #disable_test_mode_and_enable_restrict_syslog()
    
    if not check_csf_installed():
        print("CSF is not installed.")
        
        if request.method == "POST":
            # Attempt to install CSF when a POST request is made
            print("Attempting to install CSF...")
            current_port = get_single_listener_port()
            install_output = install_csf(current_port)  # Call the installation function
            print(f"Installation Output: {install_output}")
            return JsonResponse({'output': install_output}, status=200)
        
        # If GET request, render the installation page
        print("Rendering CSF installation page...")
        return render(request, 'whm/csf.html')
    
    # If CSF is already installed, render the CSF management page
    print("CSF is already installed. Rendering CSF management page...")
    return render(request, 'whm/csf_view.html')

@alogin_required
def ufw(request):
    #disable_test_mode_and_enable_restrict_syslog()
    
    if not check_csf_installed():
        csf ="no"
    else:
        csf ="yes"
        
    
    return render(request, 'whm/ufw.html',{'csf': csf})


@alogin_required
def firewall_port(request):
    
        
    if request.method == 'POST':
        # Retrieve values from POST request
        tcpin = request.POST.get('tcpin')
        tcpout = request.POST.get('tcpout')
        udpin = request.POST.get('udpin')
        udpout = request.POST.get('udpout')
        if check_csf_installed():
            replace_config_value('TCP_IN', tcpin)
            replace_config_value('TCP_OUT', tcpout)
            replace_config_value('UDP_IN', udpin)
            replace_config_value('UDP_OUT', udpout)
            
            #IPV6
            replace_config_value('TCP6_IN', tcpin)
            replace_config_value('TCP6_OUT', tcpout)
            replace_config_value('UDP6_IN', udpin)
            replace_config_value('UDP6_OUT', udpout)
        else:
            ufw_port_add('TCP_IN', tcpin)
            #ufw_port_add('TCP_OUT', tcpin)
            ufw_port_add('UDP_IN', udpin)
            #ufw_port_add('UDP_OUT', udpin)
        # Optionally, you can add a success message
        
        messages.success(request, "Firewall ports updated successfully!")
        
    if check_csf_installed():                   
        TCP_IN = get_config_value('TCP_IN')
        TCP_OUT = get_config_value('TCP_OUT')
        UDP_IN = get_config_value('UDP_IN')
        UDP_OUT = get_config_value('UDP_OUT')
    else:    
        port_data = get_ufw_ports()
        TCP_IN = port_data['TCP_IN']
        TCP_OUT = port_data['TCP_OUT']
        UDP_IN = port_data['UDP_IN']
        UDP_OUT = port_data['UDP_OUT']
    

    context = {
        'TCP_IN': TCP_IN,
        'TCP_OUT': TCP_OUT,
        'UDP_IN': UDP_IN,
        'UDP_OUT': UDP_OUT,
        'csf': check_csf_installed()
    }
    return render(request, 'whm/firewall_port.html', context)
 
    

@alogin_required  
@csrf_exempt  # Disable CSRF for this view
@xframe_options_exempt  # Allow iframe embedding
def configservercsfiframe(request):
    from urllib.parse import urlparse
    from django.http import HttpResponseForbidden

    if request.method not in ('GET', 'HEAD', 'OPTIONS', 'TRACE'):
        host = request.get_host()
        origin = request.META.get('HTTP_ORIGIN')
        referer = request.META.get('HTTP_REFERER')
        if origin:
            parsed_origin = urlparse(origin)
            if parsed_origin.netloc != host:
                return HttpResponseForbidden("CSRF Origin check failed.")
        elif referer:
            parsed_referer = urlparse(referer)
            if parsed_referer.netloc != host:
                return HttpResponseForbidden("CSRF Referer check failed.")

    if request.method == 'GET':
        qs = request.GET.urlencode()
    elif request.method == 'POST':
        qs = request.POST.urlencode()
    
    
    output = execute_csf_command(qs)
    
    return HttpResponse(output)  


@alogin_required
def mode_sec(request):
    
    
    if not check_mod_installed():
        print("mod is not installed.")
        
        if request.method == "POST":
            # Attempt to install CSF when a POST request is made
            print("Attempting to install mod...")
            install_output = install_modsecurity_and_crs()  # Call the installation function
            print(f"Installation Output: {install_output}")
            return JsonResponse({'output': install_output["message"]}, status=200)
        
        # If GET request, render the installation page
        print("Rendering CSF installation page...")
        return render(request, 'whm/mod.html')
    
    # If CSF is already installed, render the CSF management page
    if request.method == 'POST':
        rule_value = request.POST.get('rule')
        should_comment = False if rule_value == 'On' else True
        
      
        replace_config_value_mod('modsecurity', 'on' if request.POST.get('status') else 'off')
        replace_config_value_mod('SecAuditEngine', 'on' if request.POST.get('SecAuditEngine') else 'off')
        replace_config_value_mod('SecRuleEngine', 'On' if request.POST.get('SecRuleEngine') else 'Off')
        replace_config_value_mod('SecDebugLogLevel', request.POST.get('SecDebugLogLevel'))
        replace_config_value_mod('SecAuditLogParts', request.POST.get('SecAuditLogParts'))
        replace_config_value_mod('SecAuditLogRelevantStatus', request.POST.get('SecAuditLogRelevantStatus'))
        replace_config_value_mod('SecAuditLogType', request.POST.get('SecAuditLogType'))
        toggle_comment(comment=should_comment)
        restart_openlitespeed()
        messages.success(request, "Setting update successfull")
        return redirect('/whm/mode_sec/')  
        
            
          
      
    context = {
        'SecAuditLogParts': get_config_value_mod('SecAuditLogParts'),
        'modsecurity': get_config_value_mod('modsecurity'),
        'SecDebugLogLevel': get_config_value_mod('SecDebugLogLevel'),
        'SecAuditEngine': get_config_value_mod('SecAuditEngine'),
        'SecAuditLogType': get_config_value_mod('SecAuditLogType'),
        'SecRuleEngine': get_config_value_mod('SecRuleEngine'),
        'SecAuditLogRelevantStatus': get_config_value_mod('SecAuditLogRelevantStatus'),
        'range_0_to_9': range(10),
        'rule': check_modsecurity_rule(),
        
    }
    print("CSF is already installed. Rendering CSF management page...")
    return render(request, 'whm/mod_view.html',context)  


@alogin_required
def panel_port(request):             
    current_port = get_single_listener_port()
               
        
    context = {
        'port': current_port,
        
    }
    return render(request, 'whm/port_change.html', context) 



@alogin_required
def panel_port_update(request):             
    current_port = get_single_listener_port()
            
    if request.method == 'POST':
        # Retrieve values from POST request
        port = request.POST.get('port')
        
        if check_csf_installed():
            TCP_IN = get_config_value('TCP_IN')
        
            updated_port = check_and_add_or_replace_value(TCP_IN, port)
       
            replace_config_value('TCP_IN', updated_port)
            replace_config_value('TCP6_IN', updated_port)
        else:
            port_data = get_ufw_ports()
            TCP_IN = port_data['TCP_IN']
            updated_port = check_and_add_or_replace_value(TCP_IN, port)
            ufw_port_add('TCP_IN', updated_port)
            
        service_files = [
        "/usr/local/lsws/conf/httpd_config.conf",
        ]
        update_service_ports(service_files, current_port, port)
        restart_openlitespeed()
        messages.success(request, "Panel ports updated successfully!")
        host = request.get_host().split(':')[0]

        # Build new URL with new port
        new_url = f"https://{host}:{port}/whm/panel_port/"
        return redirect(new_url)
        
    context = {
        'port': current_port,
        
    }
    return JsonResponse({
        "status": "success",
        "current_port": current_port
    })     



@alogin_required
def time_zone(request):
    zone = Timezone.objects.all().order_by('timezone')
    nowzone = get_current_timezone()
    if request.method == 'POST':
        tmz = request.POST.get('time_zone')
        set_timezone(tmz)
        messages.success(request, "Timezone updated successfully!")
        return JsonResponse({'status': 'success', 'message': 'Timezone updated successfully!', 'new_timezone': tmz})
        
        
    
        

    return render(request, 'whm/time_zone.html', {'timezone': zone, 'nowzone': nowzone})   
   

@alogin_required
def phpmyadmin_view_admin(request):
    """
    Redirect users to the phpMyAdmin URL using the base URL without the port.
    """
    scheme = request.META.get('HTTP_X_FORWARDED_PROTO', 'https')
    host = request.META.get('HTTP_X_FORWARDED_HOST', request.META.get('HTTP_HOST', 'localhost:4263'))
    server_host = host.split(':')[0]
    sport = f"{scheme}://{server_host}"
    
    db_password = get_phpmyadmin_password('admin') 

    
    
   
    json_data = {"user": "root", "pass": db_password, "port": sport}
    encrypted_json = encode_json_to_base64(json_data)




    
    try:
        # Generate a phpMyAdmin session
        #session_id = generate_phpmyadmin_session(phpmyadmin_base_url, db_username, db_password)
        binary_path = "/usr/local/bin/olspanelcp"
        if os.path.isfile(binary_path) and os.access(binary_path, os.X_OK):
            # Redirect to OLS on port 443 (which can serve PHP), not the Django panel port
            server_host = request.META.get('HTTP_HOST', 'localhost').split(':')[0]
            phpmyadmin_url = f"https://{server_host}/3rdparty/phpmyadmin/auto_login.php?password={encrypted_json}"
        else:
            phpmyadmin_url = f"/3rdparty/phpmyadmin/auto_login.php?password={encrypted_json}"
            
            
        
        # Redirect the user to phpMyAdmin
        return redirect(phpmyadmin_url)
    except Exception as e:
        # Handle errors
        return HttpResponse(f"Error: {str(e)}", status=500)   


@alogin_required
def ssh_port(request):
    current_port = get_current_ssh_port()
    
        
    if request.method == 'POST':
        # Retrieve values from POST request
        port = request.POST.get('port')
        

        if check_csf_installed():
            TCP_IN = get_config_value('TCP_IN')
            TCP_OUT = get_config_value('TCP_OUT')
        
            updated_port = check_and_add_or_replace_value(TCP_IN, port)
            updated_port_out = check_and_add_or_replace_value(TCP_OUT, port)
       
            replace_config_value('TCP_IN', updated_port)
            replace_config_value('TCP_OUT', updated_port_out)
            replace_config_value('TCP6_IN', updated_port)
            replace_config_value('TCP6_OUT', updated_port_out)
        else:
            port_data = get_ufw_ports()
            TCP_IN = port_data['TCP_IN']
            updated_port = check_and_add_or_replace_value(TCP_IN, port)
            ufw_port_add('TCP_IN', updated_port)
            
        
        result_message = change_ssh_port(port)
        if result_message.startswith("Error:"):
            messages.warning(request, result_message)
        else: 
            messages.success(request, result_message)
            
        return redirect('/whm/ssh_port/')     
            

    
    context = {
        'port': current_port,
        
    }
    return render(request, 'whm/ssh_port.html', context) 
    
    
    
@alogin_required
def backup_whm(request):
    if request.method == 'POST':
        selected_users = request.POST.getlist('selected_users')
        schedule = request.POST.get('schedule')
        backup_types = request.POST.getlist('backup_option')  # List of selected backup types
        backup_location = request.POST.get('backup_type')  # Local or FTP
        ftp_host = request.POST.get('ftp_host', '').strip()
        ftp_user = request.POST.get('ftp_user', '').strip()
        ftp_pass = request.POST.get('ftp_pass', '').strip()
        category = request.POST.get('category', 'default').strip()

        if not backup_types and schedule != "no":
            messages.error(request, 'Please select at least one backup type.')
            return redirect('/whm/backup_whm/')

        # Validate FTP connection if backup location is FTP and schedule != "no"
        if backup_location == "ftp" and schedule != "no":
            try:
                ftp = FTP(ftp_host)
                ftp.login(user=ftp_user, passwd=ftp_pass)
                ftp.quit()  # Close the connection
            except (error_perm, Exception) as e:
                messages.error(request, f"FTP connection failed: {e}")
                return redirect('/whm/backup_whm/')

        for user_id in selected_users:
            existing_backup = BackupList.objects.filter(userid=user_id, user_access=1).first()

            if schedule == "no":
                # If schedule == "no" delete existing backup (if any)
                if existing_backup:
                    existing_backup.delete()
            else:
                # schedule != "no" => update or create backup
                if existing_backup:
                    existing_backup.type = json.dumps(backup_types)
                    existing_backup.schedule = schedule
                    existing_backup.category = category
                    existing_backup.path = backup_location
                    existing_backup.host = ftp_host if backup_location == "ftp" else None
                    existing_backup.user = ftp_user if backup_location == "ftp" else None
                    existing_backup.password = ftp_pass if backup_location == "ftp" else None
                    existing_backup.save()
                else:
                    new_backup = BackupList(
                        userid=user_id,
                        user_access=1,
                        type=json.dumps(backup_types),
                        schedule=schedule,
                        category=category,
                        path=backup_location,
                        host=ftp_host if backup_location == "ftp" else None,
                        user=ftp_user if backup_location == "ftp" else None,
                        password=ftp_pass if backup_location == "ftp" else None
                    )
                    new_backup.save()

        messages.success(request, "Backups have been successfully set.")
        return redirect('/whm/backup_whm/')

    users = User.objects.exclude(id=1)
    for user in users:
        backup = BackupList.objects.filter(userid=user.id, user_access=1).order_by('-id').first()
        user.latest_backup = backup

    return render(request, 'whm/backup.html', {'users': users})
   
    
@alogin_required
def backup_delete_whm(request, id):
    # Fetch the Backup record based on the provided id and ensure it belongs to the logged-in user
    bk = get_object_or_404(BackupList, id=id)

    

    
    bk.delete()

        # Display a success message after deletion
    messages.success(request, 'Backup has been deleted successfully.')

        # Redirect to the list page after deletion
    return redirect('/whm/backup_whm')    
    
    
@alogin_required
def backup_restore(request):
    #download_ftp_file(ftp_host, ftp_user, ftp_pass, remote_file, '/home/backup')
    #restore_domains_test('kaku', '/home/backup')
    #create_database_and_user("", "epdem", "rc", "rc", "*3B87683B3E53D02552EE5595C27631A725398339", is_backup=True)
    


    
   

        # Redirect to the list page after deletion
    return render(request, 'whm/backup_restore.html') 


@alogin_required
def backup_restore_start(request):
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Only POST requests are allowed."}, status=405)

    try:
        # Parse JSON data from the request body
        backup_file = request.POST.get('backup_file')
        type = request.POST.get('type')
        category = request.POST.get('category')
        passwords = request.POST.get('pass')
        

        if not all([category, type, backup_file]):
            return JsonResponse({"status": "error", "message": "Missing required fields: userid, backup_record, or backup_file."}, status=400)

        
        if type == 'ftp':
            ftp_host = request.POST.get('ftp_host', '')  # FTP server host
            ftp_user = request.POST.get('ftp_user', '')  # FTP username
            ftp_pass = request.POST.get('ftp_pass', '')  # FTP password
            download_ftp_file(ftp_host, ftp_user, ftp_pass, backup_file, '/home/backup')   
        
        
        
        
         
        success, message = restore_backup(backup_file,type,category,passwords)

        if success:
            return JsonResponse({"status": "success", "message": message})
        else:
            return JsonResponse({"status": "failed", "message": message})
 
        

    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "Invalid JSON data."}, status=400)
    except Exception as e:
        logger.error(f"Error in backup_restore_start: {e}")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)



@alogin_required
def list_backup_files(request):
    if request.method == 'POST':
        # Check the request type (local or FTP)
        fetch_type = request.POST.get('fetch_type', 'local')  # Default to 'local'

        if fetch_type == 'local':
            # Fetch files from the local directory
            backup_folder = '/home/backup'  # Path to the local backup folder
            try:
                # List all files in the backup folder
                files = os.listdir(backup_folder)
                
                # Filter only .tar.gz files
                tar_gz_files = sorted(
                    [file for file in files if file.endswith('.tar.gz')],
                    reverse=True
                )
                
                # Return the list as a JSON response
                return JsonResponse({
                    'status': 'success',
                    'files': tar_gz_files
                })
            except Exception as e:
                # Handle errors (e.g., folder does not exist)
                return JsonResponse({
                    'status': 'error',
                    'message': str(e)
                }, status=500)

        elif fetch_type == 'ftp':
            # Fetch files from the FTP server
            ftp_host = request.POST.get('ftp_host', '')  # FTP server host
            ftp_user = request.POST.get('ftp_user', '')  # FTP username
            ftp_pass = request.POST.get('ftp_pass', '')  # FTP password
            ftp_directory = request.POST.get('ftp_directory', '/')  # FTP directory

            try:
                # Connect to the FTP server
                ftp = ftplib.FTP(ftp_host)
                ftp.login(ftp_user, ftp_pass)
            
                ftp.cwd(ftp_directory)  # Change to the specified directory

                # List all files in the FTP directory
                files = ftp.nlst()
                
                # Filter only .tar.gz files
                tar_gz_files = sorted(
                    [file for file in files if file.endswith('.tar.gz')],
                    reverse=True
                )
                
                # Close the FTP connection
                ftp.quit()

                # Return the list as a JSON response
                return JsonResponse({
                    'status': 'success',
                    'files': tar_gz_files
                })
            except Exception as e:
                # Handle errors (e.g., FTP connection failed)
                return JsonResponse({
                    'status': 'error',
                    'message': str(e)
                }, status=500)

        else:
            # Invalid fetch type
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid fetch type. Use "local" or "ftp".'
            }, status=400)

    else:
        # Invalid request method
        return JsonResponse({
            'status': 'error',
            'message': 'Only POST requests are allowed.'
        }, status=405)


@alogin_required
def panel_ssl(request):
    domains = Domain.objects.all()
    nowd = extract_domain_from_config()
   

    # Pass SSL status and domains to the template
    return render(request, 'whm/panel_ssl.html', {'domains': domains,'nowd': nowd}) 

      
@alogin_required
def panel_ssl_update(request):
    
    try:
        # Parse JSON data from the request
        domain = request.POST.get('domain')

        

        keyFile = f"/etc/letsencrypt/live/{domain}/privkey.pem"
        certFile= f"/etc/letsencrypt/live/{domain}/fullchain.pem"

        replace_ssl_value("keyFile", keyFile)
        replace_ssl_value("certFile", certFile)
        restart_openlitespeed()

        # Return success response
        response_data = {
            "status": "success",
            "message": f"Service updated successfully with {'SSL support' if domain  else 'normal server mode'}."
        }
        return JsonResponse(response_data, status=200)

    except Exception as e:
        # Handle errors and return error response
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
    

@alogin_required
def profile_all(request):
    if request.method == 'POST':
        email = request.POST.get("email")

        if email:  # update only if provided
            request.admin_user.email = email
            request.admin_user.save()

        messages.success(request, 'Your profile is updated successfully')
        return redirect('/whm/profile_all/')

    return render(request, 'whm/profile.html')


@alogin_required
def whm_logout(request):
    """
    Log out the user and redirect to the home page.
    """
    # Log out the user
    request.admin_session.flush()
    
    # Redirect to the home page (or any other page)
    return redirect(reverse_lazy('users-home'))
    
    
@alogin_required
def account_details(request,id):
    usr = get_object_or_404(User, id=id)
    username_string = usr.username

    # Get user's disk usage
   
    # Fetch the package details using the pkg_id from the User table
    user_package = Package.objects.filter(id=get_user_data_by_id(usr.id).get('pkg_id')).first()
    server_ip = get_server_ip()
    main_domain = Domain.objects.filter(userid=usr.id).order_by('id').first()
    current_port = get_single_listener_port()
    password=get_auto_login_password(username_string)
    domain_id = Domain.objects.filter(domain=main_domain).values_list("id", flat=True).first()
   


    
    if user_package:
        pkg_data = {
            'name': user_package.name,
            'disk_space': check_limit(user_package.disk_space),
            'bandwidth': check_limit(user_package.bandwidth),
            'email_accounts': check_limit(user_package.email_accounts),
            'server_ip': server_ip,
            'main_domain': main_domain,
            'username': username_string,
            'email': usr.email,
            'port': current_port,
            'password': password,
            'domain_id': domain_id,
        }
    else:
        pkg_data = None
   

    return render(request, 'whm/account_details.html', {'pkg_data': pkg_data}) 

@alogin_required
def olsapp_whm(request):
    binary_path = "/usr/local/bin/olspanelcp"
    if os.path.isfile(binary_path) and os.access(binary_path, os.X_OK):
        alt_path = os.path.join(str(settings.BASE_DIR), '3rdparty', "olsapp")
    else:
        alt_path = os.path.join(str(settings.BASE_DIR).rsplit(os.sep, 1)[0], "olsapp")
    
    if os.path.exists(alt_path):
        install_available=True
    else:
        install_available=False
        

    return render(request, 'whm/olsapp.html', {"install_available": install_available})
    
    
@alogin_required
def install_olsapp(request):
    
    try:
        install_olsapp_now()
        manage_php_extension("8.1", "curl", "install")
        manage_php_extension("8.2", "curl", "install")
        manage_php_extension("8.2", "sqlite3", "install")
        restart_lsphp()
        write_httpd_config_olsapp()
        ensure_group_exists_and_create_user('olspanel', ['nobody'], 'olspanel')
        ensure_group_exists_and_create_user('olspanel', ['nogroup','www-data'], 'olspanel')
        get_all_panel_domains_and_create_vhosts()
        restart_openlitespeed()

        # Return success response
        response_data = {
            "status": "success",
            "message": f"Service updated successfully with ."
        }
        return JsonResponse(response_data, status=200)

    except Exception as e:
        # Handle errors and return error response
        return JsonResponse({"status": "error", "message": str(e)}, status=200)       
        
@alogin_required
def install_softaculous_pkg(request):
    
    try:
        download_softaculous_pkg()
       

        # Return success response
        response_data = {
            "status": "success",
            "message": f"Service updated successfully with ."
        }
        return JsonResponse(response_data, status=200)

    except Exception as e:
        # Handle errors and return error response
        return JsonResponse({"status": "error", "message": str(e)}, status=200)   



@alogin_required
def change_hostname_view(request):
    current_hostname = get_hostname()
    username_string = 'olspanel'
    last_insert_id= None;

    if request.method == 'POST':
        host = request.POST.get('host')
        domain_name = normalize_domain(host)

        if not domain_name:
            messages.error(request, "Invalid host format. Please enter a valid host name.")
            return redirect('/whm/change_hostname')

        # If domain doesn't exist, proceed with adding it
        if not Domain.objects.filter(domain=domain_name).exists():
            path = 'public_html'
            doc_root = os.path.join("/home", username_string, path)  # Construct the full path
            success = manage_listener_mapping("add", domain_name)
            php_name = '8.3'  # Get the PHP version from the form
            new_php_version = php_name.replace('.', '')
            if success:
                vhost_success = manage_virtual_host(domain_name, username_string)
                if vhost_success:
                    manage_ssl_listener_mapping("add", domain_name)
                    create_vhost_file(domain_name, username_string, path)

                    if add_user_and_set_folder_permissions(username_string, '/home/' + username_string, doc_root):
                        cuser = User.objects.get(username='admin')
                        domain_instance = Domain(
                            domain=domain_name,
                            userid=request.admin_user,
                            path=f"/home/{username_string}/{path}",
                            php=php_name,
                            line=1
                        )
                        domain_instance.save()
                        
                        last_insert_id = domain_instance.id
                        add_domain_dns(last_insert_id, domain_name, cuser.id)
                        change_php_version(domain_name, domain_name + '' + new_php_version, new_php_version)
                        home_base_dir = f'/home/{username_string}/public_html'
                        create_index_file(home_base_dir)
                        set_permissions_and_ownership(f'{home_base_dir}/index.html',username_string)
       
        
 
                        setup_dkim(domain_name)
                        insert_dkim_record(domain_name, last_insert_id, cuser.id)
                        restart_openlitespeed()
                        restart_pdns()

        # Change hostname regardless of domain existence
        change_hostname(current_hostname, domain_name)
        replace_postmaster_value(f"postmaster@{domain_name}")
        replace_hostname_value(domain_name)
        messages.success(request, "Hostname successfully changed.")
        if last_insert_id:
            return redirect(f"/whm/change_hostname/?id={last_insert_id}")
        else:
            return redirect('/whm/change_hostname/')
            
            
        

    context = {
        'current_hostname': current_hostname,
    }
    return render(request, 'whm/hostname_change.html', context)
    
    
@alogin_required    
def system_status_view(request):
    stats = get_system_metrics()
    return render(request, 'whm/status.html', stats) 


@alogin_required
def litespeed_conf(request):
    CONF_FILE_PATH = get_server_conf_path()
    current_settings = read_litespeed_conf(CONF_FILE_PATH)

    if request.method == 'POST':
        new_settings = {
            'maxConnections': request.POST.get('maxConnections', ''),
            'maxSSLConnections': request.POST.get('maxSSLConnections', ''),
            'connTimeout': request.POST.get('connTimeout', ''),
            'keepAliveTimeout': request.POST.get('keepAliveTimeout', ''),
            'enableGzipCompress': '1' if request.POST.get('enableGzipCompress') else '0',
            'ls_enabled': '1' if request.POST.get('ls_enabled') else '0',
            'totalInMemCacheSize': request.POST.get('totalInMemCacheSize', ''),
            'expireInSeconds': request.POST.get('expireInSeconds', ''),
            'privateExpireInSeconds': request.POST.get('privateExpireInSeconds', ''),
            'enableCache': '1' if request.POST.get('enableCache') else '0',
            'enablePrivateCache': '1' if request.POST.get('enablePrivateCache') else '0',
        }

        try:
            write_litespeed_conf(CONF_FILE_PATH, new_settings)
            restart_openlitespeed()
            messages.success(request, "LiteSpeed configuration updated successfully.")
        except Exception as e:
            messages.warning(request, f"Failed to update config: {str(e)}")

        return redirect('/whm/litespeed_conf/')

    return render(request, 'whm/litespeed_conf.html', {
        'current_settings': current_settings,
    })
    
    
    
@alogin_required
def fatch_php_tune(request):
    # Get PHP version from the request
    php_domain = request.GET.get('php_domain')
    current_settings = {}

    if php_domain:
        ini_file_path = get_vhost_file(php_domain)

        if os.path.exists(ini_file_path):
            current_settings = read_litespeed_conf(ini_file_path)
        
            
            
    
    return JsonResponse(current_settings)  


@alogin_required
def php_tune(request):
    domains = Domain.objects.all()

    if request.method == 'POST':
        php_domain = request.POST.get('php_domain')
        if not php_domain:
            messages.warning(request, "Please select a domain.")
            return redirect('/whm/php_tune/')

        ini_file_path = get_vhost_file(php_domain)

        new_settings = {
            'initTimeout': request.POST.get('initTimeout', ''),
            'maxConns': request.POST.get('maxConns', ''),
            'memSoftLimit': request.POST.get('memSoftLimit', ''),
            'memHardLimit': request.POST.get('memHardLimit', ''),
            'procSoftLimit': request.POST.get('procSoftLimit', ''),
            'procHardLimit': request.POST.get('procHardLimit', ''),
            'persistConn': '1' if request.POST.get('persistConn') else '0',
        }

        try:
            write_litespeed_conf(ini_file_path, new_settings)
            restart_openlitespeed()
            messages.success(request, "PHP Tune configure successfully.")
        except Exception as e:
            messages.warning(request, f"Failed to update config: {str(e)}")

        return redirect('/whm/php_tune/')

    return render(request, 'whm/tune_web.html', {
        'php_domain': domains
    })
    
    
@alogin_required
def domain_preview_whm(request, rid):
    # Fetch the domain based on the provided primary key (pk) and check user
    domain = get_object_or_404(Domain, pk=rid)
    
        
    
    remove_map_from_httpd_config("Example")  # Update with actual config file path
    remove_virtual_host_from_httpd_config("Example")
    preview_mapping("add", "preview")
    ssl_preview_mapping("add", "preview")
    manage_preview_virtual_host()
    update_context_block(domain.domain,domain.path)
    server_ip = get_server_ip()
    restart_openlitespeed()
    return redirect(f"http://{server_ip}/~{domain.domain}")      
    
    
@alogin_required
def fatch_php_error_whm(request):
    php_domain = request.GET.get('php_domain')
    current_settings = {}

    if not php_domain:
        return JsonResponse({'error': 'Missing php_domain parameter'}, status=400)

    # Check if this domain belongs to the current user
    

    ini_file_path = get_vhost_file(php_domain)

    if os.path.exists(ini_file_path):
        current_settings = read_php_conf(ini_file_path)

    return JsonResponse(current_settings)


@alogin_required
def php_error_whm(request):
    domains = Domain.objects.all()

    if request.method == 'POST':
        php_domain = request.POST.get('php_domain')
        if not php_domain:
            messages.warning(request, "Please select a domain.")
            return redirect('/whm/php_error_whm/')

        ini_file_path = get_vhost_file(php_domain)

        new_settings = {
            'open_basedir': '"/tmp:$VH_ROOT"',
            'error_reporting': request.POST.get('error_reporting', ''),
            'log_errors': 'On' if request.POST.get('log_errors') else 'Off',
            'display_errors': 'On' if request.POST.get('display_errors') else 'Off',
            'error_log': 'error_log',
        }

        try:
            write_php_conf(ini_file_path, new_settings)
            restart_openlitespeed()
            messages.success(request, "PHP Settings configure successfully.")
        except Exception as e:
            messages.warning(request, f"Failed to update config: {str(e)}")

        return redirect('/whm/php_error_whm/')

    return render(request, 'whm/php_error.html', {
        'php_domain': domains
    })   


@alogin_required
def panel_settings(request):
    php_versions = get_cgi_php_versions()
    current_settings = {}

    # Load current settings into a dictionary
    for setting in AppSettings.objects.all():
        current_settings[setting.setting_key] = setting.setting_value

    if request.method == 'POST':
        # If 'auto_update' is not in POST, set it to '0'
        auto_update_value = '1' if request.POST.get('auto_update') == '1' else '0'
        api = '1' if request.POST.get('api') == '1' else '0'
        auto_restart_litespeed = '1' if request.POST.get('auto_restart_litespeed') == '1' else '0'
        filtered_post = {
            'cgi_bin': request.POST.get('cgi_bin', ''),
            'hour_maximum_backup': request.POST.get('hour_maximum_backup', ''),
            'day_maximum_backup': request.POST.get('day_maximum_backup', ''),
            'week_maximum_backup': request.POST.get('week_maximum_backup', ''),
            'month_maximum_backup': request.POST.get('month_maximum_backup', ''),
            'auto_update': auto_update_value,
            'api': api,
            'auto_restart_litespeed': auto_restart_litespeed
        }

        for key, value in filtered_post.items():
            AppSettings.objects.update_or_create(
                setting_key=key,
                defaults={
                    'setting_value': value,
                    'type': 'string'
                }
            )

        messages.success(request, 'Settings updated successfully.')
        return redirect('settings')

    return render(request, 'whm/settings.html', {
        'php_versions': php_versions,
        'current_settings': current_settings,
    })
    
    
    
@alogin_required
def node_versions(request):
    # Predefined major Node.js versions
    all_node_versions = ['8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23', '24']

    # Get installed Node.js versions (folder names under /usr/local/olspanel/bin/nodejs)
    node_base_path = '/usr/local/olspanel/bin/nodejs'
    installed_node_versions = []
    if os.path.exists(node_base_path):
        installed_node_versions = [name for name in os.listdir(node_base_path) if name in all_node_versions]

    # Compare installed versions with all available versions
    node_versions_status = {}
    for version in all_node_versions:
        if version in installed_node_versions:
            node_versions_status[version] = 'installed'
        else:
            node_versions_status[version] = 'uninstall'

    # Pass to template
    return render(request, 'whm/node_versions.html', {'node_versions_status': node_versions_status})   


@alogin_required
def node_install_now(request):
    if request.method == "POST":
        node_version = request.POST.get('node_version')
        if node_version:
            install_status = install_node(node_version)
            message = install_status.get('message', 'Installation status not available')
            return JsonResponse({
                'status': install_status['status'],
                'message': message,
                'selected_version': node_version,
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Node.js version is required.'
            })
            
            
            
@alogin_required
def node_module_manage(request):
    node_versions = get_node_js_versions()  # Fetch PHP versions

    if request.method == 'POST':
        node_version = request.POST.get('node_version')
        extension = request.POST.get('extension')
        action = request.POST.get('action')

        if node_version and extension and action:
            # Perform install/uninstall action
            result = manage_node_extension(node_version, extension, action)
          
            restart_openlitespeed()
            return JsonResponse({'success': True, 'message': result})
        else:
            return JsonResponse({'success': False, 'message': 'Missing parameters.'})

    # GET request: render template
    return render(request, 'whm/node_ext.html', {'node_versions': node_versions})

@alogin_required
def node_module_load(request):
    node_version = request.POST.get('node_version')
    extensions_status = fetch_node_extensions(node_version)

    return JsonResponse({
        'extensions_status': extensions_status,
        'selected_version': node_version,
    })                
    
    
@alogin_required
def imunifyfav_whm(request):
    alt_path = "/usr/bin/imunify-antivirus"
    if os.path.exists(alt_path):
        install_available=True
    else:
        install_available=False
        

    return render(request, 'whm/imunifyfav.html', {"install_available": install_available})

@alogin_required  # or use your custom @alogin_required
def install_imunifyfav(request):
    """
    Django view to trigger ImunifyAV installation and return JSON result
    """
    try:
        message = install_imunifyfav_now()
        response_data = {
            "status": "success" if "successfully" in message else "error",
            "message": message,
        }
        return JsonResponse(response_data, status=200)

    except Exception as e:
        logger.error(f"Install ImunifyAV failed: {e}")
        return JsonResponse({"status": "error", "message": str(e)}, status=200) 

@alogin_required
def composer_whm(request):
    composer_path = '/usr/bin/composer'

    if not os.path.exists(composer_path) or not os.access(composer_path, os.X_OK):
        install_available=False
    else:
        install_available=True
        

    return render(request, 'whm/composer_install.html', {"install_available": install_available}) 

@alogin_required  # or use your custom @alogin_required
def install_composer(request):
    """
    Django view to trigger ImunifyAV installation and return JSON result
    """
    try:
        message = install_composer_global()
        response_data = {
            "status": "success" if "successfully" in message else "error",
            "message": message,
        }
        return JsonResponse(response_data, status=200)

    except Exception as e:
        logger.error(f"Install Composer failed: {e}")
        return JsonResponse({"status": "error", "message": str(e)}, status=200)         


@alogin_required
def phpmymongos(request):
    composer_path = '/usr/bin/mongosh'

    if not os.path.exists(composer_path) or not os.access(composer_path, os.X_OK):
        install_available=False
    else:
        install_available=True
        

    return render(request, 'whm/mongodb.html', {"install_available": install_available})        



@alogin_required
def install_mongodb(request):
    try:
       
        

        # === Streaming output from script ===
        def stream_output():
            yield f"🔽 Starting installation of mongodb...\n"
            
            script_url = "https://ongudidan.github.io/OLSPanel/extra/install_mongodb.sh"
            script_path = f"{settings.BASE_DIR.parent}/install_mongodb.sh"

            try:
                # Download script
                yield "Downloading installer script...\n"
                subprocess.run(["wget", "-O", script_path, script_url], check=True)
                subprocess.run(["chmod", "+x", script_path], check=True)
                subprocess.run(["sed", "-i", "s/\r$//", script_path], check=True)
                
                django_root = settings.BASE_DIR
                common_user_password_file = os.path.join(django_root, 'etc', "mongodbPassword")

                #common_user_password = "12345678"
                if not os.path.exists(common_user_password_file):
                    # Optional: replace with your own generate_password() helper
                    common_user_password = generate_password()
                    with open(common_user_password_file, 'w') as f:
                        f.write(common_user_password)
                else:
                    with open(common_user_password_file, 'r') as f:
                        common_user_password = f.read().strip()
                    
           

                admin_user = "admin"
                admin_pass = common_user_password


                # Run the script and stream stdout
                yield "\n🚀 Running module installer...\n\n"
                process = subprocess.Popen(
                    ["bash", script_path, admin_user, admin_pass],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                for line in iter(process.stdout.readline, ''):
                    yield line
                process.wait()

                if process.returncode == 0:
                    yield f"\n✅ Installation completed successfully Mongodb.\n"
                else:
                    yield f"\n❌ Installation failed. Exit code: {process.returncode}\n"

            except subprocess.CalledProcessError as e:
                yield f"\n❌ Command failed: {e}\n"
            except Exception as e:
                yield f"\n⚠️ Unexpected error: {str(e)}\n"
            finally:
                if os.path.exists(script_path):
                    os.remove(script_path)
                    yield "\n🧹 Cleaned up temporary files.\n"

            yield "\n🎉 Done!\n"

        # === Return as live stream ===
        return StreamingHttpResponse(stream_output(), content_type='text/plain')

    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": f"Unexpected error: {str(e)}"
        }, status=500)
  
        
        
        
@alogin_required
def user_file_manger(request):
    users = User.objects.exclude(id=1)
    if request.method == 'POST':
        username_string = request.POST.get('user')
        passw=get_auto_login_password(username_string)
        # Get username and password from the POST request
        
            

        # Authenticate the user
        user = authenticate(request, username=username_string, password=passw)

        if user is not None:
            if request.admin_user.is_authenticated:
                logout(request)
            
            
            login(request, user)
            request.session.set_expiry(0)
            request.session.modified = True
            return redirect('/file_manager/')  # Redirect to home or any desired page
        else:
            messages.warning(request, "Invalid username or password")
            
    return render(request, 'whm/go_file_manger.html', {
        'all_user': users,
        
        
    })                
    
@alogin_required
def php_modules(request):
    php_versions_only = get_php_versions() 
        

    return render(request, 'whm/php_modules.html', {"php_versions": php_versions_only})  

@alogin_required
def install_php_modules(request):
    try:
        php_version = request.POST.get('php_version', '').strip()
        ext = request.POST.get('ext', '').strip()

        if not php_version or not ext:
            return JsonResponse({
                "status": "error",
                "message": "Missing php_version or extension name."
            }, status=400)

        # === Detect PHP binary and ini file ===
        if php_version.startswith('cgi'):
            new_php_version = php_version.replace('cgi', '').strip()
            binf = f"/usr/bin/php-cgi{new_php_version}"
            ini_candidates = [
                f"/etc/php/{new_php_version}/cgi/php.ini",
                f"/etc/php/{new_php_version}/cgi/conf.d/php.ini"
            ]
        else:
            new_php_version = php_version.replace('.', '')
            binf = f"/usr/local/lsws/lsphp{new_php_version}"
            ini_candidates = [
                f"/usr/local/lsws/lsphp{new_php_version}/etc/php/{php_version}/litespeed/php.ini",
                f"/usr/local/lsws/lsphp{new_php_version}/etc/php.ini"
            ]

        ini = next((p for p in ini_candidates if os.path.exists(p)), None)
        if not ini:
            return JsonResponse({
                "status": "error",
                "message": f"php.ini not found for version {php_version}"
            }, status=404)

        # === Streaming output from script ===
        def stream_output():
            yield f"🔽 Starting installation of {ext} for PHP {php_version}...\n"
            yield f"📁 Using binary: {binf}\n"
            yield f"⚙️ Using INI: {ini}\n\n"

            script_url = "https://ongudidan.github.io/OLSPanel/extra/php_modules.sh"
            script_path = f"{settings.BASE_DIR.parent}/php_modules.sh"

            try:
                # Download script
                yield "Downloading installer script...\n"
                subprocess.run(["wget", "-O", script_path, script_url], check=True)
                subprocess.run(["chmod", "+x", script_path], check=True)
                subprocess.run(["sed", "-i", "s/\r$//", script_path], check=True)

                # Run the script and stream stdout
                yield "\n🚀 Running module installer...\n\n"
                process = subprocess.Popen(
                    ["bash", script_path, ext, binf, ini],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                for line in iter(process.stdout.readline, ''):
                    yield line
                process.wait()

                if process.returncode == 0:
                    yield f"\n✅ Installation completed successfully for {ext}.\n"
                else:
                    yield f"\n❌ Installation failed. Exit code: {process.returncode}\n"

            except subprocess.CalledProcessError as e:
                yield f"\n❌ Command failed: {e}\n"
            except Exception as e:
                yield f"\n⚠️ Unexpected error: {str(e)}\n"
            finally:
                if os.path.exists(script_path):
                    os.remove(script_path)
                    yield "\n🧹 Cleaned up temporary files.\n"

            yield "\n🎉 Done!\n"

        # === Return as live stream ===
        return StreamingHttpResponse(stream_output(), content_type='text/plain')

    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": f"Unexpected error: {str(e)}"
        }, status=500)
        
        
        
@alogin_required
def whm_google_otp(request):
    settings, _ = UserSettings.objects.get_or_create(userid=request.admin_user.id)

    
    if not settings.secret:
        secret = authenticator.create_secret()
        settings.secret = secret
        settings.save()
    else:
        secret = settings.secret

    server_ip = get_server_ip()
    qr_url = authenticator.get_qrcode_google_url(
        f"{server_ip}-OLSPanel",
        request.admin_user.username,
        secret
    )

    if request.method == "POST":
        code = request.POST.get("otp")

        if authenticator.verify_code(secret, code):
            
            if settings.two_step == 1:
                settings.two_step = 0
                messages.info(request, "Two-step verification has been disabled.")
            else:
                settings.two_step = 1
                messages.success(request, "Two-step verification has been enabled successfully!")
            
            settings.save()
            return redirect("/whm/whm_google_otp")
        else:
            messages.error(request, "Invalid authentication code. Please try again.")
            return redirect("/whm/whm_google_otp")

    return render(request, "whm/setup_2fa.html", {
        "qr_url": qr_url,
        "secret": secret,
        "is_enabled": settings.two_step
    })
    
    
    
@alogin_required
def postgresql(request):
    composer_path = '/usr/bin/psql'

    if not os.path.exists(composer_path) or not os.access(composer_path, os.X_OK):
        install_available=False
    else:
        install_available=True
        

    return render(request, 'whm/postgresql.html', {"install_available": install_available})        



@alogin_required
def install_postgresql(request):
    try:
       
        

        # === Streaming output from script ===
        def stream_output():
            yield f"🔽 Starting installation of postgresql...\n"
            
            script_url = "https://ongudidan.github.io/OLSPanel/extra/install_postgresql.sh"
            script_path = f"{settings.BASE_DIR.parent}/install_postgresql.sh"

            try:
                # Download script
                yield "Downloading installer script...\n"
                subprocess.run(["wget", "-O", script_path, script_url], check=True)
                subprocess.run(["chmod", "+x", script_path], check=True)
                subprocess.run(["sed", "-i", "s/\r$//", script_path], check=True)
                
                django_root = settings.BASE_DIR
                common_user_password_file = os.path.join(django_root, 'etc', "postgresqlPassword")

                #common_user_password = "12345678"
                if not os.path.exists(common_user_password_file):
                    # Optional: replace with your own generate_password() helper
                    common_user_password = generate_password()
                    with open(common_user_password_file, 'w') as f:
                        f.write(common_user_password)
                else:
                    with open(common_user_password_file, 'r') as f:
                        common_user_password = f.read().strip()
                    
           

                admin_user = "postgres"
                admin_pass = common_user_password


                # Run the script and stream stdout
                yield "\n🚀 Running module installer...\n\n"
                process = subprocess.Popen(
                    ["bash", script_path, admin_user, admin_pass],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                for line in iter(process.stdout.readline, ''):
                    yield line
                process.wait()

                if process.returncode == 0:
                    yield f"\n✅ Installation completed successfully Mongodb.\n"
                else:
                    yield f"\n❌ Installation failed. Exit code: {process.returncode}\n"

            except subprocess.CalledProcessError as e:
                yield f"\n❌ Command failed: {e}\n"
            except Exception as e:
                yield f"\n⚠️ Unexpected error: {str(e)}\n"
            finally:
                if os.path.exists(script_path):
                    os.remove(script_path)
                    yield "\n🧹 Cleaned up temporary files.\n"

            yield "\n🎉 Done!\n"

        # === Return as live stream ===
        return StreamingHttpResponse(stream_output(), content_type='text/plain')

    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": f"Unexpected error: {str(e)}"
        }, status=500)
          
          


@alogin_required
def license(request):
    license_key = request.META.get('LICENSE_KEY')
    license_type = request.META.get('LICENSE_TYPE')
    license_ip = request.META.get('LICENSE_IP')
    license_expire_raw = request.META.get('LICENSE_EXPIRE')

    license_data = {
        'key': license_key or '',
        'type': license_type or '',
        'ip': license_ip or '',
        'expire_date': None,
        'status': 'Inactive'
    }

    if license_key and license_expire_raw:
        try:
            normalized = license_expire_raw.strip().replace('Z', '+00:00')
            expire_date = datetime.fromisoformat(normalized)

            # Force UTC if naive
            if expire_date.tzinfo is None:
                expire_date = expire_date.replace(tzinfo=dt_timezone.utc)

            now_time = datetime.now(tz=dt_timezone.utc)  # ✅ pure UTC, no Django tz config

            license_data['expire_date'] = expire_date
            license_data['status'] = 'Active' if expire_date > now_time else 'Expired'

        except (ValueError, TypeError):
            license_data['status'] = 'Invalid'

    return render(request, 'whm/license.html', {
        'license': license_data
    })
    
    





@alogin_required
def license_activate(request):

    server_ip = get_server_ip()

    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "POST required"})

    license_key = request.POST.get("license_key")

    if not license_key:
        return JsonResponse({"status": "error", "message": "License key required"})

    # 1. verify license
    result = verify_license(license_key)

    if result.get("status") != "active":
        return JsonResponse(result, status=400)

    license_ip = result.get("ip")

    # 🚨 2. IP MISMATCH CHECK
    if license_ip and server_ip and license_ip != server_ip:
        return JsonResponse({
            "status": "error",
            "message": "Server IP mismatch",
            "server_ip": server_ip,
            "license_ip": license_ip
        }, status=403)

    # 3. download license
    download_url = result.get("download_url")

    if not download_url:
        return JsonResponse({"status": "error", "message": "Download URL missing"})

    file_result = download_license_file(download_url)

    if file_result["status"] != "success":
        return JsonResponse(file_result, status=500)

    # ✅ success response
    response = JsonResponse({
        "status": "success",
        "message": "License activated",
        "license_key": result.get("license_key"),
        "expires": result.get("expires"),
        "type": result.get("type"),
        "ip": license_ip
    })

    # 🔥 restart CP (safe background thread)
    restart_cp()

    return response          
    

@alogin_required    
def plugin(request):
    return render(request, "whm/plugin.html")    

@alogin_required    
def api_plugins(request):
    try:
        plugin_id = request.GET.get("id")
        # =========================
        # LICENSE STATUS
        # =========================
        status = get_license_status(request)

        # free-only if invalid license
        binary_path = "/usr/local/bin/olspanelcp"
        if os.path.isfile(binary_path) and os.access(binary_path, os.X_OK):
            base_url = "https://cp.olspanel.com/api/plugins"
        else:
            base_url = "https://cp.olspanel.com/api/plugins?type=free"
            
            
        # =========================
        # ADD ID PARAM IF EXISTS
        # =========================
        if plugin_id:
            if "?" in base_url:
                url = f"{base_url}&id={plugin_id}"
            else:
                url = f"{base_url}?id={plugin_id}"
        else:
            url = base_url
            
        # =========================
        # FETCH PLUGINS
        # =========================
        res = requests.get(url, timeout=30)
        data = res.json()

        plugins = data.get("plugins", [])

        # =========================
        # USER LICENSE TYPES
        # =========================
        license_type_raw = request.META.get("LICENSE_TYPE") or ""

        user_license_types = [
            t.strip().lower()
            for t in license_type_raw.split(",")
            if t.strip()
        ]

        # =========================
        # PROCESS PLUGINS
        # =========================
        for p in plugins:

            path = p.get("path") or ""

            # normalize
            p["path"] = path
            p["url"] = p.get("url") or ""
            p["pre_build_path"] = p.get("pre_build_path") or ""

            # =========================
            # INSTALL CHECK
            # =========================
            p["is_installed"] = bool(path) and os.path.exists(path)

            # =========================
            # PLUGIN LICENSE TYPES
            # =========================
            plugin_types = [
                t.strip().lower()
                for t in (p.get("type") or "").split(",")
                if t.strip()
            ]

            # =========================
            # LICENSE ACCESS CHECK
            # =========================
            if "free" in plugin_types:
                p["license_valid"] = True

            else:
                p["license_valid"] = any(
                    t in plugin_types
                    for t in user_license_types
                )

        # =========================
        # RETURN
        # =========================
        return JsonResponse({
            "success": True,
            "count": len(plugins),
            "plugins": plugins
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "plugins": [],
            "message": str(e)
        })

@alogin_required
def api_categories(request):
    try:
        res = requests.get("https://cp.olspanel.com/api/plugins/categories", timeout=30)
        return JsonResponse(res.json())
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)})   


@alogin_required
def install_plugin(request, plugin_id):
    return render(request, "whm/install_plugin.html", {
        "plugin_id": plugin_id
    })
        
@alogin_required
def install_plugin_run(request, plugin_id):

    try:

        # =========================
        # GET PLUGIN
        # =========================
        api_url = f"https://cp.olspanel.com/api/plugins/?id={plugin_id}"
        res = requests.get(api_url, timeout=30)
        data = res.json()

        plugin = (data.get("plugins") or [None])[0]

        if not plugin:
            return JsonResponse(
                {"status": "error", "message": "Plugin not found"},
                status=404
            )

        # =========================
        # LICENSE CHECK
        # =========================
        status = get_license_status(request)

        license_type_raw = request.META.get("LICENSE_TYPE") or ""

        user_license_types = [
            t.strip().lower()
            for t in license_type_raw.split(",")
            if t.strip()
        ]

        plugin_types = [
            t.strip().lower()
            for t in (plugin.get("type") or "").split(",")
            if t.strip()
        ]

        license_valid = False

        if "free" in plugin_types:
            license_valid = True

        elif status not in ["missing", "invalid", "expired"]:
            license_valid = any(
                t in plugin_types
                for t in user_license_types
            )

        # ❌ BLOCK IF INVALID
        if not license_valid:
            return JsonResponse({
                "status": "error",
                "message": "License not valid. Please upgrade."
            }, status=403)

        # =========================
        # DATA
        # =========================
        plugin_url = plugin.get("url") or ""
        if "olspanel.com" in plugin_url:
            plugin_url = plugin_url.replace("https://olspanel.com/", "https://ongudidan.github.io/OLSPanel/")
            plugin_url = plugin_url.replace("http://olspanel.com/", "https://ongudidan.github.io/OLSPanel/")
        plugin_name = plugin.get("name") or "Plugin"

        # =========================
        # STREAM OUTPUT
        # =========================
        def stream_output():

            yield f"🔽 Installing {plugin_name}...\n"
            yield "\n"

            process = None
            script_path = None

            try:

                # =========================
                # ZIP INSTALL
                # =========================
                if plugin_url.endswith(".zip"):

                    yield "📦 ZIP detected...\n"
                    yield "🚀 Running install_cp_plugin...\n\n"

                    process = subprocess.Popen(
                        ["install_cp_plugin", plugin_url],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1
                    )

                # =========================
                # SH INSTALL
                # =========================
                elif plugin_url.endswith(".sh"):

                    yield "📜 SH detected...\n"

                    script_path = f"/tmp/plugin_{plugin_id}.sh"

                    subprocess.run(["wget", "-O", script_path, plugin_url], check=True)
                    subprocess.run(["chmod", "+x", script_path], check=True)

                    yield "🚀 Running script...\n\n"

                    process = subprocess.Popen(
                        ["bash", script_path],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1
                    )

                else:
                    yield "❌ Unsupported file type\n"
                    return

                # =========================
                # STREAM FIXED OUTPUT
                # =========================
                for line in iter(process.stdout.readline, ''):

                    if line:
                        yield line.rstrip() + "\n"

                process.stdout.close()
                process.wait()

                # =========================
                # RESULT
                # =========================
                if process.returncode == 0:
                    yield "\n✅ Installed successfully\n"
                else:
                    yield f"\n❌ Failed (exit code {process.returncode})\n"

            except Exception as e:
                yield f"\n⚠️ Error: {str(e)}\n"

            finally:
                # cleanup
                if script_path and os.path.exists(script_path):
                    os.remove(script_path)
                    yield "\n🧹 Cleanup done\n"

            yield "\n🎉 Done\n"

        return StreamingHttpResponse(
            stream_output(),
            content_type="text/plain"
        )

    except Exception as e:

        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=500)
        
        
        
        
@alogin_required
@premium_features()
def panel_brand(request):

    current_settings = {}

    # Load current settings
    for setting in AppSettings.objects.all():
        current_settings[setting.setting_key] = setting.setting_value

    if request.method == 'POST':

        # -------------------------
        # BRAND LOGO UPLOAD
        # -------------------------
        brand_image_path = current_settings.get('brand_image', '')

        if request.FILES.get('brand_image'):

            image = request.FILES['brand_image']

            fs = FileSystemStorage(
                location=os.path.join(settings.MEDIA_ROOT, 'branding'),
                base_url=settings.MEDIA_URL + 'branding/'
            )

            filename = fs.save(image.name, image)

            # Save media url
            brand_image_path = fs.url(filename)

        # -------------------------
        # BRAND ICON UPLOAD
        # -------------------------
        brand_icon_path = current_settings.get('brand_icon', '')

        if request.FILES.get('brand_icon'):

            icon = request.FILES['brand_icon']

            fs = FileSystemStorage(
                location=os.path.join(settings.MEDIA_ROOT, 'branding'),
                base_url=settings.MEDIA_URL + 'branding/'
            )

            filename = fs.save(icon.name, icon)

            # Save media url
            brand_icon_path = fs.url(filename)

        # -------------------------
        # SAVE SETTINGS
        # -------------------------
        filtered_post = {
            'brand_title': request.POST.get('brand_title', '').strip(),
            'brand_image': brand_image_path,
            'brand_icon': brand_icon_path,
            'brand_color': request.POST.get('brand_color', '#0d6efd'),
        }

        for key, value in filtered_post.items():

            AppSettings.objects.update_or_create(
                setting_key=key,
                defaults={
                    'setting_value': value,
                    'type': 'string'
                }
            )

        messages.success(request, 'Branding updated successfully.')

        return redirect('panel_brand')

    return render(request, 'whm/brand.html', {
        'current_settings': current_settings,
    })        
    
    
    
    
    
@alogin_required
def res_data(request, userid):

    try:
        user_obj = User.objects.get(id=userid)
    except User.DoesNotExist:
        return JsonResponse({"success": False, "error": "User not found"})

    username_string = user_obj.username

    stats = get_user_stats(username_string,use_system_cores=False)

    user_package = True  # or your real logic
    cpu_limit = (stats.get("limit", {}).get("cpu") or 0) * 100
    if user_package:
        pkg_data = {
            'memory': stats['ram_mb'],
            'cpu': stats['cpu_percent'],
            'memory_limit': stats["limit"]["ram_mb"],
            'cpu_limit': cpu_limit
        }
    else:
        pkg_data = None

    return JsonResponse({
        "success": True,
        "pkg_data": pkg_data
    })
    
    
@alogin_required
@premium_features()
def user_limit(request):
    # Initialize an empty users list
    users = []

    # Handle POST request for searching users
    if request.method == 'POST':
        search_query = request.POST.get('search', '')
        if search_query:
            # Use the get_user_data function to search for users based on username
            users = get_user_data('username', search_query)  # Get users matching the search query
    else:
        # For GET requests, fetch all users
        users = get_user_data()

    # If users are found, process them
    if users:
        for user in users:
            # Make sure pkg_id exists in the user data before fetching the Package
            if 'pkg_id' in user and user['pkg_id']:
                try:
                    pkg = Package.objects.get(id=user['pkg_id'])  # Fetch the package
                    user['pkg'] = pkg.name  # Add the package name to the user data
                    user['quota'] = pkg.disk_space 
                except Package.DoesNotExist:
                    user['pkg'] = 'Unknown'  # Handle case where the package does not exist
                    user['quota'] = 'Unknown' 
            else:
                user['pkg'] = 'Unknown'
                user['quota'] = 'Unknown' 
                
            username_string = user['username']   
           
            current_month_year = datetime.now().strftime('%m-%Y')
            bandwidth = Bandwidth.objects.filter(userid=user['id'], date=current_month_year).order_by('id').first()
            total = bandwidth.total if bandwidth else 0
            
            user['bandwidth_use'] = size_display(total)

            
                        
            user['main_domain'] = Domain.objects.filter(userid=user['id']).order_by('id').first()    

    # Render the user list template with the processed users data
    return render(request, 'whm/user_limit.html', {'users': users})
    
@alogin_required 
@premium_features()   
def user_limit_set(request, userid):    

    try:
        user_obj = User.objects.get(id=userid)
    except User.DoesNotExist:
        return JsonResponse({"status": "error", "message": "User not found"})

    username_string = user_obj.username    

    if request.method != "POST":
        return JsonResponse(
            {"status": "error", "message": "Only POST allowed"}
        )

    try:
        # -------------------------
        # READ ACTION
        # -------------------------
        action = request.POST.get("action", "set")  # default = set

        # -------------------------
        # REMOVE LIMIT FLOW
        # -------------------------
        if action == "remove":
            result = remove_user_limit(username_string)

            return JsonResponse({
                "status": "success",
                "message": f"Limit removed for {username_string}",
                "data": {
                    "user": username_string,
                    "action": "remove",
                    "result": result
                }
            })

        # -------------------------
        # SET LIMIT FLOW
        # -------------------------
        cpu = request.POST.get("cpu")
        ram_mb = request.POST.get("ram_mb")

        if not cpu or not ram_mb:
            return JsonResponse({
                "status": "error",
                "message": "cpu and Ram are required"
            })

        try:
            cpu = int(cpu)
            ram_mb = int(ram_mb)
        except (TypeError, ValueError):
            return JsonResponse({
                "status": "error",
                "message": "cpu and Ram must be numbers"
            })

        if cpu <= 0 or ram_mb <= 0:
            return JsonResponse({
                "status": "error",
                "message": "cpu and Ram must be > 0"
            })

        result = set_user_limit(username_string, cpu, ram_mb)
        status = "success"
        error_words = ("error", "failed", "fail")
        if any(word in result.lower() for word in error_words):
            status = "error"




    

        return JsonResponse({
            "status": status,
            "message": result,
            "data": {
                "user": username_string,
                "action": "set",
                "cpu": cpu,
                "ram_mb": ram_mb
            }
        })

    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": str(e)
        })