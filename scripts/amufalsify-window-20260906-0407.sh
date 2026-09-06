#!/bin/bash
# amu-falsify 2026-09-06 04:07 JST: 8x30s sustained-window quiet-gate probe
out=/tmp/af_window_0407.txt
: > "$out"
for i in 1 2 3 4 5 6 7 8; do
  ts=$(/bin/date '+%H:%M:%S')
  l1=$(/usr/sbin/sysctl -n vm.loadavg | awk '{print $2}')
  l5=$(/usr/sbin/sysctl -n vm.loadavg | awk '{print $3}')
  l15=$(/usr/sbin/sysctl -n vm.loadavg | awk '{print $4}')
  idle=$(/usr/sbin/iostat -c 2 disk0 | tail -1 | awk '{print $(NF-3)}')
  echo "$ts load1=$l1 load5=$l5 load15=$l15 iostat_idle%=$idle" >> "$out"
  sleep 27
done
echo done >> "$out"
