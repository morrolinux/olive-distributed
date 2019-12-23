#!/bin/bash

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
