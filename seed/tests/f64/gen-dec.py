#!/usr/bin/env python3
"""seed/tests/f64/gen-dec.py [--check] -- the KIR-route dec group of seed/12-kirread.kotoba (kr-dec-text0..4, agent F64,
2026-10-04) generated from 21-check's R6D source prelude (ck-r6b-t-dec0..4): the decimal-f64-parse defns and their
helpers, renamed __r6d- -> __krd_ (decimal-f64-parse -> __krd_parse), `defn-` -> `defn`, the __r6-as casts dropped and
:f64 -> :i64 (KIR5: a float is its bit pattern in an i64). decimal-f64x3-parse and its helpers are left out.
Without --check: prints the Kotoba text. With --check: exit 0 iff 12-kirread holds exactly that text."""
import os, re, sys
R = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
KEEP = ['take', 'norm', 'small', 'muladd', 'shl', 'bitlen', 'mulpow10', 'len', 'cmpz', 'subin', 'shr1in', 'quotin',
        'sn', 'sd', 'exp', 'round', 'f64', 'value', 'dig?', 'digs', 'acc', 'p10', 'int', 'cp']

def unas(s):
    out = ''; i = 0
    while True:
        j = s.find('(__r6-as ', i)
        if j < 0: return out + s[i:]
        out += s[i:j]; k = j + len('(__r6-as ')
        k += re.match(r'(\S+) ', s[k:]).end()
        d = 0; st = k
        while True:
            c = s[k]
            if c in '([': d += 1
            elif c in ')]':
                if d == 0: break
                d -= 1
            elif c == ' ' and d == 0: break
            k += 1
        out += unas(s[st:k]); i = k + 1

def defns():
    src = open(os.path.join(R, 'seed/21-check.kotoba')).read()
    lits = []
    for k in range(5):
        m = re.search(r'\(defn- ck-r6b-t-dec%d \[\] :string\n(.*?)\n\(defn- ' % k, src, re.S)
        lits += re.findall(r'"((?:[^"\\]|\\.)*)"', m.group(1))
    by = {}
    for l in lits:
        m = re.match(r'\(defn- (?:__r6d-(\S+)|(decimal-f64-parse)) ', l)
        if m: by[m.group(1) or 'parse'] = l
    out = []
    for name in KEEP + ['parse']:
        d = unas(by[name].replace('\\n', ''))
        d = (d.replace('(defn- decimal-f64-parse ', '(defn __krd_parse ').replace('(defn- __r6d-', '(defn __krd_')
              .replace('__r6d-', '__krd_').replace('[:option :f64]', '[:option :i64]'))
        assert '__r6' not in d and ':f64' not in d and '"' not in d, d
        out.append(d)
    return out

def text():
    L = defns(); chunks = [L[i:i + 5] for i in range(0, len(L), 5)]; out = []
    for ci, ch in enumerate(chunks):
        expr = '"%s\\n"' % ch[-1]
        for d in reversed(ch[:-1]): expr = '(string-concat "%s\\n"\n    %s)' % (d, expr)
        out.append('(defn- kr-dec-text%d [] :string\n  %s)' % (ci, expr))
    names = ['(kr-dec-text%d)' % i for i in range(len(chunks))]
    e = names[-1]
    for n in reversed(names[:-1]): e = '(string-concat %s %s)' % (n, e)
    out.append('(defn- kr-dec-text [] :string %s)' % e)
    return '\n'.join(out) + '\n', len(L)

if __name__ == '__main__':
    t, n = text()
    if '--check' in sys.argv:
        kr = open(os.path.join(R, 'seed/12-kirread.kotoba')).read()
        ok = t in kr and ('(def kr-ndec %d)' % n) in kr and ('(def kr-dj-f64parse %d)' % (131 + n - 1)) in kr
        print('gen-dec: %s (%d defns)' % ('OK' if ok else 'DIFFERS', n)); sys.exit(0 if ok else 1)
    sys.stdout.write(t)
