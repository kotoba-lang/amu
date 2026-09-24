#!/bin/bash
# Same descendant proof for the kotoba CLI compile path (public product gate)
OUT=/tmp/jvm-proof3.txt
: > "$OUT"
echo "== descendants of kotoba compile run at $(date) ==" >> "$OUT"
/usr/bin/env -u JAVA_HOME /usr/bin/python3 - <<'PYEOF' >> "$OUT" 2>&1
import subprocess, time
p = subprocess.Popen(
    ['~/github/com-junkawasaki/orgs/kotoba-lang/kotoba/bin/kotoba',
     'compile', '/tmp/q9probe3/thread-frag-entry.kotoba', '--target', 'wasm',
     '--output', '/tmp/thread-frag-k2.wasm'],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
descendants = set()
for _ in range(40):
    out = subprocess.run(['pgrep', '-lP', str(p.pid)], capture_output=True, text=True).stdout
    for line in out.splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2:
            descendants.add((parts[0], parts[1].strip()))
        # walk deeper: children of children
    if p.poll() is not None:
        break
    time.sleep(0.1)
p.wait()
print("kotoba exit:", p.returncode)
print("direct children:")
for pid, name in sorted(descendants):
    print(" ", pid, name)
jvm = [n for _, n in descendants if os.path.basename(n) in ('java', 'javac', 'clojure', 'clj')]
print("JVM among them:", jvm or "NONE")
import os
PYEOF
echo DONE >> "$OUT"
