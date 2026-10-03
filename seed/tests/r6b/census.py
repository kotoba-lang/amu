#!/usr/bin/env python3
"""seed/tests/r6b/census.py <r6-scan dir> [ns ...] -- call heads the R6 modules spell (Kotoba reading: #?( selects :kotoba,
then :default) that are not seed heads, not defined in the module, and not qualified. BOOTSTRAP-TOOL (agent R6B), for
ranking source-route features only; the verdict is always the seed's own r6-scan."""
import re, sys, collections, os
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

def heads():
    s = set()
    src = open(os.path.join(REPO, 'scripts/seed/gen-names-tables.py')).read()
    s |= set(re.findall(r'\("([^"]+)", "HD-', src))
    lib = open(os.path.join(REPO, 'seed/tests/r6b/srclib/r6b-lib.kotoba')).read()
    s |= set(re.findall(r'^\(defn- ([^\s\[]+)', lib, re.M))
    return s | {'->', '->>', 'cond->', 'as->', 'not=', 'vector-i64'}

class R:
    def __init__(s, t): s.t, s.i = t, 0
    def ws(s):
        t = s.t
        while s.i < len(t):
            c = t[s.i]
            if c in ' \t\r\n,': s.i += 1
            elif c == ';':
                while s.i < len(t) and t[s.i] != '\n': s.i += 1
            else: break
    def form(s):
        s.ws(); t = s.t
        if s.i >= len(t): return None
        c = t[s.i]
        if c in '([{':
            s.i += 1; close = {'(': ')', '[': ']', '{': '}'}[c]; items = []
            while True:
                s.ws()
                if s.i >= len(t): break
                if t[s.i] == close: s.i += 1; break
                x = s.form()
                if x is not None and x != '__skip__': items.extend(x if isinstance(x, tuple) and x and x[0] == '__splice__' and False else [x])
            return (c, items)
        if c == '"':
            j = s.i + 1
            while t[j] != '"': j += 2 if t[j] == '\\' else 1
            s.i = j + 1; return ('str',)
        if c == '#':
            n = t[s.i + 1]
            if n == '?':
                splice = t[s.i + 2] == '@'; s.i += 3 if splice else 2
                _, items = s.form()
                pick = None
                for k in range(0, len(items) - 1, 2):
                    if items[k] in (':kotoba', ':default') and pick is None: pick = items[k + 1]
                return '__skip__' if pick is None else pick
            if n == '{': s.i += 1; f = s.form(); return ('{', f[1])
            if n == '_': s.i += 2; s.form(); return '__skip__'
            if n == '"': s.i += 1; s.form(); return ('str',)
            s.i += 1; return s.form()
        if c in "'`~@^":
            s.i += 1
            if c == '^': s.form(); return '__skip__' if False else s.form()
            return s.form()
        if c == '\\': s.i += 2
        j = s.i
        while j < len(t) and t[j] not in ' \t\r\n,()[]{}";': j += 1
        tok = t[s.i:j]; s.i = j; return tok

def walk(f, out, defs):
    if isinstance(f, tuple) and f and f[0] in '([{':
        items = [x for x in f[1] if x != '__skip__']
        if f[0] == '(' and items and isinstance(items[0], str):
            out.append(items[0])
            if items[0] in ('defn', 'defn-', 'def', 'defrecord', 'defhandler') and len(items) > 1 and isinstance(items[1], str): defs.add(items[1])
        for x in items: walk(x, out, defs)

def main():
    d = sys.argv[1]; only = set(sys.argv[2:])
    hs = heads(); tot = collections.Counter(); mods = collections.defaultdict(set)
    for line in open(os.path.join(d, 'order.txt')):
        ns, path = line.split()[:2]
        if only and ns not in only: continue
        r = R(open(path).read()); out = []; defs = set()
        while True:
            f = r.form()
            if f is None: break
            walk(f, out, defs)
        for h in out:
            if h in hs or h in defs or '/' in h or h.startswith('.') or h.startswith(':'): continue
            tot[h] += 1; mods[h].add(ns)
    for h, c in sorted(tot.items(), key=lambda x: -len(mods[x[0]])):
        print(len(mods[h]), c, h, ' '.join(sorted(mods[h]))[:150])
main()
