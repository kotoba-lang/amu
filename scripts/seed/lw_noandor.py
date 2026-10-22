#!/usr/bin/env python3
"""scripts/seed/lw_noandor.py <in.kotoba> -- BOOTSTRAP-TOOL (test-only, owner 30-lower).

Prints the file with every (and ..) (or ..) (not ..) rewritten into `if` over true/false, comments dropped.
Reason: the stable stage-0 (build/native-image/amu-native, 2026-10-02 00:24) answers 'internal compiler error'
on ANY and/or/not (seed/CONTRACT-REQUESTS.md, 41-a64gen line). lw-gate.sh uses this only to build its TEST
binary while that stage-0 is in use; the seed sources themselves are never rewritten.
  (and a)       -> a            (and a b ..) -> (if a (and b ..) false)
  (or a)        -> a            (or a b ..)  -> (if a true (or b ..))
  (not a)       -> (if a false true)
With --put, every `vector-assoc!` becomes `lwg-put` (define it once: lw-gate.sh does), the stage-0 linearity
workaround of seed/CONTRACT-REQUESTS.md (30-lower line), for modules not yet written that way.
"""
import sys

def lex(s):
    toks, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if c in ' \t\r\n,':
            i += 1
        elif c == ';':
            while i < n and s[i] != '\n':
                i += 1
        elif c in '()[]{}':
            toks.append(c); i += 1
        elif c == '"':
            j = i + 1
            while s[j] != '"':
                j += 2 if s[j] == '\\' else 1
            toks.append(s[i:j + 1]); i = j + 1
        else:
            j = i
            while j < n and s[j] not in ' \t\r\n,;()[]{}"':
                j += 1
            toks.append(s[i:j]); i = j
    return toks

def parse(toks, i):
    t = toks[i]
    if t in '([{':
        close = {'(': ')', '[': ']', '{': '}'}[t]
        items, i = [], i + 1
        while toks[i] != close:
            x, i = parse(toks, i)
            items.append(x)
        return (t, items), i + 1
    return t, i + 1

def rw(x):
    if isinstance(x, str):
        return x
    br, items = x
    items = [rw(y) for y in items]
    if br == '(' and items and isinstance(items[0], str):
        h, a = items[0], items[1:]
        if h == 'and' and a:
            return a[0] if len(a) == 1 else ('(', ['if', a[0], rw(('(', ['and'] + a[1:])), 'false'])
        if h == 'or' and a:
            return a[0] if len(a) == 1 else ('(', ['if', a[0], 'true', rw(('(', ['or'] + a[1:]))])
        if h == 'not' and len(a) == 1:
            return ('(', ['if', a[0], 'false', 'true'])
    return (br, items)

def show(x):
    if isinstance(x, str):
        return x
    br, items = x
    return br + ' '.join(show(y) for y in items) + {'(': ')', '[': ']', '{': '}'}[br]

put = '--put' in sys.argv
toks = lex(open(sys.argv[1]).read())
if put:  # route every direct vector-assoc! through one trivially linear writer (see CONTRACT-REQUESTS 30-lower)
    toks = ['lwg-put' if t == 'vector-assoc!' else t for t in toks]
i, out = 0, []
while i < len(toks):
    x, i = parse(toks, i)
    out.append(show(rw(x)))
print('\n'.join(out))
