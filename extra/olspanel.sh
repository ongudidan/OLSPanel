#!/bin/bash

# Get the system IP address
#IP=$(hostname -I | awk '{print $1}')
IP=$(ip=$(hostname -I | awk '{print $1}'); if [[ $ip == 10.* || $ip == 172.* || $ip == 192.168.* ]]; then ip=$(curl -4 -m 10 -s ifconfig.me); [[ -z $ip ]] && ip=$(hostname -I | awk '{print $1}'); fi; echo $ip)
 

PORT_PATH_FILE="/etc/olspanel/port"
if [ -f "$PORT_PATH_FILE" ]; then
    # Read value from file
    PORT="$(cat "$PORT_PATH_FILE")"
else
   # Get the port from cp.service (assuming it's stored in a specific format)
PORT=$(awk -F: '/listener panel/,/}/ { if ($0 ~ /address/) p=$2 } END { print p }' /usr/local/lsws/conf/httpd_config.conf | tr -dc '0-9')
fi




# Get system information
TIME1=$(date -I)
TIME2=$(date +%H:%M:%S)
RAM=$(free -m | awk 'NR==2{printf "%s/%sMB (%.2f%%)\n", $3,$2,$3*100/$2 }')
LOAD=$(uptime | awk -F'[a-z]:' '{ print $2}' | xargs)  # Trim whitespace
DISK=$(df -h | awk '$NF=="/"{printf "%d/%dGB (%s)\n", $3,$2,$5}')
CPU=$(grep 'cpu ' /proc/stat | awk '{usage=($2+$4)*100/($2+$4+$5)} END {print usage "%"}')

# Calculate system uptime
UPTIME=$(uptime | awk -F'( |,|:)+' '{if ($7=="min") m=$6; else {if ($7~/^day/) {d=$6;h=$8;m=$9} else {h=$6;m=$7}}} {print d+0,"days,",h+0,"hours,",m+0,"minutes."}')

# Display system information
echo ""
echo "
   ____  _       _____     _____        _   _ ______ _      
  / __ \| |     / ____|   |  __ \ /\   | \ | |  ____| |     
 | |  | | |    | (___     | |__) /  \  |  \| | |__  | |     
 | |  | | |     \___ \    |  ___/ /\ \ | . \` |  __| | |     
 | |__| | |____ ____) |   | |  / ____ \| |\  | |____| |____ 
  \____/|______|_____/    |_| /_/    \_\_| \_|______|______|
                                                            
                                                            
"
echo "Log in at: https://$IP:$PORT"
echo ""
echo "Server time        : $TIME1 $TIME2."
echo "CPU Load average   : $LOAD"
echo "CPU usage          : $CPU."
echo "RAM usage          : $RAM."
echo "Disk usage         : $DISK."
echo "System uptime      : $UPTIME"
echo ""