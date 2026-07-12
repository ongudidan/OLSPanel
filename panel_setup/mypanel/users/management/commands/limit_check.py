import os
import requests
from datetime import datetime
from django.core.management.base import BaseCommand
from users.function import *
from users.database import *
from users.models import *
from users.bandwidth import *
from users.server_core import *  # Import your function
from users.panellogger import *  # Logger

logger = CpLogger()

# Convert MB to bytes
def mb_to_bytes(mb_value):
    return int(mb_value) * 1048576  # 1 MB = 1,048,576 bytes

def suspend_all(rid, command_instance):
    usr = get_object_or_404(User, id=rid)
    profile, created = Profile.objects.get_or_create(user=usr)  # Ensure Profile exists
    ftp_accounts = Ftps.objects.filter(userid=usr.id)  # Retrieve all FTP accounts for this user
    email_accounts = Emails.objects.filter(userid=usr.id)  # Retrieve all email accounts for this user
    domains = Domain.objects.filter(userid=usr.id)  # Retrieve all domains for this user
    emf = EmailForword.objects.filter(userid=usr.id)
    
    # Suspend the user by deactivating them
    usr.is_active = False
    usr.save()

    # Update FTP accounts' status to inactive (suspended)
    if ftp_accounts.exists():
        ftp_accounts.update(status=0)
        
    # Suspend the domains associated with this user
    if domains.exists():
        for domain in domains:
            vhost_action(domain.domain, 'suspend')
        restart_openlitespeed()

    command_instance.stdout.write(f"User {usr.username} suspended due to exceeding limits.")

class Command(BaseCommand):
    help = "Checks if users' disk and bandwidth usage exceed package limits"

    def handle(self, *args, **kwargs):
        users_list = User.objects.filter(is_active=True).exclude(id=1)  # Fetch active users except admin

        for user in users_list:
            try:
                username_string = user.username

                # Get user's disk usage (in bytes)
                disk = get_disk_usage(f'/home/{username_string}')
                email_disk = get_disk_usage(f'/home/vmail/{username_string}')
                database_names = get_user_database_info(username_string)
                total_db_size = calculate_total_database_size(database_names)

                # Convert disk values to bytes
                disk_in_bytes = human_readable_to_bytes(str(disk)) if isinstance(disk, str) else disk
                email_disk_in_bytes = human_readable_to_bytes(str(email_disk)) if isinstance(email_disk, str) else email_disk
                total_size_in_bytes = disk_in_bytes + total_db_size + email_disk_in_bytes

                # Get the user's package details
                user_data = get_user_data_by_id(user.id)
                user_package = Package.objects.filter(id=user_data.get('pkg_id')).first()

                if not user_package:
                    self.stderr.write(f"⚠️ No package assigned to user {username_string}, skipping...")
                    continue

                # Convert package limits from MB to bytes
                pkg_disk_limit_bytes = mb_to_bytes(user_package.disk_space) if user_package.disk_space else 0
                pkg_bandwidth_limit_bytes = mb_to_bytes(user_package.bandwidth) if user_package.bandwidth else 0

                # Bandwidth Calculation
                bandwidth_total(username_string)
                current_month_year = datetime.now().strftime('%m-%Y')
                bandwidth = Bandwidth.objects.filter(userid=user.id, date=current_month_year).first()
                total_bandwidth_used_bytes = human_readable_to_bytes(str(bandwidth.total)) if bandwidth and bandwidth.total else 0

                # Compare usage with package limits (all in bytes)
                disk_exceeded = pkg_disk_limit_bytes > 0 and total_size_in_bytes > pkg_disk_limit_bytes
                bandwidth_exceeded = pkg_bandwidth_limit_bytes > 0 and total_bandwidth_used_bytes > pkg_bandwidth_limit_bytes

                # Convert bytes to MB for display
                total_size_mb = total_size_in_bytes // 1048576
                email_disk_mb = email_disk_in_bytes // 1048576
                db_size_mb = total_db_size // 1048576
                total_bandwidth_used_mb = total_bandwidth_used_bytes // 1048576

                # Package Data
                pkg_data = {
                    'name': user_package.name,
                    'disk_space': f"{user_package.disk_space} MB" if user_package.disk_space else "Unlimited",
                    'disk_use': f"{total_size_mb} MB",
                    'disk_use_email': f"{email_disk_mb} MB",
                    'disk_use_db': f"{db_size_mb} MB",
                    'bandwidth': f"{user_package.bandwidth} MB" if user_package.bandwidth else "Unlimited",
                    'bandwidth_use': f"{total_bandwidth_used_mb} MB",
                    'email_accounts': check_limit(user_package.email_accounts),
                    'total_email_count': Emails.objects.filter(userid=user.id).count(),
                    'databases': check_limit(user_package.databases),
                    'databases_use': count_users_by_prefix(username_string),
                    'ftp_accounts': check_limit(user_package.ftp_accounts),
                    'ftp_accounts_use': Ftps.objects.filter(userid=user.id).count(),
                    'allowed_domains': check_limit(user_package.allowed_domains),
                    'domain_use': Domain.objects.filter(userid=user.id).count(),
                    'main_domain': Domain.objects.filter(userid=user.id).order_by('id').first(),
                }

                # Log the results
                self.stdout.write(f"✅ User: {username_string} | Disk Usage: {pkg_data['disk_use']}/{pkg_data['disk_space']} | "
                                  f"Bandwidth Usage: {pkg_data['bandwidth_use']}/{pkg_data['bandwidth']}")

                # Only suspend the user if at least one limit exceeded and the user has not been suspended yet
                if (disk_exceeded or bandwidth_exceeded) and user.is_active:
                    suspend_all(user.id, self)  # Pass the command instance to suspend_all function
                    logger.error(f"Suspended user {username_string} for exceeding limits!")
                    self.stdout.write(f"⚠️ {('Disk' if disk_exceeded else 'Bandwidth')} limit exceeded for user {username_string}!")

            except Exception as e:
                self.stderr.write(f"❌ Error processing user {user.id} ({username_string}): {str(e)}")
