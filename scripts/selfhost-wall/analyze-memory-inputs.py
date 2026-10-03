#!/usr/bin/env python3
"""analyze-memory-inputs.py -- compiler-size single-file inputs for the analyze guest's memory ladder (H-M3/H-M4, agent MEM2,
2026-10-03; docs/selfhost-analyze-memory-20261003.md). BOOTSTRAP-TOOL (python3).

  analyze-memory-inputs.py <repo> <out-dir>

Writes <out-dir>/pfxNN-<module>.kotoba: the seed unity's MANIFEST prefixes 00-ns .. <module> plus a `seed-main` stub (every
module only calls modules listed before it, so each prefix is a closed one-namespace program of real compiler code), and
<out-dir>/unity.kotoba (the whole seed). Three textual rewrites, each meaning-preserving, keep the frontend of the
pre-ADR-0363 lineage (the KIR the guest is built from) analysing to the end instead of refusing early:
  1. vector-assoc! -> vector-assoc   (that frontend refuses linear assoc! through a loop: "requires a linear handle")
  2. -9223372036854775808 -> (- -9223372036854775807 1)   (the guest's reader TRAPS on the i64-min literal: SIGILL,
     a guest finding of its own, see the doc)
  3. (def NAME <int>) constants inlined at their uses   (that frontend refuses a symbolic case constant)
One case line per file is then made by case-line.py (the guest's input format: [:hir "<source>" nil]).
"""
import os, re, sys

repo, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
manifest = [l.split()[0] for l in open(os.path.join(repo, 'seed/MANIFEST')) if l.strip() and not l.startswith('#')]


def rewrite(s):
    s = s.replace('vector-assoc!', 'vector-assoc').replace('-9223372036854775808', '(- -9223372036854775807 1)')
    defs = dict(re.findall(r'^\(def\s+([A-Za-z][A-Za-z0-9\-_?!*]*)\s+(-?\d+)\)', s, re.M))
    if not defs:
        return s
    pat = re.compile(r'(?<![A-Za-z0-9\-_?!*>:/.])(' + '|'.join(sorted(map(re.escape, defs), key=len, reverse=True)) +
                     r')(?![A-Za-z0-9\-_?!*<>/])')
    return '\n'.join(l if re.match(r'^\(def\s', l) or l.lstrip().startswith(';') else pat.sub(lambda m: defs[m.group(1)], l)
                     for l in s.split('\n'))


acc = ''
for i, path in enumerate(manifest):
    mod = os.path.basename(path)[:-len('.kotoba')]
    acc += open(os.path.join(repo, path), encoding='utf-8').read() + '\n'
    if mod in ('90-drv', '99-entry'):
        continue
    open(os.path.join(out, 'pfx%02d-%s.kotoba' % (i + 1, mod)), 'w').write(rewrite(acc + '(defn- seed-main [] :i64 0)\n'))
open(os.path.join(out, 'unity.kotoba'), 'w').write(rewrite(acc))
