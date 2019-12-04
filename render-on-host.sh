#!/bin/bash

if [[ $# -lt 3 ]]
then
	echo "usage: <project> <user> <host> [name] [start] [end]"
	exit
fi

project_name="$(echo "$1"|rev|cut -d'/' -f1|rev)"
folder_path="$(echo "$1"|rev|cut -d'/' -f2-|rev)"
if [[ $(echo $folder_path|cut -c1) != "/" ]]
then
  folder_path=$(realpath $folder_path)
fi

sudo exportfs *:"$folder_path" -o rw

user=$2
host=$3
export_name=$4

if [[ $"export_name" == "" ]]
then
  export_name=${project_name}".mp4"
fi

if [[ $# -gt 4 ]]
then
	export_start="--export-start $5"
	export_end="--export-end $6"
else
	export_start=""
	export_end=""
fi

server_ip="$(ip -4 addr | grep -oP '(?<=inet\s)\d+(\.\d+){3}'|grep -v 127.0.0.1)"

# Make the nodes mount the NFS share
ssh ${user}@${host} "sudo mount ${server_ip}:${folder_path} ~/olive-share" >/dev/null
# Olive export
ssh ${user}@${host} 'export DISPLAY=:0 && olive-editor ~/olive-share/*.ove -e '$export_name $export_start $export_end'&>/dev/null'
# Move output to shared folder
ssh ${user}@${host} "mv ~/$export_name ~/olive-share"
# Unmount the share
scp ${user}@${host}:"sudo umount ~/olive-share"
