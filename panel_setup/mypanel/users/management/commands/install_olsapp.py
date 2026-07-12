from django.core.management.base import BaseCommand
from users.function import *
from users.server_core import *
from whm.function import *
import subprocess

class Command(BaseCommand):
    help = "Installs and configures OLSApp components"

    def handle(self, *args, **kwargs):
        try:
            # Install curl for PHP 8.1 and 8.2
            for version in ["8.1", "8.2"]:
                result = manage_php_extension(version, "curl", "install")
                self.stdout.write(f"[PHP {version}] curl install result: {result}")
                result = manage_php_extension(version, "sqlite3", "install")
                self.stdout.write(f"[PHP {version}] sqlite install result: {result}")
                result = manage_php_extension(version, "xml", "install")
                self.stdout.write(f"[PHP {version}] xml install result: {result}")

            # Restart LSPHP and OpenLiteSpeed
            restart_lsphp()
            

            
            write_httpd_config_olsapp()

            # Ensure user creation
            ensure_group_exists_and_create_user('olspanel', ['nobody'], 'olspanel')
            ensure_group_exists_and_create_user('olspanel', ['nogroup', 'www-data'], 'olspanel')

            # Setup vhosts
            get_all_panel_domains_and_create_vhosts()

            self.stdout.write(self.style.SUCCESS("✅ Olsapp successfully installed."))
            restart_openlitespeed()

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Error installing Olsapp: {str(e)}"))
