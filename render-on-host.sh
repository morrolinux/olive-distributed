#!/bin/bash

if [[ $# -lt 3 ]]
then
	echo "usage: <project folder> <user> <host> [start] [end]"
	exit
fi

folder_path="$1"
folder_name="$(echo $folder_path|rev|cut -d/ -f1|rev)"
archive_path="${folder_path}.tar"
archive_name="${folder_name}.tar"
user=$2
host=$3
if [[ $# -gt 3 ]]
then
	export_start="--export-start $4"
	export_end="--export-end $5"
else
	export_start=""
	export_end=""
fi

cd "${folder_path}/.."
tar cf "$archive_name" "$folder_name" >/dev/null
scp "$archive_name" ${user}@${host}: >/dev/null
rm "$archive_name"
ssh ${user}@${host} 'tar xf '\"${archive_name}\" >/dev/null
ssh ${user}@${host} 'rm '\"$archive_name\" >/dev/null
ssh ${user}@${host} 'export DISPLAY=:0 && olive-editor '\"$folder_name\"'/*.ove -e '$export_start $export_end'&>/dev/null'
scp ${user}@${host}:"\"${folder_name}\""/'*.ove.mp4' . >/dev/null
ssh ${user}@${host} 'rm -rf '\""$folder_name\"" >/dev/null
