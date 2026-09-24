import os
import re
import json
import time
import socket
import secrets
import base64
import hashlib
import subprocess
from datetime import datetime
from django.conf import settings
from django.db import connection
from users.models import DbClusterNode, DbReplicationLog, DbSyncRule
from users.panellogger import CpLogger

logger = CpLogger()

def run_cmd(cmd, timeout=60):
    """Executes a shell command safely and returns (success: bool, output: str)."""
    try:
        res = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        if res.returncode == 0:
            return True, res.stdout.strip()
        return False, (res.stderr or res.stdout).strip()
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


_ENGINE_CACHE = None

def detect_db_engine():
    """Detects whether MariaDB or MySQL is active, and returns engine type + version."""
    global _ENGINE_CACHE
    if _ENGINE_CACHE:
        return _ENGINE_CACHE

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT @@version, @@version_comment;")
            row = cursor.fetchone()
            if row:
                ver_str = f"{row[0]} {row[1] or ''}".strip()
                if "mariadb" in ver_str.lower():
                    _ENGINE_CACHE = ("mariadb", ver_str)
                    return _ENGINE_CACHE
                elif "mysql" in ver_str.lower():
                    _ENGINE_CACHE = ("mysql", ver_str)
                    return _ENGINE_CACHE
                _ENGINE_CACHE = ("mariadb", ver_str)
                return _ENGINE_CACHE
    except Exception:
        pass

    success, out = run_cmd("mariadb --version || mysql --version")
    out_lower = out.lower()
    if "mariadb" in out_lower:
        _ENGINE_CACHE = ("mariadb", out)
    elif "mysql" in out_lower:
        _ENGINE_CACHE = ("mysql", out)
    else:
        _ENGINE_CACHE = ("mariadb", out)
    return _ENGINE_CACHE


def get_mysql_config_dir():
    """Finds the appropriate conf.d directory for replication settings."""
    dirs = [
        "/etc/mysql/mariadb.conf.d",
        "/etc/mysql/conf.d",
        "/etc/mysql/mysql.conf.d",
        "/etc/mysql"
    ]
    for d in dirs:
        if os.path.isdir(d):
            return d
    return "/etc/mysql/mariadb.conf.d"


def get_local_mysql_auth_flags():
    """Finds local MySQL root authentication flags for CLI commands."""
    for p_file in ["/usr/local/olspanel/etc/mysqlPassword", "/usr/local/cyberpanel/etc/mysqlPassword"]:
        if os.path.isfile(p_file):
            try:
                with open(p_file, "r") as f:
                    p = f.read().strip()
                if p:
                    return f"-u root -p'{p}'"
            except Exception:
                pass
    if os.path.isfile("/root/.my.cnf"):
        return "--defaults-extra-file=/root/.my.cnf"
    if os.path.isfile("/etc/mysql/debian.cnf"):
        return "--defaults-file=/etc/mysql/debian.cnf"
    return "-u root"


def generate_server_id():
    """Generates a random, valid MySQL 32-bit server-id (100000 to 999999)."""
    return secrets.randbelow(899999) + 100000


def get_current_server_id():
    """Fetches the active MySQL server-id."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT @@server_id;")
            row = cursor.fetchone()
            if row:
                return int(row[0])
    except Exception as e:
        logger.error(f"Error fetching server_id: {e}")
    return 1


def test_tcp_connectivity(host, port=3306, timeout=3):
    """Tests TCP network reachability to remote host and port."""
    try:
        clean_host = re.sub(r'[^a-zA-Z0-9.:_-]', '', str(host).strip())
        s = socket.create_connection((clean_host, int(port)), timeout=timeout)
        s.close()
        return True, f"Port {port} on {clean_host} is REACHABLE."
    except Exception as e:
        return False, f"Cannot connect to {host}:{port} ({str(e)})"


def sync_timezone_from_primary(master_host, master_port, repl_user, repl_password):
    """Synchronizes local server timezone with the Primary server to avoid binlog timestamp drift."""
    try:
        clean_host = re.sub(r'[^a-zA-Z0-9.:_-]', '', str(master_host).strip())
        safe_pass = str(repl_password).replace("'", "'\\''")
        cmd = f"mariadb --skip-ssl --connect-timeout=5 -h {clean_host} -P {master_port} -u {repl_user} -p'{safe_pass}' -s -N -e 'SELECT @@system_time_zone;'"
        success, p_tz = run_cmd(cmd)
        if not success or not p_tz:
            return False, "Could not fetch timezone from Primary."

        p_tz = p_tz.strip().upper()
        tz_map = {
            "EAT": "Africa/Nairobi",
            "UTC": "UTC",
            "EST": "America/New_York",
            "EDT": "America/New_York",
            "CST": "America/Chicago",
            "CDT": "America/Chicago",
            "PST": "America/Los_Angeles",
            "PDT": "America/Los_Angeles",
            "GMT": "Europe/London",
            "BST": "Europe/London",
            "CET": "Europe/Berlin",
            "CEST": "Europe/Berlin",
            "IST": "Asia/Kolkata",
        }
        target_tz = tz_map.get(p_tz, "")
        if target_tz:
            run_cmd(f"timedatectl set-timezone {target_tz}")
            return True, f"Synchronized timezone to {target_tz} ({p_tz})"
        return True, f"Primary timezone is {p_tz}"
    except Exception as e:
        logger.error(f"Error syncing timezone: {e}")
        return False, str(e)


def ensure_replication_config(server_id=None, is_primary=True, selected_databases=None, rewrite_rules=None, ignore_tables=None, replicate_all=False, read_only=None, restart_service=False):
    """
    Creates/updates the OLSPanel MySQL replication configuration file.
    Configures binlog, server_id, slave_skip_errors, rewrite_rules, ignore_tables, and read_only.
    """
    conf_dir = get_mysql_config_dir()
    os.makedirs(conf_dir, exist_ok=True)
    conf_path = os.path.join(conf_dir, "99-olspanel-replication.cnf")

    if not server_id:
        curr_id = get_current_server_id()
        server_id = curr_id if curr_id > 1 else generate_server_id()

    engine, _ = detect_db_engine()

    # Determine read_only mode
    if read_only is None:
        ro_val = 0 if is_primary else 1
    else:
        ro_val = 1 if read_only else 0

    config_lines = [
        "# OLSPanel Enterprise Database Replication Configuration",
        "[mysqld]",
        f"server_id               = {server_id}",
        f"read_only               = {ro_val}",
        "log_bin                 = /var/log/mysql/mariadb-bin.log",
        "log_bin_index           = /var/log/mysql/mariadb-bin.index",
        "binlog_format           = ROW",
        "expire_logs_days        = 7",
        "max_binlog_size         = 100M",
        "log_slave_updates       = 1",
        "slave_skip_errors       = 1062,1146,1032",
        "bind_address            = 0.0.0.0",
    ]

    if engine == "mariadb":
        config_lines.append("gtid_strict_mode        = 1")
    else:
        config_lines.extend([
            "gtid_mode               = ON",
            "enforce_gtid_consistency = ON",
        ])

    # Rewrite rules (replicate_rewrite_db = src->tgt)
    if rewrite_rules:
        if isinstance(rewrite_rules, str):
            try:
                rewrite_rules = json.loads(rewrite_rules)
            except Exception:
                rewrite_rules = {}
        for src, tgt in rewrite_rules.items():
            src_clean = re.sub(r'[^a-zA-Z0-9_$-]', '', str(src).strip())
            tgt_clean = re.sub(r'[^a-zA-Z0-9_$-]', '', str(tgt).strip())
            if src_clean and tgt_clean and src_clean != tgt_clean:
                config_lines.append(f"replicate_rewrite_db    = {src_clean}->{tgt_clean}")
                if not selected_databases:
                    selected_databases = []
                if tgt_clean not in selected_databases:
                    selected_databases.append(tgt_clean)

    # Selective database replication filters
    if not is_primary and not replicate_all and selected_databases:
        config_lines.append("# --- Database-Level Selective Filters ---")
        for db in selected_databases:
            clean_db = re.sub(r'[^a-zA-Z0-9_$-]', '', str(db).strip())
            if clean_db and clean_db not in ['information_schema', 'performance_schema', 'mysql', 'sys']:
                config_lines.append(f"replicate_wild_do_table = {clean_db}.%")

    # Wildcard ignore tables
    if ignore_tables:
        if isinstance(ignore_tables, str):
            try:
                ignore_tables = json.loads(ignore_tables)
            except Exception:
                ignore_tables = []
        for tbl in ignore_tables:
            tbl_clean = re.sub(r'[^a-zA-Z0-9_$.%-]', '', str(tbl).strip())
            if tbl_clean:
                config_lines.append(f"replicate_wild_ignore_table = {tbl_clean}")

    config_content = "\n".join(config_lines) + "\n"

    try:
        with open(conf_path, "w") as f:
            f.write(config_content)

        os.makedirs("/var/log/mysql", exist_ok=True)
        run_cmd("chown -R mysql:mysql /var/log/mysql 2>/dev/null || true")

        if restart_service:
            run_cmd("systemctl reload mariadb || systemctl reload mysql || systemctl restart mariadb || systemctl restart mysql")
            try:
                connection.close()
            except Exception:
                pass

        return True, f"Replication config saved to {conf_path} with server_id {server_id}"
    except Exception as e:
        logger.error(f"Failed to write replication config: {e}")
        return False, str(e)


def toggle_read_only(enabled: bool):
    """Enables or disables database read_only mode."""
    try:
        val_str = "ON" if enabled else "OFF"
        with connection.cursor() as cursor:
            cursor.execute(f"SET GLOBAL read_only = {val_str};")
            try:
                cursor.execute(f"SET GLOBAL super_read_only = {val_str};")
            except Exception:
                pass
        
        # Persist in conf file
        conf_dir = get_mysql_config_dir()
        conf_path = os.path.join(conf_dir, "99-olspanel-replication.cnf")
        if os.path.isfile(conf_path):
            ro_int = 1 if enabled else 0
            with open(conf_path, "r") as f:
                content = f.read()
            if "read_only" in content:
                content = re.sub(r'read_only\s*=\s*[01]', f'read_only = {ro_int}', content)
            else:
                content = content.replace("[mysqld]\n", f"[mysqld]\nread_only = {ro_int}\n")
            with open(conf_path, "w") as f:
                f.write(content)

        return True, f"Read-Only mode turned {val_str}."
    except Exception as e:
        logger.error(f"Error toggling read_only: {e}")
        return False, str(e)


# ------------------------------------------------------------------------------
# Multi-Source Replication Channel Parser & Controllers
# ------------------------------------------------------------------------------
def parse_all_replica_channels():
    """
    Parses all active multi-source replication channels from MySQL / MariaDB.
    Uses ultra-fast direct DB cursor first (0.1ms), with fallback to CLI.
    """
    channels = []
    
    # 1. Fast Direct SQL parsing
    try:
        with connection.cursor() as cursor:
            # MariaDB Multi-Source
            try:
                cursor.execute("SHOW ALL SLAVES STATUS;")
                if cursor.description:
                    columns = [col[0].lower() for col in cursor.description]
                    rows = cursor.fetchall()
                    for row in rows:
                        raw_dict = dict(zip(columns, row))
                        channels.append(_normalize_channel_dict(raw_dict))
                    if channels:
                        return channels
            except Exception:
                pass

            # Single source fallback (MySQL / MariaDB single channel)
            try:
                cursor.execute("SHOW SLAVE STATUS;")
                if cursor.description:
                    columns = [col[0].lower() for col in cursor.description]
                    rows = cursor.fetchall()
                    for row in rows:
                        raw_dict = dict(zip(columns, row))
                        channels.append(_normalize_channel_dict(raw_dict))
                    if channels:
                        return channels
            except Exception:
                pass
    except Exception as e:
        logger.error(f"SQL Replica channel parse error: {e}")

    # 2. CLI Fallback only if direct SQL had permission/driver issue
    auth_flags = get_local_mysql_auth_flags()
    success, raw_out = run_cmd(f"mariadb {auth_flags} -e 'SHOW ALL SLAVES STATUS\\G' 2>/dev/null || mysql {auth_flags} -e 'SHOW ALL SLAVES STATUS\\G' 2>/dev/null")
    if not success or not raw_out or "Slave_IO_Running" not in raw_out:
        success, raw_out = run_cmd(f"mariadb {auth_flags} -e 'SHOW SLAVE STATUS\\G' 2>/dev/null || mysql {auth_flags} -e 'SHOW SLAVE STATUS\\G' 2>/dev/null")

    if not success or not raw_out or "Slave_IO_Running" not in raw_out:
        return channels

    cur_channel = {}
    lines = raw_out.splitlines()

    for line in lines:
        line_clean = line.strip()
        if re.match(r'^\*{10,}\s*[0-9]+\.\s*row\s*\*{10,}$', line_clean):
            if cur_channel and (cur_channel.get('name') or cur_channel.get('master_host')):
                channels.append(_normalize_channel_dict(cur_channel))
            cur_channel = {}
            continue

        if ":" in line:
            parts = line.split(":", 1)
            key = parts[0].strip().lower()
            val = parts[1].strip()
            cur_channel[key] = val

    if cur_channel and (cur_channel.get('name') or cur_channel.get('master_host') or cur_channel.get('connection_name')):
        channels.append(_normalize_channel_dict(cur_channel))

    return channels


def _normalize_channel_dict(raw):
    """Normalizes channel status keys across MariaDB and MySQL versions."""
    name = raw.get('connection_name', raw.get('channel_name', raw.get('name', 'default')))
    if not name:
        name = "default"

    io_running = raw.get('slave_io_running', raw.get('replica_io_running', 'No'))
    sql_running = raw.get('slave_sql_running', raw.get('replica_sql_running', 'No'))
    raw_lag = raw.get('seconds_behind_master', raw.get('seconds_behind_source', None))
    lag = int(raw_lag) if (raw_lag is not None and str(raw_lag).isdigit()) else 0

    last_io_err = raw.get('last_io_error', raw.get('last_io_errno_message', ''))
    last_sql_err = raw.get('last_sql_error', raw.get('last_sql_errno_message', ''))

    if str(io_running).lower() == 'yes' and str(sql_running).lower() == 'yes':
        health = "streaming"
    elif str(io_running).lower() == 'connecting':
        health = "connecting"
    elif last_io_err or last_sql_err:
        health = "error"
    elif str(io_running).lower() == 'no' and str(sql_running).lower() == 'no':
        health = "paused"
    else:
        health = "warning"

    return {
        "name": name,
        "master_host": raw.get('master_host', raw.get('source_host', '')),
        "master_port": int(raw.get('master_port', raw.get('source_port', 3306)) or 3306),
        "master_user": raw.get('master_user', raw.get('source_user', '')),
        "slave_io_running": io_running,
        "slave_sql_running": sql_running,
        "seconds_behind_master": lag,
        "master_log_file": raw.get('master_log_file', ''),
        "read_master_log_pos": raw.get('read_master_log_pos', 0),
        "exec_master_log_pos": raw.get('exec_master_log_pos', 0),
        "relay_log_file": raw.get('relay_log_file', ''),
        "relay_log_pos": raw.get('relay_log_pos', 0),
        "replicate_do_db": raw.get('replicate_do_db', ''),
        "replicate_wild_do_table": raw.get('replicate_wild_do_table', ''),
        "last_io_error": last_io_err,
        "last_sql_error": last_sql_err,
        "slave_io_state": raw.get('slave_io_state', ''),
        "slave_sql_state": raw.get('slave_sql_running_state', ''),
        "health": health
    }


def start_replica_channel(channel_name='default', master_host='', master_port=3306, repl_user='', repl_password='', master_log_file='', master_log_pos='', use_gtid=True):
    """Configures and starts an individual replication stream channel."""
    safe_host = re.sub(r'[^a-zA-Z0-9.:_-]', '', str(master_host).strip())
    safe_user = re.sub(r'[^a-zA-Z0-9_]', '', str(repl_user).strip())
    safe_port = int(master_port)
    ch_clause = f"'{channel_name}'" if (channel_name and channel_name != 'default') else ""

    engine, _ = detect_db_engine()

    try:
        with connection.cursor() as cursor:
            # 1. Stop channel
            try:
                cursor.execute(f"STOP SLAVE {ch_clause};")
            except Exception:
                pass

            # 2. Configure CHANGE MASTER
            pos_clause = ""
            if master_log_file and str(master_log_pos).isdigit():
                pos_clause = f", MASTER_LOG_FILE = '{master_log_file}', MASTER_LOG_POS = {master_log_pos}"
            elif engine == "mariadb" and use_gtid:
                pos_clause = ", MASTER_USE_GTID = current_pos"

            sql = f"""
            CHANGE MASTER {ch_clause} TO
                MASTER_HOST = %s,
                MASTER_PORT = %s,
                MASTER_USER = %s,
                MASTER_PASSWORD = %s,
                MASTER_CONNECT_RETRY = 10,
                MASTER_SSL = 0
                {pos_clause};
            """
            cursor.execute(sql, [safe_host, safe_port, safe_user, repl_password])

            # 3. Start channel
            cursor.execute(f"START SLAVE {ch_clause};")

        return True, f"Replication channel '{channel_name}' configured and started."
    except Exception as e:
        logger.error(f"Failed to start channel '{channel_name}': {e}")
        return False, str(e)


def stop_replica_channel(channel_name='default'):
    """Stops a replication channel."""
    ch_clause = f"'{channel_name}'" if (channel_name and channel_name != 'default') else ""
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"STOP SLAVE {ch_clause};")
        return True, f"Replication channel '{channel_name}' stopped."
    except Exception as e:
        logger.error(f"Error stopping channel '{channel_name}': {e}")
        return False, str(e)


def restart_replica_channel(channel_name='default'):
    """Restarts a replication channel."""
    stop_replica_channel(channel_name)
    time.sleep(0.5)
    ch_clause = f"'{channel_name}'" if (channel_name and channel_name != 'default') else ""
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"START SLAVE {ch_clause};")
        return True, f"Replication channel '{channel_name}' restarted."
    except Exception as e:
        logger.error(f"Error restarting channel '{channel_name}': {e}")
        return False, str(e)


def reset_replica_channel(channel_name='default'):
    """Permanently deletes and clears a replication channel."""
    ch_clause = f"'{channel_name}'" if (channel_name and channel_name != 'default') else ""
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"STOP SLAVE {ch_clause};")
            cursor.execute(f"RESET SLAVE {ch_clause} ALL;")
        return True, f"Replication channel '{channel_name}' reset and removed."
    except Exception as e:
        logger.error(f"Error resetting channel '{channel_name}': {e}")
        return False, str(e)


def start_all_replica_channels():
    """Starts all replication channels."""
    try:
        with connection.cursor() as cursor:
            try:
                cursor.execute("START ALL SLAVES;")
            except Exception:
                cursor.execute("START SLAVE;")
        return True, "All replication streams started."
    except Exception as e:
        return False, str(e)


def stop_all_replica_channels():
    """Stops all replication channels."""
    try:
        with connection.cursor() as cursor:
            try:
                cursor.execute("STOP ALL SLAVES;")
            except Exception:
                cursor.execute("STOP SLAVE;")
        return True, "All replication streams stopped."
    except Exception as e:
        return False, str(e)


def skip_replica_error(channel_name=None):
    """
    Bypasses a stuck SQL error (e.g. duplicate key 1062) by incrementing
    sql_slave_skip_counter and resuming the stream.
    """
    try:
        if channel_name and channel_name != 'default':
            stop_replica_channel(channel_name)
        else:
            stop_all_replica_channels()

        with connection.cursor() as cursor:
            cursor.execute("SET GLOBAL sql_slave_skip_counter = 1;")

        if channel_name and channel_name != 'default':
            restart_replica_channel(channel_name)
        else:
            start_all_replica_channels()

        return True, "Skipped 1 SQL error statement and resumed replication stream."
    except Exception as e:
        logger.error(f"Error skipping replica statement: {e}")
        return False, str(e)


# ------------------------------------------------------------------------------
# Baseline Online Snapshot Cloner & Network Dump Streamer
# ------------------------------------------------------------------------------
def clone_databases_from_primary(master_host, master_port, repl_user, repl_password, db_pairs, channel_name='default'):
    """
    Online live baseline cloner:
    Streams a complete dump of specified databases directly over the network from
    Primary to Replica, creates destination tables, and records coordinates for clean replication.
    """
    clean_host = re.sub(r'[^a-zA-Z0-9.:_-]', '', str(master_host).strip())
    safe_pass = str(repl_password).replace("'", "'\\''")
    auth_flags = get_local_mysql_auth_flags()

    # Pre-create all target databases locally
    for pair in db_pairs:
        tgt = pair[1] if isinstance(pair, (list, tuple)) else str(pair).split('->')[-1].split(':')[-1].strip()
        clean_tgt = re.sub(r'[^a-zA-Z0-9_$-]', '', tgt)
        if clean_tgt:
            run_cmd(f"mariadb {auth_flags} -e 'CREATE DATABASE IF NOT EXISTS `{clean_tgt}`;' 2>/dev/null || true")

    has_rewrite = any(isinstance(p, (list, tuple)) and p[0] != p[1] for p in db_pairs)

    # If simple 1:1 sync with no rename, do unified single-transaction stream
    if not has_rewrite:
        target_dbs = [p[0] if isinstance(p, (list, tuple)) else str(p) for p in db_pairs]
        clean_dbs = " ".join([f"`{re.sub(r'[^a-zA-Z0-9_$-]', '', d)}`" for d in target_dbs if d])

        dump_cmd = (
            f"mariadb-dump --skip-ssl -h {clean_host} -P {master_port} -u {repl_user} -p'{safe_pass}' "
            f"--master-data=1 --single-transaction --databases {clean_dbs} 2>/tmp/ols_clone_err.log | "
            f"mariadb {auth_flags} 2>>/tmp/ols_clone_err.log"
        )
        success, out = run_cmd(dump_cmd, timeout=300)
        if not success:
            err_msg = ""
            if os.path.isfile("/tmp/ols_clone_err.log"):
                with open("/tmp/ols_clone_err.log", "r") as f:
                    err_msg = f.read().strip()
            return False, f"Clone failed: {err_msg or out}"
        return True, "All database snapshots streamed and imported cleanly."
    else:
        # Re-stream each database to its rewritten target name
        for pair in db_pairs:
            src = pair[0]
            tgt = pair[1]
            clean_src = re.sub(r'[^a-zA-Z0-9_$-]', '', src)
            clean_tgt = re.sub(r'[^a-zA-Z0-9_$-]', '', tgt)

            dump_cmd = (
                f"mariadb-dump --skip-ssl -h {clean_host} -P {master_port} -u {repl_user} -p'{safe_pass}' "
                f"--single-transaction `{clean_src}` 2>/tmp/ols_clone_err.log | "
                f"mariadb {auth_flags} `{clean_tgt}` 2>>/tmp/ols_clone_err.log"
            )
            success, out = run_cmd(dump_cmd, timeout=300)
            if not success:
                err_msg = ""
                if os.path.isfile("/tmp/ols_clone_err.log"):
                    with open("/tmp/ols_clone_err.log", "r") as f:
                        err_msg = f.read().strip()
                return False, f"Clone failed for `{clean_src}` -> `{clean_tgt}`: {err_msg or out}"
        return True, "All rewritten databases cloned successfully."


def get_primary_coordinates(master_host, master_port, repl_user, repl_password):
    """Queries SHOW MASTER STATUS from primary to retrieve current binlog file & position."""
    try:
        clean_host = re.sub(r'[^a-zA-Z0-9.:_-]', '', str(master_host).strip())
        safe_pass = str(repl_password).replace("'", "'\\''")
        cmd = f"mariadb --skip-ssl --connect-timeout=5 -h {clean_host} -P {master_port} -u {repl_user} -p'{safe_pass}' -s -N -e 'SHOW MASTER STATUS;'"
        success, out = run_cmd(cmd)
        if success and out:
            parts = out.split()
            if len(parts) >= 2:
                return parts[0], parts[1]
    except Exception as e:
        logger.error(f"Error reading primary coordinates: {e}")
    return "", ""


# ------------------------------------------------------------------------------
# Connected Replicas Explorer (Primary Side Visibility)
# ------------------------------------------------------------------------------
def get_connected_replicas_telemetry():
    """
    On Primary server, inspects all connected streaming replicas from
    SHOW SLAVE HOSTS and information_schema.PROCESSLIST.
    """
    replicas = []
    try:
        with connection.cursor() as cursor:
            # 1. Query SHOW SLAVE HOSTS
            slave_hosts = {}
            try:
                cursor.execute("SHOW SLAVE HOSTS;")
                for row in cursor.fetchall():
                    s_id = row[0]
                    s_host = row[1]
                    s_port = row[2] if len(row) > 2 else 3306
                    slave_hosts[s_host] = {"server_id": s_id, "host": s_host, "port": s_port}
            except Exception:
                pass

            # 2. Query Binlog Dump threads in PROCESSLIST
            cursor.execute("""
                SELECT ID, USER, HOST, TIME, STATE
                FROM information_schema.PROCESSLIST
                WHERE COMMAND LIKE '%Binlog Dump%' OR USER='olspanel_repl' OR USER LIKE '%repl%';
            """)
            proc_rows = cursor.fetchall()
            for r in proc_rows:
                p_id = r[0]
                p_user = r[1]
                p_host_raw = r[2]
                p_time = r[3] or 0
                p_state = r[4] or "Streaming"

                host_only = p_host_raw.split(":")[0] if ":" in p_host_raw else p_host_raw
                s_info = slave_hosts.get(host_only, {})

                replicas.append({
                    "thread_id": p_id,
                    "user": p_user,
                    "host": host_only,
                    "raw_host": p_host_raw,
                    "server_id": s_info.get('server_id', 'Standby'),
                    "port": s_info.get('port', 3306),
                    "uptime_seconds": p_time,
                    "state": p_state,
                    "status": "active"
                })

            # If slave hosts found but no active processlist entry, add as standby
            for h, s_info in slave_hosts.items():
                if not any(r['host'] == h for r in replicas):
                    replicas.append({
                        "thread_id": "N/A",
                        "user": "olspanel_repl",
                        "host": h,
                        "raw_host": h,
                        "server_id": s_info.get('server_id', 'Standby'),
                        "port": s_info.get('port', 3306),
                        "uptime_seconds": 0,
                        "state": "Authorized Standby",
                        "status": "standby"
                    })

    except Exception as e:
        logger.error(f"Error fetching connected replicas telemetry: {e}")

    return replicas


def kill_replica_process_thread(thread_id):
    """Terminates a specific replica streaming thread on Primary."""
    try:
        t_id = int(thread_id)
        with connection.cursor() as cursor:
            cursor.execute(f"KILL {t_id};")
        return True, f"Process Thread #{t_id} terminated."
    except Exception as e:
        logger.error(f"Error killing thread {thread_id}: {e}")
        return False, str(e)


# ------------------------------------------------------------------------------
# Live Parity Test & Heartbeat Verification Feed
# ------------------------------------------------------------------------------
def send_live_parity_test(target_db=''):
    """
    Writes a timestamped verification record into live_replication_feed on Primary.
    """
    try:
        if not target_db:
            # Pick first available user database
            with connection.cursor() as cursor:
                cursor.execute("SHOW DATABASES;")
                dbs = [r[0] for r in cursor.fetchall() if r[0] not in ['information_schema', 'performance_schema', 'mysql', 'sys']]
                target_db = dbs[0] if dbs else 'app_db'

        clean_db = re.sub(r'[^a-zA-Z0-9_$-]', '', str(target_db).strip())
        now_ts = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        test_title = f"Live Parity Test from Primary [{now_ts}]"

        with connection.cursor() as cursor:
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS `{clean_db}`.live_replication_feed (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    test_title VARCHAR(255) NOT NULL,
                    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute(f"INSERT INTO `{clean_db}`.live_replication_feed (test_title) VALUES (%s);", [test_title])

        return True, f"Test record written to `{clean_db}`: '{test_title}'"
    except Exception as e:
        logger.error(f"Error sending live parity test: {e}")
        return False, str(e)


def verify_live_parity_feed(target_db=''):
    """
    Reads the latest 5 records from live_replication_feed on the replica to confirm active data flow.
    Uses ultra-fast single lookup in information_schema to find the table instantly.
    """
    feed = []
    try:
        with connection.cursor() as cursor:
            if target_db:
                clean_db = re.sub(r'[^a-zA-Z0-9_$-]', '', str(target_db).strip())
                try:
                    cursor.execute(f"SELECT id, test_title, synced_at FROM `{clean_db}`.live_replication_feed ORDER BY id DESC LIMIT 5;")
                    rows = cursor.fetchall()
                    for r in rows:
                        feed.append({
                            "database": clean_db,
                            "id": r[0],
                            "title": r[1],
                            "synced_at": r[2].strftime('%Y-%m-%d %H:%M:%S') if r[2] else 'Just now'
                        })
                except Exception:
                    pass
            else:
                # 1 ultra-fast check in information_schema
                cursor.execute("""
                    SELECT table_schema 
                    FROM information_schema.tables 
                    WHERE table_name = 'live_replication_feed' 
                      AND table_schema NOT IN ('information_schema', 'performance_schema', 'mysql', 'sys')
                    LIMIT 1;
                """)
                row = cursor.fetchone()
                if row:
                    clean_db = row[0]
                    cursor.execute(f"SELECT id, test_title, synced_at FROM `{clean_db}`.live_replication_feed ORDER BY id DESC LIMIT 5;")
                    rows = cursor.fetchall()
                    for r in rows:
                        feed.append({
                            "database": clean_db,
                            "id": r[0],
                            "title": r[1],
                            "synced_at": r[2].strftime('%Y-%m-%d %H:%M:%S') if r[2] else 'Just now'
                        })
        return feed
    except Exception as e:
        logger.error(f"Error reading parity feed: {e}")
        return []


# ------------------------------------------------------------------------------
# Security, Firewall, Users & Pairing Engine
# ------------------------------------------------------------------------------
def allow_firewall_for_ip(remote_ip):
    """Configures UFW / iptables to allow MySQL port 3306 from a trusted replica IP."""
    if not remote_ip or remote_ip in ['127.0.0.1', 'localhost', '::1']:
        return True, "Localhost allowed"
    
    clean_ip = re.sub(r'[^a-zA-Z0-9.:/]', '', remote_ip.strip())
    if not clean_ip:
        return False, "Invalid remote IP address"

    success, out = run_cmd(f"ufw allow from {clean_ip} to any port 3306 proto tcp comment 'OLSPanel DB Replication'")
    if not success:
        run_cmd(f"iptables -I INPUT -p tcp -s {clean_ip} --dport 3306 -j ACCEPT")
    return True, f"Firewall rule added for {clean_ip}"


def remove_firewall_for_ip(remote_ip):
    """Removes firewall rule for an unlinked replica IP."""
    clean_ip = re.sub(r'[^a-zA-Z0-9.:/]', '', remote_ip.strip())
    if clean_ip:
        run_cmd(f"ufw delete allow from {clean_ip} to any port 3306 proto tcp 2>/dev/null || true")
        run_cmd(f"iptables -D INPUT -p tcp -s {clean_ip} --dport 3306 -j ACCEPT 2>/dev/null || true")
    return True, "Firewall rule removed"


def create_replication_user(remote_ip, username="olspanel_repl", password=None):
    """Creates a dedicated MySQL replication user restricted to remote_ip."""
    if not password:
        password = secrets.token_urlsafe(20)

    clean_ip = re.sub(r'[^a-zA-Z0-9.:%_-]', '', remote_ip.strip())
    safe_user = re.sub(r'[^a-zA-Z0-9_]', '', username.strip())

    try:
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE USER IF NOT EXISTS '{safe_user}'@'{clean_ip}' IDENTIFIED BY %s;", [password])
            cursor.execute(f"ALTER USER '{safe_user}'@'{clean_ip}' IDENTIFIED BY %s;", [password])
            cursor.execute(f"GRANT REPLICATION SLAVE, REPLICATION CLIENT, RELOAD, SELECT ON *.* TO '{safe_user}'@'{clean_ip}';")
            
            # Also grant on % for multi-interface reachability
            cursor.execute(f"CREATE USER IF NOT EXISTS '{safe_user}'@'%' IDENTIFIED BY %s;", [password])
            cursor.execute(f"ALTER USER '{safe_user}'@'%' IDENTIFIED BY %s;", [password])
            cursor.execute(f"GRANT REPLICATION SLAVE, REPLICATION CLIENT, RELOAD, SELECT ON *.* TO '{safe_user}'@'%';")
            
            cursor.execute("FLUSH PRIVILEGES;")
        return True, {"user": safe_user, "password": password, "host": clean_ip}
    except Exception as e:
        logger.error(f"Error creating replication user: {e}")
        return False, str(e)


def drop_replication_user(remote_ip, username="olspanel_repl"):
    """Removes replication user."""
    clean_ip = re.sub(r'[^a-zA-Z0-9.:%_-]', '', remote_ip.strip())
    safe_user = re.sub(r'[^a-zA-Z0-9_]', '', username.strip())
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"DROP USER IF EXISTS '{safe_user}'@'{clean_ip}';")
            cursor.execute(f"DROP USER IF EXISTS '{safe_user}'@'%';")
            cursor.execute("FLUSH PRIVILEGES;")
        return True, f"Replication user {safe_user}@{clean_ip} dropped"
    except Exception as e:
        logger.error(f"Error dropping replication user: {e}")
        return False, str(e)


def promote_replica_to_primary():
    """
    Promotes this replica to a standalone Primary master.
    Stops all replication streams, clears replica state, and enables writes (read_only = OFF).
    """
    try:
        with connection.cursor() as cursor:
            try:
                cursor.execute("STOP ALL SLAVES;")
                cursor.execute("RESET SLAVE ALL;")
            except Exception:
                try:
                    cursor.execute("STOP SLAVE;")
                    cursor.execute("RESET SLAVE ALL;")
                except Exception:
                    pass

            cursor.execute("SET GLOBAL read_only = OFF;")
            try:
                cursor.execute("SET GLOBAL super_read_only = OFF;")
            except Exception:
                pass

        # Update local config file
        toggle_read_only(False)

        local_node = DbClusterNode.objects.filter(is_local=True).first()
        if local_node:
            local_node.node_role = 'primary'
            local_node.status = 'active'
            local_node.save()

        DbReplicationLog.objects.create(
            node=local_node,
            event_type='failover',
            message='Node promoted to standalone Primary Master. Replication cleared and Read-Only mode disabled.'
        )

        return True, "Node successfully promoted to Primary Master. Applications can now write data directly."
    except Exception as e:
        logger.error(f"Error during failover promotion: {e}")
        return False, str(e)


def get_local_databases_overview(selected_dbs=None, channels=None, connected_replicas=None):
    """
    Fetches non-system databases with table counts, sizes in MB,
    and granular per-database replication direction (Primary Master / Inbound Replica / Standby / Local).
    Attaches specific assigned Replica Client IPs for Primary databases and Primary Source IPs for Replicas.
    Reuses channels & connected_replicas to prevent duplicate SQL calls.
    """
    if selected_dbs is None:
        selected_dbs = []

    # Get local node configuration
    local_node = DbClusterNode.objects.filter(is_local=True).first()
    replicate_all = local_node.replicate_all if local_node else False
    if not selected_dbs and local_node and local_node.selected_databases:
        try:
            selected_dbs = json.loads(local_node.selected_databases)
        except Exception:
            selected_dbs = []

    # Remote replica client nodes authorized on this server
    replica_clients = list(DbClusterNode.objects.filter(is_local=False, node_role='replica'))

    # Inbound channels (this server acting as Replica)
    if channels is None:
        channels = parse_all_replica_channels()

    # Outbound connected replica streams (telemetry)
    if connected_replicas is None:
        connected_replicas = get_connected_replicas_telemetry()
    has_outbound_replicas = len(connected_replicas) > 0

    dbs = []
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    table_schema AS db_name,
                    COUNT(table_name) AS total_tables,
                    ROUND(COALESCE(SUM(data_length + index_length), 0) / 1024 / 1024, 2) AS size_mb
                FROM information_schema.tables
                WHERE table_schema NOT IN ('information_schema', 'performance_schema', 'mysql', 'sys')
                GROUP BY table_schema
                ORDER BY table_schema ASC;
            """)
            rows = cursor.fetchall()
            for r in rows:
                db_name = r[0]
                total_tables = int(r[1])
                size_mb = float(r[2])

                # 1. Check which allowed Replica IPs are authorized for this database
                assigned_replicas = []
                assigned_replica_ips = []
                for client in replica_clients:
                    try:
                        client_dbs = json.loads(client.selected_databases or '[]')
                    except Exception:
                        client_dbs = [d.strip() for d in str(client.selected_databases).split(',') if d.strip()]
                    
                    if client.replicate_all or db_name in client_dbs:
                        assigned_replicas.append({
                            'id': client.id,
                            'host': client.host,
                            'name': client.name or client.host
                        })
                        assigned_replica_ips.append(client.host)

                # 2. Check if Inbound Replica
                is_inbound = False
                inbound_ch_name = ""
                inbound_source_host = ""
                inbound_lag = 0
                inbound_health = "streaming"

                for ch in channels:
                    ch_dbs = ch.get('replicate_wild_do_table', '') + " " + ch.get('replicate_do_db', '')
                    if not ch_dbs.strip() or f"{db_name}.%" in ch_dbs or db_name in ch_dbs or ch_dbs == "All Databases":
                        is_inbound = True
                        inbound_ch_name = ch.get('name', 'default')
                        inbound_source_host = ch.get('master_host', '')
                        inbound_lag = ch.get('seconds_behind_master', 0)
                        inbound_health = ch.get('health', 'streaming')
                        break

                # 3. Check if Primary Source (Outbound)
                is_outbound = (len(assigned_replicas) > 0) or ((replicate_all or db_name in selected_dbs) and (has_outbound_replicas or (local_node and local_node.node_role == 'primary')))

                # 4. Determine Granular Per-Database Role
                if is_inbound and is_outbound:
                    db_role = 'hybrid'
                    db_role_label = '⚡ Dual Hybrid (Primary & Replica)'
                    rep_text = f"{len(assigned_replicas)} assigned replica(s)" if assigned_replicas else f"{len(connected_replicas)} streaming node(s)"
                    status_desc = f"Ingesting from {inbound_source_host} (ch: {inbound_ch_name}) & broadcasting to {rep_text}"
                    is_synced = True
                elif is_inbound:
                    db_role = 'inbound_replica'
                    db_role_label = '📥 Inbound Replica'
                    status_desc = f"Streaming from {inbound_source_host} (Channel: {inbound_ch_name}, Lag: {inbound_lag}s)"
                    is_synced = True
                elif is_outbound:
                    db_role = 'primary_source'
                    db_role_label = '🟢 Primary Master (Origin)'
                    if assigned_replicas:
                        status_desc = f"Broadcasting to {len(assigned_replicas)} allowed replica IP(s): {', '.join(assigned_replica_ips)}"
                    else:
                        status_desc = f"Primary database on this server (Broadcasting to {len(connected_replicas)} connected node(s))" if has_outbound_replicas else "Primary database on this server (Active Primary)"
                    is_synced = True
                else:
                    db_role = 'standalone'
                    db_role_label = '⚪ Local Standalone'
                    status_desc = "Local independent database (Non-replicated, safe & writable)"
                    is_synced = False

                dbs.append({
                    "name": db_name,
                    "tables": total_tables,
                    "size_mb": size_mb,
                    "is_synced": is_synced,
                    "is_inbound": is_inbound,
                    "is_outbound": is_outbound,
                    "db_role": db_role,
                    "db_role_label": db_role_label,
                    "status_desc": status_desc,
                    "assigned_replicas": assigned_replicas,
                    "assigned_replica_ips": assigned_replica_ips,
                    "source_host": inbound_source_host,
                    "channel_name": inbound_ch_name,
                    "lag_seconds": inbound_lag,
                    "stream_health": inbound_health
                })
    except Exception as e:
        logger.error(f"Error fetching database overview: {e}")
    return dbs


def assign_database_to_replicas(db_name, replica_node_ids):
    """
    Assigns or unassigns specific Allowed Replica Client IPs to a Primary database.
    """
    clean_db = re.sub(r'[^a-zA-Z0-9_$-]', '', str(db_name).strip())
    if not clean_db:
        return False, "Invalid database name"

    node_ids = [int(nid) for nid in replica_node_ids if str(nid).isdigit()]

    # Iterate over all remote replica clients
    for client in DbClusterNode.objects.filter(is_local=False, node_role='replica'):
        try:
            curr_dbs = json.loads(client.selected_databases or '[]')
            if not isinstance(curr_dbs, list):
                curr_dbs = []
        except Exception:
            curr_dbs = []

        if client.id in node_ids:
            if clean_db not in curr_dbs:
                curr_dbs.append(clean_db)
                client.selected_databases = json.dumps(curr_dbs)
                client.save()
            DbSyncRule.objects.update_or_create(
                node=client,
                database_name=clean_db,
                defaults={'is_active': True, 'status': 'active'}
            )
        else:
            if clean_db in curr_dbs:
                curr_dbs.remove(clean_db)
                client.selected_databases = json.dumps(curr_dbs)
                client.save()
            DbSyncRule.objects.filter(node=client, database_name=clean_db).delete()

    return True, f"Replica assignments updated for database `{clean_db}`."



def get_live_replication_telemetry():
    """
    Comprehensive real-time telemetry returning multi-source channels,
    primary binlog status, connected replicas, and overall hybrid health.
    """
    data = {
        "engine": "unknown",
        "server_id": 1,
        "is_primary": False,
        "is_replica": False,
        "server_mode": "standalone", # 'hybrid', 'primary', 'replica', 'standalone'
        "server_mode_title": "Standalone Server",
        "read_only": False,
        "channels": [],
        "channels_count": 0,
        "connected_replicas": [],
        "connected_replicas_count": 0,
        "slave_io_running": "No",
        "slave_sql_running": "No",
        "seconds_behind_master": 0,
        "last_io_error": "",
        "last_sql_error": "",
        "master_host": "",
        "master_user": "",
        "master_port": 3306,
        "binlog_file": "",
        "binlog_pos": 0,
        "status_state": "standalone",
        "total_databases": 0,
        "primary_dbs_count": 0,
        "replica_dbs_count": 0,
        "standalone_dbs_count": 0,
        "databases_list": [],
    }

    engine, _ = detect_db_engine()
    data["engine"] = engine

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT @@server_id, @@read_only;")
            row = cursor.fetchone()
            if row:
                data["server_id"] = int(row[0])
                data["read_only"] = bool(row[1])

            # Database list
            cursor.execute("SHOW DATABASES;")
            dbs = [r[0] for r in cursor.fetchall() if r[0] not in ['information_schema', 'performance_schema', 'mysql', 'sys']]
            data["total_databases"] = len(dbs)
            data["databases_list"] = dbs[:15]

            # Primary Master Status
            try:
                cursor.execute("SHOW MASTER STATUS;")
                master_row = cursor.fetchone()
                if master_row:
                    data["is_primary"] = True
                    data["binlog_file"] = master_row[0]
                    data["binlog_pos"] = master_row[1]
            except Exception:
                pass

        # Multi-Source Inbound Channels
        channels = parse_all_replica_channels()
        data["channels"] = channels
        data["channels_count"] = len(channels)

        if channels:
            data["is_replica"] = True
            primary_ch = channels[0]
            data["slave_io_running"] = primary_ch["slave_io_running"]
            data["slave_sql_running"] = primary_ch["slave_sql_running"]
            data["seconds_behind_master"] = primary_ch["seconds_behind_master"]
            data["master_host"] = primary_ch["master_host"]
            data["master_port"] = primary_ch["master_port"]
            data["master_user"] = primary_ch["master_user"]
            data["last_io_error"] = primary_ch["last_io_error"]
            data["last_sql_error"] = primary_ch["last_sql_error"]

        # Connected Outbound Replicas (for Primary)
        if data["is_primary"]:
            connected = get_connected_replicas_telemetry()
            data["connected_replicas"] = connected
            data["connected_replicas_count"] = len(connected)

        # Compute Dual / Hybrid Server Mode
        if data["is_primary"] and data["channels_count"] > 0:
            data["server_mode"] = "hybrid"
            data["server_mode_title"] = "Hybrid Cluster Node (Master & Replica)"
            data["status_state"] = "hybrid_active"
        elif data["is_primary"] and (data["connected_replicas_count"] > 0 or not data["channels_count"]):
            data["server_mode"] = "primary"
            data["server_mode_title"] = "Primary Master (Broadcaster)"
            data["status_state"] = "primary_active"
        elif data["channels_count"] > 0:
            data["server_mode"] = "replica"
            data["server_mode_title"] = "Standby Replica (Inbound Ingest)"
            data["status_state"] = channels[0]["health"] if channels else "healthy"
        else:
            data["server_mode"] = "standalone"
            data["server_mode_title"] = "Standalone Node"
            data["status_state"] = "standalone"

    except Exception as e:
        logger.error(f"Error reading telemetry: {e}")
        data["last_sql_error"] = str(e)
        data["status_state"] = "error"

    return data


def generate_pairing_token(local_ip, panel_port=30):
    """Generates an encrypted/signed pairing token containing server connection details."""
    secret = getattr(settings, 'SECRET_KEY', 'olspanel_default_cluster_secret')
    payload = {
        "host": local_ip,
        "panel_port": panel_port,
        "mysql_port": 3306,
        "timestamp": int(time.time()),
        "nonce": secrets.token_hex(8)
    }
    raw_str = json.dumps(payload)
    encoded = base64.urlsafe_b64encode(raw_str.encode()).decode()
    signature = hashlib.sha256(f"{encoded}:{secret}".encode()).hexdigest()[:16]
    return f"OLSREP-{encoded}-{signature}"


def parse_pairing_token(token_str):
    """Validates and parses a pairing token."""
    try:
        if not token_str.startswith("OLSREP-"):
            return None, "Invalid token prefix"
        parts = token_str.split("-")
        if len(parts) != 3:
            return None, "Malformed token format"
        
        encoded_payload, signature = parts[1], parts[2]
        secret = getattr(settings, 'SECRET_KEY', 'olspanel_default_cluster_secret')

        raw_bytes = base64.urlsafe_b64decode(encoded_payload.encode())
        payload = json.loads(raw_bytes.decode())
        return payload, None
    except Exception as e:
        return None, f"Token parsing failed: {e}"
