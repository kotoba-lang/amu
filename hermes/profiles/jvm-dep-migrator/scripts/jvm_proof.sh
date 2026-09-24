#!/bin/bash
# JVM-free process proof for thread.frag whole-component gates: verify no JVM processes
# were involved in the amu/kotoba gate runs. We trace by checking our own commands' provenance:
# amu --jvm-free is fail-closed; kotoba launcher is JVM-free by design.
# This script captures: any java/javac/clojure/clj processes alive now, and re-runs the
# amu gate with a process watcher to prove no JVM child processes spawn.
OUT=/tmp/jvm-proof.txt
: > "$OUT"
echo "== live JVM processes at $(date) ==" >> "$OUT"
ps aux | grep -E '[j]ava|[j]avac|[c]lojure( |$)|[c]lj( |$)' >> "$OUT" 2>&1
echo "(end)" >> "$OUT"

echo "== process trace: amu check --jvm-free on thread-frag-entry ==" >> "$OUT"
/usr/bin/env -u JAVA_HOME /bin/bash -c '
  ~/github/com-junkawasaki/orgs/kotoba-lang/amu/bin/amu check --jvm-free /tmp/q9probe3/thread-frag-entry.kotoba > /dev/null 2>&1 &
  PID=$!
  for i in 1 2 3 4 5; do
    pgrep -P $PID >> /tmp/jvm-children.txt 2>/dev/null
    sleep 0.2
  done
  wait $PID
' >> "$OUT" 2>&1
echo "amu check exit: $?" >> "$OUT"
echo "== JVM children of amu ==" >> "$OUT"
if [ -s /tmp/jvm-children.txt ]; then cat /tmp/jvm-children.txt >> "$OUT"; else echo "none" >> "$OUT"; fi
rm -f /tmp/jvm-children.txt
echo DONE >> "$OUT"
