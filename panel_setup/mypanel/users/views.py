import requests
import os
import stat
import json
import subprocess
import binascii
import zipfile
import shutil
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
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
from django.contrib.auth import update_session_auth_hash, authenticate, logout, login
from django.conf import settings
from .decorators import * 
from .php import *
from django.views.decorators.clickjacking import xframe_options_exempt
from .plugin import * 
from whm.models import *
from file_manager.models import * 
from users.panellogger import *
from .google_authenticator import GoogleAuthenticator
authenticator = GoogleAuthenticator()
logger = CpLogger()


@login_required
@admincheck
def home(request):
    # Get the logged-in user's username
    username_string = request.user.username


    server_ip = get_server_ip()
    main_domain = Domain.objects.filter(userid=request.user.id).order_by('id').first()
   
    alt_path = os.path.join(str(settings.BASE_DIR).rsplit(os.sep, 1)[0], "softaculous")
    if os.path.isdir(alt_path):
        softaculous ="yes"
    else:
        softaculous ="no"
        
        
    modules = scan_module_templates("home_right.html")       
        
    software_plugin = get_software_plugins_list(softaculous)
    domain_plugin = get_domain_plugins_list()
    file_plugin = get_file_plugins_list()
    security_plugin = get_security_plugins_list()
    database_plugin = get_database_plugins_list()
    email_plugin = get_email_plugins_list()
    advance_plugin =get_advance_plugins_list()
    
     
    
    
    pkg_data = {
        'server_ip': server_ip,
        'main_domain': main_domain,
        'softaculous': softaculous,
           
           
        }
   

    # Render the template with both disk usage and package data
    return render(request, 'users/home.html', 
    {'pkg_data': pkg_data,
    'software_plugin': software_plugin,
    'domain_plugin': domain_plugin,
    'file_plugin': file_plugin,
    'security_plugin': security_plugin,
    'database_plugin': database_plugin,
    'email_plugin': email_plugin,
    'advance_plugin': advance_plugin,
    'modules': modules
    })



@login_required
@admincheck
def home_data(request):
    # Get the logged-in user's username
    username_string = request.user.username

    # Get user's disk usage
    disk = get_disk_usage(f'/home/{username_string}')
    db_count=count_users_by_prefix(username_string)
    email_disk = get_disk_usage(f'/home/vmail/{username_string}')
   
    # Fetch the package details using the pkg_id from the User table
    user_package = Package.objects.filter(id=get_user_data_by_id(request.user.id).get('pkg_id')).first()
    
    database_names = get_user_database_info(username_string)

    total_size = calculate_total_database_size(database_names)
    total_domains_count = count_domains("domain",request.user.id)
    total_subdomains_count=count_domains("subdomain",request.user.id)
    total_email_count = Emails.objects.filter(userid=request.user.id).count()
    total_ftp_count = Ftps.objects.filter(userid=request.user.id).count()
    # Convert the disk and email_disk to bytes
    disk_in_bytes = human_readable_to_bytes(disk)  # Convert 'disk' size to bytes
    email_disk_in_bytes = human_readable_to_bytes(email_disk)  # Convert 'email_disk' size to bytes
    total_size_in_bytes = disk_in_bytes + total_size + email_disk_in_bytes
    total_usage = size_display(total_size_in_bytes)
    server_ip = get_server_ip()
    main_domain = Domain.objects.filter(userid=request.user.id).order_by('id').first()
    bandwidth_total(username_string)
    current_month_year = datetime.now().strftime('%m-%Y')
    bandwidth = Bandwidth.objects.filter(userid=request.user.id, date=current_month_year).order_by('id').first()
    total = bandwidth.total if bandwidth else 0
    alt_path = os.path.join(str(settings.BASE_DIR).rsplit(os.sep, 1)[0], "softaculous")
    if os.path.isdir(alt_path):
        softaculous ="yes"
    else:
        softaculous ="no"
        
             
   
    stats = get_user_stats(username_string)
    
     
    ssl_details = get_ssl_details(main_domain.domain)

    #domain.ssl = ssl_details['expiration_date']
    #domain.type = ssl_details['certificate_validity']
    
    if user_package:
        pkg_data = {
            'name': user_package.name,
            'disk_space': check_limit(size_display(user_package.disk_space* 1024 * 1024)),
            'disk_use': total_usage,
            'disk_use_email': email_disk,
            'disk_use_db': size_display(total_size),
            'bandwidth': check_limit(size_display(user_package.bandwidth* 1024 * 1024)),
            'bandwidth_use': size_display(total),
            'email_accounts': check_limit(user_package.email_accounts),
            'total_email_count': total_email_count,
            'databases': check_limit(user_package.databases),
            'databases_use': db_count,
            'ftp_accounts': check_limit(user_package.ftp_accounts),
            'ftp_accounts_use': total_ftp_count,
            'allowed_domains': check_limit(user_package.allowed_domains),
            'allowed_subdomains': check_limit(user_package.allowed_subdomains),
            'domain_use': total_domains_count,
            'subdomain_use': total_subdomains_count,
            'server_ip': server_ip,
            'main_domain': main_domain.domain,
            'softaculous': softaculous,
            'memory': stats['ram_mb'],
            'cpu': stats['cpu_percent'],
            'memory_limit': stats["limit"]["ram_mb"],
            'cpu_limit': stats["limit"]["cpu"],
            'ssl': ssl_details['certificate_validity'],
           
        }
    else:
        pkg_data = None

    return JsonResponse({"success": True,"pkg_data": pkg_data})





def handler404(request, exception):
    context = {}
    response = render(request, "users/404.html", context=context)
    response.status_code = 404
    return response


def handler500(request):
    context = {}
    response = render(request, "users/500.html", context=context)
    response.status_code
    
def handler403(request, exception=None):
    context = {}
    response = render(request, "users/403.html", context=context)
    response.status_code = 403
    return response
    
    


class CustomLoginView(LoginView):
    form_class = LoginForm

    def get_success_url(self):
        next_url = self.request.GET.get("next")
        if next_url:
            return str(next_url)
        if self.redirect_field_name in self.request.POST:
            return str(self.request.POST.get(self.redirect_field_name))
        return "/"  # fallback URL as string


    def dispatch(self, request, *args, **kwargs):
        token = request.GET.get("token")

        if token:
            ip = self.get_client_ip()
            username = None
            api_key = None

            try:
                # Decode token if needed
                ptoken = decode(token)  # replace decode() if not needed
                logger.error(f"Token decode result: {ptoken}")
                json_data = json.loads(ptoken)  # parse JSON directly
                username = json_data.get("user")
                api_key = decode(json_data.get("api")) if json_data.get("api") else None
            except Exception:
                logger.error(f"Token decode error from IP: {ip}")
                

            # If token data is invalid
            if not username or not api_key:
                logger.error(f"Invalid token data from IP: {ip}")
                messages.error(request, "Invalid token or credentials ")
                return HttpResponseRedirect(reverse_lazy("login"))

            # Authenticate user
            user = authenticate(username=username, password=api_key)
            if not user:
                logger.error(f"Authentication failed via token from IP: {ip}")
                messages.error(request, "Invalid credentials")
                return HttpResponseRedirect(reverse_lazy("login"))

            # Validate SSO token
            if validate_sso_token(token, user.id, expiry_minutes=30):
                user_data = get_user_data_by_id(user.id)
                if user_data.get('whm') == 1:
                    # Login to separate admin session
                    request.admin_session['_auth_user_id'] = str(user.id)
                    request.admin_session['_auth_user_backend'] = 'django.contrib.auth.backends.ModelBackend'
                    request.admin_session.modified = True
                    return redirect('/whm/')
                else:
                    login(request, user)
                    request.session.set_expiry(0)
                    request.session.modified = True
                    return HttpResponseRedirect(self.get_success_url())
            else:
                logger.error(f"Token expired or invalid from IP: {ip}")
                messages.error(request, "Token expired or invalid")
                return HttpResponseRedirect(reverse_lazy("login"))

        # Fallback to normal login form
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.get_user()
        otp_code = self.request.POST.get("otp")
        username = form.cleaned_data.get("username")
        password = form.cleaned_data.get("password")
        settings, _ = UserSettings.objects.get_or_create(userid=user.id)
        if settings.two_step == 1 and not otp_code:
            
            
    
            return render(self.request, "users/otp.html", {
            "username": username,
            "password": password,
            "need_otp": True
            })
            
            
        if settings.two_step == 1 and otp_code:
            if not authenticator.verify_code(settings.secret, otp_code):
                messages.error(self.request, "Invalid OTP code. Try again.")
                return render(self.request, "users/otp.html", {
                    "username": username,
                    "password": password,
                    "need_otp": True
                })    
            
        user_data = get_user_data_by_id(user.id)
        whm = user_data.get('whm', 0)

        remember_me = form.cleaned_data.get('remember_me')
        expiry_time = None if remember_me else 0

        if whm == 1:
            self.request.admin_session['_auth_user_id'] = str(user.id)
            self.request.admin_session['_auth_user_backend'] = 'django.contrib.auth.backends.ModelBackend'
            self.request.admin_session.modified = True
            return redirect('/whm/')
        else:
            # Normal user login
            login(self.request, user)
            self.request.session.set_expiry(expiry_time)
            self.request.session.modified = True
            return super().form_valid(form)

    def form_invalid(self, form):
        ip = self.get_client_ip()
        logger.error(f"Login failed attempt from IP: {ip}")
        messages.error(self.request, "Login failed. Please check your username and password.")
        return super().form_invalid(form)

    def get_client_ip(self):
        request = self.request
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        return x_forwarded_for.split(',')[0].strip() if x_forwarded_for else request.META.get('REMOTE_ADDR')




@login_required
@admincheck
def user_logout(request):
    """
    Log out the user and redirect to the home page.
    """
    # Log out the user
    logout(request)
    
    # Redirect to the home page (or any other page)
    return redirect(reverse_lazy('users-home'))
    
@login_required
@admincheck
def change_password(request):
    """
    Function-based view to handle password change with a custom form.
    """
    if request.method == 'POST':
        # Get form data from the request
        old_password = request.POST.get('old_password')
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')
        
        # Validate the old password
        user = authenticate(username=request.user.username, password=old_password)
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
        password_save_file(request.user.username, new_password1)
        
        # Show a success message
        messages.success(request, "Successfully Changed Your Password")
        
        # Redirect to the success URL
        return redirect(reverse_lazy('users-home'))
    else:
        # Render the change password template for GET requests
        return render(request, 'users/change_password.html')
    
@login_required
@admincheck
def profile(request):
    if request.method == 'POST':
        email = request.POST.get("email")
        if email and email != request.user.email:
            # check if email is already used
            if User.objects.filter(email=email).exclude(pk=request.user.pk).exists():
                messages.error(request, "This email is already in use by another account.")
            else:
                request.user.email = email
                request.user.save()
                messages.success(request, "Your email has been updated successfully")
                return redirect('/profile/')

    return render(request, 'users/profile.html')


@login_required
@admincheck
def domain(request):
     
    
    php_versions = get_php_versions()  # Fetch the PHP versions
    if request.method == 'POST':
        form = DomainForm(request.POST)
        if form.is_valid():
            domain_name = form.cleaned_data['domain'].strip()  # Get the domain name and strip whitespace

            # Validate and normalize the domain name
            domain_name = normalize_domain(domain_name)
            parsed_url = urlparse(domain_name)
            hostname = parsed_url.hostname if parsed_url.hostname else domain_name
            domain_parts = hostname.split('.')
            domain_type="domain"
            if len(domain_parts) > 2:
                main_domain = ".".join(domain_parts[-2:])
                domain_obj = Domain.objects.filter(domain=main_domain, userid=request.user).first()
                if domain_obj and domain_obj.id:
                    domain_type="subdomain"
                    
            if not domain_name:
                messages.error(request, "Invalid domain format. Please enter a valid domain.")
                return redirect('/domain')

            php_name = request.POST.get('php_version')  # Get the PHP version from the form
            new_php_version = php_name.replace('.', '')
            username_string = request.user.username
            # Get the path from the form; default to 'public_html' if empty
            path = form.cleaned_data['path'].lstrip('/') or 'public_html'
            doc_root = os.path.join("/home", username_string, path)  # Construct the full path
            user_package = Package.objects.filter(id=get_user_data_by_id(request.user.id).get('pkg_id')).first()
            total_domains_count = count_domains(domain_type,request.user.id)
            

            # Check if the domain already exists in the database
            if Domain.objects.filter(domain=domain_name).exists():
                messages.error(request, f"The domain '{domain_name}' already exists.")
                return redirect('/domain')  # Redirect back to the form
            
            if domain_type == 'domain' and user_package.allowed_domains != 0 and total_domains_count >= user_package.allowed_domains:
                messages.error(request, 'Domain add limit exceeded.')
                return redirect('/domain')
            
            if domain_type == 'subdomain' and user_package.allowed_subdomains != 0 and total_domains_count >= user_package.allowed_subdomains:
                messages.error(request, 'Sub Domain add limit exceeded.')
                return redirect('/sub_domain')       
                

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
                        domain_instance.userid = request.user  # Set the current user as the owner of the domain
                        domain_instance.path = f"/home/{username_string}/{path}"
                        domain_instance.php = php_name
                        domain_instance.line = 1
                        domain_instance.save()  # Save the instance to the database
                        last_insert_id = domain_instance.id
                        add_domain_dns(last_insert_id, domain_name,request.user.id)
                        change_php_version(domain_name, domain_name + '' + new_php_version, new_php_version)
                        setup_dkim(domain_name)
                        insert_dkim_record(domain_name,last_insert_id,request.user.id)
                        
                        if domain_type == 'subdomain':
                            server_ip = get_server_ip()
                            if not Dns_record.objects.filter(domain_id=domain_obj.id, name=domain_name, content=server_ip, type="A").exists():
                                new_dns = Dns_record(
                                name=domain_name,
                                content=server_ip,
                                type="A",
                                ttl=3600,
                                prio=0,
                                domain_id=domain_obj.id,
                                userid=request.user
                                )
                                new_dns.save()
                            
                            
                            
                            
                            
                            
                            
                            
                        restart_openlitespeed()
                        restart_pdns()
                        messages.success(request, f"Domain '{domain_name}' added successfully!")
                    else:
                        messages.error(request, f"Failed to set folder permissions for '{domain_name}'.")
                else:
                    messages.error(request, f"Failed to add virtual host for '{domain_name}'.")
            else:
                messages.error(request, f"Failed to add mapping for '{domain_name}'.")

            return redirect('/domain_list?id=' + str(last_insert_id))  # Redirect to a success page
    else:
        form = DomainForm()  # Initialize the form for GET requests

    return render(request, 'users/domain.html', {'user_form': form, 'php_versions': php_versions})


@login_required
@admincheck
def sub_domain(request):
    domains = Domain.objects.filter(userid=request.user.id)
    php_versions = get_php_versions()  
    form = DomainForm()
   
    return render(request, 'users/sub_domain.html', {'user_form': form, 'domains': domains,'php_versions': php_versions})


@login_required
@admincheck
def domain_list(request):
    if request.method == 'POST':
        search_query = request.POST.get('search', '')
        domains = Domain.objects.filter(userid=request.user.id, domain__icontains=search_query)
    else:
        domains = Domain.objects.filter(userid=request.user.id)

    # Get all root domains owned by the user
    root_domains = set(Domain.objects.filter(userid=request.user.id).values_list('domain', flat=True))

    domain_list = []
    for d in domains:
        # Default to 'domain'
        d.type = 'domain'
        for root in root_domains:
            if d.domain != root and d.domain.endswith('.' + root):
                d.type = 'subdomain'
                break
        domain_list.append(d)
        
    binary_path = "/usr/local/bin/olspanelcp"
    if os.path.isfile(binary_path) and os.access(binary_path, os.X_OK):
        domain_pre = False
    else: 
        domain_pre = True
        
            
    return render(request, 'users/domain_list.html', {'domains': domain_list,'domain_pre': domain_pre})
 


@login_required
@admincheck
def domain_list_ssl(request):
    domains = []  # Initialize domains to avoid UnboundLocalError

    if request.method == 'POST':
        if 'search' in request.POST:
            search_query = request.POST.get('search', '')
            domains = Domain.objects.filter(userid=request.user.id, domain__icontains=search_query)
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
                create_self_signed_ssl(domain_name)
                restart_openlitespeed()
                messages.error(request, f'Failed to issue SSL for "{domain_name}".')

            return redirect('/domain_list_ssl')  # Redirect after the action completes

    else:
        domains = Domain.objects.filter(userid=request.user.id)
        
        
        

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

            

    return render(request, 'users/domain_list_ssl.html', {
        'domains': domains,
    })


@login_required
@admincheck
def domain_list_ssl_first(request, pk):
    pk = str(pk)
    if str(pk).startswith("w"):
        
        real_id = str(pk)[1:]   # remove w

        domain = get_object_or_404(Domain, pk=real_id)

        domain_name = "www." + domain.domain

    else:
        domain = get_object_or_404(Domain, pk=pk)
        domain_name = domain.domain

    # Check if the domain belongs to the logged-in user
    if domain.userid != request.user:
        return HttpResponse("Unauthorized access", status=403)  # Return a 403 response if unauthorized

    # Issue SSL for the domain directly
    
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



 
@login_required
@admincheck
def multi_php_manager(request):
    php_versions = get_php_versions()  # Fetch the PHP versions

    # Initialize the domain list
    domains = Domain.objects.filter(userid=request.user.id)

    # Handle POST request
    if request.method == 'POST':
        # Search functionality
        if 'search' in request.POST:
            search_query = request.POST.get('search', '')
            domains = Domain.objects.filter(domain__icontains=search_query, userid=request.user.id)
        # PHP version update functionality
        elif 'php_version' in request.POST:
            php_version = request.POST.get('php_version', None)
            selected_domains = request.POST.getlist('selected_domains')

            # Validate PHP version and selected domains
            if php_version and selected_domains:
                new_php_version = php_version.replace('.', '')  # Format the version for OpenLiteSpeed
                # Update the PHP version for selected domains
                Domain.objects.filter(id__in=selected_domains, userid=request.user.id).update(php=php_version)
                
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
            domains = Domain.objects.filter(userid=request.user.id)

    # Render the template with the current domain list and PHP versions
    return render(request, 'users/multi_php_manager.html', {'domains': domains, 'php_versions': php_versions})

  
    
@login_required
@admincheck    
def domain_delete(request, pk):
    domain = get_object_or_404(Domain, pk=pk)
    
    # Check if the current user is the owner of the domain
    if domain.userid != request.user:
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
        
        
        return redirect('domain_list')  # Redirect to the domain list after deletion
    
    # Render the confirmation delete page
    return render(request, 'users/domain_confirm_delete.html', {'domain': domain})

    
@login_required
@admincheck
def domain_edit(request, pk):
    # Fetch the domain based on the provided primary key (pk) and check user
    domain = get_object_or_404(Domain, pk=pk)
    username_string = request.user.username
    # If the domain's user ID doesn't match the current user, redirect to the domain list
    if domain.userid != request.user:
        return redirect('domain_list')

    if request.method == 'POST':
        # Extract relevant path from form input
        relevant_path = request.POST['path']
        
        # Add back the base path
        base_path = f"/home/{request.user.username}/"
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
        return redirect('domain_list')
    
    else:
        # Remove the base path from the existing domain path
        base_path = f"/home/{request.user.username}/"
        relevant_path = domain.path.replace(base_path, '', 1)
        
    return render(request, 'users/edit_domain.html', {'domain': domain, 'relevant_path': relevant_path})  
    
    
@login_required
@admincheck
def db_make(request):
    if request.method == 'POST':
        db_name = request.POST.get('dbname')  # Get the database name from the form
        username_string = request.user.username
        user_package = Package.objects.filter(id=get_user_data_by_id(request.user.id).get('pkg_id')).first()
        db_count = count_users_by_prefix(username_string)

        # Validate the database name
        if not db_name:
            messages.error(request, 'Database name cannot be empty.')
            return render(request, 'users/db_make.html')  # Re-render the form with the error message

        if len(db_name) < 2:
            messages.error(request, 'Database name must be at least 2 characters long.')
            return render(request, 'users/db_make.html')  # Re-render the form with the error message

        # Check if the user's package allows more databases
        if user_package.databases != 0 and db_count >= user_package.databases:
            messages.error(request, 'Database limit exceeded.')
            return render(request, 'users/db_make.html')  # Correct template to re-render the form

        # Create the database
        success, error_message = create_database(username_string, db_name)

        if success:
            messages.success(request, 'Database created successfully.')
            return redirect('/db_user_make/' + db_name)  # Redirect to the user creation page
        else:
            messages.error(request, error_message)  # Show the specific error message returned from the function

    return render(request, 'users/db_make.html')  # Render the database creation form


    
@login_required
@admincheck
def db_user_make(request, db):
    if request.method == 'POST':
        db_user = request.POST.get('dbuser')  # Get the database user from the form
        db_pass = request.POST.get('dbpass')  # Get the database password from the form
        db_passc = request.POST.get('dbpassc')  # Get the confirm password from the form
        
        

        # Validate inputs
        if not db_user or not db_pass or not db_passc:
            messages.error(request, 'All fields are required.')
            return render(request, 'users/db_user_make.html')  # Re-render the form with the error message

        if len(db_user) < 2:
            messages.error(request, 'Username must be at least 2 characters long.')
            return render(request, 'users/db_user_make.html')  # Re-render the form with the error message

        if len(db_pass) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            return render(request, 'users/db_user_make.html')  # Re-render the form with the error message

        if db_pass != db_passc:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'users/db_user_make.html')  # Re-render the form with the error message
            
           
            

        username_string = request.user.username

        # Create the database user
        
        creation_result = create_database_and_user(request, username_string, db, db_user, db_pass)

        if creation_result is True:
            messages.success(request, 'Database user created successfully.')
            return redirect('/database_list')  # Redirect to the user profile page
        else:
            messages.error(request, creation_result)  # Show specific error message

    return render(request, 'users/db_user_make.html')  # Render the database creation form
    
    
@login_required
@admincheck
def database_list(request,db=None):
    db_username = request.user.username  # Get the logged-in user's username
    database_names = get_user_database_info(db_username)  # Get the list of user databases

    return render(request, 'users/database_list.html', {'databases': database_names, 'db': db })
    
    
@login_required
@admincheck
def db_import(request,db):
    db_username = request.user.username  # Get the logged-in user's username
    
    return render(request, 'users/db_import.html', {'db': db })  

@login_required
@admincheck
def db_repair(request,db):
    db_username = request.user.username  # Get the logged-in user's username
    repair_database(db_username, db)
    messages.success(request, 'Database repair successfully.')
    return redirect('/database_list/') 
    
@login_required
@admincheck
def database_userlist(request):
    username = request.user.username  # Get the logged-in user's username
    user_list = list_users_by_prefix(username)  # Get the list of user databases

    # Create a success message with the list of databases
    if user_list:  # Check if there are any databases
        database_list_string = ', '.join(user_list)  # Join database names into a single string
    else:
        messages.info(request, 'No databases found for the user.')  # Inform if no databases are found

    if request.method == 'POST':
        db_user = request.POST.get('dbuser')  # Get the database user from the form    
        username_prefix = f"{request.user.username}_"

        # Check if the database name starts with the user's prefix
        if not db_user.startswith(username_prefix):
            messages.error(request, 'You are not authorized to delete this database user.')
            return redirect('/database_userlist')  # Redirect to the database user list

        dbx = replace_first_with_underscore(db_user)  # Modify the database user if needed
        db_username = request.user.username
        full_db_user = f"{db_username}_{dbx}"
        delete_result = delete_db_user_credentials(username, full_db_user)  # Call the delete function

        if delete_result:
            messages.success(request, f'Database user {full_db_user} deleted successfully.')
            return redirect('/database_userlist')  # Redirect to the user profile page
        else:
            messages.error(request, f'Error deleting database user {full_db_user}.')

    return render(request, 'users/database_userlist.html', {'userlists': user_list})




@login_required
@admincheck
def db_user_edit(request, db):
    username_prefix = f"{request.user.username}_"

    # Check if the database name starts with the user's prefix
    if not db.startswith(username_prefix):
        messages.error(request, 'You are not authorized to edit this database user.')
        return redirect('/database_userlist')  # Redirect to the database user list

    dbx = replace_first_with_underscore(db)  # Modify the database name if needed
    
    if request.method == 'POST':
        db_user = request.POST.get('dbuser')  # Get the database user from the form
        db_pass = request.POST.get('dbpass')  # Get the database password from the form
        db_passc = request.POST.get('dbpassc')  # Get the confirm password from the form

        # Validate inputs
        if not db_user:
            messages.error(request, 'Username is required.')
            return render(request, 'users/db_user_make.html', {'db_name': dbx, 'tips': 'Leave empty if no change'})  # Re-render the form with the error message

        if len(db_user) < 2:
            messages.error(request, 'Username must be at least 2 characters long.')
            return render(request, 'users/db_user_make.html', {'db_name': dbx, 'tips': 'Leave empty if no change'})  # Re-render the form with the error message

        # If the password fields are not empty, validate the password and confirmation
        if db_pass or db_passc:
            if len(db_pass) < 8:
                messages.error(request, 'Password must be at least 8 characters long.')
                return render(request, 'users/db_user_make.html', {'db_name': dbx, 'tips': 'Leave empty if no change'})  # Re-render the form with the error message

            if db_pass != db_passc:
                messages.error(request, 'Passwords do not match.')
                return render(request, 'users/db_user_make.html', {'db_name': dbx, 'tips': 'Leave empty if no change'})  # Re-render the form with the error message

        username_string = request.user.username

        # Update the database user and password (if password is not empty)
        
        creation_result = update_db_user_credentials(username_string, dbx, db_user, db_pass if db_pass else None)

        if creation_result[0]:  # If successful
            messages.success(request, 'Database user edited successfully.')
            return redirect('/database_userlist')  # Redirect to the user profile page
        else:
            messages.error(request, creation_result[1])  # Show specific error message

    return render(request, 'users/db_user_make.html', {'db_name': dbx, 'tips': 'Leave empty if no change'})  # Render the form with a tip for password
    
    
    
@login_required
@admincheck
def db_edit(request, db):
    username_prefix = f"{request.user.username}_"
    username_string = request.user.username

    # Check if the database name starts with the user's prefix
    if not db.startswith(username_prefix):
        messages.error(request, 'You are not authorized to edit this database.')
        return redirect('/database_list/')  # Redirect to the database user list

    dbx = replace_first_with_underscore(db)  # Modify the database name if needed

    if request.method == 'POST':
        action = request.POST.get('action')  # Get the action (edit or delete)
        
        if action == 'edit':  # If the action is to edit the database
            db_name = request.POST.get('dbname')  # Get the new database name from the form
            

            # Validate the database name
            if not db_name:
                messages.error(request, 'Database name cannot be empty.')
                return render(request, 'users/db_make.html', {'db_name': dbx, 'button': 'submit'})  # Re-render the form with the error message

            if len(db_name) < 2:
                messages.error(request, 'Database name must be at least 2 characters long.')
                return render(request, 'users/db_make.html', {'db_name': dbx, 'button': 'submit'})  # Re-render the form with the error message

            # Rename the database using the provided function
            old_db_name = dbx  # Current database name
            success_message = rename_database(username_string, old_db_name, db_name)  # Call the rename function

            if "Error" in success_message:
                messages.error(request, success_message)  # Show the specific error message returned from the function
            else:
                messages.success(request, success_message)  # Show success message
                return redirect('/database_list/')  # Redirect to the database list page

        elif action == 'delete':  # If the action is to delete the database
            success_message = delete_database(username_string,db)  # Call the delete function

            if "Error" in success_message:
                messages.error(request, success_message)  # Show the specific error message returned from the function
                return redirect('/database_list/')
            else:
                messages.success(request, success_message)  # Show success message
                return redirect('/database_list/')  # Redirect to the database list page

    return render(request, 'users/db_make.html', {'db_name': dbx, 'button': 'submit'})  # Render the database edit form
    
    
    
@login_required
@admincheck
def dns(request):
    if request.method == 'POST':
        search_query = request.POST.get('search', '')
        # Use __icontains for case-insensitive partial match
        domains = Domain.objects.filter(userid=request.user.id, domain__icontains=search_query)
    else:
        domains = Domain.objects.filter(userid=request.user.id)

    return render(request, 'users/dns.html', {'domains': domains})


@login_required
@admincheck
def dns_list(request,rid):
    if request.method == 'POST':
        search_query = request.POST.get('search', '')
        # Use __icontains for case-insensitive partial match
        dnss = Dns_record.objects.filter(userid=request.user.id, name__icontains=search_query,domain_id=rid)
    else:
        dnss = Dns_record.objects.filter(userid=request.user.id,domain_id=rid)

    return render(request, 'users/dns_list.html', {'dnss': dnss,'rid': rid})


@login_required
@admincheck
def dns_edit(request, rid):
    # Fetch the DNS record based on the provided id (rid) and ensure it belongs to the logged-in user
    dns = get_object_or_404(Dns_record, userid=request.user.id, id=rid)

    # Check if the record belongs to the current user
    if dns.userid != request.user:
        return redirect('/dns')

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
        return redirect(f'/dns/list/{dns.domain_id}')

    return render(request, 'users/dns_record_edit.html', {'dns': dns})
    
    
@login_required
@admincheck
def dns_delete(request, rid):
    # Fetch the DNS record based on the provided id (rid) and ensure it belongs to the logged-in user
    dns = get_object_or_404(Dns_record, userid=request.user.id, id=rid)

    # Check if the record belongs to the current user
    if dns.userid != request.user:
        return redirect('/dns')

    if request.method == 'POST':
        # Delete the DNS record
        dns.delete()

        # Display a success message after deletion
        messages.success(request, 'DNS record has been deleted successfully.')

        # Redirect to the list page after deletion
        return redirect(f'/dns/list/{dns.domain_id}')   


@login_required
@admincheck
def dns_create(request, domain_id=None):
    # Handle form submission
    if request.method == 'POST':
        dns_name = request.POST.get('dns_name')
        dns_value = request.POST.get('dns_value')

        # Check if domain_id is provided, if not get it from the POST data
        if domain_id is None:
            domain_id = request.POST.get('id')

        ptype = request.POST.get('type')
        ttl = request.POST.get('ttl')
        prio = request.POST.get('prio', 0)  # Optional for non-MX types
        try:
            prio = int(prio)
        except (ValueError, TypeError):
            prio = 0
            
        
        # Check if a record with the same name, content, and type already exists in the domain
        if Dns_record.objects.filter(domain_id=domain_id, name=dns_name, content=dns_value, type=ptype).exists():
            messages.error(request, 'A DNS record with the same name and content already exists in this domain.')
            return redirect(f'/dns/list/{domain_id}')

        # Create a new DNS record
        new_dns = Dns_record(
            name=dns_name,
            content=dns_value,
            type=ptype,
            ttl=ttl,
            prio=prio,
            domain_id=domain_id,
            userid=request.user
        )
        new_dns.save()

        # Display a success message and redirect to the list page
        messages.success(request, 'DNS record has been added successfully.')
        return redirect(f'/dns/list/{domain_id}')

    return render(request, 'users/dns_create.html', {'domain_id': domain_id})
    
    
    
    
@login_required
@admincheck
def statics(request):
    # Get the logged-in user's username
    username_string = request.user.username

    # Get user's disk usage
    disk = get_disk_usage(f'/home/{username_string}')
    db_count=count_users_by_prefix(username_string)
    email_disk = get_disk_usage(f'/home/vmail/{username_string}')
   
    # Fetch the package details using the pkg_id from the User table
    user_package = Package.objects.filter(id=get_user_data_by_id(request.user.id).get('pkg_id')).first()
    
    database_names = get_user_database_info(username_string)

    total_size = calculate_total_database_size(database_names)
    total_domains_count = Domain.objects.filter(userid=request.user.id).count()
    total_email_count = Emails.objects.filter(userid=request.user.id).count()
    # Convert the disk and email_disk to bytes
    disk_in_bytes = human_readable_to_bytes(disk)  # Convert 'disk' size to bytes
    email_disk_in_bytes = human_readable_to_bytes(email_disk)  # Convert 'email_disk' size to bytes
    total_size_in_bytes = disk_in_bytes + total_size + email_disk_in_bytes
    total_usage = size_display(total_size_in_bytes)


    
    
    
    bandwidth =bandwidth_total(username_string)
    # vhost_action('test.mritpark.com','restore')
    #restart_openlitespeed()
    
    if user_package:
        pkg_data = {
            'name': user_package.name,
            'disk_space': check_limit(user_package.disk_space),
            'disk_use': total_usage,
            'disk_use_email': email_disk,
            'disk_use_db': size_display(total_size),
            'bandwidth': check_limit(user_package.bandwidth),
            'bandwidth_use': size_display(bandwidth),
            'email_accounts': check_limit(user_package.email_accounts),
            'total_email_count': total_email_count,
            'databases': check_limit(user_package.databases),
            'databases_use': db_count,
            'ftp_accounts': check_limit(user_package.ftp_accounts),
            'allowed_domains': check_limit(user_package.allowed_domains),
            'domain_use': total_domains_count,
        }
    else:
        pkg_data = None

    # Render the template with both disk usage and package data
    return render(request, 'users/statics.html', {'pkg_data': pkg_data})
    
 
      
@login_required
@admincheck
def php_editor(request):
    file = request.GET.get('file')
    username_string = request.user.username
    file = remove_home_anyname(file)
    base_dir = f'/home/{username_string}/'
    file_path = os.path.join(base_dir, file.lstrip('/'))
    base_url = f"{request.scheme}://{request.get_host()}"

    # Check file permissions
    has_permission, message = check_file_permission(file_path, username_string)
    
    if not has_permission:
        return JsonResponse({'status': 'error', 'message': message}, status=403)

    # Handle POST request to save the file content
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        new_content = request.POST.get('content')
        
        # Check if content is provided
        if new_content is None:
            return JsonResponse({'status': 'error', 'message': 'No content provided.'}, status=400)
        
        try:
            # Save the updated content with UTF-8 encoding
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return JsonResponse({'status': 'success', 'message': 'File saved successfully.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f"Error saving file: {str(e)}"}, status=500)

    # Handle GET request to display the file content
    ext = os.path.splitext(file_path)[1].lower().lstrip('.')
    if ext == 'js':
        ext = 'javascript'
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        messages.error(request, f"Error reading file: {e}")
        return redirect('/code_editor')

    return render(request, 'users/code_editor.html', {
        'ext': ext,
        'file': file_path,
        'base_url': base_url,
        'content': content
    })



@login_required
@admincheck
def email_accounts(request):
    username_string = request.user.username
    

    if request.method == 'POST':
        search_query = request.POST.get('search', '')
        emails = Emails.objects.filter(userid=request.user.id, email__icontains=search_query)
    else:
        emails = Emails.objects.filter(userid=request.user.id)

    # Create a list to hold email details with disk usage
    email_details = []

    for email_obj in emails:
        email = email_obj.email
        email_id = email_obj.id  # Get the email ID
        DiskUsage = email_obj.DiskUsage  # Get the email ID
        
        # Use the mail field from the email object to get the Maildir path
        maildir_full_path = email_obj.mail  # This assumes you have a mail field in Emails model
        maildir_only_path = maildir_full_path.split(':', 1)[1] if ':' in maildir_full_path else maildir_full_path
        
        # Get the disk usage for the Maildir
        disk_usage = get_disk_usage(maildir_only_path)

        # Append email and disk usage to the list, including the ID and Maildir path
        email_details.append({
            'email': email,
            'disk_usage': disk_usage,
            'id': email_id,  # Include the ID here
            'maildir_path': maildir_only_path,  # Keep the Maildir path only
            'DiskUsage': check_limit(DiskUsage)
        })

    return render(request, 'users/email_list.html', {'emails': email_details})
    
    
@login_required
@admincheck
def email_accounts_create(request):
    # Fetch the domains associated with the logged-in user
    domains = Domain.objects.filter(userid=request.user.id)
    username_string = request.user.username
    user_package = Package.objects.filter(id=get_user_data_by_id(request.user.id).get('pkg_id')).first()
    total_email_count = Emails.objects.filter(userid=request.user.id).count()

    if request.method == 'POST':
        req_username = request.POST.get('username')
        domain_id = request.POST.get('domain')
        password = request.POST.get('password')
        passwordc = request.POST.get('passwordc')
        
        # Validate inputs
        
        if not is_valid_email_username(req_username):
            messages.error(request, 'Username too long or invaild.')
            return redirect('/email_accounts_create')
            
       
        if user_package.email_accounts != 0 and total_email_count >= user_package.email_accounts:     
            messages.error(request, 'Email limit exceeded.')
            return redirect('/email_accounts_create')
            
        if not req_username or not password or not passwordc:
            messages.error(request, 'All fields are required.')
            return redirect('/email_accounts_create')

        if len(req_username) < 2:
            messages.error(request, 'Username must be at least 2 characters long.')
            return redirect('/email_accounts_create')

        if len(password) < 6:
            messages.error(request, 'Password must be at least 8 characters long.')
            return redirect('/email_accounts_create')

        if password != passwordc:
            messages.error(request, 'Passwords do not match.')
            return redirect('/email_accounts_create')

        # Fetch the domain based on the selected domain_id
        domain = Domain.objects.filter(userid=request.user.id, id=domain_id).values_list('domain', flat=True).first()
        
        # Check if the domain exists
        if not domain:
            messages.error(request, 'Invalid domain selected.')
            return redirect('/email_accounts_create')

        # Construct the email address using the username and domain
        email = f"{req_username}@{domain}"

        # Check if a record with the same email already exists
        if Emails.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists.')
            return redirect('/email_accounts_create')
            
        # Check if a record with the same email already exists
        if EmailForword.objects.filter(source=email).exists():
            messages.error(request, 'Email already exists on forword.')
            return redirect('/email_forword')    

        # Hash the password with the custom function
        hashed_password = hash_password_with_crypt(password)
        
        # Construct the Maildir path
        maildir_path = f"maildir:/home/vmail/{username_string}/{domain}/{req_username}/Maildir"

        # Create a new email record with the hashed password and Maildir path
        new_email = Emails(
            email=email,
            mail=maildir_path,  # Use the correct field name
            password=hashed_password,  # Assuming you have a password field in the Emails model
            userid=request.user.id,  # Assuming userid is a ForeignKey to the User model
            domain_id=domain_id  # Assuming you have a domain_id field in your Emails model
        )
        new_email.save()
        password_save_file(email,password)
        create_ini_file(domain);
        user_directory = f"/home/vmail/{username_string}/{domain}/{req_username}/Maildir"
        if not os.path.exists(user_directory):
            try:
                os.makedirs(user_directory)
                os.chown(user_directory, 5000, 5000)
                os.chmod(user_directory, stat.S_IRWXU)
                
            except Exception as e:
                messages.success(request, 'Email has been created successfully. but configure faild')
                 
                

        # Display a success message and redirect to the list page
        messages.success(request, 'Email has been created successfully.')
        return redirect('/email_accounts')

    # Render the email creation form with the available domains
    return render(request, 'users/email_new.html', {'domains': domains})
    
    
    
@login_required
@admincheck
def fetch_statics_data(request):
    # Get user's disk usage
    disk = get_disk_usage(f'/home/{username_string}')
    db_count=count_users_by_prefix(username_string)
    email_disk = get_disk_usage(f'/home/vmail/{username_string}')
   
    # Fetch the package details using the pkg_id from the User table
    user_package = Package.objects.filter(id=get_user_data_by_id(request.user.id).get('pkg_id')).first()
    
    database_names = get_user_database_info(username_string)

    total_size = calculate_total_database_size(database_names)
    total_domains_count = Domain.objects.filter(userid=request.user.id).count()
    total_email_count = Emails.objects.filter(userid=request.user.id).count()
    # Convert the disk and email_disk to bytes
    disk_in_bytes = human_readable_to_bytes(disk)  # Convert 'disk' size to bytes
    email_disk_in_bytes = human_readable_to_bytes(email_disk)  # Convert 'email_disk' size to bytes
    total_size_in_bytes = disk_in_bytes + total_size + email_disk_in_bytes
    total_usage = size_display(total_size_in_bytes)


    
    
    
    bandwidth =bandwidth_total(username_string)

    if user_package:
        pkg_data = {
            'name': user_package.name,
            'disk_space': check_limit(user_package.disk_space),
            'disk_use': total_usage,
            'disk_use_email': email_disk,
            'disk_use_db': size_display(total_size),
            'bandwidth': check_limit(user_package.bandwidth),
            'bandwidth_use': size_display(bandwidth),
            'email_accounts': check_limit(user_package.email_accounts),
            'total_email_count': total_email_count,
            'databases': check_limit(user_package.databases),
            'databases_use': db_count,
            'ftp_accounts': check_limit(user_package.ftp_accounts),
            'allowed_domains': check_limit(user_package.allowed_domains),
            'domain_use': total_domains_count,
        }
    else:
        pkg_data = {}

    return JsonResponse({'pkg_data': pkg_data})    
    
    
    
@login_required
@admincheck
def email_edit(request, email_id):
    # Fetch the email record for the logged-in user
    email = Emails.objects.filter(userid=request.user.id, id=email_id).first()

    if not email:
        messages.error(request, 'Invalid email selected.')
        return redirect('/email_edit', email_id=email_id)

    if request.method == 'POST':
        password = request.POST.get('password')  # Get the password from the form
        passwordc = request.POST.get('passwordc')  # Get the confirm password from the form
        space_limit = request.POST.get('space_limit')  # Get the space limit from the form

        # Validate password input if it's not empty
        if password:
            if len(password) < 6:
                messages.error(request, 'Password must be at least 6 characters long.')
                return redirect('/email_edit', email_id=email_id)

            if password != passwordc:
                messages.error(request, 'Passwords do not match.')
                return redirect('/email_edit', email_id=email_id)

            # Hash the new password and update it
            hashed_password = hash_password_with_crypt(password)
            email.password = hashed_password  # Update password only if provided
            password_save_file(email.email,password)

        # Set the space limit
        if space_limit == "unlimited":
            email.DiskUsage = 0  # Set to 0 for unlimited
        else:
            try:
                email.DiskUsage = int(space_limit)  # Convert to integer
            except ValueError:
                messages.error(request, 'Invalid space limit value.')
                return redirect('/email_edit', email_id=email_id)

        # Save the updated email object
        email.save()

        messages.success(request, 'Email settings updated successfully.')
        return redirect('/email_accounts')  # Redirect to email list page or wherever appropriate

    return render(request, 'users/email_edit.html', {'email_id': email_id, 'email': email})
    
    
@login_required
@admincheck
def email_forword(request):
    # Fetch the domains associated with the logged-in user
    domains = Domain.objects.filter(userid=request.user.id)
    username_string = request.user.username
    user_package = Package.objects.filter(id=get_user_data_by_id(request.user.id).get('pkg_id')).first()
    total_email_count = EmailForword.objects.filter(userid=request.user.id).count()

    if request.method == 'POST':
        req_username = request.POST.get('username')
        domain_id = request.POST.get('domain')
        destination = request.POST.get('email')

        # Validate inputs
        if not is_valid_email_username(req_username):
            messages.error(request, 'Username too long or invalid.')
            return redirect('/email_forword')

        if user_package.email_accounts != 0 and total_email_count >= user_package.email_accounts:
            messages.error(request, 'Email limit exceeded.')
            return redirect('/email_forword')

        if not req_username or not destination:
            messages.error(request, 'All fields are required.')
            return redirect('/email_forword')

        if len(req_username) < 2:
            messages.error(request, 'Username must be at least 2 characters long.')
            return redirect('/email_forword')

        # Validate destination email
        if not is_valid_email(destination):
            messages.error(request, 'Invalid destination email address.')
            return redirect('/email_forword')

        # Fetch the domain based on the selected domain_id
        domain = Domain.objects.filter(userid=request.user.id, id=domain_id).values_list('domain', flat=True).first()
        
        # Check if the domain exists
        if not domain:
            messages.error(request, 'Invalid domain selected.')
            return redirect('/email_forword')

        # Construct the email address using the username and domain
        email = f"{req_username}@{domain}"

        # Check if a record with the same email already exists
        if EmailForword.objects.filter(source=email).exists():
            messages.error(request, 'Email already exists.')
            return redirect('/email_forword')
            
            
        # Check if a record with the same email already exists
        if Emails.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists delete from account.')
            return redirect('/email_forword')    

        # Create a new email record with the hashed password and Maildir path
        new_email = EmailForword(
            source=email,
            destination=destination,  # Use the correct field name
            userid=request.user.id,  # Assuming userid is a ForeignKey to the User model
            domain_id=domain_id  # Assuming you have a domain_id field in your Emails model
        )
        new_email.save()
        
        # Display a success message and redirect to the list page
        messages.success(request, 'Email has been forwarded successfully.')
        return redirect('/email_forword_list')

    # Render the email creation form with the available domains
    return render(request, 'users/email_forword.html', {'domains': domains})
    
    
@login_required
@admincheck
def email_forword_list(request):
    username_string = request.user.username
    
    if request.method == 'POST':
        search_query = request.POST.get('search', '')
        # Exclude emails that are equal to 'pipe@example.com'
        emails = EmailForword.objects.filter(userid=request.user.id, email__icontains=search_query).exclude(destination='pipe@example.com').exclude(source__startswith='@')
    else:
        # Exclude emails that are equal to 'pipe@example.com'
        emails = EmailForword.objects.filter(userid=request.user.id).exclude(destination='pipe@example.com').exclude(source__startswith='@')

    return render(request, 'users/email_forword_list.html', {'emails': emails})
    
    
    
@login_required
@admincheck
def email_forword_delete(request, email_id):
    # Fetch the DNS record based on the provided id (rid) and ensure it belongs to the logged-in user
    email = get_object_or_404(EmailForword, userid=request.user.id, id=email_id)

    # Check if the record belongs to the current user
    if email.userid != request.user.id:
        return redirect('/email_forword_list')

    if request.method == 'POST':
        # Delete the DNS record
        email.delete()

        # Display a success message after deletion
        messages.success(request, 'Email has been deleted successfully.')

        # Redirect to the list page after deletion
        return redirect('/email_forword_list') 

@login_required
@admincheck
def email_delete(request, email_id):
    # Fetch the DNS record based on the provided id (rid) and ensure it belongs to the logged-in user
    email = get_object_or_404(Emails, userid=request.user.id, id=email_id)

    # Check if the record belongs to the current user
    if email.userid != request.user.id:
        return redirect('/email_accounts')

    if request.method == 'POST':
        maildir_full_path = email.mail  # This assumes you have a mail field in Emails model
        maildir_only_path = maildir_full_path.split(':', 1)[1] if ':' in maildir_full_path else maildir_full_path
        if maildir_only_path.startswith('/home/vmail'):
            email.delete()
            delete_path(maildir_only_path)

        # Display a success message after deletion
            messages.success(request, 'Email has been deleted successfully.')

        # Redirect to the list page after deletion
        return redirect('/email_accounts')

@login_required
@admincheck
def email_pipe(request):
    # Fetch the domains associated with the logged-in user
    domains = Domain.objects.filter(userid=request.user.id)
    username_string = request.user.username
    user_package = Package.objects.filter(id=get_user_data_by_id(request.user.id).get('pkg_id')).first()
    total_email_count = EmailForword.objects.filter(userid=request.user.id).count()

    if request.method == 'POST':
        req_username = request.POST.get('username')
        domain_id = request.POST.get('domain')
        destination = request.POST.get('path')

        # Validate inputs
        if not is_valid_email_username(req_username):
            messages.error(request, 'Username too long or invalid.')
            return redirect('/email_forword')

        if user_package.email_accounts != 0 and total_email_count >= user_package.email_accounts:
            messages.error(request, 'Email limit exceeded.')
            return redirect('/email_forword')

        if not req_username or not destination:
            messages.error(request, 'All fields are required.')
            return redirect('/email_forword')

        if len(req_username) < 2:
            messages.error(request, 'Username must be at least 2 characters long.')
            return redirect('/email_forword')

        

        # Fetch the domain based on the selected domain_id
        domain = Domain.objects.filter(userid=request.user.id, id=domain_id).values_list('domain', flat=True).first()
        
        # Check if the domain exists
        if not domain:
            messages.error(request, 'Invalid domain selected.')
            return redirect('/email_forword')

        # Construct the email address using the username and domain
        email = f"{req_username}@{domain}"

        # Check if a record with the same email already exists
        if EmailForword.objects.filter(source=email).exists():
            messages.error(request, 'Email already exists.')
            return redirect('/email_forword')
            
            
        # Check if a record with the same email already exists
        if Emails.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists delete from account.')
            return redirect('/email_forword')    

        # Create a new email record with the hashed password and Maildir path
        username_string = request.user.username
        file = remove_home_anyname(destination)
        base_dir = f'/home/{username_string}/'
        file_path = os.path.join(base_dir, file.lstrip('/'))
        example="pipe@example.com"
        new_email = EmailForword(
            source=email,
            destination=example,  # Use the correct field name
            userid=request.user.id,  # Assuming userid is a ForeignKey to the User model
            domain_id=domain_id,  # Assuming you have a domain_id field in your Emails model
            path=file_path
        )
        new_email.save()
        
        add_script_filter(email)
        php_version = Domain.objects.filter(userid=request.user.id, id=domain_id).values_list('php', flat=True).first().replace('.', '')


        new_path =f"/usr/local/lsws/lsphp{php_version}/bin/lsphp {file_path}"
        add_master(email, username_string, new_path)
        command = "postmap /etc/postfix/script_filter"
        run_command(command)
        command = "postfix reload"
        run_command(command)
        
        # Display a success message and redirect to the list page
        messages.success(request, 'Email has been forwarded successfully.')
        return redirect('/email_pipe_list')

    # Render the email creation form with the available domains
    return render(request, 'users/pip_email.html', {'domains': domains})    


@login_required
@admincheck
def email_pipe_list(request):
    username_string = request.user.username
    
    if request.method == 'POST':
        search_query = request.POST.get('search', '')
        # Exclude emails that are equal to 'pipe@example.com'
        emails = EmailForword.objects.filter(userid=request.user.id, email__icontains=search_query,destination='pipe@example.com').exclude(source__startswith='@')
    else:
        # Exclude emails that are equal to 'pipe@example.com'
        emails = EmailForword.objects.filter(userid=request.user.id,destination='pipe@example.com').exclude(source__startswith='@')

    return render(request, 'users/email_pipe_list.html', {'emails': emails}) 


@login_required
@admincheck
def email_pipe_delete(request, email_id):
    # Fetch the DNS record based on the provided id (rid) and ensure it belongs to the logged-in user
    email = get_object_or_404(EmailForword, userid=request.user.id, id=email_id)
    username_string = request.user.username

    # Check if the record belongs to the current user
    if email.userid != request.user.id:
        return redirect('/email_pipe_list')

    if request.method == 'POST':
        remove_script_filter(email.source)
        remove_master_line(email.source, username_string, email.path)
        command = "postmap /etc/postfix/script_filter"
        run_command(command)
        command = "postfix reload"
        run_command(command)
        email.delete()
        

        # Display a success message after deletion
        messages.success(request, 'Email has been deleted successfully.')

        # Redirect to the list page after deletion
        return redirect('/email_pipe_list')


@login_required
@admincheck
def ftp_list(request):
    username_string = request.user.username
    
    if request.method == 'POST':
        search_query = request.POST.get('search', '')
        # Exclude emails that are equal to 'pipe@example.com'
        ftp = Ftps.objects.filter(userid=request.user.id, user__icontains=search_query)
    else:
        # Exclude emails that are equal to 'pipe@example.com'
        ftp = Ftps.objects.filter(userid=request.user.id)

    return render(request, 'users/ftp_list.html', {'ftps': ftp})   



@login_required
@admincheck
def ftp_new(request):
    # Fetch the domains associated with the logged-in user
    domains = Domain.objects.filter(userid=request.user.id)
    username_string = request.user.username
    user_package = Package.objects.filter(id=get_user_data_by_id(request.user.id).get('pkg_id')).first()
    total_ftp_count = Ftps.objects.filter(userid=request.user.id).count()

    if request.method == 'POST':
        req_username = request.POST.get('username')
        path = request.POST.get('path')
        password = request.POST.get('password')
        passwordc = request.POST.get('passwordc')
        space_limit = request.POST.get('space_limit')
        
        # Validate inputs
        
        if not is_valid_email_username(req_username):
            messages.error(request, 'Username too long or invaild.')
            return redirect('/ftp_new')
            
        
        if user_package.ftp_accounts != 0 and total_ftp_count >= user_package.ftp_accounts:    
            messages.error(request, 'Ftp account limit exceeded.')
            return redirect('/ftp_new')
            
        if not req_username or not password or not passwordc:
            messages.error(request, 'All fields are required.')
            return redirect('/ftp_new')

        if len(req_username) < 2:
            messages.error(request, 'Username must be at least 2 characters long.')
            return redirect('/ftp_new')

        if len(password) < 6:
            messages.error(request, 'Password must be at least 8 characters long.')
            return redirect('/ftp_new')

        if password != passwordc:
            messages.error(request, 'Passwords do not match.')
            return redirect('/ftp_new')

        
        # Construct the email address using the username and domain
        ftp_user = f"{username_string}_{req_username}"

        # Check if a record with the same email already exists
        if Ftps.objects.filter(user=ftp_user).exists():
            messages.error(request, 'Ftp user already exists.')
            return redirect('/ftp_new')
            
          

        # Hash the password with the custom function
        hashed_password = hash_password_crypt(password)
        base_dir = f'/home/{username_string}/{path}'
        uid, gid = get_uid_gid(username_string)
        
        # Construct the Maildir path
        if space_limit == "unlimited":
            QuotaSize = 0  # Set to 0 for unlimited
        else:
            try:
                QuotaSize = int(space_limit)  # Convert to integer
            except ValueError:
                messages.error(request, 'Invalid space limit value.')
                return redirect('/ftp_new')
     
        # Create a new email record with the hashed password and Maildir path
        new_ftp = Ftps(
            user=ftp_user,
            dir=base_dir,  # Use the correct field name
            password=hashed_password,  # Assuming you have a password field in the Emails model
            userid=request.user.id,  # Assuming userid is a ForeignKey to the User model
            QuotaSize=QuotaSize,  # Assuming you have a domain_id field in your Emails model
            uid=uid,
            gid=gid,
            status=1
        )
        new_ftp.save()
       

        # Display a success message and redirect to the list page
        messages.success(request, 'FTP Account has been created successfully.')
        return redirect('/ftp_list')

    # Render the email creation form with the available domains
    return render(request, 'users/ftp_new.html', {'domains': domains})
    
    
@login_required
@admincheck
def ftp_edit(request, ftp_id):
    # Fetch the email record for the logged-in user
    ftp = Ftps.objects.filter(userid=request.user.id, id=ftp_id).first()
    username_string = request.user.username
    file = remove_home_anyname(ftp.dir)
    base_dirs = f'/home/{username_string}/'
    file_path =  file.lstrip('/')
    file_path = remove_home_anyname(file_path)

    if not ftp:
        messages.error(request, 'Invalid ftp selected.')
        return redirect('/ftp_edit', ftp_id=ftp_id)

    if request.method == 'POST':
        password = request.POST.get('password')  # Get the password from the form
        passwordc = request.POST.get('passwordc')  # Get the confirm password from the form
        space_limit = request.POST.get('space_limit')  # Get the space limit from the form
        status = request.POST.get('status')  # Get the space limit from the form
        path = request.POST.get('path')
        base_dir = f'/home/{username_string}/{path}'
        
        ftp.dir =base_dir

        # Validate password input if it's not empty
        if password:
            if len(password) < 6:
                messages.error(request, 'Password must be at least 6 characters long.')
                return redirect('/ftp_edit', ftp_id=ftp_id)

            if password != passwordc:
                messages.error(request, 'Passwords do not match.')
                return redirect('/ftp_edit', ftp_id=ftp_id)

            # Hash the new password and update it
            hashed_password = hash_password_crypt(password)
            ftp.password = hashed_password  # Update password only if provided
            
        if status == "1":
            ftp.status = 1  # Set to 0 for unlimited
        else:
            ftp.status = 0
    

        # Set the space limit
        if space_limit == "unlimited":
            ftp.QuotaSize = 0  # Set to 0 for unlimited
        else:
            try:
                ftp.QuotaSize = int(space_limit)  # Convert to integer
            except ValueError:
                messages.error(request, 'Invalid space limit value.')
                return redirect('/ftp_edit', ftp_id=ftp_id)

        # Save the updated email object
        ftp.save()

        messages.success(request, 'FTP  updated successfully.')
        return redirect('/ftp_list')  # Redirect to email list page or wherever appropriate
    
    return render(request, 'users/ftp_edit.html', {'ftp_id': ftp_id, 'ftp': ftp, 'file_path':file_path})   
    
    
@login_required
@admincheck
def ftp_delete(request, ftp_id):
    # Fetch the DNS record based on the provided id (rid) and ensure it belongs to the logged-in user
    ftp = get_object_or_404(Ftps, userid=request.user.id, id=ftp_id)

    # Check if the record belongs to the current user
    if ftp.userid != request.user.id:
        return redirect('/ftp_list')
        
        
    if ftp.user == request.user.username:
        messages.error(request, 'This account can not delete.')
        return redirect('/ftp_list')    

    if request.method == 'POST':
       
        ftp.delete()
            

        # Display a success message after deletion
        messages.success(request, 'FTP has been deleted successfully.')

        # Redirect to the list page after deletion
        return redirect('/ftp_list')   


@login_required
@admincheck
def cronjob_list(request):
    username_string = request.user.username
    
    # Call the parse_cron_jobs function to get structured data
    cronjob = parse_cron_jobs(username_string)

    return render(request, 'users/cronjob_list.html', {'cronjob': cronjob})


@login_required
@admincheck
def cronjob_add(request):
    username_string = request.user.username
    if request.method == 'POST':
        minute = request.POST.get('minute')
        hour = request.POST.get('hour')
        day = request.POST.get('day')
        month = request.POST.get('month')
        weekday = request.POST.get('weekday')
        comm = request.POST.get('comm')

        # Construct the cron command based on user input
        cron_command = f"{minute} {hour} {day} {month} {weekday} {comm}"

        try:
            # Attempt to manage the cron job
            added = manage_cron_jobs(username_string, cron_command)
            if added:
                messages.success(request, 'Cron job added successfully!')
                return redirect('/cronjob_list')
            else:
                messages.info(request, 'Cron job already exists.')
        except Exception as e:
            # Handle any errors that occur during cron job management
            error_message = str(e)
            messages.error(request, f"Failed to add cron job: {error_message}")

    return render(request, 'users/cronjob_add.html')  
    
    
@login_required
@admincheck
def cronjob_edit(request, line):
    username_string = request.user.username

    # Step 1: Call the parse_cron_jobs function to get structured data
    cronjob = get_cron_job_by_line_number(username_string, line)

    if request.method == 'POST':
        minute = request.POST.get('minute')
        hour = request.POST.get('hour')
        day = request.POST.get('day')
        month = request.POST.get('month')
        weekday = request.POST.get('weekday')
        comm = request.POST.get('comm')

        # Construct the cron command based on user input
        cron_command = f"{minute} {hour} {day} {month} {weekday} {comm}"

        try:
            # Update the cron job
            update_cron_job(username_string, line, cron_command)
            messages.success(request, 'Cron job updated successfully!')
            return redirect('/cronjob_list')
        except Exception as e:
            # Handle any errors that occur during cron job management
            error_message = str(e)
            messages.error(request, f"Failed to update cron job: {error_message}")

    return render(request, 'users/cronjob_edit.html', {'cronjob': cronjob})
    
    
@login_required
@admincheck
def cronjob_delete(request, line):
    username_string = request.user.username

    # Attempt to delete the cron job
    success = delete_cron_job_by_line(username_string, line)

    if success:
        messages.success(request, 'Cron job deleted successfully!')
    else:
        messages.error(request, 'Failed to delete the cron job. Please check the line number or cron file.')

    return redirect('/cronjob_list')    
    
        
            
@login_required
@admincheck
def visitor_list(request):
    if request.method == 'POST':
        search_query = request.POST.get('search', '')
        # Use __icontains for case-insensitive partial match
        domains = Domain.objects.filter(userid=request.user.id, domain__icontains=search_query)
    else:
        domains = Domain.objects.filter(userid=request.user.id)

    return render(request, 'users/visitor_list.html', {'domains': domains})  


@login_required
@admincheck
def visitor_view(request,id):
    username_string = request.user.username
    domain = get_object_or_404(Domain, userid=request.user.id, id=id)
    file_path = f'/home/{username_string}/logs/{domain.domain}.access_log'
    

    # Check file permissions
    #has_permission, message = check_read_permission(file_path, username_string)
    
    #if not has_permission:
        #return JsonResponse({'status': 'error', 'message': message}, status=403)

    # Handle POST request to save the file content
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        new_content = request.POST.get('content')
        
        has_permissionw, message = check_file_permission(file_path, username_string)
    
        if not has_permissionw:
            return JsonResponse({'status': 'error', 'message': message}, status=403)

        
        # Check if content is provided
        if new_content is None:
            return JsonResponse({'status': 'error', 'message': 'No content provided.'}, status=400)
        
       
    
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        messages.error(request, f"Error reading file: {e}")
        return redirect('/')

    return render(request, 'users/visitor_view.html', {
        'file': file_path,
        'content': content
    })   

@login_required
@admincheck
def bandth(request):
    
    ban = Bandwidth.objects.filter(userid=request.user.id).order_by('-id')
    user_package = Package.objects.filter(id=get_user_data_by_id(request.user.id).get('pkg_id')).first()
    limit = user_package.bandwidth if user_package.bandwidth != 0 else 2000

    return render(request, 'users/bandth.html', {'bandths': ban, 'limit':limit})
    
    
    
@login_required
@admincheck
def backup(request):
    if request.method == 'POST':
        search_query = request.POST.get('search', '')
        # Use __icontains for case-insensitive partial match
        backup = BackupList.objects.filter(userid=request.user.id, schedule__icontains=search_query).exclude(user_access=1)
    else:
        backup = BackupList.objects.filter(userid=request.user.id).exclude(user_access=1)
        #create_backup(request.user.id,'local')
        local_dir = f"backup/osman_2024-12-04_15-13-26"
        #f_compress(username_string,parent, file_name, target_name, selected_items)
        #message = gz_compress("osman", "backup", local_dir, "backup/ol.tar.gz")
        
        #messages.error(request, f"Error reading file: {message}")
        
        
        
        

    return render(request, 'users/backup.html', {'backups': backup}) 
    
    
@login_required
@admincheck
def new_backup(request):
    if request.method == 'POST':
        # Retrieve the form data
        schedule = request.POST.get('schedule')
        backup_types = request.POST.getlist('backup_option')  # List of selected backup types
        backup_location = request.POST.get('backup_type')  # Local or FTP
        ftp_host = request.POST.get('ftp_host', '').strip()
        ftp_user = request.POST.get('ftp_user', '').strip()
        ftp_pass = request.POST.get('ftp_pass', '').strip()
        category = request.POST.get('category', 'default').strip()

        # Validate that at least one backup type is selected
        if not backup_types:
            messages.error(request, 'Please select at least one backup type.')
            return redirect('new_backup')

        # Validate FTP connection if backup location is FTP
        if backup_location == "ftp":
            try:
                ftp = FTP(ftp_host)
                ftp.login(user=ftp_user, passwd=ftp_pass)
                ftp.quit()  # Close the connection
            except (error_perm, Exception) as e:
                messages.error(request, f"FTP connection failed: {e}")
                return redirect('new_backup')

        # Check for duplicate backups with the same schedule and user
        if BackupList.objects.filter(userid=request.user.id, schedule=schedule,path=backup_location).exclude(user_access=1).exists():
            messages.error(request, 'A backup with the same schedule already exists.')
            return redirect('new_backup')

        # Insert the backup record as a single entry with backup types as a JSON array
        try:
            new_backup = BackupList(
                type=json.dumps(backup_types),  # Store backup types as a JSON array
                userid=request.user.id,
                schedule=schedule,
                category=category,
                path=backup_location,
                username=request.user.username,
                host=ftp_host if backup_location == "ftp" else None,
                user=ftp_user if backup_location == "ftp" else None,
                password=ftp_pass if backup_location == "ftp" else None
            )
            new_backup.save()
            messages.success(request, 'Backup created successfully.')
            return redirect('/backup')
        except Exception as e:
            messages.error(request, f'Error creating backup: {e}')
            return redirect('new_backup')

    # Render the form
    return render(request, 'users/new_backup.html')
    
@login_required
@admincheck
def backup_delete(request, id):
    # Fetch the Backup record based on the provided id and ensure it belongs to the logged-in user
    bk = get_object_or_404(BackupList, userid=request.user.id, id=id)

    # Check if the record belongs to the current user
    if bk.userid == request.user.username:
        messages.error(request, 'This account cannot be deleted.')
        return redirect('/backup')

    
    bk.delete()

        # Display a success message after deletion
    messages.success(request, 'Backup has been deleted successfully.')

        # Redirect to the list page after deletion
    return redirect('/backup')
    
    
    
@login_required
@admincheck
def backup_now(request):
    if request.method == 'POST':
        # Retrieve the form data
        schedule = request.POST.get('schedule')
        backup_types = request.POST.getlist('backup_option')  # List of selected backup types
        backup_location = request.POST.get('backup_type')  # Local or FTP
        ftp_host = request.POST.get('ftp_host', '').strip()
        ftp_user = request.POST.get('ftp_user', '').strip()
        ftp_pass = request.POST.get('ftp_pass', '').strip()
        category = request.POST.get('category', 'default').strip()

        # Validate that at least one backup type is selected
        if not backup_types:
            return HttpResponse('Please select at least one backup type.', content_type='text/plain', status=400)

        # Validate FTP connection if backup location is FTP
        if backup_location == "ftp":
            try:
                ftp = FTP(ftp_host)
                ftp.login(user=ftp_user, passwd=ftp_pass)
                ftp.quit()  # Close the connection
            except (error_perm, Exception) as e:
                return HttpResponse(f"FTP connection failed: {e}", content_type='text/plain', status=400)

        # Check for duplicate backups with the same schedule and user
        if BackupList.objects.filter(userid=request.user.id, schedule=schedule).exclude(user_access=1).exists():
            return HttpResponse('A backup with the same schedule already exists.', content_type='text/plain', status=400)

        # Insert the backup record as a single entry with backup types as a JSON array
        try:
            new_backup = BackupList(
                type=json.dumps(backup_types),  # Store backup types as a JSON array
                userid=request.user.id,
                schedule=schedule,
                category=category,
                path=backup_location,
                username=request.user.username,
                host=ftp_host if backup_location == "ftp" else None,
                user=ftp_user if backup_location == "ftp" else None,
                password=ftp_pass if backup_location == "ftp" else None
            )
            new_backup.save()
            inserted_id = new_backup.id

            # Process the newly created backup
            create_backup(request.user.id, new_backup)
            bk = get_object_or_404(BackupList, userid=request.user.id, id=inserted_id)
            bk.delete()

       
        
            

            return HttpResponse('Backup created successfully.', content_type='text/plain')

        except Exception as e:
            return HttpResponse(f"Failed to create backup: {e}", content_type='text/plain', status=500)

    else:
        return HttpResponse('Invalid request method.', content_type='text/plain', status=405)
        
        

@login_required
@admincheck
def backup_list(request, id=None):
    username_string = request.user.username
    backups = []

    
    
    if request.method == "POST":
        file_to_delete = request.POST.get("delete_file")
        if file_to_delete:
            backup_path = os.path.join('/home', username_string, "backup", file_to_delete)
            if os.path.exists(backup_path) and os.path.isfile(backup_path):
                try:
                    os.remove(backup_path)
                    messages.success(request, f"{file_to_delete} has been deleted.")
                except Exception as e:
                    messages.error(request, f"Error deleting file: {str(e)}")
            else:
                messages.error(request, "Backup file not found.")
        return redirect('/backup_list/')  # or use `reverse()` if necessary
        
        
    # If no 'id' is provided, show all local backup files
    if not id:
        backup_path = os.path.join('/home', username_string, "backup")
        if os.path.exists(backup_path) and os.path.isdir(backup_path):
             backups = sorted(
                [f for f in os.listdir(backup_path) if f.endswith('.tar.gz')],
                key=lambda x: os.path.getmtime(os.path.join(backup_path, x)),
                reverse=True  # Show latest first
            )
        else:
            return render(request, 'users/backup_view.html', {'error': 'Local backup path not found or inaccessible.'})

    # If 'id' is provided, fetch backup entry from the database
    else:
        try:
            backup = BackupList.objects.get(userid=request.user.id, id=id)
        except BackupList.DoesNotExist:
            return render(request, 'users/backup_view.html', {'error': 'Backup entry not found.'})

        # Check if the backup source is local or FTP
        if backup.path == 'local':
            # Get the list of .tar.gz files from the local directory
            backup_path = os.path.join('/home', username_string, "backup")
            if os.path.exists(backup_path) and os.path.isdir(backup_path):
                backups = sorted(
                    [f for f in os.listdir(backup_path)if f.endswith('.tar.gz') and f.startswith(backup.schedule)],
                    key=lambda x: os.path.getmtime(os.path.join(backup_path, x)),
                    reverse=True
                )
            else:
                return render(request, 'users/backup_view.html', {'error': 'Local backup path not found or inaccessible.'})

        elif backup.path == 'ftp':
            # Connect to the FTP server and list .tar.gz files
            try:
                ftp = FTP(backup.host)
                ftp.login(backup.user, backup.password)
                ftp.cwd('')
                backups = sorted(
                    [f for f in ftp.nlst() if f.endswith('.tar.gz')],
                    reverse=True  # Alphabetical, newest first by name
                )
                ftp.quit()
            except Exception as e:
                return render(request, 'users/backup_view.html', {'error': f"FTP error: {str(e)}"})

        else:
            return render(request, 'users/backup_view.html', {'error': 'Invalid backup path type.'})

    # Render the backup list
    return render(request, 'users/backup_view.html', {'backups': backups, 'bk': 'local' if not id else backup.path})        


@login_required
@admincheck
def phpmyadmin_view(request):
    """
    Redirect users to the phpMyAdmin URL using the base URL without the port.
    """
    # Use proxy headers if present to get correct public origin (e.g. port 4263)
    scheme = request.META.get('HTTP_X_FORWARDED_PROTO', 'https')
    host = request.META.get('HTTP_X_FORWARDED_HOST', request.META.get('HTTP_HOST', 'localhost:4263'))
    sport = f"{scheme}://{host}"
    
    db_password = get_phpmyadmin_password(request.user.username) 
    
    # Guard: if the password file is missing or unreadable, show a friendly error
    if not db_password:
        return HttpResponse(
            "phpMyAdmin database password is not configured yet. "
            "Please ensure the panel has finished initialising (check that the "
            "<code>etc/mysqlPassword</code> or "
            f"<code>etc/phpmyadmin_{request.user.username}</code> file exists).",
            content_type="text/html",
            status=503
        )

    json_data = {"user": request.user.username, "pass": db_password, "port": sport}
    encrypted_json = encode_json_to_base64(json_data)

    try:
        binary_path = "/usr/local/bin/olspanelcp"
        if os.path.isfile(binary_path) and os.access(binary_path, os.X_OK):
            # Redirect to OLS on port 443 (which can serve PHP), not the Django panel port
            server_host = request.META.get('HTTP_HOST', 'localhost').split(':')[0]
            phpmyadmin_url = f"https://{server_host}/3rdparty/phpmyadmin/auto_login.php?password={encrypted_json}"
        else:
            phpmyadmin_url = f"/phpmyadmin/auto_login.php?password={encrypted_json}"
            
        # Redirect the user to phpMyAdmin
        return redirect(phpmyadmin_url)
    except Exception as e:
        # Handle errors
        return HttpResponse(f"Error: {str(e)}", status=500)


@login_required
@admincheck
def softaculous_view(request):
    # Use proxy headers if present to get correct public origin (e.g. port 4263)
    scheme = request.META.get('HTTP_X_FORWARDED_PROTO', 'https')
    host = request.META.get('HTTP_X_FORWARDED_HOST', request.META.get('HTTP_HOST', 'localhost:4263'))
    sport = f"{scheme}://{host}"

    # Create session token
    u_password = encode(get_auto_login_password(request.user.username)) 
    json_data = {"user": request.user.username, "api": u_password, "port": sport}
    encrypted_json = encode_json_to_base64(json_data)

    # Ensure olspanel user is setup with correct groups
    ensure_group_exists_and_create_user('olspanel', ['nobody', request.user.username], 'olspanel')
    ensure_group_exists_and_create_user('olspanel', ['nogroup','www-data'], 'olspanel')
    

    # Check Softaculous path
    alt_path = os.path.join(str(settings.BASE_DIR).rsplit(os.sep, 1)[0], "softaculous")
    if not os.path.isdir(alt_path):
        return render(request, "users/softaculous.html", {
            "message": "Softaculous is not installed in expected directory."
        })
        
    user_home = os.path.join('/home', request.user.username)
    softaculous_path = os.path.join(user_home, '.softaculous')    
    if not os.path.isdir(softaculous_path):
        add_user_and_set_folder_permissions(request.user.username, user_home, softaculous_path)
        
    set_api_status_u("api_status", 1)
    softaculous_url = f"/softaculous/enduser/index.php?ols_session={encrypted_json}"
    return redirect(softaculous_url)
        
@login_required
def olsapp_view(request):
    user_home = os.path.join('/home', request.user.username)
    olsapp_path = os.path.join(user_home, '.olsapp')
    # Use proxy headers if present to get correct public origin (e.g. port 4263)
    scheme = request.META.get('HTTP_X_FORWARDED_PROTO', 'https')
    host = request.META.get('HTTP_X_FORWARDED_HOST', request.META.get('HTTP_HOST', 'localhost:4263'))
    sport = f"{scheme}://{host}"

    # Create session token
    u_password = encode(get_auto_login_password(request.user.username)) 
    json_data = {"user": request.user.username, "api": u_password, "port": sport}
    encrypted_json = encode_json_to_base64(json_data)

     

    binary_path = "/usr/local/bin/olspanelcp"
    if os.path.isfile(binary_path) and os.access(binary_path, os.X_OK):
        alt_path = os.path.join(settings.BASE_DIR, "3rdparty", "olsapp")
    else: 
        alt_path = os.path.join(str(settings.BASE_DIR).rsplit(os.sep, 1)[0], "olsapp")
        
    if not os.path.isdir(alt_path):
        return render(request, "users/olsapp.html", {
            "message": "olsapp is not installed in expected directory."
        })
        
    if not os.path.isdir(olsapp_path):
        ensure_group_exists_and_create_user('olspanel', ['nobody', request.user.username], 'olspanel')
        ensure_group_exists_and_create_user('olspanel', ['nogroup','www-data'], 'olspanel')
        
       
    
    add_user_and_set_folder_permissions(request.user.username, user_home, olsapp_path)
        
    set_api_status_u("api_status", 1)
    binary_path = "/usr/local/bin/olspanelcp"
    if os.path.isfile(binary_path) and os.access(binary_path, os.X_OK):
        olsapp_url = f"/3rdparty/olsapp/index.php?ols_session={encrypted_json}"
    else:    
        olsapp_url = f"/olsapp/index.php?ols_session={encrypted_json}"
    return redirect(olsapp_url)


@login_required
def olsapp_more_view(request,view_name,id=None):
    user_home = os.path.join('/home', request.user.username)
    olsapp_path = os.path.join(user_home, '.olsapp')
    # Use proxy headers if present to get correct public origin (e.g. port 4263)
    scheme = request.META.get('HTTP_X_FORWARDED_PROTO', 'https')
    host = request.META.get('HTTP_X_FORWARDED_HOST', request.META.get('HTTP_HOST', 'localhost:4263'))
    sport = f"{scheme}://{host}"

    # Create session token
    u_password = encode(get_auto_login_password(request.user.username)) 
    json_data = {"user": request.user.username, "api": u_password, "port": sport}
    encrypted_json = encode_json_to_base64(json_data)

     

    binary_path = "/usr/local/bin/olspanelcp"
    if os.path.isfile(binary_path) and os.access(binary_path, os.X_OK):
        alt_path = os.path.join(settings.BASE_DIR, "3rdparty", "olsapp")
    else: 
        alt_path = os.path.join(str(settings.BASE_DIR).rsplit(os.sep, 1)[0], "olsapp")
        
    if not os.path.isdir(alt_path):
        return render(request, "users/olsapp.html", {
            "message": "olsapp is not installed in expected directory."
        })
        
    if not os.path.isdir(olsapp_path):
        ensure_group_exists_and_create_user('olspanel', ['nobody', request.user.username], 'olspanel')
        ensure_group_exists_and_create_user('olspanel', ['nogroup','www-data'], 'olspanel')
        
       
    
    add_user_and_set_folder_permissions(request.user.username, user_home, olsapp_path)
        
    set_api_status_u("api_status", 1)
    binary_path = "/usr/local/bin/olspanelcp"
    if os.path.isfile(binary_path) and os.access(binary_path, os.X_OK):
        olsapp_url = f"/3rdparty/olsapp/index.php?ols_session={encrypted_json}&view={view_name}"
    else:
        olsapp_url = f"/olsapp/index.php?ols_session={encrypted_json}&view={view_name}"
    
    if id:
        olsapp_url += f"&app={id}"
        
    return redirect(olsapp_url)   
        
@login_required
@admincheck
def webmail(request):
    
    # Get the full URL of the current request (e.g., "http://example.com:8001/")
    full_url = request.build_absolute_uri('/')
    current_port = request.META.get('SERVER_PORT')
    
    # Parse the URL to extract the scheme and hostname
    parsed_url = urlparse(full_url)
    scheme = parsed_url.scheme  # "http" or "https"
    hostname = parsed_url.hostname  # "example.com"
    
    # Construct the phpMyAdmin URL (e.g., "http://example.com/phpmyadmin")
    webmail_base_url = f"{scheme}://{hostname}"
    sport=f"{scheme}://{hostname}:{current_port}"
   
    try:
        # Generate a phpMyAdmin session
        #session_id = generate_phpmyadmin_session(phpmyadmin_base_url, db_username, db_password)
        
        # Construct the phpMyAdmin URL with the session ID
        webmail_url = f"{webmail_base_url}/webmail"
        
        # Redirect the user to phpMyAdmin
        return redirect(webmail_url)
    except Exception as e:
        # Handle errors
        return HttpResponse(f"Error: {str(e)}", status=500) 


@login_required
@admincheck
def app_install_view(request, name):
    domains = Domain.objects.filter(userid=request.user.id)
    username_string = request.user.username

   
    return render(request, 'users/app_install.html', {'name': name, 'domains': domains}) 
    
    


@login_required
@admincheck
def app_install(request, name):
    if request.method == 'POST':
        username_string = request.user.username
        user_data = get_user_data_by_id(request.user.id)
        user_package = Package.objects.filter(id=user_data.get('pkg_id')).first()
        db_count = count_users_by_prefix(username_string)
        
        # Enforce database limit (0 means unlimited)
        if user_package.databases != 0 and db_count >= user_package.databases:    
            return JsonResponse({'status': 'error', 'message': 'Database limit exceeded.'}, status=200)
        
        django_root = settings.BASE_DIR
        target_name = request.POST.get('target_name', '').strip('/') 
        
        target_plat = f'/home/{username_string}/{target_name}' if target_name else f'/home/{username_string}'
        target_plat = target_plat.rstrip('/')  # Remove trailing slashes

        # Validate domain
        domain_name = request.POST.get('domain_name', '').strip()
        domain = Domain.objects.filter(userid=request.user.id, domain=domain_name).first()
        if not domain:
            return JsonResponse({'status': 'error', 'message': 'Domain not found or you do not have permission to access it.'}, status=200)

        # Use domain's base path
        base_dir = domain.path.rstrip('/')  # Remove trailing slash for consistency

        # If target_plat matches base_dir, reset target_name
        if target_plat == base_dir:
            target_name = ''  # Set to empty instead of '/'

        # Ensure a valid target path
        target_path = os.path.join(base_dir, target_name)
        #return JsonResponse({'status': 'error', 'message': target_path}, status=200)
        if not target_path.startswith(f'/home/{username_string}'):
            return JsonResponse({'status': 'error', 'message': 'Invalid installation path.'}, status=200)

        if not os.path.exists(target_path):
            os.makedirs(target_path)
            
    
        target_path = ensure_user_home_prefix(target_path, request.user.username)
        set_permissions_and_ownership(target_path, request.user.username)

        # Validate ZIP file
        #file_path = os.path.join(django_root, 'app', f'{name}.zip')
        file_path = f"{target_path}/{name}.zip" 
        download_script_only(name, file_path)
        if not file_path.endswith('.zip'):
            return JsonResponse({'status': 'error', 'message': 'Only .zip files can be unzipped.'}, status=200)

        try:
            # Extract ZIP file
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(target_path)

                # Apply correct permissions to extracted files
                for item in zip_ref.namelist():
                    extracted_path = os.path.join(target_path, item)
                    set_permissions_and_ownership(extracted_path, request.user.username)

            # Special handling for WordPress installations
            wp_config_path = None 
            config_path_source = os.path.join(django_root, 'app', name)
            if name == 'wordpress':
                source_item = os.path.join(target_path, 'wordpress')
                if os.path.exists(source_item) and os.path.isdir(source_item):
                    for item_name in os.listdir(source_item):
                        s_path = os.path.join(source_item, item_name)
                        t_path = os.path.join(target_path, item_name)
                        shutil.move(s_path, t_path)
                wp_config_path = os.path.join(target_path, "wp-config.php")
                
            if name == 'joomla':
                wp_config_path = os.path.join(target_path, "installation","forms", "setup.xml")
                

            if os.path.exists(config_path_source):
                for item_name in os.listdir(config_path_source):
                    s_path = os.path.join(config_path_source, item_name)
                    t_path = os.path.join(target_path, item_name)
                    if os.path.isdir(s_path):
                        shutil.copytree(s_path, t_path, dirs_exist_ok=True)
                    else:
                        shutil.copy2(s_path, t_path)

            db_password = generate_strong_random_password()
            ran = f"{name}{generate_random_5_digit()}"
            db_name = f"{username_string}_{ran}"

            success, error_message = create_database(username_string, ran)
            if not success:
                return JsonResponse({'status': 'error', 'message': f'Database creation failed: {error_message}'}, status=200)

            create_database_and_user(request, username_string, ran, ran, db_password)

            # Replace placeholders in wp-config.php
            replacements = {
                '%db_name%': db_name,
                '%db_user%': db_name,
                '%db_pass%': db_password
            }
            
            if wp_config_path is not None:
                replace_placeholders_in_wp_config(wp_config_path, replacements)

            # Final permission check
            set_permissions_and_ownership(target_path, request.user.username)

            # Generate Virtual Link
            link = generate_virtual_link(domain, target_path, request.user.username)
            if os.path.exists(file_path):
                os.remove(file_path)

            return JsonResponse({'status': 'success', 'message': f'Application installed successfully. Visit now: {link}'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Error during installation: {str(e)}'}, status=200)

    # For GET requests, return a success response
    return JsonResponse({'status': 'success'})

@login_required
@admincheck
def default_email(request):
    # Fetch the domains associated with the logged-in user
    domains = Domain.objects.filter(userid=request.user.id)
    username_string = request.user.username
    user_package = Package.objects.filter(id=get_user_data_by_id(request.user.id).get('pkg_id')).first()
    total_email_count = EmailForword.objects.filter(userid=request.user.id).count()

    if request.method == 'POST':
        forwardType = request.POST.get('forwardType')
        domain_id = request.POST.get('domain')
        destination = request.POST.get('email')
        path = request.POST.get('path')

        # Check if email limits are exceeded
        if user_package.email_accounts != 0 and total_email_count >= user_package.email_accounts:
            messages.error(request, 'Email limit exceeded.')
            return redirect('/default_email')

        # Validate required fields
        if not path and not destination:
            messages.error(request, 'Both "Forward to Email" or "Path" fields are required.')
            return redirect('/default_email')

        # Validate the destination email
        if forwardType == 'email' and destination and not is_valid_email(destination):
            messages.error(request, 'Invalid destination email address.')
            return redirect('/default_email')

        # Fetch the domain and validate its existence
        domain = Domain.objects.filter(userid=request.user.id, id=domain_id).values_list('domain', flat=True).first()
        if not domain:
            messages.error(request, 'Invalid domain selected.')
            return redirect('/default_email')

        # Construct the email address using the username and domain
        email = f"@{domain}"

        # Check if the email address already exists
        if EmailForword.objects.filter(source=email).exists():
            messages.error(request, 'Email already exists.')
            return redirect('/default_email')

        # Handle Email Forward (destination email)
        if forwardType == 'email' and destination:
            new_email = EmailForword(
                source=email,
                destination=destination,  # Forward to destination email
                userid=request.user.id,  # Assuming userid is a ForeignKey to the User model
                domain_id=domain_id  # Assuming you have a domain_id field in your Emails model
            )
            new_email.save()

        # Handle Pipe Forward (destination path)
        elif forwardType == 'pipe' and path:
            # Process the destination path for pipe forward
            file = remove_home_anyname(path)
            base_dir = f'/home/{username_string}/'
            file_path = os.path.join(base_dir, file.lstrip('/'))
            example = "pipe@example.com"  # Example placeholder for pipe forwarding

            new_email = EmailForword(
                source=email,
                destination=example,  # Destination is a placeholder for pipe forwarding
                userid=request.user.id,
                domain_id=domain_id,
                path=file_path
            )
            new_email.save()

            add_script_filter(domain)  # Call script filter function
            php_version = Domain.objects.filter(userid=request.user.id, id=domain_id).values_list('php', flat=True).first().replace('.', '')
            new_path = f"/usr/local/lsws/lsphp{php_version}/bin/lsphp {file_path}"
            add_master(domain, username_string, new_path)  # Add master configuration
            run_command("postmap /etc/postfix/script_filter")
            run_command("postfix reload")

        # Display a success message and redirect to the list page
        messages.success(request, 'Email has been forwarded successfully.')
        return redirect('/default_email_list')

    # Render the email creation form with the available domains
    return render(request, 'users/new_default_email.html', {'domains': domains})

    
    
@login_required
@admincheck
def default_email_list(request):
    username_string = request.user.username
    
    if request.method == 'POST':
        search_query = request.POST.get('search', '')
        # Exclude emails that are equal to 'pipe@example.com' and filter emails that start with '@'
        emails = EmailForword.objects.filter(
            userid=request.user.id, 
            email__icontains=search_query
        ).filter(source__startswith='@')
    else:
        # Exclude emails that are equal to 'pipe@example.com' and filter emails that start with '@'
        emails = EmailForword.objects.filter(userid=request.user.id).filter(source__startswith='@')
        
    for email in emails:
        email.source = email.source.replace('@', '')    

    return render(request, 'users/default_email_list.html', {'emails': emails})

    
    
      
@login_required
@admincheck
def default_email_delete(request, email_id):
    username_string = request.user.username
    email = get_object_or_404(EmailForword, userid=request.user.id, id=email_id)

    # Check if the record belongs to the current user
    if email.userid != request.user.id:
        return redirect('/default_email_list')

    if request.method == 'POST':
        email_source = email.source.replace('@', '')
        if email.path:
            remove_script_filter(email_source)
            remove_master_line(email_source, username_string, email.path)
            command = "postmap /etc/postfix/script_filter"
            run_command(command)
            command = "postfix reload"
            run_command(command)
        email.delete()

        # Display a success message after deletion
        messages.success(request, 'Email has been deleted successfully.')

        # Redirect to the list page after deletion
        return redirect('/default_email_list') 
        
        
@login_required
@admincheck
def domain_preview(request, rid):
    # Fetch the domain based on the provided primary key (pk) and check user
    domain = get_object_or_404(Domain, pk=rid)
    username_string = request.user.username
    # If the domain's user ID doesn't match the current user, redirect to the domain list
    if domain.userid != request.user:
        return redirect('domain_list')
        
    
    remove_map_from_httpd_config("Example")  # Update with actual config file path
    remove_virtual_host_from_httpd_config("Example")
    preview_mapping("add", "preview")
    ssl_preview_mapping("add", "preview")
    manage_preview_virtual_host()
    update_context_block(domain.domain,domain.path)
    server_ip = get_server_ip()
    restart_openlitespeed()
    return redirect(f"http://{server_ip}/~{domain.domain}")    
              
              
@login_required
@admincheck
def fatch_php_error(request):
    php_domain = request.GET.get('php_domain')
    current_settings = {}

    if not php_domain:
        return JsonResponse({'error': 'Missing php_domain parameter'}, status=400)

    # Check if this domain belongs to the current user
    domain_exists = Domain.objects.filter(userid=request.user.id, domain=php_domain).exists()
    if not domain_exists:
        return HttpResponseForbidden("You are not authorized to access this domain.")

    ini_file_path = get_vhost_file(php_domain)

    if os.path.exists(ini_file_path):
        current_settings = read_php_conf(ini_file_path)

    return JsonResponse(current_settings)


@login_required
@admincheck
def php_error(request):
    domains = Domain.objects.filter(userid=request.user.id)

    if request.method == 'POST':
        php_domain = request.POST.get('php_domain')
        if not php_domain:
            messages.warning(request, "Please select a domain.")
            return redirect('/php_error/')
            
        if not Domain.objects.filter(userid=request.user.id, domain=php_domain).exists():
            messages.warning(request, "You are not authorized to modify this domain.")
            return redirect('/php_error/')
            
            
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

        return redirect('/php_error/')

    return render(request, 'users/php_error.html', {
        'php_domain': domains
    })
                  
                  
                  
@login_required
@admincheck
def custom_ssl(request):
    domains = Domain.objects.filter(userid=request.user.id)

    if request.method == 'POST':
        php_domain = request.POST.get('php_domain')
        crt = request.POST.get('crt', '').strip()
        cabundle = request.POST.get('cabundle', '').strip()
        privkey = request.POST.get('privatekey', '').strip()
        disable_renew = request.POST.get('renew') == 'On'

        if not php_domain:
            messages.warning(request, "Please select a domain.")
            return redirect('/custom_ssl/')

        if not crt or not privkey:
            messages.warning(request, "Missing required SSL fields.")
            return redirect('/custom_ssl/')

        if not Domain.objects.filter(userid=request.user.id, domain=php_domain).exists():
            messages.warning(request, "You are not authorized to modify this domain.")
            return redirect('/custom_ssl/')

        try:
            save_ssl_files(php_domain, crt, cabundle, privkey)
            
            if disable_renew:
                acme_dir = f'/root/.acme.sh/{php_domain}_ecc'
                if os.path.exists(acme_dir):
                    shutil.rmtree(acme_dir)
                    
            restart_openlitespeed()
            messages.success(request, "SSL files saved successfully.")
        except Exception as e:
            messages.warning(request, f"Failed to update SSL: {str(e)}")

        return redirect('/custom_ssl/')

    return render(request, 'users/custom_ssl.html', {
        'php_domain': domains
    })

     
@login_required
@admincheck
def fatch_custom_ssl(request):
    php_domain = request.GET.get('php_domain')
    current_settings = {}

    if not php_domain:
        return JsonResponse({'error': 'Missing php_domain parameter'}, status=400)

    # Check if this domain belongs to the current user
    domain_exists = Domain.objects.filter(userid=request.user.id, domain=php_domain).exists()
    if not domain_exists:
        return HttpResponseForbidden("You are not authorized to access this domain.")

    

    
    current_settings = read_ssl_files(php_domain)

    return JsonResponse(current_settings)    


@login_required
@admincheck
def fatch_custom_ssl_info(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST allowed'}, status=405)

    pem = request.POST.get('pem')
    if not pem:
        return JsonResponse({'error': 'Missing pem parameter'}, status=400)

    result = parse_certificate(pem)
    return JsonResponse(result)
    
    
@login_required
@admincheck
def multi_php_ini_u(request):
    domains = Domain.objects.filter(userid=request.user.id)

    if request.method == 'POST':
        php_domain = request.POST.get('php_domain')
        if not php_domain:
            messages.warning(request, "Please select a domain.")
            return redirect('/multi_php_ini_u/')
            
        if not Domain.objects.filter(userid=request.user.id, domain=php_domain).exists():
            messages.warning(request, "You are not authorized to modify this domain.")
            return redirect('/multi_php_ini_u/')
            
            
        ini_file_path = get_vhost_file(php_domain)

        new_settings = {
            'open_basedir': '"/tmp:$VH_ROOT"',
            'error_reporting': request.POST.get('error_reporting', ''),
            'log_errors': 'On' if request.POST.get('log_errors') else 'Off',
            'display_errors': 'On' if request.POST.get('display_errors') else 'Off',
            'error_log': 'error_log',
            'memory_limit': request.POST.get('memory_limit'),
            'upload_max_filesize': request.POST.get('upload_max_filesize'),
            'post_max_size': request.POST.get('post_max_size'),
            'max_execution_time': request.POST.get('max_execution_time'),
            'max_input_time': request.POST.get('max_input_time'),
            'allow_url_fopen': 'On' if request.POST.get('allow_url_fopen') else 'Off',
            'allow_url_include': 'On' if request.POST.get('allow_url_include') else 'Off',
            'file_uploads': 'On' if request.POST.get('file_uploads') else 'Off',
        }

        try:
            write_php_conf(ini_file_path, new_settings)
            restart_openlitespeed()
            messages.success(request, "PHP Settings configure successfully.")
        except Exception as e:
            messages.warning(request, f"Failed to update config: {str(e)}")

        return redirect('/multi_php_ini_u/')

    return render(request, 'users/multi_php_ini.html', {
        'php_domain': domains
    })
                     
                     
@login_required
@admincheck
def fatch_php_ini_u(request):
    php_domain = request.GET.get('php_domain')
    current_settings = {}

    if not php_domain:
        return JsonResponse({'error': 'Missing php_domain parameter'}, status=400)

    # Check if this domain belongs to the current user
    domain_exists = Domain.objects.filter(userid=request.user.id, domain=php_domain).first()
    if not domain_exists:
        return HttpResponseForbidden("You are not authorized to access this domain.")

    ini_file_path = get_vhost_file(php_domain)

    if os.path.exists(ini_file_path):
        current_settings = get_php_settings(domain_exists.php,ini_file_path)

    return JsonResponse(current_settings) 


@loginadminoruser
@csrf_exempt
@xframe_options_exempt
def web_server(request, php_file):
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

    custom_cookies = get_custom_cookies(request, prefix="CUSTOMCOOK_")
    for header_name, header_value in custom_cookies.items():
        request.META[header_name] = header_value

    plugin_name = None
    try:
        if php_file:
            php_path = php_file.split('?', 1)[0].strip('/')
            parts = php_path.split('/')
            if parts and parts[0]:
                plugin_name = parts[0]

        if plugin_name:
            headers = get_plugin_headers(plugin_name)
            replaced_headers = {}
            needs_username = any('%username%' in v for v in headers.values())
            needs_userid = any('%userid%' in v for v in headers.values())
            needs_dbinfo = any('%dbinfo%' in v for v in headers.values())
            needs_usertoken = any('%usertoken%' in v for v in headers.values())

            # Prepare replacements only if needed
            if not request.user:
                username = request.admin_user.username if needs_username or needs_dbinfo else ''
                userid = str(request.admin_user.id) if needs_userid else ''
            else:
                username = request.user.username if needs_username or needs_dbinfo else ''
                userid = str(request.user.id) if needs_userid else ''
            encrypted_json = ''
            if needs_usertoken:
                if not request.user:
                    u_token = encode(get_auto_login_password(request.admin_user.username))
                else:
                    u_token = encode(get_auto_login_password(request.user.username))
                    
                

            if needs_dbinfo:
                scheme = request.META.get('HTTP_X_FORWARDED_PROTO', 'https')
                host = request.META.get('HTTP_X_FORWARDED_HOST', request.META.get('HTTP_HOST', 'localhost:4263'))
                sport = f"{scheme}://{host}"

                db_password = get_phpmyadmin_password(username)
                json_data = {"user": username, "pass": db_password, "port": sport}
                encrypted_json = encode_json_to_base64(json_data)

            # Now replace placeholders
            for key, val in headers.items():
                if '%username%' in val:
                    val = val.replace('%username%', username)
                    request.META[key] = val
                if '%userid%' in val:
                    val = val.replace('%userid%', userid)
                    request.META[key] = val
                if '%dbinfo%' in val:
                    val = val.replace('%dbinfo%', encrypted_json)
                    request.META[key] = val
                if '%usertoken%' in val:
                    val = val.replace('%usertoken%', u_token) 
                    request.META[key] = val
                    
                #replaced_headers[key] = val
                
            #request.META.update(replaced_headers)   

            
            user_value = get_plugin_config_value('user', plugin_name)
            group_value = get_plugin_config_value('group', plugin_name)
            service_value = get_plugin_config_value('service', plugin_name)
            if request.user:
                user_data = get_user_data_by_id(request.user.id)
                whm = user_data.get('whm', 0) if user_data else (1 if request.user.is_superuser or request.user.is_staff else 0)
            elif request.admin_user:
                user_data = get_user_data_by_id(request.admin_user.id)
                whm = user_data.get('whm', 0) if user_data else (1 if request.admin_user.is_superuser or request.admin_user.is_staff else 0)
            else:
                whm = 0
                

            # Authorization check
            if service_value == 'user_panel':
                if whm == 1:
                    return HttpResponse("Forbidden: WHM users cannot access user panel plugins.", status=403)
            elif service_value == 'whm':
                if whm != 1:
                    return HttpResponse("Forbidden: Only WHM users can access admin panel plugins.", status=403)

            
            if user_value == '$authuser':
                if whm == 1:
                    user_value = 'root'
                else:    
                    user_value = request.user.username 

                    
            if group_value == '$authuser':
                if whm == 1:
                    group_value = 'root'
                else:    
                    group_value = request.user.username 
                    
                    
            user_value2 = get_plugin_config_value('user2', plugin_name)
            group_value2 = get_plugin_config_value('group2', plugin_name)
            path_value2 = get_plugin_config_value('path2', plugin_name)
            if user_value2 and group_value2 and path_value2 and os.path.basename(php_file) == os.path.basename(path_value2):
                return php_server(request, php_file, PHP_USER=user_value2, PHP_GROUP=group_value2)
                
            
            
                    
            if user_value and group_value:
                return php_server(request, php_file, PHP_USER=user_value, PHP_GROUP=group_value)

        # fallback if no plugin or no user/group config found
        return php_server(request, php_file)

    except Http404:
        raise Http404()

  
         

        
        

@login_required
@admincheck
def webmail_service(request, email):
    email_main = Emails.objects.filter(userid=request.user.id, email=email).first()
    passw = get_auto_login_password(email)
    auto_login_is_enable = passw and not passw.startswith("Password file for user") and not passw.startswith("An error occurred")

    if not auto_login_is_enable:
        messages.error(request, "Please change your email password once to enable auto-login when clicking Open Mail.")
      
        
        

    if not email_main:
        messages.error(request, 'Invalid email selected.')
        return redirect('/email_accounts')
        
    plugin_names = get_all_plugin_names('mail','user_panel')
   
    plugin_list = []
    if request.method == 'POST':
        plugin_item = request.POST.get('plugin_name')
        headers = get_plugin_headers(plugin_item)

        # Replace placeholders in headers
        replaced_headers = {}
        for key, val in headers.items():
            val = val.replace('%email%', email)
            val = val.replace('%email_password%', passw)
            replaced_headers[key] = val
        
        auto_login_url = get_plugin_config_value('auto_login_url', plugin_item)
        if not auto_login_url:
            auto_login_url = get_plugin_config_value('url', plugin_item)
            
        if auto_login_url:
            response = redirect(auto_login_url)
      

        prefix = "CUSTOMCOOK_"
        for cookie_name, cookie_value in replaced_headers.items():
            response.set_cookie(
                prefix + cookie_name,
                cookie_value,
                httponly=True,
                secure=True,
                samesite='Lax',
            )
        return response
            

    for plugin_name in plugin_names:
        icon = get_plugin_config_value('icon', plugin_name)
        url = get_plugin_config_value('url', plugin_name)
        auto_login_url = get_plugin_config_value('auto_login_url', plugin_name)
       

        plugin_list.append({
            'name': plugin_name,
            'icon': icon,
            'url': url,
            'auto_login_url': auto_login_url,
        })

    return render(request, 'users/webmail.html', {
        'list': plugin_list,
        'email': email,
        'email_id': email_main.id
    })



@login_required
@admincheck
def backup_settings(request):
    user = request.user

    settings = UserSettings.objects.filter(userid=user.id).first()
    if settings is None:
        settings = UserSettings.objects.create(userid=user.id)

    # defaults (optional safety)
    if settings.hour_maximum_backup is None:
        settings.hour_maximum_backup = 24
    if settings.day_maximum_backup is None:
        settings.day_maximum_backup = 100
    if settings.week_maximum_backup is None:
        settings.week_maximum_backup = 50
    if settings.month_maximum_backup is None:
        settings.month_maximum_backup = 12

    settings.save()

    if request.method == 'POST':
        try:
            hour = request.POST.get('hour_maximum_backup')
            day = request.POST.get('day_maximum_backup')
            week = request.POST.get('week_maximum_backup')
            month = request.POST.get('month_maximum_backup')

            if hour is not None:
                settings.hour_maximum_backup = int(hour)

            if day is not None:
                settings.day_maximum_backup = int(day)

            if week is not None:
                settings.week_maximum_backup = int(week)

            if month is not None:
                settings.month_maximum_backup = int(month)

            settings.save()

            return JsonResponse({
                'status': 'success',
                'hour_maximum_backup': settings.hour_maximum_backup,
                'day_maximum_backup': settings.day_maximum_backup,
                'week_maximum_backup': settings.week_maximum_backup,
                'month_maximum_backup': settings.month_maximum_backup
            })

        except ValueError:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid numeric value'
            }, status=400)

    return JsonResponse({
        'hour_maximum_backup': settings.hour_maximum_backup,
        'day_maximum_backup': settings.day_maximum_backup,
        'week_maximum_backup': settings.week_maximum_backup,
        'month_maximum_backup': settings.month_maximum_backup
    })
 
    
    
    
@login_required
@admincheck
def app_add(request, name, app_id=None):
    nodejs_path = '/usr/local/olspanel/bin/nodejs/'

    if not os.path.exists(nodejs_path) or not os.listdir(nodejs_path):
        # Node.js folder does not exist or is empty → render empty page
        return render(request, 'users/node_empty.html')
        
    format_nam = format_name(name)
    target_path_simple = name.split("_", 1)[0] if "_" in name else name
    domains = Domain.objects.filter(userid=request.user.id)
    type = get_app_type_from_name(name)
    app_versions = []

    if type == "node_js":
        app_versions = get_node_js_versions()

    # Check if editing
    app_instance = None
    edit_mode = False
    app_path = ''  # default

    if app_id:
        app_instance = get_object_or_404(Apps, id=app_id, userid=request.user.id)
        edit_mode = True
        # For template display
        app_path = app_instance.path
        domain_s = Domain.objects.filter(userid=request.user.id, id=app_instance.domain_id).first()
        if domain_s:
            relative_path = app_path[len(domain_s.path):].lstrip('/')  # remove domain.path prefix
            app_path = relative_path or '/'  # '/' if no subpath

    if request.method == 'POST' and 'delete' in request.POST:
        if app_instance:
            # optional: cleanup Node.js context
            delete_ols_node_context(domain_s.domain, app_path)
            app_instance.delete()
            messages.success(request, 'App has been deleted successfully.')
            restart_openlitespeed()
        return redirect(f'/apps_list/{type}')



    if request.method == 'POST':
        username_string = request.user.username

        # Target subdirectory (optional)
        target_name = request.POST.get('target_name', '').strip('/')
        target_plat = f'/home/{username_string}/{target_name}' if target_name else f'/home/{username_string}'
        target_plat = target_plat.rstrip('/')
        new_app_version = request.POST.get('app_version')
        startup_file = request.POST.get('startup_file', '').strip()

        # Validate startup file
        if not startup_file or '.' not in startup_file:
            messages.error(request, 'Startup file is required and must include an extension (e.g., app.js).')
            return redirect(f'/app_add/{name}' if not edit_mode else f'/app_edit/{name}/{app_id}')

        # Validate domain ownership
        domain_name = request.POST.get('domain_name', '').strip()
        if edit_mode:
            domain = Domain.objects.filter(userid=request.user.id, id=app_instance.domain_id).first()
        else:
            domain = Domain.objects.filter(userid=request.user.id, domain=domain_name).first()

        if not domain:
            messages.error(request, 'Domain not found or you do not have permission to access it.')
            return redirect(f'/app_add/{name}' if not edit_mode else f'/app_edit/{name}/{app_id}')

        base_dir = domain.path.rstrip('/')

        if target_plat == base_dir:
            target_name = ''

        target_path = os.path.join(base_dir, target_name)

        if not target_path.startswith(f'/home/{username_string}'):
            messages.error(request, 'Invalid installation path.')
            return redirect(f'/app_add/{name}' if not edit_mode else f'/app_edit/{name}/{app_id}')

        if not os.path.exists(target_path):
            os.makedirs(target_path)

        target_path = ensure_user_home_prefix(target_path, request.user.username)

        # Edit existing app
        if edit_mode:
            app_instance.domain_id = domain.id
            app_instance.path = target_path
            app_instance.version = new_app_version
            app_instance.startup_file = startup_file
            app_instance.save()

            relative_path = target_path[len(domain.path):].lstrip('/')  # remove domain.path prefix
            app_path_ols = relative_path or '/'  # '/' if no subpath

            create_ols_node_context(new_app_version, app_path_ols, startup_file, domain.domain, app_path)
            set_permissions_and_ownership(target_path, request.user.username)
            messages.success(request, 'App has been updated successfully.')

        # Create new app
        else:
            new_app = Apps(
                userid=request.user.id,
                type=type,
                domain_id=domain.id,
                path=target_path,
                version=new_app_version,
                startup_file=startup_file
            )
            new_app.save()

            relative_path = target_path[len(domain.path):].lstrip('/')  # remove domain.path prefix
            app_path_ols = relative_path or '/'  # '/' if no subpath

            create_ols_node_context(new_app_version, app_path_ols, startup_file, domain.domain)
            set_permissions_and_ownership(target_path, request.user.username)
            messages.success(request, 'App has been added successfully.')

        # For Node.js apps, create app.js if missing
        if type == "node_js":
            create_app_js(target_path, startup_file)

        restart_openlitespeed()
        return redirect(f'/apps_list/{type}')

    return render(request, 'users/app_add.html', {
        'name': format_nam,
        'target_name_simple': target_path_simple,
        'app_versions': app_versions,
        'domains': domains,
        'app': app_instance,
        'edit_mode': edit_mode,
        'app_path': app_path
    })




@login_required
@admincheck
def apps_list(request, type):
    nodejs_path = '/usr/local/olspanel/bin/nodejs/'

    if not os.path.exists(nodejs_path) or not os.listdir(nodejs_path):
        # Node.js folder does not exist or is empty → render empty page
        return render(request, 'users/node_empty.html')
    
    
    types = get_app_type_from_name(type)
    username_string = request.user.username

    if request.method == 'POST':
        search_query = request.POST.get('search', '').strip()
        apps = Apps.objects.filter(userid=request.user.id, type=types)\
                           .filter(path__icontains=search_query)
    else:
        apps = Apps.objects.filter(userid=request.user.id, type=types)

    # Add display_path, domain_name, and app_path for each app
    for app in apps:
        # Simplify path
        app.display_path = app.path.replace(f'/home/{username_string}/', '')
        app.type = format_name(app.type)
        # Get domain name and domain path
        if app.domain_id:
            domain = Domain.objects.filter(id=app.domain_id).first()
            if domain:
                app.domain_name = domain.domain
                # Compute app_path relative to domain.path
                if app.path.startswith(domain.path):
                    relative_path = app.path[len(domain.path):].lstrip('/')  # remove domain.path prefix
                    app.app_path = relative_path or '/'  # '/' if no subpath
                else:
                    app.app_path = app.path  # fallback
            else:
                app.domain_name = 'N/A'
                app.app_path = app.path
        else:
            app.domain_name = 'N/A'
            app.app_path = app.path

    return render(request, 'users/apps_list.html', {
        'apps': apps,
        'type': format_name(types),
        'main_type': type
    })



@login_required
@admincheck
def restart_node_view(request, app_id):
    # Verify the app exists and belongs to the user
    app = Apps.objects.filter(id=app_id, userid=request.user.id,type="node_js").first()
    if not app:
        return JsonResponse({'status': 'error', 'message': 'App not found or you do not have permission'}, status=404)

    # Ensure path ends with no trailing slash
    app_path = app.path.rstrip('/')

    try:
        # Call the restart function
        result = restart_node(app_path)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
        
        
@login_required
@admincheck
def install_node_npm_view(request, app_id):
    # Verify the app exists and belongs to the user
    app = Apps.objects.filter(id=app_id, userid=request.user.id,type="node_js").first()
    if not app:
        return JsonResponse({'status': 'error', 'message': 'App not found or you do not have permission'}, status=404)

    # Ensure path ends with no trailing slash
    app_path = app.path.rstrip('/')

    try:
        # Call the restart function
        result = npm_node_install(app.version,app_path)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)            


@login_required
@admincheck
def composer_run(request):
    composer_path = '/usr/bin/composer'

    if not os.path.exists(composer_path) or not os.access(composer_path, os.X_OK):
        # Node.js folder does not exist or is empty → render empty page
        return render(request, 'users/composer_empty.html')

    target_path_simple = ""
    domains = Domain.objects.filter(userid=request.user.id)

    # 🔹 Remove /home/<username>/ prefix from domain.path
    cleaned_domains = []
    prefix = f"/home/{request.user.username}/"

    for d in domains:
        cleaned_path = d.path
        if cleaned_path.startswith(prefix):
            cleaned_path = cleaned_path.replace(prefix, "", 1)
            
        if not cleaned_path.endswith("/"):
            cleaned_path += "/"
        

        cleaned_domains.append({
            "domain": d.domain,
            "path": cleaned_path,
        })

    return render(request, 'users/composer.html', {
        'target_name_simple': target_path_simple,
        'domains': cleaned_domains,
    })


@login_required
@admincheck
def composer_install_run(request):
    """
    Django view that triggers Composer install in the user’s selected path.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)

    target_path = request.POST.get("target_path", "").strip()
    if not target_path:
        return JsonResponse({"error": "No target path provided"}, status=400)

    # Build full path (/home/username/...)
    full_path = os.path.join(f"/home/{request.user.username}", target_path)

    # 🔹 Run composer install
    result = run_composer_install(full_path)

    # Return JSON
    return JsonResponse(result) 


@login_required
@admincheck
def google_otp(request):
    settings, _ = UserSettings.objects.get_or_create(userid=request.user.id)

    
    if not settings.secret:
        secret = authenticator.create_secret()
        settings.secret = secret
        settings.save()
    else:
        secret = settings.secret

    server_ip = get_server_ip()
    qr_url = authenticator.get_qrcode_google_url(
        f"{server_ip}-OLSPanel",
        request.user.username,
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
            return redirect("google_otp")
        else:
            messages.error(request, "Invalid authentication code. Please try again.")
            return redirect("google_otp")

    return render(request, "users/setup_2fa.html", {
        "qr_url": qr_url,
        "secret": secret,
        "is_enabled": settings.two_step
    })




             