#!/bin/bash
# kotoba CLI deeper descendant trace (kotoba launcher is a bash/clj wrapper? check)
OUT=/tmp/jvm-proof4.txt
: > "$OUT"
/usr/bin/head -15 ~/github/com-junkawasaki/orgs/kotoba-lang/kotoba/bin/kotoba >> "$OUT"
echo "== full descendant walk at $(date) ==" >> "$OUT"
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
     '--output', '/tmp/thread-frag-k3.wasm'],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
all_desc = {}
for _ in range(60):
    for pid, name in descendants(p.pid):
        all_desc[pid] = name
        for pid2, name2 in descendants(pid):
            all_desc[pid2] = name2
    if p.poll() is not None:
        break
    time.sleep(0.1)
p.wait()
print("kotoba exit:", p.returncode)
for pid, name in sorted(all_desc.items()):
    base = os.path.basename(name.split()[0])
    tag = "JVM!" if base in ('java', 'javac', 'clojure', 'clj') else ""
    print(f"  {pid} {name} {tag}")
jvm = [n for n in all_desc.values() if os.path.basename(n.split()[0]) in ('java','javac','clojure','clj')]
print("JVM among descendants:", jvm or "NONE")
PYEOF
echo DONE >> "$OUT"
