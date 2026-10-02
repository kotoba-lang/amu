#!/usr/bin/env python3
"""Selfhost ledger: per module, how many DEFINITIONS carry a real Kotoba body.

The progress metric of the selfhost effort (docs/selfhost-efficiency-analysis-20261002.md section 4, rule 5).
Files OK is a diagnostic; this counts definitions.

A definition is a top-level (def | defn | defn- | defonce | defmacro | defmulti) form, found at the top level,
inside a top-level (do ...), or as an arm of a top-level reader conditional. The Kotoba reading of a form is
  - a plain form (no reader conditional)            the form itself                    -> real
  - #?(:kotoba X ...)                               X
  - #?(... :default Y) without a :kotoba arm        Y (the Kotoba reader takes :default)
  - #?(:clj / :cljs arms only)                      nothing                            -> nil (host only)
and a definition is classified
  real      the Kotoba reading defines it with a body that does something
  nil       the Kotoba reading is nil / absent: the definition exists only on the host
  refusal   the Kotoba reading is a short stub that throws / refuses / says "not available on the Kotoba route"
  stub      the body is an empty literal (nil, false, 0, "", [] or {}): hollow (a constant like 4096 is real)
A `#?(:kotoba nil :default (do (defn a ..) (defn b ..)))` wrapper makes every definition inside it `nil`.

REAL (the headline) is a `real` definition in a module the native checker admits (--scan, status OK): a body that
is not just written but accepted by the Kotoba route. A `real` definition in a module that is not admitted is
counted separately as unverified: `arm` when it sits in an explicit #?(:kotoba ..) arm, `plain` when the Kotoba
reading is the shared code, which has never been admitted. Agreement with the host is the --diff column.

Usage: ledger.py <list.txt> [--rows rows.tsv] [--scan scan.tsv] [--diff diff.tsv]
  list.txt  one source path per line (reach-minimal.py output)
  --rows    write one row per definition: module, name, host-lines, kotoba-body, diff-cases, disagreements
  --scan    a wall-scan TSV (path<TAB>OK|refusal): adds the native-checker status per module (matched by the
            path after /src/ or /compat/)
  --diff    a TSV `module<TAB>name<TAB>cases<TAB>disagreements`: the differential coverage column
Output (stdout): one TSV line per module, then TOTAL lines. The classification is a conservative heuristic: a
body that merely looks real is `real`; agreement with the host is established by the differential column, not here."""
import os, re, sys

DEFS = ('def', 'defn', 'defn-', 'defonce', 'defmacro', 'defmulti')
WS = ' \t\r\n,'
OPEN, CLOSE = '([{', ')]}'


def close_of(s, j):
    """Index just after the bracketed form opening at s[j], skipping strings, char literals and comments."""
    depth, k, n = 0, j, len(s)
    while k < n:
        c = s[k]
        if c == '"':
            k += 1
            while k < n and s[k] != '"':
                k += 2 if s[k] == '\\' else 1
        elif c == '\\':
            k += 1
        elif c == ';':
            while k < n and s[k] != '\n':
                k += 1
        elif c in OPEN:
            depth += 1
        elif c in CLOSE:
            depth -= 1
            if depth == 0:
                return k + 1
        k += 1
    return n


def atom_end(s, k):
    n = len(s)
    while k < n and s[k] not in WS + '()[]{}";':
        k += 1
    return max(k, 1)


def one_form_end(s, k):
    """End of the single form that starts at s[k] (after its prefixes)."""
    n = len(s)
    if s[k] in OPEN:
        return close_of(s, k)
    if s[k] == '"':
        e = k + 1
        while e < n and s[e] != '"':
            e += 2 if s[e] == '\\' else 1
        return e + 1
    if s[k] == '\\':
        return atom_end(s, k + 2) if k + 1 < n else k + 1
    return atom_end(s, k)


def forms(s):
    """Split text into its forms. Reader prefixes (' ^meta #? #?@ #' #_) stay attached; #_ drops its form."""
    out, k, n = [], 0, len(s)
    while k < n:
        c = s[k]
        if c in WS:
            k += 1
            continue
        if c == ';':
            while k < n and s[k] != '\n':
                k += 1
            continue
        start, discard = k, False
        while k < n:
            if s.startswith('#_', k):
                discard = True
                k += 2
            elif s.startswith('#?@', k):
                k += 3
            elif s.startswith('#?', k) or s.startswith("#'", k):
                k += 2
            elif c == '#' and False:
                k += 1
            elif s[k] in "'`~@":
                k += 1
            elif s[k] == '^':
                k += 1
                while k < n and s[k] in WS:
                    k += 1
                k = one_form_end(s, k) if k < n else k
                while k < n and s[k] in WS:
                    k += 1
            else:
                break
        if k >= n:
            break
        end = one_form_end(s, k)
        if not discard:
            out.append(s[start:end])
        k = end
    return out


def strip_prefix(f):
    """Drop leading ^meta / quote prefixes from a form's text."""
    while f[:1] == '^':
        k = 1
        while f[k] in WS:
            k += 1
        k = one_form_end(f, k)
        f = f[k:].lstrip(WS)
    return f


def inner(f):
    f = strip_prefix(f)
    return f[f.index('(') + 1:-1] if f.startswith('(') else ''


def conditional_arms(f):
    """For #?( ... ) return {key: form}; None when f is not a reader conditional."""
    if not (f.startswith('#?(') or f.startswith('#?@(')):
        return None
    items = forms(f[f.index('(') + 1:-1])
    return {items[i]: items[i + 1] for i in range(0, len(items) - 1, 2)}


def name_of(items):
    if len(items) < 2:
        return None
    n = strip_prefix(items[1])
    m = re.match(r'[^\s()\[\]{}"]+', n)
    return m.group(0) if m else None


REFUSAL = re.compile(r'(not available|not supported|unsupported|not ported|not implemented)[^"]*(kotoba|route|reading)', re.I)
LITERAL = re.compile(r'^(nil|true|false|-?\d[\d_.rRxXeE+\-/]*|:[^\s()\[\]{}]+|"(?:[^"\\]|\\.)*"|\[\s*\]|\{\s*\})$')


def body_class(f):
    """real / refusal / stub for a def form's text."""
    items = forms(inner(f))
    if not items or items[0] not in DEFS:
        return 'real'
    rest = items[2:]
    if rest and rest[0].startswith('"'):          # docstring
        rest = rest[1:]
    if rest and rest[0].startswith('{'):          # attr map
        rest = rest[1:]
    if items[0] in ('defn', 'defn-', 'defmacro'):
        while rest and not rest[0].startswith('['):
            if rest[0].startswith('('):           # multi-arity: judge the whole remainder
                break
            rest = rest[1:]
        if rest and rest[0].startswith('['):
            rest = rest[1:]
        # type tags (:i64 [:ref ..]) between the parameters and the body
        while len(rest) > 1 and (re.match(r':[\w/.\-?!*]+$', rest[0]) or rest[0].startswith('[:')):
            rest = rest[1:]
    else:
        return 'real'                                  # a constant (def / defonce / defmulti) is its own value
    text = ' '.join(rest).strip()
    if not rest:
        return 'stub'
    if len(rest) == 1 and re.match(r'^(nil|false|0|""|\[\s*\]|\{\s*\})$', text):
        return 'stub'
    if len(text) <= 400 and re.search(r'\((throw|reject!|usage-error!|io/write-error)\b|\(do\s+\(io/write-error', text) \
            and REFUSAL.search(text):
        return 'refusal'
    return 'real'


def lines_of(f):
    return f.count('\n') + 1


def definitions(form, origin='plain'):
    """Yield (name, host_lines, klass, origin) for every definition in a top-level form. origin is `arm` when the
    Kotoba reading is an explicit #?(:kotoba ..) arm, `plain` when it is the shared (plain or :default) code."""
    arms = conditional_arms(form)
    if arms is not None:
        pick = arms.get(':kotoba', arms.get(':default'))
        origin = 'arm' if ':kotoba' in arms else 'plain'
        host = arms.get(':default', arms.get(':clj', arms.get(':cljs', pick or '')))
        # definitions named by the host arms (to report nil ones)
        host_defs = list(definitions(host)) if host else []
        if pick is None or pick.strip() == 'nil':
            for name, hl, _, _ in host_defs:
                yield name, hl, 'nil', 'arm'
            return
        k_defs = list(definitions(pick, origin))
        k_names = {n for n, _, _, _ in k_defs}
        hl_by = {n: hl for n, hl, _, _ in host_defs}
        for name, hl, kl, og in k_defs:
            yield name, hl_by.get(name, hl), kl, og
        for name, hl, _, _ in host_defs:                 # on the host but absent from the Kotoba arm
            if name not in k_names:
                yield name, hl, 'nil', 'arm'
        return
    f = strip_prefix(form)
    if not f.startswith('('):
        return
    items = forms(f[1:-1])
    if not items:
        return
    head = items[0]
    if head == 'do':
        for sub in items[1:]:
            yield from definitions(sub, origin)
    elif head in DEFS:
        name = name_of(items)
        if name:
            yield name, lines_of(form), body_class(f), origin


def module_name(path):
    s = open(path, errors='ignore').read()
    m = re.search(r'\(ns\s+(?:\^\S+\s+)*([^\s()]+)', s)
    return m.group(1) if m else os.path.basename(path)


def rel(path):
    m = re.search(r'/(?:src|compat)/(.*)$', path)
    return m.group(1) if m else path


def main():
    argv = sys.argv[1:]
    opts = {}
    pos = []
    i = 0
    while i < len(argv):
        if argv[i] in ('--rows', '--scan', '--diff'):
            opts[argv[i]] = argv[i + 1]
            i += 2
        else:
            pos.append(argv[i])
            i += 1
    files = [l.strip() for l in open(pos[0]) if l.strip()]
    scan = {}
    if '--scan' in opts and os.path.exists(opts['--scan']):
        for l in open(opts['--scan'], errors='ignore'):
            p = l.rstrip('\n').split('\t')
            if len(p) >= 2:
                scan[rel(p[0])] = 'OK' if p[1].strip() == 'OK' else 'refused'
    diff = {}
    if '--diff' in opts and os.path.exists(opts['--diff']):
        for l in open(opts['--diff']):
            p = l.rstrip('\n').split('\t')
            if len(p) >= 4:
                diff[(p[0], p[1])] = (p[2], p[3])
    rows = []
    hdr = ['module', 'path', 'defs', 'REAL', 'real_unverified_arm', 'real_unverified_plain', 'nil', 'refusal', 'stub',
           'real_pct', 'lines', 'native_check']
    print('\t'.join(hdr))
    keys = ('defs', 'REAL', 'ua', 'up', 'nil', 'refusal', 'stub', 'lines', 'real_lines', 'covered')
    tot = {k: 0 for k in keys}
    for path in files:
        if not os.path.exists(path):
            continue
        text = open(path, errors='ignore').read()
        mod = module_name(path)
        status = scan.get(rel(path), '-')
        c = {k: 0 for k in keys}
        for f in forms(text):
            for name, hl, kl, og in definitions(f):
                c['defs'] += 1
                if kl == 'real':
                    if status == 'OK':
                        c['REAL'] += 1
                        c['real_lines'] += hl
                    elif og == 'arm':
                        c['ua'] += 1
                    else:
                        c['up'] += 1
                else:
                    c[kl] += 1
                d = diff.get((mod, name), ('-', '-'))
                body = kl if kl != 'real' else ('real' if status == 'OK' else 'unverified-' + og)
                rows.append((mod, name, hl, body, d[0], d[1]))
                if d[0] not in ('-', '0') and kl == 'real' and status == 'OK':
                    c['covered'] += 1
        nl = text.count('\n') + 1
        c['lines'] = nl
        pct = '%.0f' % (100.0 * c['REAL'] / c['defs']) if c['defs'] else '-'
        print('\t'.join(map(str, [mod, rel(path), c['defs'], c['REAL'], c['ua'], c['up'], c['nil'], c['refusal'],
                                   c['stub'], pct, nl, status])))
        for k in keys:
            tot[k] += c[k]
    d = tot['defs'] or 1
    print('TOTAL\tmodules=%d\tdefs=%d\tREAL=%d (%.1f%%)\tunverified-arm=%d\tunverified-plain=%d\tnil=%d\trefusal=%d\tstub=%d'
          '\tcovered-by-differential=%d' % (len(files), tot['defs'], tot['REAL'], 100.0 * tot['REAL'] / d, tot['ua'],
                                           tot['up'], tot['nil'], tot['refusal'], tot['stub'], tot['covered']))
    print('REAL-HOST-LINES\t%d of %d module lines (%.1f%%)' % (
        tot['real_lines'], tot['lines'], 100.0 * tot['real_lines'] / (tot['lines'] or 1)))
    if '--rows' in opts:
        with open(opts['--rows'], 'w') as out:
            out.write('module\tname\thost_lines\tkotoba_body\tdiff_cases\tdisagreements\n')
            for r in rows:
                out.write('\t'.join(map(str, r)) + '\n')


if __name__ == '__main__':
    main()
