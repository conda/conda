#!/ bin/bash

sudo apt update \
&& sudo apt upgrade --yes \
&& DEBIAN_FRONTEND=noninteractive sudo apt install --yes squid \
&& sudo echo "auth_param basic program /usr/lib/squid/basic_ncsa_auth /etc/squid/passwords
auth_param basic realm proxy
acl authenticated proxy_auth REQUIRED
http_access allow authenticated
http_port 8118" > /etc/squid/squid.conf \
&& sudo echo "admin:$apr1$foJbPHfy$K54kqCzIEYgxAGTAtJrgv1" > /etc/squid/passwords \
&& sudo squid
