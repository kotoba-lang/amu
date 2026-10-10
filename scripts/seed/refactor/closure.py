#!/usr/bin/env python3
"""scripts/seed/refactor/closure.py <entry> <root>... -- the dependency-first module list (`ns path` per line) of an entry
over source roots, for rf_compile_sep (lib.sh). BOOTSTRAP-TOOL (python3). The loader's resolution rule
(src/kotoba/compiler/project_files.cljk resolve-module-file): within a root `.kotoba` > `.cljk` > `.cljc`; across roots a
single `.kotoba` stands in for any number of `.cljk` / `.cljc`; two candidates otherwise are refused here. Requires are
r6_scan's (the union of both readings' require vectors, as the selfbuild scan): a superset never orders a module late."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from r6_scan import ns_form, requires  # noqa: E402


def main():
    entry, roots = sys.argv[1], sys.argv[2:]

    def resolve(ns):
        rel = ns.replace('.', '/').replace('-', '_')
        c = []
        for r in roots:
            for e in ('.kotoba', '.cljk', '.cljc'):
                p = os.path.join(r, rel + e)
                if os.path.isfile(p):
                    c.append(p)
                    break
        if len(c) == 1:
            return c[0]
        g = [p for p in c if p.endswith('.kotoba')]
        if len(g) == 1:
            return g[0]
        if c:
            sys.exit('closure: ambiguous %s: %s' % (ns, ' '.join(c)))
        return None  # external (not on these roots)

    order, seen = [], set()

    def visit(ns, p):
        seen.add(ns)
        _, t = ns_form(open(p, encoding='utf-8').read())
        for r in requires(t):
            if r not in seen:
                q = resolve(r)
                if q:
                    visit(r, q)
        order.append((ns, p))
    nm, _ = ns_form(open(entry, encoding='utf-8').read())
    visit(nm, entry)
    for ns, p in order:
        print(ns, p)


if __name__ == '__main__':
    main()
