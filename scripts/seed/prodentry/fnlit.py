#!/usr/bin/env python3
"""scripts/seed/prodentry/fnlit.py FILE [--write] -- rewrite every host `#( .. )` fn literal of FILE as `(fn [..] ..)`
(agent PRODENTRY, 2026-10-05). BOOTSTRAP-TOOL. The seed's reader refuses `#(` (E1005) even inside a non-selected
reader-conditional branch, so a dual-runtime module keeps its host code only with the literal spelled out. `%`/`%1` ->
`p1`, `%2` -> `p2`, ...; a literal whose body already uses the chosen names is refused. Prints each rewrite."""
import re, sys
src = open(sys.argv[1]).read()
out, i, n = [], 0, 0
def match(s, k):  # index of the paren closing the one at s[k]
    d, j, instr = 0, k, False
    while j < len(s):
        c = s[j]
        if instr:
            if c == '\\': j += 1
            elif c == '"': instr = False
        elif c == '"': instr = True
        elif c == ';':
            while j < len(s) and s[j] != '\n': j += 1
        elif c == '(': d += 1
        elif c == ')':
            d -= 1
            if d == 0: return j
        j += 1
    raise SystemExit('unbalanced at %d' % k)
instr = False
while i < len(src):
    c = src[i]
    if instr:
        out.append(c)
        if c == '\\': out.append(src[i+1]); i += 2; continue
        if c == '"': instr = False
        i += 1; continue
    if c == '"': instr = True; out.append(c); i += 1; continue
    if c == ';':
        e = src.find('\n', i); e = len(src) if e < 0 else e
        out.append(src[i:e]); i = e; continue
    if src.startswith('#(', i):
        e = match(src, i + 1)
        body = src[i + 2:e]
        args = sorted(set(re.findall(r'%(\d*)(?![\w-])', re.sub(r'"(\\.|[^"\\])*"', '""', body))), key=lambda a: int(a or 1))
        hi = max([int(a or 1) for a in args], default=0)
        names = ['p%d' % k for k in range(1, hi + 1)]
        for nm in names:
            if re.search(r'(?<![\w-])%s(?![\w-])' % nm, body): raise SystemExit('name clash %s' % nm)
        nb = re.sub(r'%(\d*)(?![\w-])', lambda m: 'p' + (m.group(1) or '1'), body)
        rep = '(fn [%s] (%s))' % (' '.join(names), nb)
        print('%d: #(%s) -> %s' % (src.count('\n', 0, i) + 1, body[:60].replace('\n', ' '), rep[:70].replace('\n', ' ')), file=sys.stderr)
        out.append(rep); i = e + 1; n += 1; continue
    out.append(c); i += 1
if '--write' in sys.argv:
    open(sys.argv[1], 'w').write(''.join(out))
print('%s: %d fn literals' % (sys.argv[1], n), file=sys.stderr)
