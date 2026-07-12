import os
from django.core.management.base import BaseCommand
from users.models import BackupList
from whm.models import *
from file_manager.models import * 
from users.function import *
from users.database import *
from django.utils import timezone
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = "Creates backups and saves them locally or sends them via FTP."

    def add_arguments(self, parser):
        # Add flags for different time-based filters: hour, day, week, month
        parser.add_argument('--hour', action='store_true', help='Run backups for the hour schedule.')
        parser.add_argument('--day', action='store_true', help='Run backups for the day schedule.')
        parser.add_argument('--week', action='store_true', help='Run backups for the week schedule.')
        parser.add_argument('--month', action='store_true', help='Run backups for the month schedule.')

    def handle(self, *args, **options):
        # Check which argument is passed and assign the corresponding schedule value
        schedule_value = None
                
        
        
            
        # Check for the flags and set the schedule value accordingly
        
        if options['hour']:
            schedule_value = 'hour'
            self.stdout.write(f"Processing backups for hour schedule...")
        elif options['day']:
            schedule_value = 'day'
            self.stdout.write(f"Processing backups for day schedule...")
        elif options['week']:
            schedule_value = 'week'
            self.stdout.write(f"Processing backups for week schedule...")
        elif options['month']:
            schedule_value = 'month'
            self.stdout.write(f"Processing backups for month schedule...")
        else:
            self.stderr.write("Error: You must specify one of the arguments --hour, --day, --week, or --month.")
            return
        
        field_map = {
            'hour': 'hour_maximum_backup',
            'day': 'day_maximum_backup',
            'week': 'week_maximum_backup',
            'month': 'month_maximum_backup',
        }

        field = field_map[schedule_value]
            
        for user in User.objects.all():
            #max_backup = int(AppSettings.objects.filter(setting_key=f'{user.username}_maximum_backup').values_list('setting_value', flat=True).first() or 100)
            max_backup = int(UserSettings.objects.filter(userid=user.id).values_list(field, flat=True).first() or 100)
            backup_dir = f'/home/{user.username}/backup'
            delete_old_local_backups(max_backup,backup_dir,schedule_value)  
            

        max_backup = int(AppSettings.objects.filter(setting_key=f'{schedule_value}_maximum_backup').values_list('setting_value', flat=True).first() or 100)

        delete_old_local_backups(max_backup,'/home/backup',schedule_value)
        
        
        # Filter backups based on the value of the schedule (hour, day, week, or month)
        backups = BackupList.objects.filter(schedule=schedule_value)

        # Process each backup
        for backup in backups:
            try:
                username = backup.userid
                
                # Call the function to create the backup (implement backup creation in create_backup function)
                if backup.path == "ftp":
                    if backup.user_access == 1:
                        fmax_backup = int(AppSettings.objects.filter(setting_key=f'{schedule_value}_maximum_backup').values_list('setting_value', flat=True).first() or 100)
                    else:
                        fmax_backup = int(UserSettings.objects.filter(userid=backup.userid).values_list(field, flat=True).first() or 100)
                        
                        
                        
                    delete_old_ftp_backups(backup.host, backup.user, backup.password, "/",fmax_backup)
                    
                success = create_backup(username, backup,schedule_value)

                if success:
                    self.stdout.write(f"Backup for {username} completed successfully.")
                else:
                    self.stderr.write(f"Failed to create backup for {username}.")
            except Exception as e:
                self.stderr.write(f"Error processing backup for {backup.userid}: {e}")

    def ftp_backup(self, backup, username):
        # Example FTP backup logic
        self.stdout.write(f"Performing FTP backup for {username}...")
        # Implement FTP logic here
        pass

    def local_backup(self, backup, username):
        # Example local backup logic
        self.stdout.write(f"Performing local backup for {username}...")
        # Implement local backup logic here
        pass
