#!/usr/bin/env python3
"""scripts/seed/selfbuild.py -- the analysis half of scripts/seed/selfbuild.sh (agent SELF, 2026-10-04). BOOTSTRAP-TOOL
(python, host only: it summarises verdicts; every verdict is the seed's or stage-0's own).

  selfbuild.py report <W>        W = the selfbuild work dir: W/r6/r6-scan.tsv + W/r6/order.txt (r6-scan.sh), W/s0/s0.tsv
                                 (stage-0 check per farm file: file, verdict, source, line), W/link/images.tsv (optional)
  selfbuild.py tops <W>          the OK modules no other OK module requires (the link probe's requires), one per line
  selfbuild.py count <W> ns..    "<modules> <lines>" of the union of the closures of ns

Milestone (f) asks: does the seed build the big amu image from source? The image is the 138-module loader-faithful reach
set (scripts/seed/reach-twins.py over docs/selfhost-minimal-reach-20261002.md's roots) linked behind an amu entry. This
report says how far the seed gets and ranks what blocks it.

WALLS. A wall is a module where a refusal is located: every module the seed refuses (it was attempted, so all its requires
compiled), plus every module at which stage-0's own check of a still-BLOCKED module stops (stage-0 checks the whole
closure, so its :source names the module that refuses). A wall is
  SEED    stage-0 accepts the module, the seed refuses it  -> seed work (21-check / 30-lower / 60-proj ...)
  SOURCE  stage-0 refuses the module itself as well         -> source work (port the module), whatever the seed does
A module is ATTEMPTABLE when no wall is in its require closure (itself included). The ranking is greedy: at each step the
wall whose fix makes the most modules attemptable (ties: the wall named by most not-yet-attemptable modules). The counts are
UPPER BOUNDS on what the scan would reach: a module behind a fixed wall may still be refused for its own reason (the seed
has not seen it yet); stage-0 OK on a BLOCKED module is not a seed verdict.
"""
import os, re, sys
from collections import defaultdict

ENTRIES = [('check', 'kotoba.compiler.nbb.check-cli'), ('compile', 'kotoba.compiler.nbb.aarch64-cli'),
           ('refactor', 'kotoba.compiler.nbb.refactor-cli')]


def load(W):
    rows = [l.rstrip('\n').split('\t') for l in open(os.path.join(W, 'r6', 'r6-scan.tsv')) if l.strip() and not l.startswith('#')]
    st = {r[0]: r for r in rows}
    deps, path = {}, {}
    for l in open(os.path.join(W, 'r6', 'order.txt')):
        f = l.split()
        deps[f[0]] = [d for d in f[2:] if d != '-']
        path[f[0]] = f[1]
    s0 = {}
    p = os.path.join(W, 's0', 's0.tsv')
    if os.path.exists(p):
        byfile = {path[m]: m for m in path}
        for l in open(p):
            f = l.rstrip('\n').split('\t')
            if len(f) >= 2 and f[0] in byfile:
                s0[byfile[f[0]]] = (f[1], f[2] if len(f) > 2 else '-', f[3] if len(f) > 3 else '-')
    return st, deps, path, s0


def closure(m, deps):
    seen, todo = {m}, [m]
    while todo:
        x = todo.pop()
        for d in deps.get(x, []):
            if d not in seen: seen.add(d); todo.append(d)
    return seen


def src_module(m, s0src, deps, path):
    """the module of a stage-0 :source file name inside m's closure (stage-0 prints a basename or a full path)"""
    if s0src in ('-', ''): return m
    base = os.path.basename(s0src)
    cands = [x for x in closure(m, deps) if os.path.basename(path[x]) == base]
    if len(cands) == 1: return cands[0]
    if m in cands: return m
    return cands[0] if cands else m


def walls(st, deps, path, s0):
    w = {}
    for m, r in st.items():
        if r[1] in ('REFUSED', 'TRAP'):
            v = s0.get(m)
            # a template module checked on its own needs an instantiation for stage-0 too; stage-0 admits it through its
            # importers (they are stage-0 OK), so the wall is the seed's (separate mode has no instantiation, E2105)
            tmpl = bool(v) and v[0].startswith('template module')
            kind = 'SOURCE' if (v and v[0] != 'OK' and not tmpl and src_module(m, v[1], deps, path) == m) else 'SEED'
            w[m] = dict(kind=kind, seed='%s %s' % (r[3], re.sub(r' \(byte -?\d+\)$', '', r[4])),
                        s0=(v[0] if v else '?'))
    for m, r in st.items():
        v = s0.get(m)
        if r[1] == 'BLOCKED' and v and v[0] != 'OK':
            sm = src_module(m, v[1], deps, path)
            if sm not in w:
                w[sm] = dict(kind='SOURCE', seed='(blocked: not attempted by the seed)', s0=v[0])
    return w


def kotoba_main(p):
    """does the Kotoba reading of the entry file define and export an arity-0 main? (text check over the :kotoba arms)"""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from r6_scan import resolve_conditionals
    t = resolve_conditionals(open(p, encoding='utf-8', errors='replace').read())
    has = re.search(r'\(defn\s+main\s+\[\s*\]', t) is not None
    exp = re.search(r':kotoba/export\s+\[[^\]]*\bmain\b', t) is not None
    top = [x for x in re.findall(r'^\((\S+)', t, re.M) if x not in ('ns', 'defn', 'defn-', 'def', 'defrecord', 'comment')]
    return has, exp, top


def report(W):
    st, deps, path, s0 = load(W)
    mods = list(st)
    n = len(mods)
    cnt = defaultdict(int)
    for r in st.values(): cnt[r[1]] += 1
    lines = {m: int(st[m][2]) for m in mods}
    okl = sum(lines[m] for m in mods if st[m][1] == 'OK')
    print('# selfbuild report (scripts/seed/selfbuild.py)')
    print('modules %d (%d lines): seed OK %d (%d lines, %.1f%%), REFUSED %d, TRAP %d, BLOCKED %d'
          % (n, sum(lines.values()), cnt['OK'], okl, 100.0 * okl / max(1, sum(lines.values())), cnt['REFUSED'], cnt['TRAP'], cnt['BLOCKED']))
    if s0:
        s0ok = sum(1 for m in mods if m in s0 and s0[m][0] == 'OK')
        both = sum(1 for m in mods if st[m][1] == 'OK' and s0.get(m, ('?',))[0] == 'OK')
        print('stage-0 check (BOOTSTRAP-REFERENCE, same farm): OK %d of %d; seed OK and stage-0 OK %d; seed OK, stage-0 refuses %d'
              % (s0ok, len(s0), both, sum(1 for m in mods if st[m][1] == 'OK' and s0.get(m, ('OK',))[0] != 'OK')))
        s0w = defaultdict(list)
        for m in mods:
            v = s0.get(m)
            if v and v[0] != 'OK' and not v[0].startswith('template module'):
                s0w[src_module(m, v[1], deps, path)].append(m)
        print('stage-0 refuses %d modules (templates checked alone excluded) at %d source walls: %s'
              % (sum(len(x) for x in s0w.values()), len(s0w),
                 ', '.join('%s %d' % (w, len(x)) for w, x in sorted(s0w.items(), key=lambda kv: -len(kv[1])))))
    W0 = walls(st, deps, path, s0)
    cl = {m: closure(m, deps) for m in mods}

    def attemptable(F):
        return {m for m in mods if not any((x in W0 and x not in F) for x in cl[m])}
    F, cur = set(), attemptable(set())
    print('\n## walls ranked by modules made attemptable (greedy, cumulative; upper bounds)')
    print('step\twall\tkind\t+mods\tcum\tseed verdict\tstage-0 verdict')
    step = 0
    while len(F) < len(W0):
        best = None
        for w in W0:
            if w in F: continue
            gain = len(attemptable(F | {w})) - len(cur)
            named = sum(1 for m in mods if w in cl[m] and m not in cur)
            key = (gain, named, w)
            if best is None or key > best[0]: best = (key, w)
        w = best[1]; F.add(w); new = attemptable(F); step += 1
        print('%d\t%s\t%s\t%d\t%d\t%s\t%s' % (step, w, W0[w]['kind'], len(new) - len(cur), len(new),
                                            W0[w]['seed'][:90], W0[w]['s0'][:90]))
        cur = new
    print('\nwalls: %d (%d SEED = stage-0 accepts, %d SOURCE = stage-0 refuses too)'
          % (len(W0), sum(1 for w in W0.values() if w['kind'] == 'SEED'), sum(1 for w in W0.values() if w['kind'] == 'SOURCE')))
    print('\n## entries (the amu commands of the image)')
    print('command\tentry\tclosure\tseed OK\twalls in closure (= the smallest next set; SEED/SOURCE)\tKotoba main')
    for cmd, e in ENTRIES:
        if e not in st: print('%s\t%s\tnot in the reach list' % (cmd, e)); continue
        c = cl[e]; ws = sorted(x for x in c if x in W0)
        has, exp, top = kotoba_main(path[e])
        mn = 'defn main + export' if (has and exp) else ('defn main, not exported' if has else 'NO main')
        if top: mn += '; top-level forms ' + ','.join(sorted(set(top)))
        print('%s\t%s\t%d\t%d\t%d: %s\t%s' % (cmd, e, len(c), sum(1 for x in c if st[x][1] == 'OK'), len(ws),
                                            ' '.join('%s/%s' % (x, W0[x]['kind'][:2]) for x in ws), mn))
    allw = sorted(W0)
    print('image (all %d modules)\twalls %d' % (n, len(allw)))
    p = os.path.join(W, 'link', 'images.tsv')
    if os.path.exists(p):
        print('\n## link (the seed links the OK modules into packaged images)')
        print(open(p).read().rstrip())


def tops(W):
    st, deps, _, _ = load(W)
    ok = [m for m in st if st[m][1] == 'OK']
    req = {d for m in ok for d in deps[m]}
    for m in ok:
        if m not in req: print(m)


def count(W, ns):
    """modules and source lines in the union of the closures of ns (the modules a probe image links)"""
    st, deps, _, _ = load(W)
    u = set()
    for m in ns: u |= closure(m, deps)
    print('%d %d' % (len(u), sum(int(st[m][2]) for m in u)))


if __name__ == '__main__':
    if sys.argv[1] == 'count':
        count(sys.argv[2], sys.argv[3:])
    else:
        {'report': report, 'tops': tops}[sys.argv[1]](sys.argv[2])
