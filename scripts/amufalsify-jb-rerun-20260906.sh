#!/bin/sh
# J-B idle>=9/10 gate + measured run of jb_imod_control.c (amu-falsify 2026-09-06, rev2)
OUT=/tmp/amufalsify_jb.txt
: > "$OUT"
date >> "$OUT"
idle=0
i=0
while [ $i -lt 10 ]; do
  l=$(sysctl -n vm.loadavg | cut -d' ' -f3 | cut -d. -f1)
  echo "sample $i load1_int=$l" >> "$OUT"
  if [ "$l" -lt 7 ] 2>/dev/null; then idle=$((idle+1)); fi
  sleep 55
  i=$((i+1))
done
echo "idle samples: $idle / 10" >> "$OUT"
if [ $idle -ge 9 ]; then
  echo "GATE PASS - running bench" >> "$OUT"
  cc -O2 -o /tmp/jb_imod_control bench/runtime-comparison/jb_imod_control.c >> "$OUT" 2>&1
  /tmp/jb_imod_control 200000 60 >> "$OUT" 2>&1
  echo "BENCH DONE" >> "$OUT"
else
  echo "GATE FAIL - no bench run (host not idle>=9/10)" >> "$OUT"
fi
date >> "$OUT"