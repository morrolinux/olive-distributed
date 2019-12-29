#!/bin/bash

if [[ $# -lt 1 ]]
then
	echo "usage: <setup> | <add> <hostname>"
	exit
fi

# This oneliner is from https://serverfault.com/questions/367141/how-to-get-the-fully-qualified-name-fqn-on-unix-in-a-bash-script
fqn=$(host -TtA $(hostname -s)|grep "has address"|awk '{print $1}') ; if [[ "${fqn}" == "" ]] ; then fqn=$(hostname -s) ; fi 

if [[ $1 == "setup" ]]
then
	# Generate the CA:
	make rootCA.crt
	
	# Generate your local certificate needed for NFS Exporter
	make DOMAIN=localhost
	
	# Generate your network-wide certificate
	make DOMAIN=$fqn
elif [[ $1 == "add" ]]
then
	if [[ $2 != "" ]]
	then
		make DOMAIN=${2}.$(echo $fqn|cut -d. -f2-)
		make DOMAIN=localhost NAME=${2}_local
		echo $fqn > whoismaster
		scp whoismaster rootCA.crt ${2}* ${2}:olive-distributed-rendering/ssl/certs/
	fi
fi


