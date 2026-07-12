#!/bin/bash

APP_TO_RESTART="$1"

if [ -z "$APP_TO_RESTART" ]; then
    echo "Usage: $0 <app_path>"
    exit 1
fi

echo "Searching for Node.js processes (lsnode) matching app path: $APP_TO_RESTART ..."

FOUND=false

# Find processes
ps aux | grep "lsnode:" | grep -v grep | while read -r line
do
    PID=$(echo $line | awk '{print $2}')
    APP_PATH=$(echo $line | awk '{for(i=1;i<=NF;i++){ if($i ~ /^lsnode:/){split($i,a,":"); print a[2]}}}')

    if [ "$APP_PATH" == "$APP_TO_RESTART" ]; then
        FOUND=true
        echo "Found matching app: $APP_PATH (PID: $PID)"
        echo "Killing PID $PID ..."
        kill -9 $PID
    fi
done

sleep 2

if [ "$FOUND" = true ]; then
    echo "Restarting OpenLiteSpeed (this will respawn $APP_TO_RESTART)..."
    /usr/local/lsws/bin/lswsctrl restart
    echo "App restarted: $APP_TO_RESTART"
else
    echo "No matching app found for path: $APP_TO_RESTART"
fi
