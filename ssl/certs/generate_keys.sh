#!/bin/bash

echo -e "On your master node, run:"
echo -e "\t make rootCA.crt"
echo -e "to generate the CA."
echo -e "Then,"
echo -e "\t make DOMAIN=localhost"
echo -e "to generate your local certificate needed for NFS Exporter"
echo -e "And finally,"
echo -e "\t make DOMAIN=$(echo -n $(hostname))"
echo -e "to generate your network-wide certificate."
echo ""
echo -e "For each worker node you wish to add, generate the certificate for local and network-wide usage like so:"
echo -e "\t make DOMAIN=nodename && make DOMAIN=localhost"
echo -e "and cp nodename* files to the the actual node, in cert/ folder along with the rootCA.crt file."

exit

if [[ $# -lt 1 ]]
then
	echo "usage: <node>|<master>"
	exit
fi

role="node"

if [[ $1 == "master" ]]
then
	role="master"
fi

openssl req -x509 -newkey rsa:4096 -keyout ${role}_key.pem -out ${role}_cert.pem -days 365 -nodes -subj "/CN=$(echo -n $(hostname))"
