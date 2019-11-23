#!/bin/bash

if [[ $# -ne 2 ]]
then
	echo "usage: <user> <host>"
	exit
fi

user=$1
host=$2
ssh ${user}@${host} 'sysbench --test=cpu --num-threads=$(grep -c ^processor /proc/cpuinfo) --cpu-max-prime=20000 run 2>/dev/null |grep "events per second"|rev|cut -d" " -f 1|rev'

