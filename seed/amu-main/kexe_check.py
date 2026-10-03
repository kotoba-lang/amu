#!/usr/bin/env python3
"""seed/amu-main/kexe_check.py -- BOOTSTRAP-TOOL (python3): read a :kotoba.kexe/v1 artifact (EDN) and check its seal the way
kotoba.artifact.core/valid-seal? does: :sha256 == sha256(pr-str(canonical(artifact without :sha256))), canonical = maps
sorted by the pr-str of their keys, sets as vectors sorted by pr-str, lists as vectors. (agent CMD, 2026-10-04)

  kexe_check.py seal <file.kexe>          -> "seal ok <sha>" (exit 0) or "seal BAD stored <a> computed <b>" (exit 1)
  kexe_check.py code <file.kexe> <sym> <out.bin>   -> writes :code, prints the export's offset (as kbd_exports s0code)
  kexe_check.py keys <file.kexe>          -> the top-level keys and the export table, one line each
"""
import hashlib, sys


class Kw(str):
    pass


class Sym(str):
    pass


class Set(list):
    pass


class Lst(list):
    pass


def parse(s):
    i = 0
    n = len(s)

    def ws():
        nonlocal i
        while i < n and (s[i] in ' \t\r\n,' or s[i] == ';'):
            if s[i] == ';':
                while i < n and s[i] != '\n':
                    i += 1
            else:
                i += 1

    def tok():
        nonlocal i
        j = i
        while i < n and s[i] not in ' \t\r\n,()[]{}"':
            i += 1
        return s[j:i]

    def val():
        nonlocal i
        ws()
        c = s[i]
        if c == '{':
            i += 1; d = []
            while True:
                ws()
                if s[i] == '}':
                    i += 1; return dict(d) if False else d_wrap(d)
                k = val(); v = val(); d.append((k, v))
        if c == '[' or c == '(':
            close = ']' if c == '[' else ')'
            i += 1; out = [] if c == '[' else Lst()
            while True:
                ws()
                if s[i] == close:
                    i += 1; return out
                out.append(val())
        if c == '#' and s[i + 1] == '{':
            i += 2; out = Set()
            while True:
                ws()
                if s[i] == '}':
                    i += 1; return out
                out.append(val())
        if c == '"':
            i += 1; b = []
            while s[i] != '"':
                if s[i] == '\\':
                    b.append(s[i:i + 2]); i += 2
                else:
                    b.append(s[i]); i += 1
            i += 1
            return ('str', ''.join(b))
        t = tok()
        if t.startswith(':'):
            return Kw(t)
        if t in ('nil', 'true', 'false'):
            return ('lit', t)
        try:
            return int(t)
        except ValueError:
            return Sym(t)

    v = val()
    return v


class Map(list):
    pass


def d_wrap(pairs):
    m = Map(); m.extend(pairs); return m


def pr(x):
    if isinstance(x, Map):
        return '{' + ', '.join(pr(k) + ' ' + pr(v) for k, v in x) + '}'
    if isinstance(x, Set):
        return '#{' + ' '.join(pr(v) for v in x) + '}'
    if isinstance(x, Lst):
        return '(' + ' '.join(pr(v) for v in x) + ')'
    if isinstance(x, list):
        return '[' + ' '.join(pr(v) for v in x) + ']'
    if isinstance(x, tuple):
        return '"' + x[1] + '"' if x[0] == 'str' else x[1]
    return str(x)


def jkey(t):
    # Java String.compareTo order (UTF-16 code units); ASCII here
    return [ord(c) for c in t]


def canonical(x):
    if isinstance(x, Map):
        items = [(canonical(k), canonical(v)) for k, v in x]
        items.sort(key=lambda kv: jkey(pr(kv[0])))
        return d_wrap(items)
    if isinstance(x, Set):
        vs = [canonical(v) for v in x]
        vs.sort(key=lambda v: jkey(pr(v)))
        return list(vs)
    if isinstance(x, list):
        return [canonical(v) for v in x]
    return x


def get(m, k):
    for kk, v in m:
        if kk == k:
            return v
    return None


def main():
    cmd, path = sys.argv[1], sys.argv[2]
    a = parse(open(path, encoding='utf-8').read())
    if cmd == 'seal':
        stored = get(a, Kw(':sha256'))
        body = d_wrap([(k, v) for k, v in a if k != Kw(':sha256')])
        h = hashlib.sha256(pr(canonical(body)).encode('utf-8')).hexdigest()
        st = stored[1] if isinstance(stored, tuple) else None
        if st == h:
            print('seal ok', h); return 0
        print('seal BAD stored', st, 'computed', h); return 1
    if cmd == 'keys':
        for k, v in a:
            print(k, pr(v)[:120])
        return 0
    if cmd == 'code':
        sym, out = sys.argv[3], sys.argv[4]
        ex = get(get(a, Kw(':exports')), Sym(sym))
        if ex is None:
            print('{:ok false :message "symbol not exported"}'); return 1
        open(out, 'wb').write(bytes(get(a, Kw(':code'))))
        print('{:ok true :symbol %s :offset %d :arity %d}' % (sym, get(ex, Kw(':offset')), get(ex, Kw(':arity'))))
        return 0
    return 2


if __name__ == '__main__':
    sys.exit(main())
