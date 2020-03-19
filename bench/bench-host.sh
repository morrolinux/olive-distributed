#!/bin/bash

sysbench --test=cpu --num-threads=$(grep -c ^processor /proc/cpuinfo) --cpu-max-prime=20000 run 2>/dev/null |grep "events per second"|rev|cut -d" " -f 1|rev
# echo 100
exit

# a better benchmark?
# t=$( (time -p olive-editor bench/sample.ove -e) |& grep real | cut -d" " -f2 | tr "," ".")


score=$(echo "scale=8; (1 / $t) * 1000000" | bc)
echo $score
