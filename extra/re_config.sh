#!/bin/bash


replace_password_placeholder() {
    local SEARCH_DIR="$1"
    local NEW_PASS="$2"

    if [ -z "$SEARCH_DIR" ] || [ -z "$NEW_PASS" ]; then
        echo "Usage: replace_password_placeholder <directory> <new_password>"
        return 1
    fi

    echo "🔍 Searching for %password% in $SEARCH_DIR ..."
    grep -Ril "%password%" "$SEARCH_DIR" 2>/dev/null | while read file; do
        echo "✅ Replacing in: $file"
        sed -i "s|%password%|$NEW_PASS|g" "$file"
    done

    echo "🎉 Replacement complete."
}

get_panel_password() {
    if [ -f "/root/db_credentials_panel.txt" ]; then
        cat /root/db_credentials_panel.txt | tr -d '[:space:]'
    elif [ -f "/etc/dovecot/dovecot-sql.conf.ext" ]; then
        grep -oP 'password=\K\S+' /etc/dovecot/dovecot-sql.conf.ext
    elif [ -f "/etc/postfix/mysql-virtual_domains.cf" ]; then
        grep -oP '^password\s*=\s*\K\S+' /etc/postfix/mysql-virtual_domains.cf
    elif [ -f "/usr/local/olspanel/mypanel/etc/mysqlPassword" ]; then
        cat /usr/local/olspanel/mypanel/etc/mysqlPassword | tr -d '[:space:]'
    fi
}

PASS="$(get_panel_password)"
if [ -n "$PASS" ]; then
    replace_password_placeholder /etc "$PASS"
else
    echo "Error: Could not determine panel database password." >&2
    exit 1
fi
