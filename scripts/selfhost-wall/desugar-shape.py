#!/usr/bin/env python3
"""The shape of the desugar cycle on the Kotoba route, and the host-neutrality check of the dual-runtime wrapping.

usage: SEMA=<kotoba-sema checkout> desugar-shape.py scc          # SCC of desugar-expr over the :kotoba view of the frontend
       SEMA=<..> desugar-shape.py leftovers                      # frontend/desugar.cljk forms that are not in ds-names.txt (K view)
       SEMA=<..> desugar-shape.py hostview <git-rev>             # the :default view of desugar.cljk after the ns form, against <git-rev>'s

The :kotoba view is tm-gen.py's `expand` (the reader conditional resolved with :kotoba, else :default); the :default view resolves the
other way and drops the `nil` a `:default nil` leaves, so a Kotoba-only addition is invisible there."""
import os, re, sys, glob, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
SEMA = os.environ.get('SEMA', '/Users/junkawasaki/github/kotoba-lang/kotoba-sema')
S = SEMA + '/src/kotoba/compiler/'
src = open(HERE + '/tm-gen.py').read().replace('\nmain()\n', '\n')
ns = {}; exec(src, ns)
form_end, skip_ws, elem_end, expand = ns['form_end'], ns['skip_ws'], ns['elem_end'], ns['expand']
TOK = re.compile(r"[^\s()\[\]{}\"',`~@^]+")

def strip(t):
    """the text without string literals, character literals and comments (a `;` inside a string is not a comment)"""
    out = []; i = 0; n = len(t)
    while i < n:
        c = t[i]
        if c == '"':
            i += 1
            while i < n and t[i] != '"': i += 2 if t[i] == '\\' else 1
            i += 1; out.append(' ')
        elif c == ';':
            while i < n and t[i] != '\n': i += 1
        elif c == '\\' and i + 1 < n:
            i += 2; out.append(' ')
        else:
            out.append(c); i += 1
    return ''.join(out)
def tokens(t): return set(TOK.findall(strip(t)))
def toplevel(s):
    forms = {}; i = 0; n = len(s)
    while True:
        i = skip_ws(s, i)
        if i >= n: break
        if s[i] == '(':
            e = form_end(s, i); t = s[i:e]; i = e
            m = re.match(r'\((defn-?|def)\s+(\^:?[a-z-]+\s+)*([^\s\)\[]+)', t)
            if m: forms[m.group(3)] = t
        else:
            j = i
            while j < n and s[j] not in ' \t\r\n(': j += 1
            i = max(j, i + 1)
    return forms

def kview():
    files = [S + 'frontend.cljk'] + sorted(glob.glob(S + 'frontend/*.cljk'))
    return toplevel('\n'.join(expand(open(f).read()) for f in files))

def scc():
    forms = kview(); names = set(forms)
    g = {x: {y for y in tokens(forms[x]) if y in names and y != x} for x in forms}
    sys.setrecursionlimit(100000)
    idx = {}; low = {}; st = []; on = set(); comps = []; c = [0]
    def sc(v):
        idx[v] = low[v] = c[0]; c[0] += 1; st.append(v); on.add(v)
        for w in g[v]:
            if w not in idx: sc(w); low[v] = min(low[v], low[w])
            elif w in on: low[v] = min(low[v], idx[w])
        if low[v] == idx[v]:
            comp = []
            while True:
                w = st.pop(); on.discard(w); comp.append(w)
                if w == v: break
            comps.append(comp)
    for v in forms:
        if v not in idx: sc(v)
    big = sorted((x for x in comps if len(x) > 1), key=len, reverse=True)
    print('definitions in the K view', len(forms), '; components with a cycle', len(big), 'sizes', [len(x) for x in big[:6]])
    main = [x for x in big if 'desugar-expr' in x][0]
    print('desugar-expr component:', len(main), 'functions,', sum(forms[x].count('\n') + 1 for x in main), 'lines')
    for k in ['desugar-expr', 'desugar-expr*', 'desugar-result-expr', 'desugar-cond-rest', 'desugar-bool-expr',
              'desugar-expected-value', 'desugar-tail-expressions', 'desugar-each']:
        print(' ', k, 'called from', len([x for x in main if k in tokens(forms[x]) and x != k]), 'functions of the cycle')

def leftovers():
    f = S + 'frontend/desugar.cljk'
    have = set(open(HERE + '/ds-names.txt').read().split())
    forms = toplevel(expand(open(f).read()))
    miss = [x for x in forms if x not in have]
    print(len(forms), 'definitions in the K view of desugar.cljk;', len(miss), 'not in ds-names.txt:', ' '.join(miss))

def expand_default(s):
    out = []; i = 0
    while True:
        m = s.find('#?(', i)
        if m < 0: out.append(s[i:]); break
        out.append(s[i:m]); end = form_end(s, m + 2); j = m + 3; pairs = []
        while True:
            j = skip_ws(s, j)
            if s[j] == ')': break
            fe = elem_end(s, j); feat = s[j:fe]; j = skip_ws(s, fe); ve = elem_end(s, j); pairs.append((feat, s[j:ve])); j = ve
        pick = ''
        for f, v in pairs:
            if f == ':default': pick = expand_default(v); break
        out.append(pick if pick != 'nil' else ''); i = end
    return ''.join(out)

def hostview(rev):
    f = 'src/kotoba/compiler/frontend/desugar.cljk'
    cur = open(SEMA + '/' + f).read()
    old = subprocess.run(['git', '-C', SEMA, 'show', rev + ':' + f], capture_output=True, text=True).stdout
    norm = lambda t: re.sub(r'\s+', ' ', re.sub(r';[^\n]*', '', t)).strip()
    body = lambda s: s[form_end(s, 0):]
    a = norm(expand_default(body(old))); b = norm(expand_default(body(cur)))
    print('host view of the file after the ns form is identical to', rev + ':', a == b, len(a), len(b))
    sys.exit(0 if a == b else 1)

cmd = sys.argv[1] if len(sys.argv) > 1 else 'scc'
{'scc': scc, 'leftovers': leftovers}.get(cmd, lambda: hostview(sys.argv[2]))()
