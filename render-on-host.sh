#!/bin/bash

if [[ $# -ne 3 ]]
then
	echo "usage: <project folder> <user> <host>"
	exit
fi

folder=$1
archive=${folder}.tar
project=${folder}.ove
user=$2
host=$3

tar cf ${archive} ${folder}
scp ${archive} ${user}@${host}:
ssh ${user}@${host} 'tar xf '${archive}
ssh ${user}@${host} 'rm '${archive}
ssh ${user}@${host} 'export DISPLAY=:0 && olive-editor '${folder}'/*.ove -e &>/dev/null' &
