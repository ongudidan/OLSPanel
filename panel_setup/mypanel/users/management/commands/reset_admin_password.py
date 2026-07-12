from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from django.db import connection

class Command(BaseCommand):
    help = 'Resets the Panel admin password for user ID 1.'

    def add_arguments(self, parser):
        # Add an argument to accept the new password from the command line
        parser.add_argument('new_password', type=str, help='The new password for the admin user')

    def handle(self, *args, **kwargs):
        new_password = kwargs['new_password']

        # Generate hashed password
        hashed_password = make_password(new_password)

        try:
            # Using Django's default database connection to update the password
            with connection.cursor() as cursor:
                cursor.execute("UPDATE auth_user SET password = %s WHERE id = 1", [hashed_password])
                self.stdout.write(self.style.SUCCESS('✅ Panel admin password updated successfully!'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Error: {e}"))
