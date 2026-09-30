#!/usr/bin/env python3
"""Sources reachable from nbb/*_cli.cljk via :require, resolved on the harness classpath.
Usage: reach-list.py <amu-root> <classpath-file> <kotoba-lang-checkout> > list.txt"""
import glob, os, re, sys
amu, cpf, k = sys.argv[1:4]
roots = [e for e in open(cpf).read().split(':') if e.endswith('/src')] + [amu + '/src', k + '/lang/compat']
def find(ns):
    rel = ns.replace('.', '/').replace('-', '_')
    for r in roots:
        for ext in ('.kotoba', '.cljk', '.cljc'):
            p = os.path.join(r, rel + ext)
            if os.path.exists(p): return p
seen, queue = {}, glob.glob(amu + '/src/kotoba/compiler/nbb/*_cli.cljk')
while queue:
    f = queue.pop()
    if f in seen: continue
    seen[f] = 1
    s = open(f, errors='ignore').read()
    m = re.search(r'\(ns\s.*?(?=\n\(def|\n\(ns|\Z)', s, re.S)
    for n in re.findall(r'\[([a-z][\w.\-]*)(?:\s|\])', m.group(0) if m else s[:6000]):
        p = '.' in n and find(n)
        if p and p not in seen: queue.append(p)
print('\n'.join(sorted(seen)))
