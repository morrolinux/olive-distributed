#!/bin/bash

if [[ $# -ne 3 ]]
then
	echo "usage: <project folder> <user> <host>"
	exit
fi

folder_path="$1"
folder_name="$(echo $folder_path|rev|cut -d/ -f1|rev)"
archive_path="${folder_path}.tar"
archive_name="${folder_name}.tar"
user=$2
host=$3

cd "${folder_path}/.."
tar cf "$archive_name" "$folder_name"
scp "$archive_name" ${user}@${host}:
rm "$archive_name"
ssh ${user}@${host} 'tar xf '\"${archive_name}\"
ssh ${user}@${host} 'rm '\"$archive_name\"
ssh ${user}@${host} 'export DISPLAY=:0 && olive-editor '\"$folder_name\"'/*.ove -e &>/dev/null'
scp ${user}@${host}:"\"${folder_name}\""/'*.ove.mp4' .
ssh ${user}@${host} 'rm -rf '\""$folder_name\""
