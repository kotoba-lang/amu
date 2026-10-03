#!/usr/bin/env python3
"""scripts/seed/front_census.py -- attribute the native analyze's arena handles to KIR functions (agent ARENA, 2026-10-04).
BOOTSTRAP-TOOL (python3), diagnostic only; MEM2's method (docs/selfhost-analyze-memory-20261003.md section 2) as a script.

  front_census.py mark <in.kir> <out.kir>
      insert an exported zero-arity marker function __mkN (body 0) before every function of a KIR program, so that the
      compiled container's export table gives every function's start offset (marker offset + the marker's code length).
  front_census.py report <marked.kir> <marked.kseed> <census-path> [top]
      read KEXE_ARENA_CENSUS=<census-path> output (<path> vectors, <path>.pairs), map each site (a return address into the
      guest code) to its function, and print per function: SELF (innermost guest frame) and INCLUSIVE (any of the 8 recorded
      frames, once per handle) counts for pairs and vectors, with the head of the function's KIR body to recognise it.
"""
import collections
import re
import sys


def top_level_maps(s, start):
    """yield (begin, end) of the top-level {...} items of the vector that opens at s[start] == '['"""
    i = start + 1
    depth = 0
    begin = None
    n = len(s)
    while i < n:
        c = s[i]
        if c == '"':
            i += 1
            while s[i] != '"':
                if s[i] == '\\':
                    i += 1
                i += 1
        elif c == '\\':          # a character literal like \a or \{
            i += 1
        elif c in '{[(':
            if depth == 0 and c == '{':
                begin = i
            depth += 1
        elif c in '}])':
            if depth == 0:
                return
            depth -= 1
            if depth == 0 and c == '}':
                yield begin, i + 1
        i += 1


def functions_span(s):
    k = s.index(':functions [')
    return k + len(':functions ')


def mark(src, dst):
    s = open(src).read()
    v = functions_span(s)
    spans = list(top_level_maps(s, v))
    out = []
    last = 0
    names = []
    for j, (b, e) in enumerate(spans):
        out.append(s[last:b])
        if j == 0:      # two adjacent markers: their offset gap is the marker's own code length
            out.append('{:name __mkpre, :params [], :result :i64, :effects #{}, :body 0, :param-types []} ')
            names.append('__mkpre')
        out.append('{:name __mk%d, :params [], :result :i64, :effects #{}, :body 0, :param-types []} ' % j)
        last = b
        names.append('__mk%d' % j)
    out.append(s[last:])
    t = ''.join(out)
    m = re.search(r':exports \[([^\]]*)\]', t)
    t = t[:m.end() - 1] + ' ' + ' '.join(names) + t[m.end() - 1:]
    open(dst, 'w').write(t)
    print('marked %d functions' % len(spans))


def kseed_exports(p):
    b = open(p, 'rb').read(1 << 22)
    head = b.split(b'\n\n', 1)[0].decode()
    lines = head.split('\n')
    ex = {}
    for ln in lines[1:]:
        parts = ln.split()
        if len(parts) >= 2:
            ex[parts[0]] = int(parts[1])
    return ex


def report(kir, kseed, census, top=40):
    s = open(kir).read()
    v = functions_span(s)
    spans = list(top_level_maps(s, v))
    ex = kseed_exports(kseed)
    funcs = []      # (start offset, name, body head)
    mk = None
    for b, e in spans:
        item = s[b:e]
        name = re.match(r'\{:name ([^,]+),', item).group(1)
        if name == '__mkpre':
            continue
        if name.startswith('__mk'):
            mk = ex[name]
            continue
        body = item[item.find(':body ') + 6:]
        funcs.append((mk, name, body[:160].replace('\n', ' ')))
    mlen = ex['__mk0'] - ex['__mkpre']
    starts = sorted((o + mlen, n, h) for o, n, h in funcs)
    offs = [x[0] for x in starts]
    import bisect

    def fn_of(site):
        i = bisect.bisect_right(offs, site - 1) - 1
        return starts[i][1] if i >= 0 else '?'
    heads = {n: h for _, n, h in starts}
    for kind, path in (('pairs', census + '.pairs'), ('vectors', census)):
        self_c = collections.Counter()
        incl = collections.Counter()
        total = 0
        cache = {}
        with open(path) as f:
            for ln in f:
                xs = ln.split()
                if kind == 'vectors':
                    xs = xs[2:]
                sites = [int(x) for x in xs if x != '0']
                total += 1
                if not sites:
                    self_c['<no guest frame>'] += 1
                    continue
                fs = []
                for x in sites:
                    if x not in cache:
                        cache[x] = fn_of(x)
                    fs.append(cache[x])
                self_c[fs[0]] += 1
                for fname in set(fs):
                    incl[fname] += 1
        print('== %s: %d handles; marker length %d B' % (kind, total, mlen))
        print('-- inclusive (any of the 8 innermost guest frames)')
        for fname, c in incl.most_common(top):
            print('%6.2f%% %10d %-28s self %6.2f%%  %s' % (100.0 * c / total, c, fname, 100.0 * self_c[fname] / total,
                                                      heads.get(fname, '')[:110]))


if __name__ == '__main__':
    if sys.argv[1] == 'mark':
        mark(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == 'report':
        report(sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]) if len(sys.argv) > 5 else 40)
    else:
        sys.exit('usage: front_census.py mark|report ...')
