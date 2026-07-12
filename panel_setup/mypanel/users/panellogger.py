import os
import subprocess
from datetime import datetime

class CpLogger:
    def __init__(self, log_file='/usr/local/lsws/logs/panel.log', max_file_size_mb=10, max_backup_files=5):
        """
        Initializes the custom logger.

        :param log_file: Path to the log file (default: '/usr/local/lsws/logs/panel.log').
        :param max_file_size_mb: Maximum size of a log file in MB (default: 10).
        :param max_backup_files: Maximum number of backup log files to keep (default: 5).
        """
        self.log_file = log_file
        self.max_file_size_mb = max_file_size_mb
        self.max_backup_files = max_backup_files

        # Create the log directory if it doesn't exist
        log_dir = os.path.dirname(self.log_file)
        os.makedirs(log_dir, exist_ok=True)

        # Initialize the current log file
        self._rotate_logs_if_needed()

    def _rotate_logs_if_needed(self):
        """
        Rotates log files if the current log file exceeds the maximum size.
        """
        if os.path.exists(self.log_file):
            file_size_mb = os.path.getsize(self.log_file) / (1024 * 1024)  # Convert bytes to MB
            if file_size_mb >= self.max_file_size_mb:
                self._rotate_logs()

    def _rotate_logs(self):
        """
        Rotates log files by renaming the current log file and creating a new one.
        """
        # Get a list of existing log files in the same directory
        log_dir = os.path.dirname(self.log_file)
        log_files = sorted(
            [f for f in os.listdir(log_dir) if f.startswith(os.path.basename(self.log_file))],
            key=lambda x: os.path.getmtime(os.path.join(log_dir, x))
        )

        # Remove old log files if the number exceeds max_backup_files
        while len(log_files) >= self.max_backup_files:
            oldest_file = log_files.pop(0)
            os.remove(os.path.join(log_dir, oldest_file))

        # Rename the current log file
        timestamp = datetime.now().strftime('%b %e %H:%M:%S')
        new_log_file = f"{self.log_file}.{timestamp}"
        os.rename(self.log_file, new_log_file)

    def get_server_timex(self):
        
        try:
            # Run the `timedatectl` command to get the system time information
            result = subprocess.run(
                ["timedatectl"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Check if the command was successful
            if result.returncode == 0:
                # Parse the output to find the "Local time" line
                for line in result.stdout.splitlines():
                    if "Local time:" in line:
                        local_time_str = line.split(": ", 1)[1].strip()  # e.g. "Tue 2025-08-06 22:59:01 +0600"                    
                        dt_str = ' '.join(local_time_str.split()[1:3])  # "2025-08-06 22:59:01"
                        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")                    
                        return dt.strftime('%b %e %H:%M:%S')
                # If "Local time" is not found in the output
                print("Error: 'Local time' not found in `timedatectl` output.")
                return None
            else:
                # Handle errors if the command fails
                print(f"Error retrieving local time: {result.stderr}")
                return None
        except FileNotFoundError:
            # Handle the case where `timedatectl` is not available
            print("Error: `timedatectl` command not found. This function requires a systemd-based Linux system.")
            return None
        except Exception as e:
            # Handle any other exceptions that occur
            print(f"An error occurred: {e}")
            return None

    def log(self, level, message):
        """
        Logs a message with the specified level.

        :param level: Log level (e.g., 'INFO', 'WARNING', 'ERROR').
        :param message: The message to log.
        """
        server_time = self.get_server_timex()
        if not server_time:
            # Fallback to system time if server time cannot be retrieved
            server_time = datetime.now().strftime('%b %e %H:%M:%S')
        log_entry = f"{server_time}  {level}  {message}\n"

        # Write the log entry to the current log file
        with open(self.log_file, 'a') as log_file:
            log_file.write(log_entry)

        # Rotate logs if needed
        self._rotate_logs_if_needed()

    def info(self, message):
        """
        Logs an INFO message.

        :param message: The message to log.
        """
        self.log('INFO', message)

    def warning(self, message):
        """
        Logs a WARNING message.

        :param message: The message to log.
        """
        self.log('WARNING', message)

    def error(self, message):
        """
        Logs an ERROR message.

        :param message: The message to log.
        """
        self.log('ERROR', message)