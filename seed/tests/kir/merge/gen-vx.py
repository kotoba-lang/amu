#!/usr/bin/env python3
"""seed/tests/kir/merge/gen-vx.py <desugared-defns> <out-file> -- KIR5: the validate-expr batch of vx.cljk from the desugar
pass's answers (one desugared defn per line, e.g. stage-0's native ds_pass `!desugar` output on build/hc/forms.txt).
Line 0: [#{} #{}] (forbidden heads, grammar-declared heads: empty, the host tables are not in the guest). Per defn
`(defn NAME (vector-new P ..) [RESULT] BODY)`: one case [BODY [p ..] {F arity ..} 0] -- the body with its parameter
symbols as locals and, as the functions, every defn of the file the body names, with its arity. Deterministic; BOOTSTRAP-TOOL (test data)."""
import sys


def tokens(s):
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c in ' \t\n,':
            i += 1
        elif c in '()[]{}':
            yield c, i, i + 1
            i += 1
        elif c == '#' and i + 1 < n and s[i + 1] == '{':
            yield '#{', i, i + 2
            i += 2
        elif c == '"':
            j = i + 1
            while s[j] != '"':
                j += 2 if s[j] == '\\' else 1
            yield 'atom', i, j + 1
            i = j + 1
        elif c == '\\':
            j = i + 2
            while j < n and s[j] not in ' \t\n,()[]{}':
                j += 1
            yield 'atom', i, j
            i = j
        else:
            j = i
            while j < n and s[j] not in ' \t\n,()[]{}"':
                j += 1
            yield 'atom', i, j
            i = j


def parse(s):
    """[(kind, start, end, children)] of the top-level items of s"""
    stack = [('top', 0, 0, [])]
    for t, a, b in tokens(s):
        if t in ('(', '[', '{', '#{'):
            stack.append((t, a, 0, []))
        elif t in (')', ']', '}'):
            k, st, _, ch = stack.pop()
            stack[-1][3].append((k, st, b, ch))
        else:
            stack[-1][3].append(('atom', a, b, []))
    return stack[0][3]


def atoms(items):
    for x in items:
        if x[0] == 'atom':
            yield x
        else:
            yield from atoms(x[3])


def main():
    lines = [l.rstrip('\n') for l in open(sys.argv[1], encoding='utf-8') if l.startswith('(defn')]
    defs = []
    for l in lines:
        top = parse(l)
        if len(top) != 1 or top[0][0] != '(':
            continue
        it = top[0][3]
        if len(it) < 4 or it[2][0] != '(':
            continue
        name = l[it[1][1]:it[1][2]]
        pv = it[2][3]
        if not pv or l[pv[0][1]:pv[0][2]] != 'vector-new':
            continue
        params = [l[x[1]:x[2]] for x in pv[1:] if x[0] == 'atom' and not l[x[1]].startswith((':', '"'))]
        body = l[it[-1][1]:it[-1][2]]
        defs.append((name, params, body))
    arity = {}
    for n, p, _ in defs:
        arity.setdefault(n, len(p))
    with open(sys.argv[2], 'w', encoding='utf-8') as o:
        o.write('[#{} #{}]\n')
        for n, p, b in defs:
            used = sorted({b[x[1]:x[2]] for x in atoms(parse(b)) if b[x[1]:x[2]] in arity})
            fns = '{' + ' '.join('%s %d' % (u, arity[u]) for u in used) + '}'
            o.write('[%s [%s] %s 0]\n' % (b, ' '.join(sorted(set(p))), fns))


if __name__ == '__main__':
    main()
