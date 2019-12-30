#!/bin/sh

cat <<EOF
[req]
default_bits       = 2048
distinguished_name = req_distinguished_name
req_extensions     = req_ext

[req_distinguished_name]
countryName                 = $2
stateOrProvinceName         = $3
organizationName           = $4
commonName                 = $1

[req_ext]
subjectAltName = @alt_names
[alt_names]
DNS.1   = $1
DNS.2   = www.$1
EOF
