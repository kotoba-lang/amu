#!/usr/bin/env python3
"""scripts/seed/reach-twins.py -- the R6 reach list under stage-0's own module resolution (agent TEXT, 2026-10-04).
BOOTSTRAP-TOOL (python, host only; it chooses input files, every verdict is the seed's or stage-0's own).

  reach-twins.py <reach-list> <classpath-file> <amu-root> <kotoba-lang> [--only=ns1,ns2] > list.txt   (summary on stderr)

  --only: apply the loader's rule to these namespaces only (every other entry is kept as listed; the swaps it would make are
          printed as 'would swap'), so one owner's twins can be measured without moving the scan's other modules.

Why: reach-minimal.py takes, per namespace, the FIRST source root that has a file for it. amu's project loader
(src/kotoba/compiler/project_files.cljk, `resolve-module-file`) does not: across roots, exactly one guest-native `.kotoba`
stands in for any number of dual-runtime `.cljk`/`.cljc` twins. stage-0 therefore checks every importer of
`kotoba.lang.text` / `kotoba.lang.coll` / `kotoba.string` against the GUEST twins in kotoba-lang `lang/compat`, while the
R6 scan compiled the HOST `.cljk` libraries (regex literals, #(), host interop; their Kotoba reading has no body), so the
seed and stage-0 were not compiling the same program. This list applies the loader's rule to every entry and closes the
set over the Kotoba reading of the new files' requires (the twins require kotoba.string.join / .split, kotoba.walk, ...).
The roots are the reach generator's: the classpath's /src entries, <amu-root>/src, <kotoba-lang>/lang/compat.
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r6_scan import ns_form, requires  # noqa: E402

EXTS = ('.kotoba', '.cljk', '.cljc')


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    only = [a[7:].split(',') for a in sys.argv[1:] if a.startswith('--only=')]
    only = set(only[0]) if only else None
    lst, cpf, amu, k = args[:4]
    roots = [e for e in open(cpf).read().strip().split(':') if e.endswith('/src')] + [amu + '/src', k + '/lang/compat']

    def candidates(ns):
        rel = ns.replace('.', '/').replace('-', '_')
        out = []
        for r in roots:
            for e in EXTS:
                p = os.path.join(r, rel + e)
                if os.path.isfile(p):
                    out.append(p)
                    break  # within one root the first extension wins (the loader's per-root order)
        return out

    def resolve(ns):
        c = candidates(ns)
        if len(c) == 1:
            return c[0], 'one'
        if not c:
            return None, 'missing'
        g = [p for p in c if p.endswith('.kotoba')]
        if len(g) == 1:
            return g[0], 'twin'
        return None, 'ambiguous'

    paths = [l.strip() for l in open(lst) if l.strip()]
    mods, swapped, notes, would = {}, [], [], []
    todo = []
    for p in paths:
        nm, _ = ns_form(open(p, encoding='utf-8', errors='replace').read())
        if not nm:
            continue
        q, how = resolve(nm)
        if q is None:
            notes.append('%s %s, kept %s' % (nm, how, p)); q = p
        if os.path.realpath(q) != os.path.realpath(p) and only is not None and nm not in only:
            would.append('%s: %s -> %s' % (nm, p, q)); q = p
        if os.path.realpath(q) != os.path.realpath(p):
            swapped.append('%s: %s -> %s' % (nm, p, q))
        mods[nm] = q; todo.append(nm)
    added = []
    while todo:
        m = todo.pop()
        _, t = ns_form(open(mods[m], encoding='utf-8', errors='replace').read())
        for r in requires(t):
            if r in mods:
                continue
            q, how = resolve(r)
            if q is None:
                continue  # unresolvable requires stay EXTERNAL, as in the reach generator
            mods[r] = q; todo.append(r); added.append('%s (required by %s): %s' % (r, m, q))
    for nm in mods:
        print(mods[nm])
    print('reach-twins: %d modules (%d in the input list), %d swapped to the loader\'s choice, %d added by closure'
          % (len(mods), len(paths), len(swapped), len(added)), file=sys.stderr)
    for s in swapped:
        print('  swapped ' + s, file=sys.stderr)
    for s in added:
        print('  added   ' + s, file=sys.stderr)
    for s in would:
        print('  would swap ' + s, file=sys.stderr)
    for s in notes:
        print('  note    ' + s, file=sys.stderr)


if __name__ == '__main__':
    main()
