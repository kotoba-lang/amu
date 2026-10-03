#!/usr/bin/env python3
"""seed/split/gen-split.py [--check] -- the rung R5 proof: the seed's own source split into namespaces (owner R5A).
BOOTSTRAP-TOOL (python3), a pure text transformation like scripts/seed/gen-ns.sh; it runs nothing.

Input: seed/MANIFEST (the unity order). Output: seed/split/seed/<name>.kotoba, one namespace per MANIFEST module
(01-mem -> seed.mem, ..., 60-proj -> seed.proj) and the entry seed.main = 90-drv + 99-entry + `main`. Each namespace:
  (ns seed.<name> (:require [seed.<dep> :refer [f g ..]] ..))   -- the functions of EARLIER modules it spells
  the contract constants (00-ns) it spells, and the (def ..) forms of earlier modules it spells (a def is not an import
  in the reference, design 2.1: each namespace carries the constants it uses)
  the module text, with (defn- f ..) turned into (defn f ..) for every f a later namespace refers to (its interface; a
  library without an :export clause exports its public defns, ADR 0353 floor 1).
Build: seed compile seed/split/seed/main.kotoba --source-path seed/split --unpinned --output X (60-proj, per-module compile
against interfaces + image link). --check: regenerate into memory and fail when the committed files differ.
"""
import os, re, sys
R = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(R, 'seed', 'split', 'seed')
NAMES = {'01-mem': 'mem', '02-io': 'io', '10-lex': 'lex', '11-read': 'read', '12-kirread': 'kirread', '20-names': 'names',
         '21-check': 'check', '30-lower': 'lower', '40-a64enc': 'enc', '41-a64gen': 'gen', '42-layout': 'layout',
         '50-out': 'out', '60-proj': 'proj'}

def manifest():
    out = []
    for line in open(os.path.join(R, 'seed', 'MANIFEST')):
        line = line.strip()
        if line and not line.startswith('#'):
            out.append(line.split()[0])
    return out

def strip(text):
    """the text without comments, strings and character data (symbols only)"""
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c == ';':
            j = text.find('\n', i); i = n if j < 0 else j
        elif c == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == '\\' else 1
            i = j + 1; out.append(' ')
        else:
            out.append(c); i += 1
    return ''.join(out)

SYM = re.compile(r"[A-Za-z0-9*+!_?<>=/.&-]+")
def symbols(text):
    s = set()
    for m in SYM.finditer(strip(text)):
        t = m.group(0)
        if m.start() > 0 and text and strip(text)[m.start() - 1] == ':':
            continue
        s.add(t)
    return s

def symbols_fast(text):
    st = strip(text)
    s = set()
    for m in SYM.finditer(st):
        if m.start() > 0 and st[m.start() - 1] == ':':
            continue
        s.add(m.group(0))
    return s

HEAD = re.compile(r'\((defn-|defn|def)\s+([^\s()\[\]]+)')

def top_forms(text):
    """(kind, name, start, end) of each top-level (defn|defn-|def NAME ..) form"""
    res = []
    depth, i, n, start = 0, 0, len(text), -1
    while i < n:
        c = text[i]
        if c == ';':
            j = text.find('\n', i); i = n if j < 0 else j; continue
        if c == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == '\\' else 1
            i = j + 1; continue
        if c in '([{':
            if depth == 0: start = i
            depth += 1
        elif c in ')]}':
            depth -= 1
            if depth == 0:
                m = HEAD.match(text, start)
                if m: res.append((m.group(1), m.group(2), start, i + 1))
        i += 1
    return res

def main():
    check = '--check' in sys.argv
    files = manifest()
    ns_text = open(os.path.join(R, files[0])).read()
    consts = {}
    for m in re.finditer(r'^\(def ([A-Z][A-Z0-9-]*) (-?\d+)\)$', ns_text, re.M):
        consts[m.group(1)] = m.group(0)
    mods = []   # (key, nsname, text, forms)
    for f in files[1:]:
        key = os.path.basename(f)[:-len('.kotoba')]
        if key in ('90-drv', '99-entry'):
            continue
        mods.append((key, 'seed.' + NAMES[key], open(os.path.join(R, f)).read()))
    root_text = open(os.path.join(R, 'seed', '90-drv.kotoba')).read() + '\n' + open(os.path.join(R, 'seed', '99-entry.kotoba')).read() \
        + '\n(defn main [] :i64 (seed-main))\n'
    mods.append(('main', 'seed.main', root_text))
    info = []
    for key, ns, text in mods:
        forms = top_forms(text)
        info.append({'key': key, 'ns': ns, 'text': text, 'forms': forms, 'uses': symbols_fast(text),
                     'fns': {nm for k, nm, a, b in forms if k != 'def'}, 'defs': {nm: text[a:b] for k, nm, a, b in forms if k == 'def'}})
    # who refers to what
    public = [set() for _ in info]
    refers = [dict() for _ in info]   # i -> {j: [names]}
    copied = [list() for _ in info]
    for i, mi in enumerate(info):
        for j in range(i):
            mj = info[j]
            used = sorted(mi['uses'] & mj['fns'] - mi['fns'])
            if used:
                refers[i][j] = used; public[j].update(used)
            for d in sorted(mi['uses'] & set(mj['defs']) - mi['fns'] - set(mi['defs'])):
                copied[i].append(mj['defs'][d])
    outs = {}
    for i, mi in enumerate(info):
        req = ''.join('\n  (:require [%s :refer [%s]])' % (info[j]['ns'], ' '.join(names)) for j, names in sorted(refers[i].items()))
        exp = '\n  (:export [main])' if mi['key'] == 'main' else ''
        cs = '\n'.join(consts[c] for c in sorted(mi['uses'] & set(consts), key=lambda c: list(consts).index(c)))
        text = mi['text']
        def pub(m):
            return '(defn %s' % m.group(1) if m.group(1) in public[i] else m.group(0)
        text = re.sub(r'^\(defn- ([^\s()\[\]]+)', pub, text, flags=re.M)
        # a record's identity keyword is :<ns>/<Name>: the unity's ns is `seed`
        text = text.replace(':seed/', ':%s/' % mi['ns'])
        body = ('(ns %s%s%s)\n\n;; GENERATED by seed/split/gen-split.py from seed/MANIFEST (rung R5 proof); edit the modules, not this file.\n'
                ';; contract constants used here (seed/00-ns.kotoba)\n%s\n' % (mi['ns'], req, exp, cs))
        if copied[i]:
            body += ';; defs of earlier modules used here (a def is not importable)\n' + '\n'.join(copied[i]) + '\n'
        body += '\n' + text
        outs[os.path.join(OUT, mi['ns'].split('.', 1)[1] + '.kotoba')] = body
    bad = 0
    if check:
        for p, b in outs.items():
            if not os.path.exists(p) or open(p).read() != b:
                print('gen-split: %s differs' % os.path.relpath(p, R)); bad = 1
        sys.exit(bad)
    os.makedirs(OUT, exist_ok=True)
    for p, b in outs.items():
        open(p, 'w').write(b)
    print('gen-split: %d namespaces -> %s (%d refers, %d public functions)' % (len(outs), os.path.relpath(OUT, R),
          sum(len(v) for r in refers for v in r.values()), sum(len(p) for p in public)))

main()
