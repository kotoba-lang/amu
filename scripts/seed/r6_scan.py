#!/usr/bin/env python3
"""scripts/seed/r6_scan.py -- helper of r6-scan.sh (agent R6A, 2026-10-03). BOOTSTRAP-TOOL (python, host only: it prepares
inputs and summarises outputs; every verdict is the seed's own).

  r6_scan.py farm <list> <dir>     copy the modules of <list> (one source path per line, /private/tmp/reach-minimal.txt) into
                                   <dir>/src at their namespace paths (one root, so the seed's 16-root limit is not in the way)
                                   and print "<ns> <path-in-farm>" per module in a dependency-first order (post-order DFS
                                   over the Kotoba reading of each ns form, sorted roots), then "EDGE a b" lines on stderr
  r6_scan.py hist <tsv> [order]    the first-refusal histogram of a scan table (r6-scan.tsv); with order.txt, what each blocks
"""
import os, re, shutil, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'selfhost-wall'))


def resolve_conditionals(s):
    # same selection as the seed's 10-lex (and reach-minimal.py): the first clause whose feature is :kotoba or :default
    out, i, n = [], 0, len(s)
    while i < n:
        if s.startswith('#?', i) and i + 2 < n and (s[i + 2] == '(' or s[i + 2:i + 4] == '@('):
            at = s[i + 2] == '@'
            j = i + 3 if at else i + 2
            end = scan_in(s, j)
            inner = s[j + 1:end - 1]
            forms, k = [], 0
            while k < len(inner):
                if inner[k] in ' \t\r\n,': k += 1; continue
                if inner[k] == ';':
                    while k < len(inner) and inner[k] != '\n': k += 1
                    continue
                if inner[k] in '([{':
                    m = scan_in(inner, k)
                else:
                    m = k
                    while m < len(inner) and inner[m] not in ' \t\r\n,([{': m += 1
                forms.append(inner[k:m]); k = m
            pick = None
            for q in range(0, len(forms) - 1, 2):
                if forms[q] in (':kotoba', ':default'): pick = forms[q + 1]; break
            if pick is not None:
                out.append(resolve_conditionals(pick[1:-1] if at and pick[:1] in '[(' else pick))
            i = end
        else:
            out.append(s[i]); i += 1
    return ''.join(out)


def scan_in(s, j):
    depth, k, instr, n = 0, j, False, len(s)
    while k < n:
        c = s[k]
        if instr:
            if c == '\\': k += 1
            elif c == '"': instr = False
        elif c == '"': instr = True
        elif c == ';':
            while k < n and s[k] != '\n': k += 1
        elif c == '\\': k += 1
        elif c in '([{': depth += 1
        elif c in ')]}':
            depth -= 1
            if depth == 0: return k + 1
        k += 1
    return n


def ns_form(s):
    m0 = re.search(r'^\(ns\s', s, re.M)
    if not m0: return '', ''
    i = m0.start()
    end = scan_in(s, i)
    t = resolve_conditionals(s[i:end])
    m = re.match(r'\(ns\s+([^\s()\[\]{}]+)', t)
    return (m.group(1) if m else ''), t


def requires(t):
    out = []
    for m in re.finditer(r'\(:require\b', t):
        body = t[m.start():scan_in(t, m.start())]
        out += re.findall(r'\[\s*([a-zA-Z][\w.\-]*)(?=[\s\]])', body)
    return out


def farm(lst, d):
    paths = [l.strip() for l in open(lst) if l.strip()]
    src = os.path.join(d, 'src')
    if os.path.isdir(src): shutil.rmtree(src)
    mods = {}
    for p in paths:
        s = open(p, encoding='utf-8', errors='replace').read()
        nm, t = ns_form(s)
        if not nm:
            print('r6_scan: no ns form in %s' % p, file=sys.stderr); continue
        ext = '.kotoba' if p.endswith('.kotoba') else ('.cljk' if p.endswith('.cljk') else '.cljc')
        rel = nm.replace('.', '/').replace('-', '_') + ext
        dst = os.path.join(src, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(p, dst)
        mods[nm] = (dst, [r for r in requires(t)], p)
    order, state = [], {}

    def visit(m):
        state[m] = 1
        for r in mods[m][1]:
            if r in mods and r not in state: visit(r)
        state[m] = 2
        order.append(m)
    for m in sorted(mods):
        if m not in state: visit(m)
    for m in order:
        print('%s %s %s' % (m, mods[m][0], ' '.join(r for r in mods[m][1] if r in mods) or '-'))
    for m in order:
        for r in mods[m][1]:
            if r not in mods: print('EXTERNAL %s %s' % (m, r), file=sys.stderr)


def hist(tsv, order=None):
    """The first-refusal histogram of a scan table; with the farm's order.txt also, per refused module, how many modules it
    blocks (its transitive importers among the 126), which ranks the refusals by what fixing them would let the scan reach."""
    import re as _re
    from collections import Counter, defaultdict
    rows = [l.rstrip('\n').split('\t') for l in open(tsv) if l.strip() and not l.startswith('#')]
    st = Counter(r[1] for r in rows)
    print('modules %d: %s' % (len(rows), ', '.join('%s %d' % kv for kv in sorted(st.items()))))
    importers = defaultdict(set)
    if order:
        for l in open(order):
            f = l.split()
            for d in (f[2:] if f[2:] != ['-'] else []): importers[d].add(f[0])
    def blocked(m):
        seen, todo = set(), [m]
        while todo:
            x = todo.pop()
            for y in importers[x]:
                if y not in seen: seen.add(y); todo.append(y)
        return seen
    norm = lambda t: _re.sub(r' \(byte -?\d+\)$', '', t)
    key = defaultdict(list)
    for r in rows:
        if r[1] in ('REFUSED', 'TRAP'): key[(r[3], norm(r[4])[:100])].append(r[0])
    print('first refusals (count, code, text, modules; "blocks" = modules that import it directly or not):')
    for (code, txt), ms in sorted(key.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        b = set().union(*[blocked(m) for m in ms]) if order else set()
        print('%4d  %s  %s  [%s]%s' % (len(ms), code, txt, ' '.join(ms), ('  blocks %d' % len(b)) if order else ''))
    c2 = Counter(r[3] for r in rows if r[1] in ('REFUSED', 'TRAP'))
    print('by code: ' + ', '.join('%s %d' % kv for kv in sorted(c2.items(), key=lambda kv: -kv[1])))
    if order:
        ref = [r[0] for r in rows if r[1] in ('REFUSED', 'TRAP')]
        rank = sorted(((len(blocked(m)), m) for m in ref), reverse=True)
        print('refused modules by modules blocked: ' + ', '.join('%s %d' % (m, n) for n, m in rank[:15]))


if __name__ == '__main__':
    if sys.argv[1] == 'farm': farm(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == 'hist': hist(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
