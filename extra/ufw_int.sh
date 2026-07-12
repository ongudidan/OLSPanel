wget -O /usr/local/ufw.zip "http://127.0.0.1:8000/plugin/ufw.zip"
sudo unzip -o /usr/local/ufw.zip -d /usr/local

wget -O /usr/local/config_ufw.zip "http://127.0.0.1:8000/plugin/config_ufw.zip"

if [ ! -d "/usr/local/ufw/conf" ]; then
    sudo unzip -o /usr/local/config_ufw.zip -d /usr/local/ufw
fi