#!/bin/bash

if [[ $# -lt 3 ]]
then
	echo "usage: <project> <user> <host> [name] [start] [end]"
	exit
fi

project_name="$(echo "$1"|rev|cut -d'/' -f1|rev)"
folder_path="$(echo "$1"|rev|cut -d'/' -f2-|rev)"

# Make the path absolute if it isn't 
if [[ $(echo $folder_path|cut -c1) != "/" ]]
then
  folder_path=$(realpath $folder_path)
fi

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

ssh ${user}@${host} 'mkdir ~/Scrivania/olive-share'

# reverse mount the local folder to olive-share on remote host (FS push)
dpipe /usr/lib/ssh/sftp-server = ssh ${user}@${host} sshfs :\"${folder_path}\" ~/Scrivania/olive-share -o slave,auto_cache,reconnect,no_readahead &

# because the previous call is asyncronous, make sure the remote filesystem is mounted before proceeding
ssh ${user}@${host} 'while [[ $(mount|grep olive) == "" ]]; do sleep 1; done'

# Olive export
ssh ${user}@${host} "export DISPLAY=:0 && cd ~/Scrivania/olive-share && olive-editor ${project_name} -e $export_name $export_start $export_end &>/dev/null"

# Move output to shared folder and umount the share
# ssh ${user}@${host} "mv ~/"$export_name".mp4 ~/Scrivania/olive-share"

ssh ${user}@${host} "umount ~/Scrivania/olive-share"
sleep 1
