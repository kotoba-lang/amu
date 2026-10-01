#!/usr/bin/env python3
"""Rewrite a reach list so each file points at the newest worktree that owns it.

A reach list (map-reach.py) names the file the classpath resolved at the time:
a ~/.gitlibs checkout or an older wt-<letter>-<repo> worktree. The classpath the
checker uses (make-classpath.py) lets the LATEST letter win, so a list that still
names the gitlib copy or a stale wt-A- copy measures a file the checker never
reads for that module -- e.g. kotoba-io-* showed 'referred name Reader is not
exported' on gitlib sources while wt-G-kotoba-io-* is green.

Usage: remap-reach.py <reach-list> [wt-root=/private/tmp]  > remapped-list
BOOTSTRAP-REFERENCE tooling (dev measurement only)."""
import os, re, sys
src = sys.argv[1]
root = sys.argv[2] if len(sys.argv) > 2 else '/private/tmp'
newest = {}
for d in sorted(os.listdir(root)):
    m = re.match(r'wt-[A-Z]-(.+)$', d)
    if m: newest[m.group(1)] = os.path.join(root, d)      # later letters win
def candidates(path, base):
    yield os.path.join(base, path)
    if path.endswith('.cljc'):
        yield os.path.join(base, path[:-5] + '.cljk')
out = []
for line in open(src).read().split('\n'):
    l = line.strip()
    if not l: continue
    m = (re.match(r'.*/io\.github\.kotoba-lang/([^/]+)/[0-9a-f]{40}/(.*)$', l)
         or re.match(re.escape(root) + r'/wt-[A-Z]-([^/]+)/(.*)$', l))
    if m and m.group(1) in newest and m.group(1) != 'amu-measure':
        for c in candidates(m.group(2), newest[m.group(1)]):
            if os.path.exists(c):
                l = c
                break
    out.append(l)
print('\n'.join(out))
