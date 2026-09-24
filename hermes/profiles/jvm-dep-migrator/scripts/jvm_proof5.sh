#!/bin/bash
# kotoba source-checkout CLI (bin/kotoba) descendant trace — check if clojure spawns JVM
OUT=/tmp/jvm-proof5.txt
: > "$OUT"
/usr/bin/env -u JAVA_HOME /usr/bin/python3 - <<'PYEOF' >> "$OUT" 2>&1
import subprocess, time, os
def descendants(pid):
    out = subprocess.run(['pgrep', '-lP', str(pid)], capture_output=True, text=True).stdout
    res = []
    for line in out.splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2:
            res.append((parts[0], parts[1].strip()))
    return res

p = subprocess.Popen(
    ['~/github/com-junkawasaki/orgs/kotoba-lang/kotoba/bin/kotoba',
     'compile', '/tmp/q9probe3/thread-frag-entry.kotoba', '--target', 'wasm',
     '--output', '/tmp/thread-frag-k4.wasm'],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
seen = {}
for _ in range(300):
    frontier = [p.pid]
    all_desc = {}
    visited = set()
    while frontier:
        cur = frontier.pop()
        if cur in visited: continue
        visited.add(cur)
        for pid, name in descendants(cur):
            all_desc[pid] = name
            frontier.append(pid)
    for pid, name in all_desc.items():
        seen[pid] = name
    if p.poll() is not None and not all_desc:
        break
    time.sleep(0.1)
p.wait()
print("kotoba exit:", p.returncode)
for pid, name in sorted(seen.items()):
    base = os.path.basename(name.split()[0])
    tag = "JVM!" if base in ('java', 'javac') else ""
    print(f"  {pid} {name[:80]} {tag}")
jvm = [n for n in seen.values() if os.path.basename(n.split()[0]) in ('java','javac')]
print("JVM among descendants:", jvm or "NONE")
PYEOF
echo DONE >> "$OUT"
