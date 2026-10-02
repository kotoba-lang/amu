#!/usr/bin/env python3
"""seed/tests/kir/census.py -- KIR shape census (agent KIR, BOOTSTRAP-TOOL: test harness only, never in a seed's
process tree).

  census.py hist <out.tsv> <file.kir> ...        operation histogram over the bodies of all KIR programs given
  census.py info <file.kir>                      one line: exports with arity 0 and their result type ("name:T ...")
  census.py gaps <hist.tsv> [<big-hist.tsv>]     the ops of a histogram that neither a seed head nor a 12-kirread rewrite
                                                 covers, ranked by programs (then occurrences in the second histogram)

An "operation" is the head symbol of a list in a function :body (`let`, `if`, `+`, `record-get`, `__kotoba_loop_*` is
counted as `<loop-helper>`, a call of a function of the same program as `<call>`), plus one pseudo-op per non-integer
type that occurs in :result/:param-types (`type:[:record ..]` is `type:record`, `type:[:option T]` is `type:option` ..).
The tsv has: op, total occurrences, number of programs using it, the programs (first 6).
"""
import sys
import collections


class Sym(str):
    pass


class Kw(str):
    pass


class Lst(list):
    pass


class Vec(list):
    pass


class SetV(list):
    pass


class MapV(list):
    pass


def read(s):
    i = 0
    n = len(s)

    def ws(i):
        while i < n:
            c = s[i]
            if c in ' \t\r\n,':
                i += 1
            elif c == ';':
                while i < n and s[i] != '\n':
                    i += 1
            else:
                break
        return i

    def item(i):
        i = ws(i)
        c = s[i]
        if c in '([{':
            close = {'(': ')', '[': ']', '{': '}'}[c]
            out = []
            i += 1
            while True:
                i = ws(i)
                if s[i] == close:
                    i += 1
                    break
                v, i = item(i)
                out.append(v)
            return ({'(': Lst, '[': Vec, '{': MapV}[c])(out), i
        if c == '#' and s[i + 1] == '{':
            v, i = item(i + 1)
            return SetV(v), i
        if c == '"':
            j = i + 1
            buf = []
            while s[j] != '"':
                if s[j] == '\\':
                    buf.append(s[j:j + 2])
                    j += 2
                else:
                    buf.append(s[j])
                    j += 1
            return ''.join(buf), j + 1
        if c == '\\':
            j = i + 2
            while j < n and s[j] not in ' \t\r\n,()[]{}':
                j += 1
            return ('char', s[i:j]), j
        j = i
        while j < n and s[j] not in ' \t\r\n,()[]{}"':
            j += 1
        t = s[i:j]
        if t.startswith(':'):
            return Kw(t), j
        try:
            return int(t), j
        except ValueError:
            pass
        try:
            return float(t), j
        except ValueError:
            pass
        return Sym(t), j

    v, _ = item(0)
    return v


def pairs(m):
    return dict(zip(m[0::2], m[1::2]))


def type_name(t):
    if isinstance(t, Kw):
        return t[1:]
    if isinstance(t, Vec) and t and isinstance(t[0], Kw):
        return t[0][1:]
    return str(type(t).__name__)


def program(path):
    prog = pairs(read(open(path, encoding='utf-8').read()))
    fns = [pairs(f) for f in prog.get(Kw(':functions'), [])]
    return prog, fns


def walk(x, names, acc):
    if isinstance(x, Lst):
        if x and isinstance(x[0], Sym):
            h = str(x[0])
            if h.startswith('__kotoba_loop_'):
                op = '<loop-helper>'
            elif h in names:
                op = '<call>'
            else:
                op = h
            acc[op] += 1
            rest = x[1:]
        else:
            acc['<list-head-non-symbol>'] += 1
            rest = x
        for y in rest:
            walk(y, names, acc)
    elif isinstance(x, (Vec, MapV, SetV)):
        if isinstance(x, MapV):
            acc['<map-literal>'] += 1
        elif isinstance(x, SetV):
            acc['<set-literal>'] += 1
        else:
            pass
        for y in x:
            walk(y, names, acc)
    elif isinstance(x, str) and not isinstance(x, (Sym, Kw)):
        acc['<string-literal>'] += 1
    elif isinstance(x, Kw):
        acc['<keyword-literal>'] += 1
    elif isinstance(x, float):
        acc['<float-literal>'] += 1


def census(path):
    prog, fns = program(path)
    names = {str(f.get(Kw(':name'))) for f in fns}
    acc = collections.Counter()
    for f in fns:
        walk(f.get(Kw(':body')), names, acc)
        ts = [f.get(Kw(':result'))] + list(f.get(Kw(':param-types')) or [])
        for t in ts:
            tn = type_name(t)
            if tn not in ('i64',):
                acc['type:' + tn] += 1
        if f.get(Kw(':effects')):
            acc['<fn-effects>'] += 1
        if str(f.get(Kw(':name'))).startswith('__kotoba_loop_'):
            acc['<loop-helper-def>'] += 1
    acc['<format:' + str(prog.get(Kw(':format'))) + '>'] += 1
    if prog.get(Kw(':effects')):
        acc['<program-effects>'] += 1
    return acc


# seed heads (seed/HEADS spellings, R1) and the KIR spellings 12-kirread rewrites into them
SEED_OPS = set('''let loop recur if and or not = < > <= >= + - * quot bit-and bit-or bit-xor bit-not u64-shift-right
i64-shift-left i64-shift-right vector-at vector-conj vector-assoc vector-assoc! vector-alloc string-code-point-at
string-length typed-cap-call bytes-from-vector-i64 string-concat cond vector-i64-from-bytes do when when-not if-not case
condp -> ->> as-> cond-> cond->> dotimes doseq range inc dec zero? pos? neg? not= assert vector-count record-new record
record-get get assoc'''.split())
KIR_REWRITES = set('''vector-new string-byte-length bool-not record-assoc min max <loop-helper> <call> <loop-helper-def>
<string-literal> <keyword-literal> <format::kotoba.kir/v3> <format::kotoba.kir/v4> type:bool type:string
type:vector-i64 type:record type:keyword type:bytes'''.split())


def gaps(paths):
    rows = {}
    for i, path in enumerate(paths):
        for line in open(path).read().splitlines()[1:]:
            op, occ, progs, _ = (line.split('\t') + [''])[:4]
            r = rows.setdefault(op, [0, 0, 0, 0])
            r[2 * i] += int(progs)
            r[2 * i + 1] += int(occ)
    print('op\tcorpus-programs\tcorpus-occurrences\tbig-pieces\tbig-occurrences')
    for op, r in sorted(rows.items(), key=lambda kv: (-kv[1][0], -kv[1][2], -kv[1][3], kv[0])):
        if op in SEED_OPS or op in KIR_REWRITES:
            continue
        print('%s\t%d\t%d\t%d\t%d' % (op, r[0], r[1], r[2], r[3]))


def prog_name(p):
    parts = p.split('/')
    base = parts[-1].rsplit('.', 1)[0]
    return parts[-2] if base == 'p' and len(parts) > 1 else base


def main():
    if sys.argv[1] == 'hist':
        out = sys.argv[2]
        tot = collections.Counter()
        progs = collections.defaultdict(list)
        bad = 0
        for p in sys.argv[3:]:
            try:
                acc = census(p)
            except Exception as e:  # unreadable KIR: reported, not counted
                bad += 1
                print('census: cannot read %s: %s' % (p, e), file=sys.stderr)
                continue
            for k, v in acc.items():
                tot[k] += v
                progs[k].append(prog_name(p))
        with open(out, 'w') as f:
            f.write('op\toccurrences\tprograms\texamples\n')
            for k, v in sorted(tot.items(), key=lambda kv: (-len(progs[kv[0]]), -kv[1], kv[0])):
                f.write('%s\t%d\t%d\t%s\n' % (k, v, len(progs[k]), ' '.join(progs[k][:6])))
        print('census: %d programs, %d unreadable, %d distinct ops' % (len(sys.argv) - 3 - bad, bad, len(tot)))
    elif sys.argv[1] == 'gaps':
        gaps(sys.argv[2:])
    elif sys.argv[1] == 'info':
        prog, fns = program(sys.argv[2])
        ex = {str(e) for e in prog.get(Kw(':exports'), [])}
        out = []
        for f in fns:
            nm = str(f.get(Kw(':name')))
            if nm in ex and not f.get(Kw(':params')):
                out.append('%s:%s' % (nm, type_name(f.get(Kw(':result')))))
        print(' '.join(out))


if __name__ == '__main__':
    main()
