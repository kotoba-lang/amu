#!/usr/bin/env python3
"""Rewrite a reach list (one source file per line) so every file that lives in a gitlib
checkout or in a stale worktree is the copy the harness classpath actually serves.

The classpath (make-classpath.py) already substitutes a worktree for each gitlib pin, but a
reach list recorded earlier still names the pinned checkout (or an older wt-<L>-<repo>), so
`check` read the wrong file: e.g. kotoba.io.copy checked as the pinned .cljc, which refers
`Reader` from a kotoba.io.reader whose served copy no longer exports it. This maps each path
to the same relative file under the classpath entry of that repo (trying .cljc -> .cljk),
and drops duplicates.
A module with a guest-route twin under <WALL_K>/lang/compat/<ns path>.kotoba is served by the
twin on the project route (extension priority across roots), so the twin is what is checked.
Usage: [WALL_K=/private/tmp/wt-K-kotoba-lang] map-reach.py <classpath-file> <reach-list> <out-list>"""
import os, re, sys
cp = open(sys.argv[1]).read().split(':')
K = os.environ.get('WALL_K', '/private/tmp/wt-K-kotoba-lang')
out, seen = [], set()
for l in open(sys.argv[2]).read().split():
    m = (re.match(r'.*/io\.github\.kotoba-lang/([^/]+)/[0-9a-f]{40}/(src/.*)$', l)
         or re.match(r'.*/wt-[A-Z]-([^/]+)/(src/.*)$', l))
    if m:
        cands = [e for e in cp if re.search(r'/wt-[A-Z]-' + re.escape(m.group(1)) + r'/src$', e)]
        if cands:
            for rel in (m.group(2), re.sub(r'\.cljc$', '.cljk', m.group(2))):
                p = cands[-1][:-4] + '/' + rel
                if os.path.exists(p):
                    l = p
                    break
    m = re.search(r'/src/(.+)\.clj[kc]$', l)
    if m:
        twin = os.path.join(K, 'lang/compat', m.group(1) + '.kotoba')
        if os.path.exists(twin):
            l = twin
    if l not in seen:
        seen.add(l)
        out.append(l)
open(sys.argv[3], 'w').write('\n'.join(out) + '\n')
print(len(out), 'files;', sum('.gitlibs' in e for e in out), 'still from a gitlib checkout')
