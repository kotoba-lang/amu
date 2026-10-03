#!/usr/bin/env python3
"""seed/tests/kir/slice.py -- KIR program slicing for the merge test (agent KIR3, BOOTSTRAP-TOOL: test harness only,
never in a seed's process tree).

  slice.py fns   <in.kir>                         one line per function: name, params, result, n-callees (tsv)
  slice.py slice <in.kir> <out.kir> ROOT [ROOT..] the KIR program cut down to the call closure of the roots: :entry ROOT1,
                                                  :exports [ROOTS], :signature from ROOT1, :functions = the closure in the
                                                  original order (the function maps are copied byte for byte)
  slice.py scan  <in.kir> <out.tsv> <cmd>         for every function F that is not a loop helper: slice the closure of F
                                                  into a temp file and run `<cmd> <file>` (a shell command; exit 0 = the
                                                  seed compiles it). tsv: name, params, result, closure size, status, first
                                                  line of the refusal
  slice.py frontier <in.kir> <scan.tsv>           the refused functions whose callees (outside their own loop helpers)
                                                  all compile: their refusal is their OWN shape, not a callee's. tsv: name,
                                                  params, result, functions blocked (whose closure contains it), refusal

A function's callees are the symbols of its :body that name a function of the same program (loop helpers, lambda-lifted
`$` functions and `__kotoba_invoke$arityN` dispatchers are reached the same way). The function maps are cut out of the
text (balanced brackets, string-aware), so a slice is the stage-0 KIR itself minus unreachable functions.
"""
import os
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import census  # noqa: E402  (the KIR reader)

Kw = census.Kw


def close_of(s, i):
    """index after the bracket closing the one that opens at i (string- and comment-aware)"""
    depth, j, n = 0, i, len(s)
    while j < n:
        c = s[j]
        if c == '"':
            j += 1
            while s[j] != '"':
                j += 2 if s[j] == '\\' else 1
        elif c == ';':
            while j < n and s[j] != '\n':
                j += 1
            continue
        elif c in '([{':
            depth += 1
        elif c in ')]}':
            depth -= 1
            if depth == 0:
                return j + 1
        j += 1
    raise ValueError('unbalanced')


def top_value(s, key):
    """(start, end) of the value of a depth-1 key of the program map"""
    depth, j, n = 0, 0, len(s)
    while j < n:
        c = s[j]
        if c == '"':
            j += 1
            while s[j] != '"':
                j += 2 if s[j] == '\\' else 1
        elif c in '([{':
            depth += 1
        elif c in ')]}':
            depth -= 1
        elif depth == 1 and s.startswith(key, j) and s[j + len(key)] in ' \n':
            a = j + len(key) + 1
            while s[a] in ' \n,':
                a += 1
            if s[a] in '([{' or s.startswith('#{', a):
                b = close_of(s, a + 1 if s[a] == '#' else a)
            else:
                b = a
                while s[b] not in ' \n,}':
                    b += 1
            return a, b
        j += 1
    return None


def functions(s):
    """[(name, start, end, parsed-map)] of the :functions vector"""
    a, b = top_value(s, ':functions')
    out, j = [], a + 1
    while j < b - 1:
        if s[j] == '{':
            e = close_of(s, j)
            m = census.pairs(census.read(s[j:e]))
            out.append((str(m.get(Kw(':name'))), j, e, m))
            j = e
        else:
            j += 1
    return out


def syms(x, acc):
    if isinstance(x, census.Sym):
        acc.add(str(x))
    elif isinstance(x, list):
        for y in x:
            syms(y, acc)
    return acc


def graph(fns):
    names = {f[0] for f in fns}
    return {f[0]: (syms(f[3].get(Kw(':body')), set()) & names) - {f[0]} for f in fns}


def closure(g, roots):
    seen, todo = set(), list(roots)
    while todo:
        f = todo.pop()
        if f in seen:
            continue
        seen.add(f)
        todo.extend(g.get(f, ()))
    return seen


def tstr(t):
    if isinstance(t, census.Vec):
        return '[' + ' '.join(tstr(x) for x in t) + ']'
    return str(t)


def write_slice(s, fns, keep, roots, out):
    by = {f[0]: f for f in fns}
    r = by[roots[0]][3]
    sig = '{:params [%s], :result %s}' % (' '.join(tstr(t) for t in (r.get(Kw(':param-types')) or [])),
                                         tstr(r.get(Kw(':result'))))
    edits = []
    for key, val in ((':entry', roots[0]), (':exports', '[' + ' '.join(roots) + ']'), (':signature', sig)):
        sp = top_value(s, key)
        if sp:
            edits.append((sp[0], sp[1], val))
    a, b = top_value(s, ':functions')
    edits.append((a, b, '[' + ' '.join(s[f[1]:f[2]] for f in fns if f[0] in keep) + ']'))
    edits.sort()
    parts, p = [], 0
    for x, y, v in edits:
        parts.append(s[p:x])
        parts.append(v)
        p = y
    parts.append(s[p:])
    with open(out, 'w', encoding='utf-8') as f:
        f.write(''.join(parts))


def helper(name):
    return name.startswith('__kotoba_loop_') or name.startswith('__kotoba_invoke') or '$' in name


def main():
    cmd = sys.argv[1]
    s = open(sys.argv[2], encoding='utf-8').read().rstrip('\n')
    fns = functions(s)
    g = graph(fns)
    if cmd == 'fns':
        for name, _, _, m in fns:
            print('%s\t%s\t%s\t%d' % (name, tstr(m.get(Kw(':param-types'))), tstr(m.get(Kw(':result'))), len(g[name])))
    elif cmd == 'slice':
        roots = sys.argv[4:]
        write_slice(s, fns, closure(g, roots), roots, sys.argv[3])
    elif cmd == 'scan':
        out, shell = sys.argv[3], sys.argv[4]
        tmp = tempfile.mkdtemp(prefix='kir3-scan.', dir=os.path.dirname(os.path.abspath(out)))  # inside the seed's wire-35 scope
        with open(out, 'w') as o:
            for name, _, _, m in fns:
                if helper(name):
                    continue
                keep = closure(g, [name])
                p = os.path.join(tmp, 'f.kir')
                write_slice(s, fns, keep, [name], p)
                r = subprocess.run(shell + ' ' + p, shell=True, capture_output=True, text=True, errors='replace')
                line = (r.stdout + r.stderr).strip().splitlines()
                first = line[0][:160] if line else ''
                ok = r.returncode == 0 and ':ok true' in first
                why = '' if ok else re.sub(r'\s+', ' ', first)
                o.write('%s\t%s\t%s\t%d\t%s\t%s\n' % (name, tstr(m.get(Kw(':param-types'))), tstr(m.get(Kw(':result'))),
                                                     len(keep), 'ok' if ok else 'refused', why))
                o.flush()
    elif cmd == 'frontier':
        st = {}
        for ln in open(sys.argv[3], encoding='utf-8'):
            c = ln.rstrip('\n').split('\t')
            st[c[0]] = (c[4], c[5] if len(c) > 5 else '')
        own = {}
        for name, _, _, _ in fns:  # F's own helpers: helpers reachable from F through helpers only
            seen, todo = set(), [x for x in g[name] if helper(x)]
            while todo:
                h = todo.pop()
                if h not in seen:
                    seen.add(h)
                    todo.extend(x for x in g.get(h, ()) if helper(x))
            own[name] = seen
        clos = {n: closure(g, [n]) for n in st}
        for name, _, _, m in fns:
            if st.get(name, ('ok',))[0] == 'ok':
                continue
            callees = set()
            for x in {name} | own[name]:
                callees |= {y for y in g.get(x, ()) if not helper(y) and y != name}
            if all(st.get(y, ('ok',))[0] == 'ok' for y in callees):
                blocked = sum(1 for n in st if name in clos[n])
                why = st[name][1]
                mb = re.search(r'\(byte (\d+)\)', why)
                if mb:  # the form at the reported byte of F's slice, e.g. the whole type vector of an E2105
                    tmp = tempfile.mkdtemp(prefix='kir3-front.')
                    p = os.path.join(tmp, 'f.kir')
                    write_slice(s, fns, closure(g, [name]), [name], p)
                    b = open(p, 'rb').read()
                    i = int(mb.group(1))
                    j = i
                    if b[i:i + 1] in (b'[', b'(', b'{'):
                        j = close_of(b.decode('utf-8', 'replace'), i) if b.isascii() else i + 1
                        if not b.isascii():  # byte offsets: close by hand
                            d, j = 0, i
                            while j < len(b):
                                d += b[j:j + 1] in (b'[', b'(', b'{')
                                d -= b[j:j + 1] in (b']', b')', b'}')
                                j += 1
                                if d == 0:
                                    break
                    else:
                        while j < len(b) and b[j:j + 1] not in (b' ', b'\n', b')', b']', b'}'):
                            j += 1
                    why = why[:mb.start()].strip() + ' AT ' + b[i:min(j, i + 120)].decode('utf-8', 'replace')
                    os.remove(p)
                    os.rmdir(tmp)
                print('%s\t%s\t%s\t%d\t%s' % (name, tstr(m.get(Kw(':param-types'))), tstr(m.get(Kw(':result'))), blocked,
                                               why))
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == '__main__':
    main()
