#!/usr/bin/env python3
"""Write the harness classpath: `clojure -Spath` of this repo, with every gitlib checkout
replaced by a local worktree named <WT_ROOT>/wt-<letter>-<repo> when one exists.
Usage: make-classpath.py <amu-root> <out-file> [wt-root=/private/tmp]"""
import os, re, subprocess, sys
amu, out = sys.argv[1], sys.argv[2]
root = sys.argv[3] if len(sys.argv) > 3 else '/private/tmp'
cp = subprocess.run(['clojure', '-Spath'], cwd=amu, capture_output=True, text=True, check=True).stdout.strip().split(':')
wt = {}
for d in sorted(os.listdir(root)):
    m = re.match(r'wt-[A-Z]-(.+)$', d)
    if m: wt[m.group(1)] = os.path.join(root, d)   # later letters win
res = []
for e in cp:
    m = re.search(r'/io\.github\.kotoba-lang/([^/]+)/[0-9a-f]{40}(/.*)?$', e)
    if m and m.group(1) in wt: e = wt[m.group(1)] + (m.group(2) or '')
    res.append(e)
open(out, 'w').write(':'.join(res))
print(len(res), 'entries;', sum('/wt-' in e for e in res), 'from worktrees')
