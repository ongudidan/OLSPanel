import re
from .models import *
import os
import base64
from datetime import datetime,timedelta
from django.db.models import Q
from django.db import IntegrityError
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.contrib.auth.views import LoginView, PasswordResetView, PasswordChangeView
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.views import View
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from .forms import RegisterForm, LoginForm, UpdateUserForm, UpdateProfileForm
from .forms import DomainForm
from .server_core import *  # Import your function
from .database import *  # Import your function
from django.db import connection
from .function import *  # Import your function
from .bandwidth import *  # Import your function
from django.contrib.auth.hashers import make_password

def get_userid_from_username(username):
    """
    Retrieve the userid for a given username.
    """
    try:
        user = User.objects.get(username=username)
        return user.id
    except User.DoesNotExist:
        print(f"User with username '{username}' does not exist.")
        return None

def read_last_position(username):
    """
    Read the last position (line) and total bandwidth for a user.
    Insert a new row if it does not exist for the current month in mm-YYYY format.
    If there is no data for the current month, use the last month's line value if available.
    """
    try:
        # Get the userid
        userid = get_userid_from_username(username)
        if userid is None:
            print(f"User with username '{username}' does not exist.")
            return 0, 0

        # Get the current month and year in mm-YYYY format
        current_month_year = datetime.now().strftime('%m-%Y')

        # Check for an entry for the current mm-YYYY
        bandwidth_entry = Bandwidth.objects.filter(userid=userid, date=current_month_year).first()

        if bandwidth_entry:
            # Return the existing line and total
            return bandwidth_entry.line, bandwidth_entry.total
        else:
            # Calculate the previous month and year in mm-YYYY format
            first_day_of_current_month = datetime.now().replace(day=1)
            last_day_of_previous_month = first_day_of_current_month - timedelta(days=1)
            previous_month_year = last_day_of_previous_month.strftime('%m-%Y')

            # Check for an entry for the previous month
            previous_bandwidth_entry = Bandwidth.objects.filter(userid=userid, date=previous_month_year).first()

            # Use previous month's line if available, otherwise default to 0
            previous_line = previous_bandwidth_entry.line if previous_bandwidth_entry else 0

            # Insert a new row for the current month
            Bandwidth.objects.create(userid=userid, date=current_month_year, line=previous_line, total=0)

            # Return the new row's values
            return previous_line, 0  # Default total is 0

    except Exception as e:
        print(f"Error reading last position: {e}")
        return 0, 0

    except IntegrityError as e:
        print(f"Database integrity error: {e}")
        return 0, 0
    except Exception as e:
        print(f"Error reading last position: {e}")
        return 0, 0

def read_last_positionx(username,domain):
    position_file = f"/home/{username}/logs/{domain}.pos"
    if os.path.exists(position_file):
        with open(position_file, 'r') as pos_file:
            lines = pos_file.readlines()
            last_position = int(lines[0].strip()) if len(lines) > 0 and lines[0].strip().isdigit() else 0
            existing_bandwidth = int(lines[1].strip()) if len(lines) > 1 and lines[1].strip().isdigit() else 0
            return last_position, existing_bandwidth
    return 0, 0

def update_last_positionx(username,domain,new_position, total_bandwidth):
    position_file = f"/home/{username}/logs/{domain}.pos"
    with open(position_file, 'w') as pos_file:
        pos_file.write(f"{new_position}\n")  # Write new position on the first line
        pos_file.write(f"{total_bandwidth}\n")  # Write total bandwidth on the second line
        
def update_last_position(username, line, total):
    """
    Update the last position (line) and total bandwidth for a user.
    If a record for the current mm-YYYY does not exist, create it.
    """
    try:
        # Get the userid
        userid = get_userid_from_username(username)
        if userid is None:
            print(f"User with username '{username}' does not exist.")
            return

        # Get the current month and year in mm-YYYY format
        current_month_year = datetime.now().strftime('%m-%Y')

        if Bandwidth.objects.filter(userid=userid, date=current_month_year).exists():
            # Update the existing record
            band = get_object_or_404(Bandwidth, userid=userid, date=current_month_year)
            band.total = total
            band.line = line
            band.save()
        else:
            # Create a new record if none exists
            new_ban = Bandwidth(
                total=0,
                line=line,
                date=current_month_year,
                userid=userid
            )
            new_ban.save()

    except Exception as e:
        print(f"Error updating position: {e}")

        

def calculate_total_bandwidth(username, domain, last_position):
    log_file = f"/home/{username}/logs/{domain}.access_log"
    log_pattern = r"(\d{3}) (\d+)"  # Matches HTTP response size following status code

    # Read last position and existing bandwidth
    last_positionx, existing_bandwidth = read_last_position(username)

    # Ensure existing_bandwidth is an integer
    total_bandwidth = int(existing_bandwidth)

    # Open the log file and read from the last position
    if os.path.exists(log_file):
        current_file_size = os.path.getsize(log_file)
        
        # If file is empty or the size is less than the last position, reset last position
        if current_file_size == 0 or current_file_size < last_position:
            last_position = 0

        with open(log_file, 'r') as file:
            try:
                # Move the file pointer to the last read position
                file.seek(last_position)
            except Exception as e:
                print(f"Error seeking to last position: {e}")
                file.seek(0)  # Fallback to the beginning if error occurs

            # Read new lines from the log file
            new_lines = file.readlines()
            new_position = file.tell()  # Get the new position after reading

            for line in new_lines:
                match = re.search(log_pattern, line)
                if match:
                    size_str = match.group(2)  # Size is in the second capture group
                    size = int(size_str) if size_str.isdigit() else 0

                    # Update total bandwidth
                    total_bandwidth += size
                else:
                    print(f"No match for line: {line.strip()}")  # Debugging line

            # Update last position and total bandwidth in the database
            update_last_position(username, new_position, total_bandwidth)

            # Get domain object and save the new position
            userid = get_userid_from_username(username)
            dm = get_object_or_404(Domain, userid=userid, domain=domain)
            dm.line = new_position
            dm.save()

    else:
        print(f"Log file not found: {log_file}")

    # Return the total bandwidth in bytes
    return total_bandwidth
    
    
    
def bandwidth_total(username):
    # Get the list of access log files for the given username
    userid = get_userid_from_username(username)
    domains = Domain.objects.filter(userid=userid)

    print("Access log files:")
    for domain in domains:       
        total_bandwidth = calculate_total_bandwidth(username, domain.domain,domain.line)

       
    return sum_second_line_from_files(username)
    
        
def sum_second_line_from_files(username):
    total_sum=0
    

    return total_sum 


