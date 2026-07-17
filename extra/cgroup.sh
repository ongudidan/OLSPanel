#!/bin/bash

ARCH=$(uname -m)




if [[ "$ARCH" == "aarch64" || "$ARCH" == "armv7l" ]]; then
  
	wget https://olspanel.com/extra/arm/userlimit -O /usr/local/bin/userlimit
else
   
	wget https://olspanel.com/extra/userlimit -O /usr/local/bin/userlimit

fi

chmod +x /usr/local/bin/userlimit

sudo /usr/local/lsws/lsns/bin/lssetup


