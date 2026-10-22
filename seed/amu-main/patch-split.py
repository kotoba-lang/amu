#!/usr/bin/env python3
"""seed/amu-main/patch-split.py <split-dir> -- BOOTSTRAP-TOOL (python3, a text edit of a COPY of the seed's split source).
(agent CMD, 2026-10-04; seed/CONTRACT-REQUESTS.md 2026-10-04 CMD -> FOLD)

amu.compile calls `seed.main/drv-compile-file src out`: the seed driver's compile of src into the kseed file out, with the
flags of argv (--policy, --source-path, ..), status 0 / 1 (refusal printed) / 2 (usage), and WITHOUT the seed's own ok line
on stdout (amu prints stage-0's). Until the seed's 90-drv carries that function, this script adds it to the copy of the
split that an amu build links in:
  (defn drv-compile-file [src :string out :string] :i64 (drv-run src 1 out))   right after drv-run, and
  `drv-compile-file` added to seed.main's (:export [main]) clause, and
  drv-cok (the seed's ok line) made silent in that copy (seed.main's own `main` is linked into amu images but never called).
No-op (prints "patch-split: native") when seed/split/seed/main.kotoba already defines a public drv-compile-file.
"""
import os, re, sys

p = os.path.join(sys.argv[1], 'seed', 'main.kotoba')
s = open(p).read()
if re.search(r'^\(defn drv-compile-file ', s, re.M):
    # REBUILD 2026-10-04 (rung r6l): drv-compile-file is quiet (MM-QUIET) on the single-module route only; the project
    # route's pj-read -> pj-reset zeroes the header cells 0..255, MM-QUIET (37) included, so `amu compile --source-path`
    # printed the seed's ok line before amu's (usage-parity case 25). Until the seed keeps it (CONTRACT-REQUESTS
    # 2026-10-04 REBUILD -> SEEDLANG), the copy's pj-read carries MM-QUIET across the reset. No-op when already kept.
    q = os.path.join(sys.argv[1], 'seed', 'proj.kotoba')
    t = open(q).read()
    old = ('(defn pj-read [M :vector-i64 S :string] :vector-i64\n'
           '  (let [M1 (mem-set (pj-reset M) MM-SRC-LEN (string-length S))\n')
    if old in t:
        t = t.replace(old, '(defn pj-read [M :vector-i64 S :string] :vector-i64\n'
                           '  (let [q (vector-at M 37)   ; MM-QUIET of seed.main (amu-main patch-split.py)\n'
                           '        M1 (mem-set (mem-set (pj-reset M) 37 q) MM-SRC-LEN (string-length S))\n', 1)
        open(q, 'w').write(t)
        print('patch-split: native (seed.main defines drv-compile-file; pj-read keeps MM-QUIET)')
    else:
        print('patch-split: native (seed.main defines drv-compile-file)')
    sys.exit(0)
m = re.search(r'^\(defn- drv-run \[path :string mode :i64 out :string\] :i64\n.*\n', s, re.M)
if not m:
    sys.exit('patch-split: drv-run not found in ' + p)
add = (';; amu-main interim (patch-split.py, CMD 2026-10-04): compile into the kseed file out, no ok line\n'
       '(defn drv-compile-file [src :string out :string] :i64 (drv-run src 1 out))\n')
s = s[:m.end()] + add + s[m.end():]
c = re.search(r'^\(defn- drv-cok \[out :string n :i64\] :i64\n(.*\n)(.*\n)', s, re.M)
if not c or not c.group(2).strip() == '0))':
    sys.exit('patch-split: drv-cok not in the expected shape in ' + p)
s = s[:c.start(1)] + '  (let [w 0]\n' + s[c.start(2):]
if '(:export [main]))' not in s:
    sys.exit('patch-split: seed.main export clause not in the expected shape in ' + p)
s = s.replace('(:export [main]))', '(:export [main drv-compile-file]))', 1)
open(p, 'w').write(s)
print('patch-split: patched (drv-compile-file added, drv-cok silent)')
