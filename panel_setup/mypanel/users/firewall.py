from datetime import timedelta, datetime
from django.utils import timezone
import os
import subprocess
import ipaddress
import time
import re
from .models import *
from django.db import models
import glob
import configparser
from users.panellogger import *
logger = CpLogger()
from django.utils.timezone import now
from django.db.models import Q
from django.conf import settings

def load_config(path):
    # Read config file and ensure it has a section header
    with open(path, "r") as f:
        content = f.read()
    if not content.strip().startswith("[DEFAULT]"):
        content = "[DEFAULT]\n" + content

    cfg = configparser.ConfigParser()
    cfg.optionxform = str  # preserve case
    cfg.read_string(content)

    def parse_list(val):
        # Comma-separated values → list, strip spaces
        return [item.strip() for item in val.split(",") if item.strip()]

    # Safely get int with default fallback
    def get_int_with_default(section, option, default=0):
        try:
            return cfg.getint(section, option)
        except Exception:
            return default

    return {
        "STATUS": get_int_with_default("DEFAULT", "STATUS", 0),
        "LOG_FILE": cfg.get("DEFAULT", "LOG_FILE"),
        "DATA_FILE": cfg.get("DEFAULT", "DATA_FILE"),
        "TEMP_BLOCK_DURATION": timedelta(minutes=get_int_with_default("DEFAULT", "TEMP_BLOCK_DURATION", 10)),
        "TEMP_BLOCK_THRESHOLD": get_int_with_default("DEFAULT", "TEMP_BLOCK_THRESHOLD", 5),
        "TEMP_WINDOW": timedelta(minutes=get_int_with_default("DEFAULT", "TEMP_WINDOW", 5)),
        "PERM_BLOCK_THRESHOLD": get_int_with_default("DEFAULT", "PERM_BLOCK_THRESHOLD", 50),
        "PERM_WINDOW": timedelta(hours=get_int_with_default("DEFAULT", "PERM_WINDOW", 24)),
        "KEYWORD": parse_list(cfg.get("DEFAULT", "KEYWORD")),
        "IGNORE_IP": parse_list(cfg.get("DEFAULT", "IGNORE_IP"))
    }

#LOG_FILE = "/var/log/auth.log"
#OFFSET_FILE = "/tmp/authlog_offset.dat"


"""
TEMP_BLOCK_DURATION = timedelta(minutes=10)
TEMP_BLOCK_THRESHOLD = 5       # 5 attempts in 5 mins
PERM_BLOCK_THRESHOLD = 50      # 50 temp blocks in 24 hours
TEMP_WINDOW = timedelta(minutes=5)
PERM_WINDOW = timedelta(hours=24)
"""

firewall_changed = False 

def get_offset_file_for_log(offset_dir, log_file_path):
    # Make sure offset_dir ends with /
    offset_dir = offset_dir.rstrip("/") + "/"
    # Take basename of log file
    log_filename = os.path.basename(log_file_path)
    # Create offset filename, replace dots with underscores or keep dots if you want
    offset_filename = f"{log_filename}.dat"
    # Full path
    return os.path.join(offset_dir, offset_filename)
    
def get_saved_offset(OFFSET_FILE):
    try:
        with open(OFFSET_FILE, "r") as f:
            content = f.read().strip()
            if not content:
                return None
            return int(content)
    except Exception:
        return None

def save_offset(OFFSET_FILE,offset):
    with open(OFFSET_FILE, "w") as f:
        f.write(str(offset))

def temp_block_ip(ip,TEMP_BLOCK_DURATION):
    global firewall_changed
    try:
        ipaddress.ip_address(ip)
    except ValueError:
        logger.error(f"Invalid IP address format: {ip}")
        return
    try:
        subprocess.run(["ufw", "insert", "1", "deny", "from", ip, "comment", "auto_temp_block"], check=True)
        # Fallback raw iptables drop at top to override any high-priority raw ACCEPT rules
        subprocess.run(["iptables", "-I", "INPUT", "1", "-s", ip, "-j", "DROP", "-m", "comment", "--comment", "auto_temp_block"], check=True)
        firewall_changed = True
        logger.info(f"[TEMP BLOCK] {ip} blocked for {TEMP_BLOCK_DURATION.total_seconds() / 60} minutes.")
        print(f"[TEMP BLOCK] {ip} blocked for {TEMP_BLOCK_DURATION.total_seconds() / 60} minutes.")
    except Exception as e:
        logger.error(f"Error running ufw block for {ip}: {e}")

def perm_block_ip(ip):
    global firewall_changed
    try:
        ipaddress.ip_address(ip)
    except ValueError:
        logger.error(f"Invalid IP address format: {ip}")
        return
    try:
        subprocess.run(["ufw", "insert", "1", "deny", "from", ip, "comment", "auto_permanently_block"], check=True)
        # Fallback raw iptables drop at top to override any high-priority raw ACCEPT rules
        subprocess.run(["iptables", "-I", "INPUT", "1", "-s", ip, "-j", "DROP", "-m", "comment", "--comment", "auto_permanently_block"], check=True)
        firewall_changed = True
        logger.info(f"[PERM BLOCK] {ip} permanently blocked.")
        print(f"[PERM BLOCK] {ip} permanently blocked.")
    except Exception as e:
        logger.error(f"Error running ufw perm block for {ip}: {e}")

def remove_perm_firewall_rule(ip):
    global firewall_changed
    try:
        ipaddress.ip_address(ip)
    except ValueError:
        logger.error(f"Invalid IP address format: {ip}")
        return
    try:
        subprocess.run(["ufw", "delete", "deny", "from", ip, "comment", "auto_permanently_block"], check=True)
        # Remove fallback raw iptables drop rule
        subprocess.run(["iptables", "-D", "INPUT", "-s", ip, "-j", "DROP", "-m", "comment", "--comment", "auto_permanently_block"], check=True)
        firewall_changed = True
        logger.info(f"[PERM BLOCK REMOVED] {ip} block removed.")
        print(f"[PERM BLOCK REMOVED] {ip} block removed.")
    except Exception as e:
        logger.error(f"Error removing perm block for {ip}: {e}")

def remove_firewall_rule(ip):
    global firewall_changed
    try:
        ipaddress.ip_address(ip)
    except ValueError:
        logger.error(f"Invalid IP address format: {ip}")
        return
    try:
        subprocess.run(["ufw", "delete", "deny", "from", ip, "comment", "auto_temp_block"], check=True)
        # Remove fallback raw iptables drop rule
        subprocess.run(["iptables", "-D", "INPUT", "-s", ip, "-j", "DROP", "-m", "comment", "--comment", "auto_temp_block"], check=True)
        firewall_changed = True
        logger.info(f"[TEMP BLOCK REMOVED] {ip} block removed.")
        print(f"[TEMP BLOCK REMOVED] {ip} block removed.")
    except Exception as e:
        logger.error(f"Error removing ufw block for {ip}: {e}")


def monitor_failed_ssh_logins(LOG_FILE,OFFSET_FILE,keywords,TEMP_BLOCK_DURATION,TEMP_BLOCK_THRESHOLD,PERM_BLOCK_THRESHOLD,PERM_WINDOW,TEMP_WINDOW,IGNORE_IP,TYPE):
    global firewall_changed
    
    offset = get_saved_offset(OFFSET_FILE)

    try:
        filesize = os.path.getsize(LOG_FILE)
    except FileNotFoundError:
        print(f"[!] Log file {LOG_FILE} not found.")
        return  # exit immediately for cron

    with open(LOG_FILE, "r") as f:
        if offset is None or offset > filesize:
            # Start from the end, don't read old lines
            f.seek(0, 2)
            offset = f.tell()
            save_offset(OFFSET_FILE,offset)
            print(f"[*] Starting at end of file (offset={offset})")
            return  # nothing new to read, exit

        # Go to last saved offset
        f.seek(offset)

        while True:
            line = f.readline()
            if not line:
                break  # no more new lines, exit loop

            offset = f.tell()
            save_offset(OFFSET_FILE,offset)

            found, matched_keyword = find_keyword_in_line(line, keywords)
            if found:
                timestamp = extract_syslog_timestamp(line)
                if timestamp:
                    timestamp = make_aware(timestamp) 
                    print(f"Extracted datetime: {timestamp}")
                    ips = extract_ips(line)
                    filtered_ips = [ip for ip in ips if not is_local_ip(ip,IGNORE_IP)]
                    if filtered_ips:
                        for ip in filtered_ips:
                            register_failed_attempt(ip, timestamp,TEMP_BLOCK_DURATION,TEMP_BLOCK_THRESHOLD,PERM_BLOCK_THRESHOLD,PERM_WINDOW,TEMP_WINDOW,TYPE)
            
                        
            
       
                    print(f"IPs found: {filtered_ips}")
    
    
    
def make_aware(dt):
    if dt is None:
        return None
    if settings.USE_TZ:
        if timezone.is_naive(dt):
            return timezone.make_aware(dt, timezone.get_current_timezone())
        else:
            return dt
    else:
        # Strip timezone info if any, because DB expects naive datetime
        if not timezone.is_naive(dt):
            return dt.replace(tzinfo=None)
        return dt    

def make_awareold(dt):
    if timezone.is_naive(dt):
        # Assume your log timestamps are in local time or UTC, adjust accordingly
        return timezone.make_aware(dt, timezone.get_current_timezone())
    return dt

def is_local_ip(ip, IGNORE_IP):
    local_prefixes = [
        "127.", "::1", "10.", "172.16.", "172.17.", "172.18.", "172.19.", "172.20.",
        "172.21.", "172.22.", "172.23.", "172.24.", "172.25.", "172.26.", "172.27.",
        "172.28.", "172.29.", "172.30.", "172.31.", "192.168.", "169.254.", "fc00:", "fe80:"
    ]

    if any(ip.startswith(prefix) for prefix in local_prefixes):
        return True

    # Normalize IGNORE_IP to a list if it's a string
    if isinstance(IGNORE_IP, str):
        IGNORE_IP = [IGNORE_IP]

    if ip in IGNORE_IP:
        return True

    return False


def extract_ips(line):
    """
    Extract all IPv4 and IPv6 addresses from a text line.
    Returns a list of IPs found (can be empty if none found).
    """

    # IPv4 regex
    ipv4_pattern = r"(?:\d{1,3}\.){3}\d{1,3}"

    # IPv6 regex (simple version, matches normal full or abbreviated IPv6)
    ipv6_pattern = (
        r"(?:(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|"
        r"(?:[0-9a-fA-F]{1,4}:){1,7}:|"
        r"(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|"
        r"(?:[0-9a-fA-F]{1,4}:){1,5}(?::[0-9a-fA-F]{1,4}){1,2}|"
        r"(?:[0-9a-fA-F]{1,4}:){1,4}(?::[0-9a-fA-F]{1,4}){1,3}|"
        r"(?:[0-9a-fA-F]{1,4}:){1,3}(?::[0-9a-fA-F]{1,4}){1,4}|"
        r"(?:[0-9a-fA-F]{1,4}:){1,2}(?::[0-9a-fA-F]{1,4}){1,5}|"
        r"[0-9a-fA-F]{1,4}:(?:(?::[0-9a-fA-F]{1,4}){1,6})|"
        r":(?:(?::[0-9a-fA-F]{1,4}){1,7}|:))"
    )

    ip_pattern = re.compile(f"({ipv4_pattern})|({ipv6_pattern})")

    ips = []
    for match in ip_pattern.finditer(line):
        # match.group(1) = IPv4 if matched, else None
        # match.group(2) = IPv6 if matched, else None
        ips.append(match.group(1) or match.group(2))

    return ips

def extract_syslog_timestamp_old(line, year=None):
    """
    Extract the timestamp from a syslog line in format: 'Aug  8 19:09:07'
    Returns a datetime.datetime object (using current year if not specified).
    Returns None if no valid timestamp found.
    """
    # Default to current year if not provided
    if year is None:
        year = datetime.now().year

    # Regex pattern for syslog date/time (month, day, HH:MM:SS)
    # Example: "Aug  8 19:09:07"
    pattern = r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s{1,2}(\d{1,2})\s(\d{2}:\d{2}:\d{2})"

    match = re.match(pattern, line)
    if not match:
        return None

    month_str, day_str, time_str = match.groups()

    # Parse month name to month number
    month = datetime.strptime(month_str, "%b").month
    day = int(day_str)

    # Combine into datetime string
    datetime_str = f"{year}-{month:02d}-{day:02d} {time_str}"

    try:
        dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
        return dt
    except ValueError:
        return None

def extract_syslog_timestamp(line):
    
    # A list of regex patterns and their corresponding datetime formats.
    # The order is important: start with the most specific patterns.
    patterns_and_formats = [
        # Example: '2026-07-24T07:22:10.683067+00:00'
        (r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}(?:[+-]\d{2}:\d{2}|Z))", "iso"),
        # Example: '2025-08-05 01:15:02.113502'
        (r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{6})", "%Y-%m-%d %H:%M:%S.%f"),
        # Example: '2025-08-05 01:15:02'
        (r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", "%Y-%m-%d %H:%M:%S"),
        # Example: 'Aug  8 19:09:07' (Syslog-style)
        (r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s{1,2}(\d{1,2})\s(\d{2}:\d{2}:\d{2})", "%b %d %H:%M:%S"),
    ]

    for pattern_str, fmt in patterns_and_formats:
        match = re.search(pattern_str, line)
        if match:
            if fmt == "iso":
                try:
                    return datetime.fromisoformat(match.group(1))
                except ValueError:
                    continue
            # For the syslog format, we need to add the current year.
            elif fmt == "%b %d %H:%M:%S":
                try:
                    month_str, day_str, time_str = match.groups()
                    current_year = datetime.now().year
                    # Reconstruct the string with the current year
                    datetime_str = f"{current_year} {month_str} {day_str} {time_str}"
                    dt = datetime.strptime(datetime_str, "%Y %b %d %H:%M:%S")

                    # Handle case where timestamp is from the previous year
                    if dt > datetime.now():
                        dt = dt.replace(year=current_year - 1)
                    return dt
                except ValueError:
                    continue # Continue to next pattern if this fails
            else:
                # For all other formats, parse the matched substring directly.
                try:
                    return datetime.strptime(match.group(1), fmt)
                except ValueError:
                    continue # Continue to next pattern if this fails
    return None


def register_panel_failed_login(ip):
    try:
        conf_file = "/usr/local/ufw/config/olspanel.conf"
        if not os.path.exists(conf_file):
            return
        conf_data = load_config(conf_file)
        STATUS = conf_data.get("STATUS", 0)
        if STATUS != 1:
            return
            
        TEMP_BLOCK_DURATION = conf_data["TEMP_BLOCK_DURATION"]
        TEMP_BLOCK_THRESHOLD = conf_data["TEMP_BLOCK_THRESHOLD"]
        TEMP_WINDOW = conf_data["TEMP_WINDOW"]
        PERM_BLOCK_THRESHOLD = conf_data["PERM_BLOCK_THRESHOLD"]
        PERM_WINDOW = conf_data["PERM_WINDOW"]
        IGNORE_IP = conf_data["IGNORE_IP"]
        
        if is_local_ip(ip, IGNORE_IP):
            return
            
        timestamp = make_aware(datetime.now())
        register_failed_attempt(
            ip, timestamp,
            TEMP_BLOCK_DURATION, TEMP_BLOCK_THRESHOLD,
            PERM_BLOCK_THRESHOLD, PERM_WINDOW, TEMP_WINDOW, "olspanel"
        )
    except Exception as e:
        logger.error(f"Error registering panel failed login for {ip}: {e}")


def find_keyword_in_line(line, keywords):
    
    for keyword in keywords:
        # We use a regular expression to match the keyword.
        # The r prefix makes it a raw string.
        # \b is a word boundary, which ensures we match the whole word.
        # re.IGNORECASE makes the search case-insensitive.
        pattern = r'\b' + re.escape(keyword.strip()) + r'\b'
        
        # We're allowing for surrounding whitespace by stripping the keyword.
        if re.search(pattern, line.strip(), re.IGNORECASE):
            return True, keyword.strip()
            
    return False, None

def register_failed_attempt(ip, timestamp,TEMP_BLOCK_DURATION,TEMP_BLOCK_THRESHOLD,PERM_BLOCK_THRESHOLD,PERM_WINDOW,TEMP_WINDOW,TYPE):
    now = timestamp
    
    block_entry, created = BlockedIP.objects.get_or_create(ip_address=ip)

    # If no previous attempts, initialize
    if block_entry.first_attempt_time is None:
        block_entry.first_attempt_time = timestamp
        block_entry.attempts = 1
    else:
        elapsed = timestamp - block_entry.first_attempt_time
        if elapsed > TEMP_WINDOW:
            # Outside time window: reset count and window start time
            block_entry.attempts = 1
            block_entry.first_attempt_time = timestamp
        else:
            # Within time window: increment attempts
            block_entry.attempts += 1
    block_entry.type = TYPE
    block_entry.last_detected = timestamp
    block_entry.save()

    # TEMP BLOCK LOGIC
    if block_entry.attempts >= TEMP_BLOCK_THRESHOLD and block_entry.block_type != "TEMP":
        block_entry.block_type = "TEMP"
        block_entry.temp_block_expires = now + TEMP_BLOCK_DURATION
        block_entry.temp_block_count += 1  # Increment temp block count here
        block_entry.save()
        temp_block_ip(ip,TEMP_BLOCK_DURATION)

    # PERM BLOCK LOGIC
    # Count temp blocks in last 24 hours
    # You want to count entries with temp_block_count incremented recently
    # So filter by last_detected and temp_block_count > 0 maybe?
    temp_blocks_in_24h = BlockedIP.objects.filter(
        ip_address=ip,
        block_type="TEMP",
        last_detected__gte=now - PERM_WINDOW
    ).aggregate(total_temp_blocks=models.Sum('temp_block_count'))['total_temp_blocks'] or 0

    if temp_blocks_in_24h >= PERM_BLOCK_THRESHOLD and block_entry.block_type != "PERM":
        block_entry.block_type = "PERM"
        block_entry.temp_block_expires = None
        block_entry.save()
        perm_block_ip(ip)
        
    



def cleanup_expired_temp_blocks(TEMP_WINDOW,TYPE):
    now = timezone.now()
    print(f"now {now} last {TEMP_WINDOW}.")
    inactive_blocks = BlockedIP.objects.filter(
        last_detected__lte=now - TEMP_WINDOW,
        block_type__in=["","NONE", None]
    )
    
    if inactive_blocks.exists():
        for block in inactive_blocks:
            second_filter_ip(block.ip_address,block.attempts,block.temp_block_count)
        
    count = inactive_blocks.count()
    inactive_blocks.delete()

    
    if count:
        print(f"[CLEANUP] Removed {count} inactive IP(s) with no attempts in last {TEMP_WINDOW}.")
    
    expired_blocks = BlockedIP.objects.filter(
        block_type="TEMP",
        type=TYPE,
        temp_block_expires__lte=now
    )
    for block in expired_blocks:
        remove_firewall_rule(block.ip_address)
        block.block_type = ""
        block.attempts = 0
        block.temp_block_expires = None
        block.save()
        print(f"[TEMP BLOCK EXPIRED] {block.ip_address} temp block expired and reset.")
 

def second_filter_ip(ip, attempts,temp_block_count):
    timestamp = now()

    block_entry, created = FilterBlockedIP.objects.get_or_create(ip_address=ip)

    if created or block_entry.first_attempt_time is None:
        # New IP or first time recorded
        block_entry.first_attempt_time = timestamp
        block_entry.attempts = attempts
        block_entry.temp_block_count = temp_block_count
    else:
        # Existing IP: increment attempts
        block_entry.attempts += attempts
        block_entry.temp_block_count += temp_block_count

    block_entry.last_detected = timestamp
    block_entry.save()


def register_second_failed_attempt(ip, attempts=1,temp_block_count=0):
    TEMP_BLOCK_DURATION_MINUTES = 1440  # 24 hours block duration
    temp_block_duration = timedelta(minutes=TEMP_BLOCK_DURATION_MINUTES)
    timestamp = now()

    block_entry, created = BlockedIP.objects.get_or_create(ip_address=ip)

    if block_entry.temp_block_count is None:
        block_entry.temp_block_count = 0

    if created:
        # New IP entry — initialize attempts and counts
        block_entry.first_attempt_time = timestamp
        block_entry.attempts = attempts
        block_entry.temp_block_count = temp_block_count
    else:
        # Existing IP — increment attempts and counts by incoming 'attempts'
        block_entry.attempts += attempts
        block_entry.temp_block_count += temp_block_count

    block_entry.block_type = "TEMP"
    block_entry.type = "ssh"  # change dynamically if needed
    block_entry.last_detected = timestamp
    block_entry.temp_block_expires = timestamp + temp_block_duration

    block_entry.save()

    temp_block_ip(ip, temp_block_duration)
    
def second_filter_attempt_ips(window_hours=24, threshold=30):
    cutoff_time = timezone.now() - timedelta(hours=window_hours)
    cutoff_time = make_aware(cutoff_time)  # just to be sure

    old_ips = FilterBlockedIP.objects.filter(first_attempt_time__lte=cutoff_time)

    for ip_entry in old_ips:
        if ip_entry.attempts >= threshold:
            print(f"[ACTION] Registering temp block for IP {ip_entry.ip_address} with {ip_entry.attempts} attempts.")
            register_second_failed_attempt(ip_entry.ip_address, ip_entry.attempts,ip_entry.temp_block_count)
        else:
            print(f"[INFO] Removing IP {ip_entry.ip_address} with {ip_entry.attempts} attempts below threshold {threshold}.")
        ip_entry.delete()
        


def get_existing_log_files(log_files_str):
    paths = [path.strip() for path in log_files_str.split(",") if path.strip()]
    existing_files = [path for path in paths if os.path.exists(path)]
    return existing_files  # list of existing paths (can be empty)

def get_type_from_filename(filepath):
        # Extract base filename without extension
        basename = os.path.basename(filepath)
        name, _ = os.path.splitext(basename)
        return name.lower()

def run_monitor():
    global firewall_changed
    firewall_changed = False
    priority = {
        "ssh": 1,
        "ftp": 2,
        "mail": 3,
        "olspanel": 4,
    }
    config_folder = "/usr/local/ufw/config/"
    conf_files = glob.glob(os.path.join(config_folder, "*.conf"))
    conf_files.sort(key=lambda f: priority.get(get_type_from_filename(f), 999))
    for conf_file in conf_files:
        print(f"Running monitor for config: {conf_file}")
        try:
            TYPE = os.path.splitext(os.path.basename(conf_file))[0]
            print(f"config type: {TYPE}")
            conf_data = load_config(conf_file)
            
            STATUS = conf_data.get("STATUS", 0)
            if STATUS == 1:
                
                
                log_file_setting = conf_data["LOG_FILE"]
                existing_log_files = get_existing_log_files(log_file_setting)

                if not existing_log_files:
                    print(f"[!] No valid log files found for config {conf_file}, skipping.")
                    continue

                OFFSET_FILE = conf_data["DATA_FILE"]
                TEMP_BLOCK_DURATION = conf_data["TEMP_BLOCK_DURATION"]
                TEMP_BLOCK_THRESHOLD = conf_data["TEMP_BLOCK_THRESHOLD"]
                TEMP_WINDOW = conf_data["TEMP_WINDOW"]
                PERM_BLOCK_THRESHOLD = conf_data["PERM_BLOCK_THRESHOLD"]
                PERM_WINDOW = conf_data["PERM_WINDOW"]
                keywords = conf_data["KEYWORD"]
                IGNORE_IP = conf_data["IGNORE_IP"]

                # You can either call the monitor function for each log file:
                for LOG_FILE in existing_log_files:
                    OFFSET_FILE = get_offset_file_for_log(conf_data["DATA_FILE"], LOG_FILE)
                    cleanup_expired_temp_blocks(TEMP_WINDOW,TYPE)
                    monitor_failed_ssh_logins(
                        LOG_FILE, OFFSET_FILE, keywords,
                        TEMP_BLOCK_DURATION, TEMP_BLOCK_THRESHOLD,
                        PERM_BLOCK_THRESHOLD, PERM_WINDOW, TEMP_WINDOW, IGNORE_IP,TYPE
                    )
            else:
                
                
                log_file_setting = conf_data["LOG_FILE"]
                existing_log_files = get_existing_log_files(log_file_setting)
                #print(f"skiping off log ")
                if existing_log_files:
                    print(f"skiping off log")
                    for LOG_FILE in existing_log_files:
                        OFFSET_FILE = get_offset_file_for_log(conf_data["DATA_FILE"], LOG_FILE)
                        try:
                            with open(LOG_FILE, 'rb') as f:
                                f.seek(0, 2)  # Seek to end of file
                                offset = f.tell()
                            save_offset(OFFSET_FILE, offset)
                            print(f"[+] Saved offset {offset} for {OFFSET_FILE} because STATUS != 1")
                        except Exception as e:
                            print(f"[!] Error reading log file '{LOG_FILE}': {e}")
                else:
                    print(f"[!] No valid log files found for config {conf_file}, skipping saving offset.")
                
        except Exception as e:
            #print(f"[!] Skipping invalid or unreadable config '{conf_file}': {e}")
            continue
            
    second_filter_attempt_ips() 
    if firewall_changed:
        print("[*] Reloading UFW rules...")
        try:
            subprocess.run(["ufw", "reload"], check=True)
        except Exception as e:
            logger.error(f"Error reloading ufw: {e}")

