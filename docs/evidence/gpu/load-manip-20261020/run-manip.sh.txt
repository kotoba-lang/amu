#!/bin/sh
# LOAD-MANIPULATION EXPERIMENT dispatch (JUN-58, tick 20261020-1533, parent
# JUN-55). Implements the PRE-REGISTERED design in analyze-manip.py (rules
# fixed before the first dispatched run; that file's sha256 is recorded in
# the README). Arms: I = natural host load, no induced load (pairs 1-2);
# L = induced CPU load, 12 CPU-burner processes started >=120 s before the
# first L run and killed after the last (pairs 3-4). Blocked order I then L
# (fixed order confounds dose with time drift -- recorded as a confound, not
# claimed away). Cells w64t31 (anchor) / w64t32 (flip cell) at lanes
# 2,095,104; cell order rotated t31,t32 / t32,t31 / t31,t32 / t32,t31.
# Idempotent: a slot whose log exists is skipped. A failed/unverified attempt
# is preserved as attempt<N>-<slot>.log and retried once; a slot failing both
# attempts stays missing (the analyzer reports it -- never silently dropped).
set -e
cd "$(dirname "$0")/../../../.."
EV=docs/evidence/gpu/load-manip-20261020
PROBE=scripts/gpu-subgroup-reduce-chunksweep-pinned-3696ca0d.cljk
mkdir -p "$EV"

# the probe bytes are the chain's or nothing: refuse to run anything else
echo "3696ca0db0e28c5b41fa5c8551df2ae1302deb190e91722408117a06077ef652  $PROBE" | shasum -a 256 -c - >/dev/null

TAB=$(printf '\t')
VERIFIED="RESULT${TAB}verified=true"

run() { # pair cell W chunks
  log="$EV/run-$1-$2.log"
  if [ -f "$log" ]; then echo "skip $log"; return 0; fi
  att=1
  while [ "$att" -le 2 ]; do
    alog="$EV/attempt${att}-run-$1-$2.log"
    echo "run attempt$att -> $log"
    (date; uptime; time kbb --backend sci "$PROBE" "$3" 2095104 "$4") > "$alog" 2>&1 || true
    if grep -q "$VERIFIED" "$alog"; then
      mv "$alog" "$log"
      return 0
    fi
    echo "UNVERIFIED attempt$att run-$1-$2 (preserved as $alog)"
    att=$((att + 1))
  done
  echo "MISSING run-$1-$2 after 2 attempts"
  return 0
}

# ---- ARM I: natural host load (pairs 1-2) ----
echo "ARM-I start $(date)"
date; uptime
run 1 w64t31 64 31
run 1 w64t32 64 32
run 2 w64t32 64 32
run 2 w64t31 64 31

# ---- ARM L: 12 CPU burners, >=120 s before the first L run ----
: > "$EV/burner-pids.txt"
i=1
while [ "$i" -le 12 ]; do
  nohup sh -c 'while :; do :; done' >/dev/null 2>&1 &
  echo $! >> "$EV/burner-pids.txt"
  i=$((i + 1))
done
echo "burners started $(date): $(tr '\n' ' ' < "$EV/burner-pids.txt")"
uptime
sleep 120
echo "burn-in done $(date)"
uptime

run 3 w64t31 64 31
run 3 w64t32 64 32
run 4 w64t32 64 32
run 4 w64t31 64 31

# ---- teardown: kill the burners after the last L run ----
kill $(cat "$EV/burner-pids.txt") 2>/dev/null || true
echo "burners killed $(date)"
uptime
echo "MANIP-SWEEP-COMPLETE"
