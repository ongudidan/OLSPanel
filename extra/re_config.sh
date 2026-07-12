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

get_password_from_file() {
    local password_file="$1"

    # Check if the file exists
    if [ ! -f "$password_file" ]; then
        echo "Error: File $password_file does not exist." >&2
        return 1
    fi

    # Read the password from the file
    local password
    password=$(cat "$password_file")

    # Check if the password is empty
    if [ -z "$password" ]; then
        echo "Error: File $password_file is empty." >&2
        return 1
    fi

    # Return the password
    echo "$password"
}

replace_password_placeholder /etc "$(get_password_from_file "/root/db_credentials_panel.txt")"
