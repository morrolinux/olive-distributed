#!/bin/bash

openssl req -x509 -newkey rsa:4096 -keyout node_key.pem -out node_cert.pem -days 365 -nodes -subj "/CN=$(cat /etc/hostname)"
