#!/bin/bash
echo "please wait... php cgi installing...."
# Suppress all output and errors
# LOGFILE="/root/cgi_install.log"
# touch "$LOGFILE" 2>/dev/null || LOGFILE="/tmp/cgi_install.log"
# exec >>"$LOGFILE" 2>&1
HOME_PATH_FILE="/etc/olspanel/base_dir"
if [ -f "$HOME_PATH_FILE" ]; then
    # Read value from file
    PROJECT_DIR="$(cat "$HOME_PATH_FILE")"
else
    # Extract from systemd service
    PROJECT_DIR="/usr/local/lsws/Example/html/mypanel"
fi

# Path to the file containing MySQL root password
MYSQL_PASS_FILE="$PROJECT_DIR/etc/mysqlPassword"

# Read password from the file
MYSQL_PASSWORD=$(cat "$MYSQL_PASS_FILE")

SockPath=$(mysql -u root -p"$MYSQL_PASSWORD" -e "SHOW VARIABLES LIKE 'socket';" | awk 'NR==2 {print $2}')

 # echo "mysqli.default_socket set to $SockPath "
# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS_NAME=$ID
    OS_VERSION=${VERSION_ID%%.*}
elif [ -f /etc/centos-release ]; then
    OS_NAME="centos"
    OS_VERSION=$(awk '{print $4}' /etc/centos-release | cut -d. -f1)
fi

OUTPUT=$(cat /etc/*release)


# Choose package manager
if [[ "$OS_NAME" == "ubuntu" || "$OS_NAME" == "debian" ]]; then
    PACKAGE_MANAGER="apt"
elif [[ "$OS_NAME" =~ ^(centos|almalinux|rhel|fedora|rocky|oraclelinux)$ ]]; then
    if command -v dnf &>/dev/null; then
        PACKAGE_MANAGER="dnf"
    else
        PACKAGE_MANAGER="yum"
    fi
else
    exit 0
fi

install_all_cgi_php_versions() {
    sudo ${PACKAGE_MANAGER} update -y || true
    sudo ${PACKAGE_MANAGER} install -y software-properties-common lsb-release apt-transport-https ca-certificates || true

if [ "$OS_NAME" = "debian" ]; then
    sudo apt install apt-transport-https lsb-release ca-certificates wget -y
    sudo wget -O /etc/apt/trusted.gpg.d/php.gpg https://packages.sury.org/php/apt.gpg 
    sudo sh -c 'echo "deb https://packages.sury.org/php/ $(lsb_release -sc) main" > /etc/apt/sources.list.d/php.list'
    sudo ${PACKAGE_MANAGER} update -y || true
fi

    if ! grep -q "ondrej/php" /etc/apt/sources.list /etc/apt/sources.list.d/* 2>/dev/null; then
        sudo add-apt-repository -y ppa:ondrej/php || true
        sudo ${PACKAGE_MANAGER} update -y || true
    fi





    for version in 7.4 8.2; do
        ini_file="/etc/php/$version/cgi/php.ini"
        if [ ! -f "$ini_file" ]; then
            sudo ${PACKAGE_MANAGER} install -y \
                php${version}-cgi \
                php${version}-cli \
                php${version}-common \
                php${version}-mbstring \
                php${version}-zip \
                php${version}-curl \
                php${version}-sqlite3 \
                php${version}-bcmath \
                php${version}-intl || true

sudo ${PACKAGE_MANAGER} install -y php${version}-xml || true
sudo ${PACKAGE_MANAGER} install -y php${version}-mysql || true
sudo ${PACKAGE_MANAGER} install -y php${version}-imap || true
sudo ${PACKAGE_MANAGER} install -y php${version}-mysqlnd || true
sudo ${PACKAGE_MANAGER} install -y php${version}-php-imap || true
sudo ${PACKAGE_MANAGER} install -y php${version}-json || true

            [ -f "$ini_file" ] && {
                sudo sed -i 's/^upload_max_filesize\s*=.*/upload_max_filesize = 80M/' "$ini_file" || true
                sudo sed -i 's/^post_max_size\s*=.*/post_max_size = 80M/' "$ini_file" || true
            }
        fi
    done

    sudo pkill php || true
}

install_all_cgi_php_versions_centos() {

    for version in 8.2 8.3; do
        ini_file="/etc/php/${version}/cgi/php.ini"

      
        case "$version" in
            8.2) rpm_url="http://127.0.0.1:8000/repo-files/centos-php82-cgi/php8.2-8.2.0-1.el9.x86_64.rpm" ;;
            8.3) rpm_url="http://127.0.0.1:8000/repo-files/centos-php83-cgi/php8.3-8.3.0-1.el9.x86_64.rpm" ;;
            *) continue ;;
        esac

        # Install PHP RPM if ini file doesn't exist
        if [ ! -f "$ini_file" ]; then
            echo "Installing PHP $version..."
            sudo ${PACKAGE_MANAGER} install -y "$rpm_url" || true
            
             sudo sed -i 's/^upload_max_filesize\s*=.*/upload_max_filesize = 80M/' "$ini_file" || true
            sudo sed -i 's/^post_max_size\s*=.*/post_max_size = 80M/' "$ini_file" || true
        fi

        # Apply .ini changes every time
        if [ -f "$ini_file" ]; then
            echo "Applying PHP ini changes for $ini_file..."

           

            if grep -q "mysqli\.default_socket" "$ini_file"; then
                sudo sed -i "s#^\s*;*\s*mysqli\.default_socket\s*=.*#mysqli.default_socket = $SockPath#" "$ini_file"
            else
                echo "mysqli.default_socket = $SockPath" | sudo tee -a "$ini_file" > /dev/null
            fi

            echo "mysqli.default_socket set to $SockPath in $ini_file"
        else
            echo "Warning: PHP ini file not found: $ini_file"
        fi

    done
}



install_repo_el8() {
    for version in 8.2; do
        # Detect PHP ini file
        ini_file="/etc/php/${version}/cgi/php.ini"   # adjust if different on your system

      
        case "$version" in
            8.2) rpm_url="http://127.0.0.1:8000/repo-files/centos-php82-cgi/php8.2-8.2.0-1.el8.x86_64.rpm" ;;
            *) continue ;;
        esac

        # Install PHP RPM if ini file doesn't exist
        if [ ! -f "$ini_file" ]; then
            echo "Installing PHP $version..."
            sudo ${PACKAGE_MANAGER} install -y "$rpm_url" || true
             sudo sed -i 's/^upload_max_filesize\s*=.*/upload_max_filesize = 80M/' "$ini_file" || true
            sudo sed -i 's/^post_max_size\s*=.*/post_max_size = 80M/' "$ini_file" || true
        fi

        # Apply .ini changes every time
        if [ -f "$ini_file" ]; then
            echo "Applying PHP ini changes for $ini_file..."
            
           

            if grep -q "mysqli\.default_socket" "$ini_file"; then
                sudo sed -i "s#^\s*;*\s*mysqli\.default_socket\s*=.*#mysqli.default_socket = $SockPath#" "$ini_file"
            else
                echo "mysqli.default_socket = $SockPath" | sudo tee -a "$ini_file" > /dev/null
            fi

            echo "mysqli.default_socket set to $SockPath in $ini_file"
        else
            echo "Warning: PHP ini file not found: $ini_file"
        fi
    done
}



install_all_cgi_php_versions_ubuntu20() {
    echo "os ubuntu 20"

    for version in 8.2; do
        ini_file="/etc/php/${version}/cgi/php.ini"

        case "$version" in
            8.2)
                rpm_url="http://127.0.0.1:8000/repo-files/ubunto-20-php82-cgi/php8.2_8.2.0-1_amd64.deb"
                ;;
            *)
                continue
                ;;
        esac

        deb_file="/tmp/php${version}.deb"

        # Install PHP if ini not exists
        if [ ! -f "$ini_file" ]; then
            echo "Downloading PHP $version..."

            wget -O "$deb_file" "$rpm_url"

            if [ -f "$deb_file" ]; then
                echo "Installing PHP $version..."

                sudo apt install -y "$deb_file"

                echo "Removing temp file..."
                rm -f "$deb_file"
            else
                echo "Download failed for PHP $version"
                continue
            fi

            sudo sed -i 's/^upload_max_filesize\s*=.*/upload_max_filesize = 80M/' "$ini_file" || true
            sudo sed -i 's/^post_max_size\s*=.*/post_max_size = 80M/' "$ini_file" || true
        fi

        # Apply ini changes every time
        if [ -f "$ini_file" ]; then
            echo "Applying PHP ini changes for $ini_file..."

            if grep -q "mysqli\.default_socket" "$ini_file"; then
                sudo sed -i "s#^\s*;*\s*mysqli\.default_socket\s*=.*#mysqli.default_socket = $SockPath#" "$ini_file"
            else
                echo "mysqli.default_socket = $SockPath" | sudo tee -a "$ini_file" > /dev/null
            fi

            echo "mysqli.default_socket set to $SockPath in $ini_file"
        else
            echo "Warning: PHP ini file not found: $ini_file"
        fi
    done
}

install_all_cgi_php_versions_ubuntu22() {

    echo "deb [trusted=yes] http://127.0.0.1:8000/repo-files/ubunto-22-php82-cgi/php82-repo ./" \
    | sudo tee /etc/apt/sources.list.d/php82.list

    sudo apt update -y || true

    for version in 8.2; do

        apt install -y php${version}-cli php${version}-cgi php${version}-curl php${version}-gd php${version}-mbstring php${version}-xml php${version}-mysql php${version}-opcache php${version}-common php${version}-session php${version}-filter php${version}-filter php${version}-fileinfo php${version}-zlib php${version}-sqlite3  
        apt install php${version}-openssl php${version}-ctype php${version}-iconv
        ini_file="/etc/php/$version/cgi/php.ini"

        if [ -f "$ini_file" ]; then
            sudo sed -i 's/^upload_max_filesize\s*=.*/upload_max_filesize = 80M/' "$ini_file" || true
            sudo sed -i 's/^post_max_size\s*=.*/post_max_size = 80M/' "$ini_file" || true
             if grep -q "mysqli\.default_socket" "$ini_file"; then
                sudo sed -i "s#^\s*;*\s*mysqli\.default_socket\s*=.*#mysqli.default_socket = $SockPath#" "$ini_file"
            else
                echo "mysqli.default_socket = $SockPath" | sudo tee -a "$ini_file" > /dev/null
            fi
        fi

    done
}




EL_VERSION=$(rpm -E %rhel 2>/dev/null || echo 0)


if [[ "$OS_NAME" =~ ^(centos|almalinux|rhel|fedora|rocky|oraclelinux)$ ]]; then
    if [[ "$EL_VERSION" == "8" ]]; then
            install_repo_el8
        else
            install_all_cgi_php_versions_centos
    fi        
elif echo "$OUTPUT" | grep -q "Ubuntu 20.04"; then
    install_all_cgi_php_versions_ubuntu20
else
    install_all_cgi_php_versions
fi

sudo ${PACKAGE_MANAGER} install -y php8.2-intl || true
