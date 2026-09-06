#!/bin/bash
# amu-falsify sustained-window probe: 8 x 30s samples
for i in $(seq 1 8); do
  L=$(uptime | sed -E 's/.*load averages: ([0-9.]+).*/\1/')
  IDLE=$(iostat -c 2 disk0 2>/dev/null | tail -1 | awk '{nf=NF; s=$(NF-3); print s}')
  echo "$(date '+%H:%M:%S') load1=$L idle=$IDLE"
  [ "$i" -lt 8 ] && sleep 30
done
