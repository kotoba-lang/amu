#!/bin/bash
# v2: fix iostat parse; 8x30s load1 samples only
out=/tmp/amufalsify_probe_20260906.txt
: > "$out"
for i in 1 2 3 4 5 6 7 8; do
  l1=$(/usr/sbin/sysctl -n vm.loadavg | /usr/bin/awk '{print $2}')
  /usr/sbin/iostat -c 2 > /tmp/amuf_iostat_$i.txt 2>&1
  echo "sample $i load1=$l1 $(/bin/date '+%H:%M:%S')" >> "$out"
  /bin/sleep 30
done
echo DONE >> "$out"
