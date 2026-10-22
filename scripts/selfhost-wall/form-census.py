#!/usr/bin/env python3
"""Form-tree census of Clojure/Kotoba sources (measurement tool, BOOTSTRAP-TOOL; docs/selfhost-memory-plan-20261002.md).

  form-census.py [--edn OUT] <file.cljk | @list.txt>...   (env PREFER=:kotoba,:default picks reader-conditional branches)

Reads each file the way the Kotoba route sees it (reader conditionals take the
:kotoba branch, else :default; metadata dropped; reader macros become lists),
builds kotoba.form-shaped trees (tags: nil bool int string keyword symbol seq
vec set map f64) and counts:
  nodes          every node of every tree
  leaves         leaf nodes
  dleaves        distinct leaves (tag, value)
  leafshare      nodes after sharing leaves only = interior + distinct leaves
  hashcons       distinct subtrees (structural)
Optionally writes the trees as plain EDN (--edn OUT) for a guest to re-read.
"""
import sys, re, json, collections

class R:
    def __init__(s, t): s.t, s.i, s.n = t, 0, len(t)

DELIM = set('()[]{}"; \t\r\n,\\^`~@')

def skip(r):
    t = r.t
    while r.i < r.n:
        c = t[r.i]
        if c in ' \t\r\n,': r.i += 1
        elif c == ';':
            j = t.find('\n', r.i); r.i = r.n if j < 0 else j + 1
        elif t.startswith('#!', r.i):
            j = t.find('\n', r.i); r.i = r.n if j < 0 else j + 1
        else: break

SKIP = object()

def read(r):
    """one form or SKIP (a discarded / empty conditional), None at EOF"""
    skip(r)
    if r.i >= r.n: return None
    t = r.t; c = t[r.i]
    if c in '([{':
        close = {'(': ')', '[': ']', '{': '}'}[c]; r.i += 1
        kids = read_until(r, close)
        return ({'(': 'seq', '[': 'vec', '{': 'map'}[c], kids)
    if c in ')]}': raise ValueError('unexpected %s at %d' % (c, r.i))
    if c == '"':
        j = r.i + 1
        while t[j] != '"':
            j += 2 if t[j] == '\\' else 1
        s = t[r.i+1:j]; r.i = j + 1
        return ('string', s)
    if c == '\\':
        m = re.compile(r'\\(newline|space|tab|return|backspace|formfeed|u[0-9a-fA-F]{4}|o[0-7]{1,3}|.)').match(t, r.i)
        r.i = m.end(); return ('int', 'char:' + m.group(1))
    if c == "'":
        r.i += 1; return ('seq', [('symbol', 'quote'), read_one(r)])
    if c == '`':
        r.i += 1; return ('seq', [('symbol', 'syntax-quote'), read_one(r)])
    if c == '~':
        if t.startswith('~@', r.i): r.i += 2; return ('seq', [('symbol', 'unquote-splicing'), read_one(r)])
        r.i += 1; return ('seq', [('symbol', 'unquote'), read_one(r)])
    if c == '@':
        r.i += 1; return ('seq', [('symbol', 'deref'), read_one(r)])
    if c == '^':
        r.i += 1; read_one(r); return read(r)  # metadata dropped (Form has no meta slot)
    if c == '#':
        d = t[r.i+1] if r.i + 1 < r.n else ''
        if d == '{': r.i += 2; return ('set', read_until(r, '}'))
        if d == '(': r.i += 2; return ('seq', [('symbol', 'fn*')] + [('vec', [])] + [('seq', read_until(r, ')'))])
        if d == '"':
            j = r.i + 2
            while t[j] != '"': j += 2 if t[j] == '\\' else 1
            s = t[r.i+2:j]; r.i = j + 1; return ('string', s)
        if d == "'": r.i += 2; return ('seq', [('symbol', 'var'), read_one(r)])
        if d == '_': r.i += 2; read_one(r); return SKIP
        if d == '?':
            splice = t.startswith('#?@', r.i)
            r.i += 3 if splice else 2
            skip(r)
            assert t[r.i] == '('; r.i += 1
            kids = read_until(r, ')')
            pick = None
            for want in PREFER:
                for k in range(0, len(kids) - 1, 2):
                    if kids[k] == ('keyword', want): pick = kids[k+1]; break
                if pick is not None: break
            if pick is None: return SKIP
            if splice: return ('splice', pick[1])
            return pick
        if d == '#':  # ##Inf etc
            r.i += 2; tok = token(r); return ('f64', tok)
        if d == ':':  # namespaced map #:ns{...}
            r.i += 2; token(r); return read(r)
        # tagged literal #inst "..." -> keep the value
        r.i += 1; token(r); return read_one(r)
    tok = token(r)
    if tok == 'nil': return ('nil', None)
    if tok in ('true', 'false'): return ('bool', tok)
    if tok.startswith(':'): return ('keyword', tok)
    if re.match(r'^[+-]?\d', tok):
        if re.match(r'^[+-]?\d+N?$', tok) or re.match(r'^[+-]?0x[0-9a-fA-F]+$', tok): return ('int', tok)
        return ('f64', tok)
    return ('symbol', tok)

def token(r):
    j = r.i
    while j < r.n and (r.t[j] not in DELIM or (j == r.i)):
        if r.t[j] in DELIM and j != r.i: break
        j += 1
        if j < r.n and r.t[j] in DELIM: break
    tok = r.t[r.i:j]; r.i = j; return tok

def read_one(r):
    while True:
        x = read(r)
        if x is not SKIP: return x

def read_until(r, close):
    kids = []
    while True:
        skip(r)
        if r.i >= r.n: raise ValueError('eof in coll')
        if r.t[r.i] == close: r.i += 1; return kids
        x = read(r)
        if x is SKIP: continue
        if x[0] == 'splice': kids.extend(x[1]); continue
        kids.append(x)

def read_all(text):
    r = R(text); out = []
    while True:
        x = read(r)
        if x is None: return out
        if x is SKIP: continue
        if x[0] == 'splice': out.extend(x[1]); continue
        out.append(x)

import os
PREFER = tuple(os.environ.get('PREFER', ':kotoba,:default').split(','))
LEAF = {'nil', 'bool', 'int', 'string', 'keyword', 'symbol', 'f64'}

class Census:
    def __init__(s):
        s.table = {}       # structural key -> id  (hash-consing)
        s.leafset = set()
        s.nodes = s.leaves = s.interior = s.kid_items = 0
    def walk(s, f):
        s.nodes += 1
        tag = f[0]
        if tag in LEAF:
            s.leaves += 1; key = (tag, f[1]); s.leafset.add(key)
        else:
            s.interior += 1; s.kid_items += len(f[1])
            key = (tag, tuple(s.walk(k) for k in f[1]))
        i = s.table.get(key)
        if i is None: i = len(s.table); s.table[key] = i
        return i

def edn(f, out):
    tag, v = f
    if tag == 'nil': out.append('nil')
    elif tag == 'bool': out.append(v)
    elif tag == 'int':
        out.append(v if re.match(r'^-?\d+$', v) and abs(int(v)) < 2**53 else '0')
    elif tag == 'f64': out.append('0')
    elif tag == 'string': out.append('"' + re.sub(r'[^ -~]', '?', v.replace('\\', '').replace('"', '')) + '"')
    elif tag == 'keyword':
        k = re.sub(r'[^A-Za-z0-9*+!_?<>=/.:-]', '_', v)
        out.append(k if len(k) > 1 and k != ':/' and not k.startswith('::/') else ':k')
    elif tag == 'symbol':
        sym = re.sub(r'[^A-Za-z0-9*+!_?<>=/.$&%-]', '_', v)
        out.append(sym if sym and not sym[0].isdigit() and sym not in ('nil', 'true', 'false') else 's_')
    else:
        o, c = {'seq': ('(', ')'), 'vec': ('[', ']'), 'map': ('{', '}'), 'set': ('#{', '}')}[tag]
        out.append(o)
        for i, k in enumerate(v):
            if i: out.append(' ')
            edn(k, out)
        out.append(c)

def main():
    args = sys.argv[1:]
    edn_out = None
    if args and args[0] == '--edn': edn_out = args[1]; args = args[2:]
    files = []
    for a in args:
        if a.startswith('@'): files += [l.strip() for l in open(a[1:]) if l.strip()]
        else: files.append(a)
    glob = Census(); rows = []; tops = collections.Counter(); per_file_forms = []
    efh = open(edn_out, 'w') if edn_out else None
    for p in files:
        text = open(p, encoding='utf-8', errors='replace').read()
        try: forms = read_all(text)
        except Exception as e:
            print('READFAIL', p, e, file=sys.stderr); continue
        c = Census()
        for f in forms:
            c.walk(f); top = glob.walk(f)
            if f[0] == 'seq' and f[1] and f[1][0][0] == 'symbol' and f[1][0][1] in ('defn', 'defn-', 'def', 'def-'):
                tops[top] += 1
            if efh:
                o = []; edn(f, o); efh.write(''.join(o) + '\n')
        rows.append(dict(file=p, bytes=len(text.encode()), forms=len(forms), nodes=c.nodes, leaves=c.leaves,
                         interior=c.interior, kid_items=c.kid_items, dleaves=len(c.leafset),
                         leafshare=c.interior + len(c.leafset), hashcons=len(c.table)))
    tot = {k: sum(r[k] for r in rows) for k in ('bytes', 'forms', 'nodes', 'leaves', 'interior', 'kid_items', 'dleaves', 'leafshare', 'hashcons')}
    tot['global_dleaves'] = len(glob.leafset)
    tot['global_leafshare'] = glob.interior + len(glob.leafset)
    tot['global_hashcons'] = len(glob.table)
    tot['files'] = len(rows)
    tot['top_defs'] = sum(tops.values()); tot['top_defs_distinct'] = len(tops)
    print(json.dumps(dict(total=tot, files=rows)))

if __name__ == '__main__':
    main()
