#!/bin/bash

if [[ $# -ne 2 ]]
then
	echo "usage: <user> <host>"
	exit
fi

user=$1
host=$2
# ssh ${user}@${host} 'sysbench --test=cpu --num-threads=$(grep -c ^processor /proc/cpuinfo) --cpu-max-prime=20000 run 2>/dev/null |grep "events per second"|rev|cut -d" " -f 1|rev'

# a better benchmark?
scp "bench/sample.mp4" ${user}@${host}:
scp "bench/sample.ove" ${user}@${host}:
t=$(ssh ${user}@${host} 'export DISPLAY=:0 && (time -p olive-editor sample.ove -e) |& grep real | cut -d" " -f2 | tr "," "."')
ssh ${user}@${host} 'rm "sample.mp4"; rm "sample.ove"; rm "sample.ove.mp4"'

score=$(echo "scale=8; (1 / $t) * 1000000" | bc)
echo $score
