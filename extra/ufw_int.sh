wget -O /usr/local/ufw.zip "https://ongudidan.github.io/FortunePanel/plugin/ufw.zip"
sudo unzip -o /usr/local/ufw.zip -d /usr/local

wget -O /usr/local/config_ufw.zip "https://ongudidan.github.io/FortunePanel/plugin/config_ufw.zip"

if [ ! -d "/usr/local/ufw/conf" ]; then
    sudo unzip -o /usr/local/config_ufw.zip -d /usr/local/ufw
fi