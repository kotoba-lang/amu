#!/usr/bin/env python3
"""scripts/selfhost-wall/kbd_exports.py -- export signatures of a sealed KIR program, for kir-backend-diff.sh
(agent EXPORT, 2026-10-04; BOOTSTRAP-TOOL: test harness only, never in a seed's or a product's process tree).

  kbd_exports.py list <p.kir>
      one line per KIR :exports entry, tab separated:  name  arity  param-kinds(csv|-)  result  class  argsets  rtype
      rtype: the loader's KEXE_RESULT_TYPE that observes the result by content (i64, string, option-i64, option-string,
      result-i64, vector-i64, bytes, record:N with scalar fields), or 'opaque' (a handle with no content report)
      class: loop (a __kotoba_loop_* helper), gen (another KIR-generated __kotoba_* function), user
      param-kinds: the loader's boundary kinds (tools/kexe_loader.c kexe_boundary_kind_names) when every parameter has one
      the runner can supply a value for (i64, bool, string, vector-i64), else '-'
      argsets: ';'-separated representative argument vectors (each a '|'-separated list), '-' when not runnable
  kbd_exports.py s0code <in.kexe> <symbol> <out.bin>
      scripts/seed/kexe_code.py's output for any symbol spelling (its regex misses `->Name`)
  kbd_exports.py seedsyms <k.kseed>
      the export symbols of a seed container (KSEED1 header: `KSEED1 <code-bytes> <n>` then n lines `name offset arity`)

Representative arguments (arity > 0, all parameters i64/bool/string/vector-i64): the vectors are fixed, not random, so a run is
reproducible: 0s, 1s, small mixed (3, 1, 4, 1, 5 ..), a negative mix, and a larger value (1000, 7, ..). bool parameters
take 0/1, :string parameters `s:<hex>` of fixed texts, :vector-i64 `vi:<items>` (the loader's argument tokens).
Five vectors per export at most; the arguments of one vector are separated by '|'."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'seed', 'tests', 'kir'))
import census  # noqa: E402  (the KIR EDN reader of seed/tests/kir/census.py, read-only use)

I64_SETS = [
    [0, 0, 0, 0, 0],
    [1, 1, 1, 1, 1],
    [3, 1, 4, 1, 5],
    [-2, 7, -1, 8, 2],
    [1000, 13, 21, 34, 55],
]


def kind(t):
    if isinstance(t, census.Kw) and t in (':i64', ':bool', ':string', ':vector-i64'):
        return t[1:]
    return None


STR_SETS = ['', 'a', 'hello', 'GET /health HTTP/1.1', '{"k" 1}']
VEC_SETS = ['', '1', '3,1,4,1,5', '-2,7', '1000,13,21']


def cls(name):
    if name.startswith('__kotoba_loop_'):
        return 'loop'
    if name.startswith('__kotoba_'):
        return 'gen'
    return 'user'


def tname(t):
    if isinstance(t, census.Kw):
        return t[1:]
    return census.type_name(t) if t is not None else 'nil'


def arg(k, row, j, i):
    v = row[i]
    if k == 'bool':
        return '1' if v > 0 else '0'
    if k == 'string':
        return 's:' + STR_SETS[(j + i) % len(STR_SETS)].encode('utf-8').hex()
    if k == 'vector-i64':
        return 'vi:' + VEC_SETS[(j + i) % len(VEC_SETS)]
    return str(v)


def argsets(kinds):
    out = []
    for j, row in enumerate(I64_SETS):
        s = '|'.join(arg(k, row, j, i) for i, k in enumerate(kinds))
        if s not in out:
            out.append(s)
    return ';'.join(out)


SCALAR = (':i64', ':bool')


def is_kw(t, *names):
    return isinstance(t, census.Kw) and str(t) in names


def rtype(t):
    """the loader's typed report for a KIR result type (KEXE_RESULT_TYPE), or 'opaque' when it has none whose content
    is independent of allocation order (the raw word of a handle numbers allocations)"""
    if is_kw(t, *SCALAR):
        return 'i64'
    if is_kw(t, ':string'):
        return 'string'
    if is_kw(t, ':bytes'):
        return 'bytes'
    if is_kw(t, ':vector-i64'):
        return 'vector-i64'
    if isinstance(t, census.Vec) and t:
        h = str(t[0])
        if h == ':option' and len(t) == 2:
            if is_kw(t[1], *SCALAR):
                return 'option-i64'
            if is_kw(t[1], ':string'):
                return 'option-string'
        if h == ':result' and len(t) == 3 and is_kw(t[1], *SCALAR) and is_kw(t[2], *SCALAR):
            return 'result-i64'
        if h in (':list', ':vector') and len(t) == 2 and is_kw(t[1], ':i64'):
            return 'vector-i64'
        if h == ':record' and len(t) == 3 and isinstance(t[2], census.Vec) and 0 < len(t[2]) <= 16 \
                and all(isinstance(f, census.Vec) and len(f) == 2 and is_kw(f[1], *SCALAR) for f in t[2]):
            return 'record:%d' % len(t[2])
    return 'opaque'


def lst(path):
    prog, fns = census.program(path)
    byname = {str(f.get(census.Kw(':name'))): f for f in fns}
    for e in prog.get(census.Kw(':exports'), []):
        nm = str(e)
        f = byname.get(nm)
        if f is None:
            print('%s\t?\t-\t?\t%s\t-\topaque' % (nm, cls(nm)))
            continue
        ps = f.get(census.Kw(':params')) or []
        pt = f.get(census.Kw(':param-types'))
        if not pt:
            pt = [census.Kw(':i64')] * len(ps)
        ks = [kind(t) for t in pt]
        runnable = len(ps) <= 5 and all(ks)
        pk = ','.join(ks) if runnable and ps else '-'
        a = ('' if not ps else argsets(ks)) if runnable else '-'
        r = f.get(census.Kw(':result'))
        print('%s\t%d\t%s\t%s\t%s\t%s\t%s' % (nm, len(ps), pk, tname(r), cls(nm), a or '.', rtype(r)))


def seedsyms(path):
    with open(path, 'rb') as fh:
        head = fh.readline().split()
        n = int(head[2])
        for _ in range(n):
            print(fh.readline().split()[0].decode('utf-8'))


def s0code(path, sym, out):
    """the raw :code of a stage-0 kexe and the offset of <sym>, as scripts/seed/kexe_code.py, whose `\\b` anchor cannot
    match a symbol that starts with a non-word character (`->Name` record constructors)"""
    import re
    s = open(path, encoding='utf-8').read()
    i = s.index(':code [') + len(':code [')
    m = re.search(r'(?:[\s{,])' + re.escape(sym) + r' \{:offset (\d+), :length (\d+), :arity (\d+)\}', s)
    if not m:
        print('{:ok false :message "symbol not exported"}')
        sys.exit(1)
    open(out, 'wb').write(bytes(int(x) for x in s[i:s.index(']', i)].split()))
    print('{:ok true :symbol %s :offset %s :arity %s}' % (sym, m.group(1), m.group(3)))


if __name__ == '__main__':
    if sys.argv[1] == 's0code':
        s0code(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        {'list': lst, 'seedsyms': seedsyms}[sys.argv[1]](sys.argv[2])
