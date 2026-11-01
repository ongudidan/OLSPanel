#!/bin/bash
REPO_URL="${OLSPANEL_REPO_URL:-$(cat /etc/olspanel/repo_url 2>/dev/null | tr -d '\r\n')}"
REPO_URL="${REPO_URL:-https://ongudidan.github.io/OLSPanel}"

ARCH=$(uname -m)




if [[ "$ARCH" == "aarch64" || "$ARCH" == "armv7l" ]]; then
  
	wget ${REPO_URL}/extra/arm/userlimit -O /usr/local/bin/userlimit
else
   
	wget ${REPO_URL}/extra/userlimit -O /usr/local/bin/userlimit

fi

chmod +x /usr/local/bin/userlimit

sudo /usr/local/lsws/lsns/bin/lssetup


