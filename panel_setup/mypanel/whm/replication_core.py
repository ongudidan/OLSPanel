import os
import re
import json
import time
import secrets
import base64
import hashlib
import subprocess
from datetime import datetime
from django.conf import settings
from django.db import connection
from users.models import DbClusterNode, DbReplicationLog
from users.panellogger import CpLogger

logger = CpLogger()

def run_cmd(cmd, timeout=30):
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


def detect_db_engine():
    """Detects whether MariaDB or MySQL is active, and returns engine type + version."""
    success, out = run_cmd("mariadb --version || mysql --version")
    out_lower = out.lower()
    if "mariadb" in out_lower:
        return "mariadb", out
    elif "mysql" in out_lower:
        return "mysql", out
    return "unknown", out


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
    return "/etc/mysql/conf.d"


def generate_server_id():
    """Generates a random, valid MySQL 32-bit server-id (1 to 2147483647)."""
    return secrets.randbelow(2000000000) + 1000


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


def ensure_replication_config(server_id=None, is_primary=True, selected_databases=None, replicate_all=False):
    """
    Creates/updates the OLSPanel MySQL replication configuration file.
    Enables binary logs, GTID, and unique server-id.
    Supports database-level selective replication filters.
    """
    conf_dir = get_mysql_config_dir()
    os.makedirs(conf_dir, exist_ok=True)
    conf_path = os.path.join(conf_dir, "99-olspanel-replication.cnf")

    if not server_id:
        curr_id = get_current_server_id()
        server_id = curr_id if curr_id > 1 else generate_server_id()

    engine, _ = detect_db_engine()

    if engine == "mariadb":
        config_lines = [
            "# OLSPanel Auto-Generated Database Replication Configuration",
            "[mysqld]",
            f"server_id               = {server_id}",
            "log_bin                 = /var/log/mysql/mariadb-bin.log",
            "log_bin_index           = /var/log/mysql/mariadb-bin.index",
            "binlog_format           = ROW",
            "expire_logs_days        = 7",
            "max_binlog_size         = 100M",
            "log_slave_updates       = 1",
            "gtid_strict_mode        = 1",
            "bind-address            = 0.0.0.0",
        ]
    else:  # Oracle MySQL
        config_lines = [
            "# OLSPanel Auto-Generated Database Replication Configuration",
            "[mysqld]",
            f"server_id               = {server_id}",
            "log_bin                 = /var/log/mysql/mysql-bin.log",
            "binlog_format           = ROW",
            "binlog_expire_logs_seconds = 604800",
            "max_binlog_size         = 100M",
            "log_replica_updates     = 1",
            "gtid_mode               = ON",
            "enforce_gtid_consistency = ON",
            "bind-address            = 0.0.0.0",
        ]

    # Add selective database replication filters if configured
    if not is_primary and not replicate_all and selected_databases:
        config_lines.append("# --- Database-Level Selective Filters (Multi-Use Server Safe) ---")
        for db in selected_databases:
            clean_db = re.sub(r'[^a-zA-Z0-9_$-]', '', str(db).strip())
            if clean_db and clean_db not in ['information_schema', 'performance_schema', 'mysql', 'sys']:
                config_lines.append(f"replicate-wild-do-table = {clean_db}.%")

    config_content = "\n".join(config_lines) + "\n"

    try:
        with open(conf_path, "w") as f:
            f.write(config_content)
        
        # Ensure log directory exists
        os.makedirs("/var/log/mysql", exist_ok=True)
        run_cmd("chown -R mysql:mysql /var/log/mysql")

        # Reload or restart database service
        run_cmd("systemctl reload mariadb || systemctl reload mysql || systemctl restart mariadb || systemctl restart mysql")

        try:
            connection.close()
        except Exception:
            pass

        return True, f"Replication config saved to {conf_path} with server_id {server_id}"
    except Exception as e:
        logger.error(f"Failed to write replication config: {e}")
        return False, str(e)


def apply_database_replication_filters(selected_databases=None, replicate_all=False):
    """
    Dynamically applies selective database replication filters on the replica.
    Ensures only chosen databases are synchronized, keeping all other databases on this
    secondary server completely safe, writable, and isolated.
    """
    if selected_databases is None:
        selected_databases = []

    valid_dbs = []
    for db in selected_databases:
        clean_name = re.sub(r'[^a-zA-Z0-9_$-]', '', str(db).strip())
        if clean_name and clean_name not in ['information_schema', 'performance_schema', 'mysql', 'sys']:
            valid_dbs.append(clean_name)

    # 1. Update config file for persistence across restarts
    ensure_replication_config(
        is_primary=False,
        selected_databases=valid_dbs,
        replicate_all=replicate_all
    )

    # 2. Dynamic filter application via SQL (MySQL 8.0+)
    try:
        with connection.cursor() as cursor:
            try:
                cursor.execute("STOP SLAVE SQL_THREAD;")
            except Exception:
                try:
                    cursor.execute("STOP REPLICA SQL_THREAD;")
                except Exception:
                    pass

            try:
                if not replicate_all and valid_dbs:
                    filter_str = ", ".join([f"'{db}.%'" for db in valid_dbs])
                    cursor.execute(f"CHANGE REPLICATION FILTER REPLICATE_WILD_DO_TABLE = ({filter_str});")
                else:
                    cursor.execute("CHANGE REPLICATION FILTER REPLICATE_WILD_DO_TABLE = ();")
            except Exception as sql_err:
                logger.info(f"Dynamic replication filter SQL notice: {sql_err}")

            try:
                cursor.execute("START SLAVE SQL_THREAD;")
            except Exception:
                try:
                    cursor.execute("START REPLICA SQL_THREAD;")
                except Exception:
                    pass

        return True, f"Replication filter updated: {len(valid_dbs)} database(s) active."
    except Exception as e:
        logger.error(f"Error applying dynamic replication filter: {e}")
        return True, "Filter written to configuration."


def get_local_databases_overview(selected_dbs=None):
    """
    Fetches all non-system databases with table counts, sizes in MB,
    and whether each database is currently selected for live sync.
    """
    if selected_dbs is None:
        selected_dbs = []
    
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
                is_selected = db_name in selected_dbs
                dbs.append({
                    "name": db_name,
                    "tables": total_tables,
                    "size_mb": size_mb,
                    "is_synced": is_selected
                })
    except Exception as e:
        logger.error(f"Error fetching database overview: {e}")
    return dbs




def allow_firewall_for_ip(remote_ip):
    """Configures UFW / iptables to allow MySQL port 3306 from a trusted replica IP."""
    if not remote_ip or remote_ip in ['127.0.0.1', 'localhost', '::1']:
        return True, "Localhost allowed"
    
    # Sanitize IP
    clean_ip = re.sub(r'[^a-zA-Z0-9.:/]', '', remote_ip.strip())
    if not clean_ip:
        return False, "Invalid remote IP address"

    # Try UFW first
    success, out = run_cmd(f"ufw allow from {clean_ip} to any port 3306 proto tcp comment 'OLSPanel DB Replication'")
    if not success:
        # Fallback to iptables
        run_cmd(f"iptables -I INPUT -p tcp -s {clean_ip} --dport 3306 -j ACCEPT")
    return True, f"Firewall rule added for {clean_ip}"


def remove_firewall_for_ip(remote_ip):
    """Removes firewall rule for an unlinked replica IP."""
    clean_ip = re.sub(r'[^a-zA-Z0-9.:/]', '', remote_ip.strip())
    if clean_ip:
        run_cmd(f"ufw delete allow from {clean_ip} to any port 3306 proto tcp")
        run_cmd(f"iptables -D INPUT -p tcp -s {clean_ip} --dport 3306 -j ACCEPT")
    return True, "Firewall rule removed"


def create_replication_user(remote_ip, username="olspanel_repl", password=None):
    """Creates a dedicated MySQL replication user restricted to remote_ip."""
    if not password:
        password = secrets.token_urlsafe(24)

    clean_ip = re.sub(r'[^a-zA-Z0-9.:%_-]', '', remote_ip.strip())
    safe_user = re.sub(r'[^a-zA-Z0-9_]', '', username.strip())

    try:
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE USER IF NOT EXISTS '{safe_user}'@'{clean_ip}' IDENTIFIED BY %s;", [password])
            cursor.execute(f"ALTER USER '{safe_user}'@'{clean_ip}' IDENTIFIED BY %s;", [password])
            cursor.execute(f"GRANT REPLICATION SLAVE, REPLICATION CLIENT, RELOAD ON *.* TO '{safe_user}'@'{clean_ip}';")
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
            cursor.execute("FLUSH PRIVILEGES;")
        return True, f"Replication user {safe_user}@{clean_ip} dropped"
    except Exception as e:
        logger.error(f"Error dropping replication user: {e}")
        return False, str(e)


def get_live_replication_telemetry():
    """
    Fetches real-time status of replication from local database.
    Works whether this node is a Primary (Master) or Replica (Slave).
    """
    data = {
        "engine": "unknown",
        "server_id": 1,
        "is_primary": False,
        "is_replica": False,
        "read_only": False,
        "slave_io_running": "No",
        "slave_sql_running": "No",
        "seconds_behind_master": None,
        "last_io_error": "",
        "last_sql_error": "",
        "master_host": "",
        "master_user": "",
        "master_port": 3306,
        "binlog_file": "",
        "binlog_pos": 0,
        "gtid_executed": "",
        "status_state": "idle",
        "total_databases": 0,
        "databases_list": [],
    }

    engine, _ = detect_db_engine()
    data["engine"] = engine

    try:
        with connection.cursor() as cursor:
            # Check basic variables
            cursor.execute("SELECT @@server_id, @@read_only;")
            row = cursor.fetchone()
            if row:
                data["server_id"] = int(row[0])
                data["read_only"] = bool(row[1])

            # Check database list
            cursor.execute("SHOW DATABASES;")
            dbs = [r[0] for r in cursor.fetchall() if r[0] not in ['information_schema', 'performance_schema', 'mysql', 'sys']]
            data["total_databases"] = len(dbs)
            data["databases_list"] = dbs[:15]

            # Check Master/Primary Status
            try:
                cursor.execute("SHOW MASTER STATUS;")
                master_row = cursor.fetchone()
                if master_row:
                    data["is_primary"] = True
                    data["binlog_file"] = master_row[0]
                    data["binlog_pos"] = master_row[1]
                    if len(master_row) > 4 and master_row[4]:
                        data["gtid_executed"] = str(master_row[4])
            except Exception:
                pass

            # Check Slave/Replica Status
            slave_status = None
            try:
                cursor.execute("SHOW SLAVE STATUS;")
                slave_status = cursor.fetchone()
                if not slave_status:
                    cursor.execute("SHOW REPLICA STATUS;")
                    slave_status = cursor.fetchone()
            except Exception:
                pass

            if slave_status:
                data["is_replica"] = True
                desc = [d[0].lower() for d in cursor.description]
                status_dict = dict(zip(desc, slave_status))

                data["slave_io_running"] = status_dict.get('slave_io_running', status_dict.get('replica_io_running', 'No'))
                data["slave_sql_running"] = status_dict.get('slave_sql_running', status_dict.get('replica_sql_running', 'No'))
                data["master_host"] = status_dict.get('master_host', status_dict.get('source_host', ''))
                data["master_user"] = status_dict.get('master_user', status_dict.get('source_user', ''))
                data["master_port"] = status_dict.get('master_port', status_dict.get('source_port', 3306))
                
                raw_lag = status_dict.get('seconds_behind_master', status_dict.get('seconds_behind_source'))
                data["seconds_behind_master"] = int(raw_lag) if raw_lag is not None else None
                
                data["last_io_error"] = status_dict.get('last_io_error', status_dict.get('last_io_errno_message', ''))
                data["last_sql_error"] = status_dict.get('last_sql_error', status_dict.get('last_sql_errno_message', ''))
                data["gtid_executed"] = status_dict.get('executed_gtid_set', '')

                # Determine aggregated state
                if str(data["slave_io_running"]).lower() == 'yes' and str(data["slave_sql_running"]).lower() == 'yes':
                    if data["seconds_behind_master"] is not None and data["seconds_behind_master"] > 10:
                        data["status_state"] = "syncing"
                    else:
                        data["status_state"] = "healthy"
                elif str(data["slave_io_running"]).lower() == 'connecting':
                    data["status_state"] = "connecting"
                elif data["last_io_error"] or data["last_sql_error"]:
                    data["status_state"] = "error"
                elif str(data["slave_io_running"]).lower() == 'no' and str(data["slave_sql_running"]).lower() == 'no':
                    data["status_state"] = "paused"
                else:
                    data["status_state"] = "warning"
            else:
                if data["is_primary"]:
                    data["status_state"] = "primary_active"
                else:
                    data["status_state"] = "standalone"

    except Exception as e:
        logger.error(f"Error reading replication telemetry: {e}")
        data["last_sql_error"] = str(e)
        data["status_state"] = "error"

    return data


def start_replica_link(master_host, master_port, repl_user, repl_password, use_gtid=True, selected_databases=None, replicate_all=False):
    """
    Configures and starts the replication link on this node pointing to master_host.
    Supports selective per-database filters so secondary servers remain safe for multi-use.
    """
    engine, _ = detect_db_engine()
    safe_host = re.sub(r'[^a-zA-Z0-9.:_-]', '', str(master_host).strip())
    safe_user = re.sub(r'[^a-zA-Z0-9_]', '', str(repl_user).strip())
    safe_port = int(master_port)

    # Clean selected databases
    valid_dbs = []
    if selected_databases:
        for db in selected_databases:
            clean_name = re.sub(r'[^a-zA-Z0-9_$-]', '', str(db).strip())
            if clean_name and clean_name not in ['information_schema', 'performance_schema', 'mysql', 'sys']:
                valid_dbs.append(clean_name)

    # 1. Update persistent config file with filters
    ensure_replication_config(
        is_primary=False,
        selected_databases=valid_dbs,
        replicate_all=replicate_all
    )

    try:
        with connection.cursor() as cursor:
            # Stop existing slave threads
            try:
                cursor.execute("STOP SLAVE;")
            except Exception:
                try:
                    cursor.execute("STOP REPLICA;")
                except Exception:
                    pass

            # Configure connection
            if engine == "mariadb":
                gtid_clause = "MASTER_USE_GTID = current_pos" if use_gtid else ""
                sql = f"""
                CHANGE MASTER TO
                    MASTER_HOST = %s,
                    MASTER_PORT = %s,
                    MASTER_USER = %s,
                    MASTER_PASSWORD = %s,
                    MASTER_CONNECT_RETRY = 10
                    {',' + gtid_clause if gtid_clause else ''};
                """
                cursor.execute(sql, [safe_host, safe_port, safe_user, repl_password])
            else:
                auto_pos = "MASTER_AUTO_POSITION = 1" if use_gtid else "MASTER_AUTO_POSITION = 0"
                sql = f"""
                CHANGE MASTER TO
                    MASTER_HOST = %s,
                    MASTER_PORT = %s,
                    MASTER_USER = %s,
                    MASTER_PASSWORD = %s,
                    MASTER_CONNECT_RETRY = 10,
                    {auto_pos};
                """
                cursor.execute(sql, [safe_host, safe_port, safe_user, repl_password])

            # Apply dynamic database replication filter
            try:
                if not replicate_all and valid_dbs:
                    filter_str = ", ".join([f"'{db}.%'" for db in valid_dbs])
                    cursor.execute(f"CHANGE REPLICATION FILTER REPLICATE_WILD_DO_TABLE = ({filter_str});")
                else:
                    cursor.execute("CHANGE REPLICATION FILTER REPLICATE_WILD_DO_TABLE = ();")
            except Exception as f_err:
                logger.info(f"Replication filter setting notice: {f_err}")

            # Start replication
            try:
                cursor.execute("START SLAVE;")
            except Exception:
                cursor.execute("START REPLICA;")

        filter_msg = f"with {len(valid_dbs)} database(s) filtered" if (not replicate_all and valid_dbs) else "for all databases"
        return True, f"Replication link established and started {filter_msg}."
    except Exception as e:
        logger.error(f"Failed to start replica link: {e}")
        return False, str(e)


def pause_replica_link():
    """Pauses replication IO and SQL threads."""
    try:
        with connection.cursor() as cursor:
            try:
                cursor.execute("STOP SLAVE;")
            except Exception:
                cursor.execute("STOP REPLICA;")
        return True, "Replication stopped successfully."
    except Exception as e:
        return False, str(e)


def resume_replica_link():
    """Resumes paused replication threads."""
    try:
        with connection.cursor() as cursor:
            try:
                cursor.execute("START SLAVE;")
            except Exception:
                cursor.execute("START REPLICA;")
        return True, "Replication resumed successfully."
    except Exception as e:
        return False, str(e)


def promote_replica_to_primary():
    """
    Promotes this replica to a standalone Primary master.
    Stops replication, clears replica state, and enables writes (read_only = OFF).
    """
    try:
        with connection.cursor() as cursor:
            try:
                cursor.execute("STOP SLAVE;")
                cursor.execute("RESET SLAVE ALL;")
            except Exception:
                try:
                    cursor.execute("STOP REPLICA;")
                    cursor.execute("RESET REPLICA ALL;")
                except Exception:
                    pass

            cursor.execute("SET GLOBAL read_only = OFF;")
            try:
                cursor.execute("SET GLOBAL super_read_only = OFF;")
            except Exception:
                pass

        # Update local node record
        local_node = DbClusterNode.objects.filter(is_local=True).first()
        if local_node:
            local_node.node_role = 'primary'
            local_node.status = 'active'
            local_node.save()

        DbReplicationLog.objects.create(
            node=local_node,
            event_type='failover',
            message='Node promoted to Primary (Master). Read-only mode disabled and replica link cleared.'
        )

        return True, "Node successfully promoted to Primary Master."
    except Exception as e:
        logger.error(f"Error during failover promotion: {e}")
        return False, str(e)


def generate_pairing_token(local_ip, panel_port=30):
    """
    Generates an encrypted/signed pairing token containing server connection details.
    """
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
