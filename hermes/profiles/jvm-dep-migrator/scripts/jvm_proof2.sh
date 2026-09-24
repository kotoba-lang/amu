#!/bin/bash
# Precise JVM-child proof: run amu check and sample all descendant processes,
# checking none is a JVM. amu is a node shim; its child should be node (nbb).
OUT=/tmp/jvm-proof2.txt
: > "$OUT"
echo "== descendants of amu check run at $(date) ==" >> "$OUT"
/usr/bin/env -u JAVA_HOME /usr/bin/python3 - <<'PYEOF' >> "$OUT" 2>&1
import subprocess, time, os, signal
p = subprocess.Popen(
    ['~/github/com-junkawasaki/orgs/kotoba-lang/amu/bin/amu',
     'check', '--jvm-free', '/tmp/q9probe3/thread-frag-entry.kotoba'],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
descendants = set()
for _ in range(12):
    out = subprocess.run(['pgrep', '-lP', str(p.pid)], capture_output=True, text=True).stdout
    for line in out.splitlines():
        pid, name = line.split(None, 1)
        descendants.add((pid, name.strip()))
    if p.poll() is not None:
        break
    time.sleep(0.1)
p.wait()
print("amu exit:", p.returncode)
print("descendants (pid name):")
for pid, name in sorted(descendants):
    print(" ", pid, name)
jvm = [n for _, n in descendants if n in ('java', 'javac', 'clojure', 'clj')]
print("JVM processes among descendants:", jvm or "NONE")
PYEOF
echo DONE >> "$OUT"
