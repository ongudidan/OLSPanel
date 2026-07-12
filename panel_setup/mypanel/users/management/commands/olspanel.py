from django.core.management.base import BaseCommand
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
from whm.models import * 
from users.models import * 
from whm.decorators import * 
from whm.function import * 
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
from file_manager.models import * 



class Command(BaseCommand):
    help = "Manages users (create, suspend, unsuspend)"

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest='command', help='Available commands')

        # createUser subcommand
        create_parser = subparsers.add_parser('adduser', help='Create a new user')
        create_parser.add_argument('--first_name', required=True, help='First name of the user')
        create_parser.add_argument('--last_name', required=True, help='Last name of the user')
        create_parser.add_argument('--email', required=True, help='Email address of the user')
        create_parser.add_argument('--username', required=True, help='Username for the account')
        create_parser.add_argument('--password',  required=True, help='Password for the account')
        create_parser.add_argument('--domain', required=True, help='Domain Name')
        create_parser.add_argument('--pkg_id', required=True, help='Package id')
        create_parser.add_argument('--php_version', required=True, help='PHP Version')

        # actionuser subcommand
        actionuser_parser = subparsers.add_parser('actionuser', help='Suspend , unsuspend and delete a user')
        actionuser_parser.add_argument('--username', required=True, help='Username of the account')
        actionuser_parser.add_argument('--state', required=True, choices=['suspend', 'unsuspend','delete','disable_otp'], help='Suspend or unsuspend the account')

        # edituser subcommand
        edituser_parser = subparsers.add_parser('edituser', help='Edit a user')
        edituser_parser.add_argument('--username', required=True, help='Username of the user to update')
        edituser_parser.add_argument('--first_name', help='First name')
        edituser_parser.add_argument('--last_name', help='Last name')
        edituser_parser.add_argument('--email', help='Email address')
        edituser_parser.add_argument('--pkg_id', type=int, help='Package ID')
        edituser_parser.add_argument('--password', help='New password')
        
        list_parser = subparsers.add_parser('pkglist', help='List all packages')
        
        
        
        newpackage_parser = subparsers.add_parser('newpkg', help='Create a new package')
        newpackage_parser.add_argument('--name', required=True, help='Package name')
        newpackage_parser.add_argument('--disk_space', type=int, required=True, help='Disk space in MB')
        newpackage_parser.add_argument('--bandwidth', type=int, required=True, help='Bandwidth in MB')
        newpackage_parser.add_argument('--email_accounts', type=int, required=True, help='Number of email accounts')
        newpackage_parser.add_argument('--databases', type=int, required=True, help='Number of databases')
        newpackage_parser.add_argument('--ftp_accounts', type=int, required=True, help='Number of FTP accounts')
        newpackage_parser.add_argument('--allowed_domains', type=int, required=True, help='Allowed domains')
        newpackage_parser.add_argument('--allowed_subdomains', type=int, required=True, help='Allowed subdomains')
        newpackage_parser.add_argument('--limit_action', required=True, help='Limit action')

        ssl_parser = subparsers.add_parser('ssl', help='Issue SSL for a given domain')
        ssl_parser.add_argument('--domain', required=True, help='Domain name to issue SSL for')
        
        adddomain_parser = subparsers.add_parser('domainadd', help='Add a domain for a user')
        adddomain_parser.add_argument('--username', required=True, help='Username of the account')
        adddomain_parser.add_argument('--domain', required=True, help='Domain name to add')
        adddomain_parser.add_argument('--php_version', required=True, help='PHP version (e.g., 8.1)')
        adddomain_parser.add_argument('--path', default='public_html', help='Document root path (default: public_html)')
        
        backup_parser = subparsers.add_parser('backupnow', help='Run a local backup for a specific user')
        backup_parser.add_argument('--username', required=True, help='Username of the account to backup')
        backup_parser.add_argument('--backup_option', nargs='+', required=True, help='List of backup types (coma separated)')
        backup_parser.add_argument('--category', default='default', help='Backup category')

        makedb_parser = subparsers.add_parser('makedb', help='Create a database for a user')
        makedb_parser.add_argument('--username', required=True, help='Username of the account')
        makedb_parser.add_argument('--dbname', required=True, help='Database name to create')
        makedb_parser.add_argument('--dbuser', help='Database user (optional)')
        makedb_parser.add_argument('--dbpass', help='Database password (optional, required if dbuser provided)')
        makedb_parser.add_argument('--dbpassc', help='Database password confirmation (optional, required if dbuser provided)')

    
        cron_parser = subparsers.add_parser('cronjob_add', help='Add a new cron job for a user')
        cron_parser.add_argument('--username', required=True, help='Username of the account')
        cron_parser.add_argument('--minute', required=True, help='Minute field for cron (0-59 or *)')
        cron_parser.add_argument('--hour', required=True, help='Hour field for cron (0-23 or *)')
        cron_parser.add_argument('--day', required=True, help='Day of month field for cron (1-31 or *)')
        cron_parser.add_argument('--month', required=True, help='Month field for cron (1-12 or *)')
        cron_parser.add_argument('--weekday', required=True, help='Day of week field for cron (0-6 or *)')
        cron_parser.add_argument('--comm', required=True, help='Command to execute')

        fixperm_parser = subparsers.add_parser('fixperm', help='Fix folder permission for a user')
        fixperm_parser.add_argument('--username', required=True, help='Username of the account')
        fixperm_parser.add_argument('--full_path', required=True, help='Full path inside /home/username/')


        dbedit_parser = subparsers.add_parser('dbedit', help='Edit or delete a user database')
        dbedit_parser.add_argument('--username', required=True, help='Username of the owner')
        dbedit_parser.add_argument('--db', required=True, help='Database name')
        dbedit_parser.add_argument('--action', required=True, choices=['edit','delete'], help='Action to perform')
        dbedit_parser.add_argument('--data', help='Optional JSON data for editing (as string)')


        
    def handle(self, *args, **options):
        try:
            command = options.get('command')
            self.stderr.write(f"Running comand for {command}")

            if command == 'adduser':
                output = self.add_new_user(options)
                if output:
                    self.stdout.write(output);
            elif command == 'actionuser':
                self.suspend_user(options)
            elif command == 'edituser':
                self.update_user(options) 
            elif command == 'pkglist':
                self.list_packages(options)
            elif command == 'newpkg':
                self.new_package(options)
            elif command == 'ssl':
                self.issue_ssl_by_domain(options)
            elif command == 'domainadd':
                self.add_domain_by_username(options)
            elif command == 'backupnow':
                self.backup_now(options) 
            elif command == 'makedb':
                self.create_database_command(options)   
            elif command == 'cronjob_add':
                self.add_cronjob_command(options)
            elif command == 'fixperm':
                self.fix_user_permission_command(options)  
            elif command == 'dbedit':
                self.db_edit_command(options)
    
            else:
                self.stderr.write("❌ No valid command provided. Use --help for usage.")

        except Exception as e:
            self.stderr.write(f"❌ Error: {e}")   
  

    

    def add_new_user(self, options):
        
        if options['domain']:
            username = options['username']
            first_name = options['first_name']
            last_name = options['last_name']
            email = options['email']
            pkg_id = options['pkg_id']
            password = options['password']
            domain_name = options['domain']
            php_name = options['php_version']

            # Check if username already exists
            if User.objects.filter(username=username).exists():
                self.stdout.write(json.dumps({
                    "success": False,
                    "message": "A username with the same name already exists."
                }))

            hashed_password = make_password(password)

            # Create new user
            new_user = User(
                username=username,
                first_name=first_name,
                last_name=last_name,
                email=email,
                password=hashed_password,
            )
            new_user.save()
            password_save_file(username, password)

            last_insert_id = new_user.id
            update_fields = {
                'pkg_id': pkg_id
            }
            update_user_data(last_insert_id, update_fields)

            doc_root = os.path.join("/home", username)
            try:
                package = Package.objects.get(id=pkg_id)
            except (Package.DoesNotExist, ValueError):
                self.stdout.write(json.dumps({
                    "success": False,
                    "message": "Invalid package ID."
                }))
            soft_limit = package.disk_space
            hard_limit = 0 if soft_limit == 0 else soft_limit + 200

            # set_disk_quota(username, doc_root, soft_limit, hard_limit)

            result = make_domains(domain_name, php_name, username, 'public_html')
            if not result['success']:
                self.stdout.write(json.dumps({
                    "success": False,
                    "message": result['message']
                }))

            hashed_password = hash_password_crypt(password)
            base_dir = f'/home/{username}'
            uid, gid = get_uid_gid(username)

            new_ftp = Ftps(
                user=username,
                dir=base_dir,
                password=hashed_password,
                userid=last_insert_id,
                QuotaSize=0,
                uid=uid,
                gid=gid,
                status=1
            )
            new_ftp.save()

            home_base_dir = f'/home/{username}/public_html'
            create_index_file(home_base_dir)
            set_permissions_and_ownership(f'{home_base_dir}/index.html', username)

            self.stdout.write(json.dumps({
                "success": True,
                "message": result['message'],
                "user_id": last_insert_id
            }))

          

    def suspend_user(self, options):
        username = options['username']
        state = options['state'].upper()

        try:
            usr = User.objects.get(username=username)
        except User.DoesNotExist:
            output = {
                "success": False,
                "message": f"User '{username}' does not exist."
            }
            self.stderr.write(json.dumps(output))
            return

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
            output = {
                "success": True,
                "message": f"User '{username}' and all associated accounts/domains have been suspended."
            }
            self.stdout.write(json.dumps(output))

        elif state == 'UNSUSPEND':
            usr.is_active = True
            usr.save()

            if ftp_accounts.exists():
                ftp_accounts.update(status=1)

            if domains.exists():
                for domain in domains:
                    vhost_action(domain.domain, 'restore')

            restart_openlitespeed()
            output = {
                "success": True,
                "message": f"User '{username}' and all associated accounts/domains have been unsuspended."
            }
            self.stdout.write(json.dumps(output))

        elif state == 'DELETE':
            if usr.is_active:
                output = {
                    "success": False,
                    "message": f"User '{username}' must be suspended before deletion."
                }
                self.stderr.write(json.dumps(output))
                return

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

            if usr.username:
                base_dir = f'/home/{usr.username}'
                if os.path.isdir(base_dir):
                    shutil.rmtree(base_dir)

                maildir_path = f"/home/vmail/{usr.username}"
                if os.path.isdir(maildir_path):
                    shutil.rmtree(maildir_path)

            usr.delete()
            restart_openlitespeed()
            output = {
                "success": True,
                "message": f"User '{username}' and all associated FTP, email accounts, and domains have been deleted."
            }
            self.stdout.write(json.dumps(output))
        elif state == 'DISABLE_OTP':
            settings, _ = UserSettings.objects.get_or_create(userid=usr.id)
            settings.two_step = 0
            settings.save()
            output = {
                "success": True,
                "message": f"OTP Disabled for User '{username}'"
            }
            self.stdout.write(json.dumps(output))
        else:
            output = {
                "success": False,
                "message": f"Unknown state '{state}'. Use SUSPEND, UNSUSPEND or DELETE."
            }
            self.stderr.write(json.dumps(output))



    def update_user(self, options):
        username = options['username']

        try:
            usr = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stderr.write(json.dumps({
                "success": False,
                "message": f"User with username '{username}' not found."
            }))

        first_name = options.get('first_name') or usr.first_name
        last_name = options.get('last_name') or usr.last_name
        email = options.get('email') or usr.email
        pkg_id = options.get('pkg_id')
        password = options.get('password')

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

        self.stdout.write(json.dumps({
            "success": True,
            "message": f"User '{username}' updated successfully.",
            "user_id": usr.id
        }))
        
        
        
    def list_packages(self, options):
        packages = Package.objects.all()
        package_list = []
        for pkg in packages:
            package_list.append({
                'id': pkg.id,
                'name': pkg.name,
                'disk_space': pkg.disk_space,
                # add other relevant fields
            })
        import json
        self.stdout.write(json.dumps({
            'success': True,
            'packages': package_list
        }, indent=2))
        
        
        
    def new_package(self, options):
        name = options.get('name')
        disk_space = options.get('disk_space')
        bandwidth = options.get('bandwidth')
        email_accounts = options.get('email_accounts')
        databases = options.get('databases')
        ftp_accounts = options.get('ftp_accounts')
        allowed_domains = options.get('allowed_domains')
        allowed_subdomains = options.get('allowed_subdomains')
        limit_action = options.get('limit_action')

        # Check if a package with the same name exists
        if Package.objects.filter(name=name).exists():
            self.stdout.write(json.dumps({
                "success": False,
                "message": "A package with the same name already exists."
            }))
            return

        # Create new package
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

        self.stdout.write(json.dumps({
            "success": True,
            "message": "Package has been added successfully.",
            "package_id": new_pk.id
        }))
        
        
        
    def issue_ssl_by_domain(self, options):
        try:
            domain_name = options.get('domain')
            if not domain_name:
                self.stderr.write(json.dumps({
                    "success": False,
                    "message": "Domain name is required."
                }))
                return

            # Get domain object
            try:
                domain_obj = Domain.objects.get(domain=domain_name)
            except Domain.DoesNotExist:
                self.stderr.write(json.dumps({
                    "success": False,
                    "message": f"Domain '{domain_name}' not found."
                }))
                return

            # Issue SSL
            success = issue_ssl_certificate(domain_obj.domain, domain_obj.path)

            if success:
                restart_openlitespeed()
                self.stdout.write(json.dumps({
                    "success": True,
                    "message": f"SSL issued successfully for '{domain_name}'."
                }))
            else:
                self.stderr.write(json.dumps({
                    "success": False,
                    "message": f"Failed to issue SSL for '{domain_name}'."
                }))

        except Exception as e:
            self.stderr.write(json.dumps({
                "success": False,
                "message": str(e)
            }))
        
        
        
        
    def add_domain_by_username(self, options):
        try:
            username = options.get('username')
            domain_name = options.get('domain')
            php_version = options.get('php_version')
            path = options.get('path', 'public_html').lstrip('/') or 'public_html'

            if not username or not domain_name or not php_version:
                self.stderr.write(json.dumps({
                    "success": False,
                    "message": "Username, domain, and php_version are required."
                }))
                return

            # Validate user
            try:
                cuser = User.objects.get(username=username)
            except User.DoesNotExist:
                self.stderr.write(json.dumps({
                    "success": False,
                    "message": f"User '{username}' not found."
                }))
                return

            # Normalize domain
            domain_name = normalize_domain(domain_name)
            if not domain_name:
                self.stderr.write(json.dumps({
                    "success": False,
                    "message": "Invalid domain format."
                }))
                return

            # Check domain exists
            if Domain.objects.filter(domain=domain_name).exists():
                self.stderr.write(json.dumps({
                    "success": False,
                    "message": f"The domain '{domain_name}' already exists."
                }))
                return

            # Check package limits
            user_package = Package.objects.filter(
                id=get_user_data_by_id(cuser.id).get('pkg_id')
            ).first()
            total_domains_count = Domain.objects.filter(userid=cuser.id).count()
            if user_package.allowed_domains != 0 and total_domains_count >= user_package.allowed_domains:
                self.stderr.write(json.dumps({
                    "success": False,
                    "message": "Domain add limit exceeded."
                }))
                return

            doc_root = os.path.join("/home", username, path)

            # Add listener mapping
            if not manage_listener_mapping("add", domain_name):
                self.stderr.write(json.dumps({
                    "success": False,
                    "message": f"Failed to add mapping for '{domain_name}'."
                }))
                return

            # Add virtual host
            if not manage_virtual_host(domain_name, username):
                self.stderr.write(json.dumps({
                    "success": False,
                    "message": f"Failed to add virtual host for '{domain_name}'."
                }))
                return

            # SSL, vhost file, permissions
            manage_ssl_listener_mapping("add", domain_name)
            create_vhost_file(domain_name, username, path)

            if not add_user_and_set_folder_permissions(username, '/home/' + username, doc_root):
                self.stderr.write(json.dumps({
                    "success": False,
                    "message": f"Failed to set folder permissions for '{domain_name}'."
                }))
                return

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

            self.stdout.write(json.dumps({
                "success": True,
                "message": f"Domain '{domain_name}' added successfully!",
                "domain_id": last_insert_id
            }))

        except Exception as e:
            self.stderr.write(json.dumps({
                "success": False,
                "message": str(e)
            }))
        
        
        
    def backup_now(self, options):
        username = options.get('username')
        backup_option = options.get('backup_option')  # this should be a list
        category = options.get('category', 'default')

        user = get_object_or_404(User, username=username)

        if not backup_option:
            self.stderr.write("Error: Please select at least one backup type.")
            return

        try:
            new_backup = BackupList(
                type=json.dumps(backup_option),
                userid=user.id,
                schedule='manual',  # no schedule for immediate backup
                category=category,
                path='local',
                username=user.username,
                host=None,
                user=None,
                password=None
            )
            new_backup.save()
            inserted_id = new_backup.id

            create_backup(user.id, new_backup)

            bk = get_object_or_404(BackupList, userid=user.id, id=inserted_id)
            bk.delete()

            self.stdout.write("Backup created successfully.")

        except Exception as e:
            self.stderr.write(f"Failed to create backup: {e}")
        
        
    def create_database_command(self, options):
        username = options['username']
        db_name = options['dbname']
        db_user = options.get('dbuser')
        db_pass = options.get('dbpass')
        db_passc = options.get('dbpassc')

        # Validate username
        try:
            user_obj = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stderr.write(json.dumps({
                "success": False,
                "message": f"User '{username}' does not exist."
            }))
            return

        if len(db_name) < 2:
            self.stderr.write(json.dumps({
                "success": False,
                "message": "Database name must be at least 2 characters."
            }))
            return

        # Check DB limit
        user_data = get_user_data_by_id(user_obj.id)
        user_package = Package.objects.filter(id=user_data.get('pkg_id')).first()
        db_count = count_users_by_prefix(username)

        if user_package and user_package.databases != 0 and db_count >= user_package.databases:
            self.stderr.write(json.dumps({
                "success": False,
                "message": "Database limit exceeded."
            }))
            return

        # Create the database
        db_success, db_error = create_database(username, db_name)
        if not db_success:
            self.stderr.write(json.dumps({
                "success": False,
                "message": db_error
            }))
            return

        # Optional DB user creation
        if db_user or db_pass or db_passc:
            if not db_user or not db_pass or not db_passc:
                self.stderr.write(json.dumps({
                    "success": False,
                    "message": "All database user fields are required."
                }))
                return

            if len(db_user) < 2:
                self.stderr.write(json.dumps({
                    "success": False,
                    "message": "Database username must be at least 2 characters."
                }))
                return

            if len(db_pass) < 8:
                self.stderr.write(json.dumps({
                    "success": False,
                    "message": "Password must be at least 8 characters."
                }))
                return

            if db_pass != db_passc:
                self.stderr.write(json.dumps({
                    "success": False,
                    "message": "Passwords do not match."
                }))
                return

            result = create_database_and_user(None, username, db_name, db_user, db_pass)
            if result is not True:
                self.stderr.write(json.dumps({
                    "success": False,
                    "message": result
                }))
                return

        self.stdout.write(json.dumps({
            "success": True,
            "message": f"Database '{db_name}' created successfully for user '{username}'."
        }))
    
    
    
    
    def add_cronjob_command(self, options):
        username = options['username']
        minute = options['minute']
        hour = options['hour']
        day = options['day']
        month = options['month']
        weekday = options['weekday']
        comm = options['comm']

        # Validate username
        try:
            user_obj = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stderr.write(json.dumps({
                "success": False,
                "message": f"User '{username}' does not exist."
            }))
            return

        # Validate all fields
        if not all([minute, hour, day, month, weekday, comm]):
            self.stderr.write(json.dumps({
                "success": False,
                "message": "All cron fields are required."
            }))
            return

        cron_command = f"{minute} {hour} {day} {month} {weekday} {comm}"

        try:
            added = manage_cron_jobs(username, cron_command)
            if added:
                self.stdout.write(json.dumps({
                    "success": True,
                    "message": "Cron job added successfully."
                }))
            else:
                self.stderr.write(json.dumps({
                    "success": False,
                    "message": "Cron job already exists."
                }))
        except Exception as e:
            self.stderr.write(json.dumps({
                "success": False,
                "message": str(e)
            }))
    
    
    
    def fix_user_permission_command(self, options):
        username = options['username']
        full_path = options['full_path'].strip()

        # Validate user
        try:
            user_obj = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stderr.write(json.dumps({
                "success": False,
                "message": f"User '{username}' does not exist."
            }))
            return

        # Validate path
        if not full_path.startswith('/home/'):
            self.stderr.write(json.dumps({
                "success": False,
                "message": "Invalid path: must start with /home/"
            }))
            return

        base_home = f"/home/{username}"

        if not full_path.startswith(base_home):
            self.stderr.write(json.dumps({
                "success": False,
                "message": "Path does not belong to the specified user."
            }))
            return

        relative_path = full_path[len(base_home):].lstrip('/')
        rebuilt_path = os.path.join(base_home, relative_path)

        result = add_user_and_set_folder_permissions(
            username,
            base_home,
            rebuilt_path
        )

        if result is True:
            restart_openlitespeed()
            self.stdout.write(json.dumps({
                "success": True,
                "message": "Permission successfully set."
            }))
        else:
            self.stderr.write(json.dumps({
                "success": False,
                "message": str(result)
            }))
    
    
    
    def db_edit_command(self, options):
        username = options['username']
        db = options['db']
        action = options['action']

        # Validate user
        try:
            user_obj = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stderr.write(json.dumps({'success': False, 'message': f"User '{username}' does not exist."}))
            return

        # Security: ensure database belongs to the user
        username_prefix = f"{username}_"
        if not db.startswith(username_prefix):
            self.stderr.write(json.dumps({'success': False, 'message': 'You are not authorized to edit this database.'}))
            return

        dbx = replace_first_with_underscore(db)

        # Only handle delete action
        if action == 'delete':
            success_message = delete_database(username, db)
            if "Error" in success_message:
                self.stderr.write(json.dumps({'success': False, 'message': success_message}))
            else:
                self.stdout.write(json.dumps({'success': True, 'message': success_message}))
        else:
            self.stderr.write(json.dumps({'success': False, 'message': 'Invalid action. Only "delete" is supported.'}))
    