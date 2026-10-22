#!/usr/bin/env python3
"""seed/tests/kir/merge/gen-ri-doc.py <out> <lines> [seed] [--unknown] -- canonical EDN corpus for ri_doc.cljk (agent KIR4,
BOOTSTRAP-TOOL: test input only). Profiles are maps with keyword keys in text order; trust maps hold sets of 64-hex strings
(canonical order = text order for equal lengths). --unknown also uses :os keywords the guest never spells (the seed traps
there: a keyword whose text no program keyword spells has no seed value)."""
import random
import sys

out, n = sys.argv[1], int(sys.argv[2])
rnd = random.Random(int(sys.argv[3]) if len(sys.argv) > 3 and not sys.argv[3].startswith('-') else 5)
unknown = '--unknown' in sys.argv
KNOWN = [':linux', ':macos', ':windows']
OTHER = [':plan9', ':freebsd'] if unknown else []


def hexs():
    return ''.join(rnd.choice('0123456789abcdef') for _ in range(64))


def edn_str(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'


def profile():
    m = {}
    r = rnd.random()
    if r < 0.7:
        m[':os'] = rnd.choice(KNOWN + OTHER)
    elif r < 0.8:
        m[':os'] = edn_str('linux')
    elif r < 0.9:
        m[':os'] = str(rnd.randint(-5, 5))
    for k in rnd.sample([':execution', ':isa', ':abi', ':a/b'], rnd.randint(0, 3)):
        m[k] = rnd.choice([':native', ':aarch64', 'nil', 'true', '[1 2]', edn_str('x y')])
    return '{' + ' '.join('%s %s' % (k, m[k]) for k in sorted(m)) + '}'


def hset(xs):
    return '#{' + ' '.join(edn_str(x) for x in sorted(set(xs))) + '}'


lines = []
pool = [hexs() for _ in range(40)]
while len(lines) < n:
    if rnd.random() < 0.5:
        lines.append('l' + profile())
    else:
        ident = rnd.choice(pool)
        m = {}
        if rnd.random() < 0.8:
            m[':trusted-runtime-sha256'] = hset(rnd.sample(pool, rnd.randint(0, 6)) + ([ident] if rnd.random() < 0.4 else []))
        if rnd.random() < 0.5:
            m[':revoked-runtime-sha256'] = hset(rnd.sample(pool, rnd.randint(0, 3)) + ([ident] if rnd.random() < 0.2 else []))
        if rnd.random() < 0.1:
            m[':trusted-runtime-sha256'] = '[' + edn_str(ident) + ']'
        lines.append('t' + '{' + ' '.join('%s %s' % (k, m[k]) for k in sorted(m)) + '}' + '\t' + ident)
open(out, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
