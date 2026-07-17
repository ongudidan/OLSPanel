#!/bin/bash

# Detect OS info
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS_NAME=$ID
    OS_VERSION=${VERSION_ID%%.*}
elif [ -f /etc/centos-release ]; then
    OS_NAME="centos"
    OS_VERSION=$(awk '{print $4}' /etc/centos-release | cut -d. -f1)
fi

# Function to remove blank/duplicate cron lines
remove_extra_cron_lines() {
    crontab -l 2>/dev/null | grep -v '^[[:space:]]*$' | sort | uniq | crontab -
    echo "Extra lines (blank/duplicate) have been removed from the cron jobs!"
}

# Add backup cronjobs based on OS
add_backup_cronjobs() {
    local PYTHON_CMD

    if [[ ("$OS_NAME" == "centos" || "$OS_NAME" == "almalinux") && ("$OS_VERSION" == "7" || "$OS_VERSION" == "8") ]]; then
        PYTHON_CMD="/root/venv/bin/python3.12"
    elif [[ "$OS_NAME" == "ubuntu" && "$OS_VERSION" -ge 24 ]]; then
        PYTHON_CMD="/root/venv/bin/python"
    elif [[ "$OS_NAME" == "ubuntu" && "$OS_VERSION" -lt 24 ]]; then
        PYTHON_CMD=$(which python3)
    else
        PYTHON_CMD="/root/venv/bin/python3"
    fi

    local CRON_JOBS="\
0 0 * * * $PYTHON_CMD /usr/local/lsws/Example/html/mypanel/manage.py check_version
0 */3 * * * $PYTHON_CMD /usr/local/lsws/Example/html/mypanel/manage.py limit_check
"

    ( crontab -l 2>/dev/null; echo "$CRON_JOBS" ) | crontab -
    remove_extra_cron_lines
    echo "Cron jobs have been added successfully!"
}

# Install ionCube loader
icob_loader_install() {
    for version in 81; do
        echo "Installing ionCube Loader for PHP $version..."

        PHP_BIN="/usr/local/lsws/lsphp$version/bin/php"
        PHP_LIB="/usr/local/lsws/lsphp$version/lib"
        TARGET_DIR="/usr/local/lsws/Example/html/ioncube"
        
        php_version=$(echo "$version" | awk '{print substr($0,1,1) "." substr($0,2,1)}')
        
        ioncube_so="ioncube_loader_lin_${php_version}.so"
        ini_file_path="/usr/local/lsws/lsphp$version/etc/php/$php_version/litespeed/php.ini"
        ini_file_path_old="/usr/local/lsws/lsphp$version/etc/php.ini"

        if [ ! -x "$PHP_BIN" ]; then
            echo "PHP $version not found. Skipping..."
            continue
        fi

        mkdir -p "$TARGET_DIR"
        cd "$TARGET_DIR" || exit

        if [ ! -f ioncube_loaders_lin_x86-64.tar.gz ]; then
            echo "Downloading ionCube..."
            wget -q https://downloads.ioncube.com/loader_downloads/ioncube_loaders_lin_x86-64.tar.gz
        fi

        tar -xzf ioncube_loaders_lin_x86-64.tar.gz

        if [ -f "$TARGET_DIR/ioncube/$ioncube_so" ]; then
            cp "$TARGET_DIR/ioncube/$ioncube_so" "$PHP_LIB/"
            echo "Copied $ioncube_so to $PHP_LIB"
        else
            echo "$ioncube_so not found. Skipping..."
            continue
        fi

        if [ -f "$ini_file_path" ]; then
            target_ini="$ini_file_path"
        elif [ -f "$ini_file_path_old" ]; then
            target_ini="$ini_file_path_old"
        else
            echo "php.ini not found. Skipping..."
            continue
        fi

       
      echo -e "\nzend_extension = $PHP_LIB/$ioncube_so" >> "$target_ini"
             

echo "Appended ionCube config to $target_ini"

           
       
    done
 rm -rf "$TARGET_DIR/ioncube"
 rm -f "$TARGET_DIR/ioncube_loaders_lin_x86-64.tar.gz"
    echo "Restarting PHP..."
    pkill lsphp
    sudo ln -s /usr/local/lsws/lsphp81/bin/php /usr/bin/php
    echo "ionCube installation completed."
}

install_softaculous() {
    ZIP_URL="https://ongudidan.github.io/OLSPanel/softaculous/softaculous.zip"
    DEST_DIR="/usr/local/lsws/Example/html/softaculous"
    ZIP_FILE="/usr/local/lsws/Example/html/softaculous.zip"

    echo "⬇️ Downloading Softaculous..."
    wget -O "$ZIP_FILE" "$ZIP_URL"

    echo "📂 Extracting Softaculous..."
    mkdir -p "$DEST_DIR"
    unzip -o "$ZIP_FILE" -d "$DEST_DIR"
    rm -f "$ZIP_FILE"

    echo "✅ Softaculous installed at: $DEST_DIR"
}
# Run installer
icob_loader_install
install_softaculous
#wget -O /usr/local/lsws/Example/html/phpmyadmin/config.inc.php https://ongudidan.github.io/OLSPanel/softaculous/config.inc.ph
#chown -R olspanel:olspanel /usr/local/lsws/Example/html/phpmyadmin
#chown -R olspanel:olspanel /usr/local/lsws/Example/html/webmail
chown -R olspanel:olspanel /usr/local/lsws/Example/html/softaculous

