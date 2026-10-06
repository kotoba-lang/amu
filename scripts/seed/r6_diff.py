#!/usr/bin/env python3
"""scripts/seed/r6_diff.py -- helper of r6-diff.sh, the per-module R6 differential (agent R6C, 2026-10-03). BOOTSTRAP-TOOL
(python, host only: it writes driver sources and reads containers; every value compared is computed by native code).

  r6_diff.py gen <scan-dir> <out-dir> [ns ..]   for every module the seed compiled in the R6 scan (<scan-dir>/r6-scan.tsv OK,
        its object <scan-dir>/o/<ns>.kso), a DRIVER project <out-dir>/<ns>/main.kotoba: one arity-0 export cK per case, each
        calling one export of the module (its interface line in the object: the seed's own checked signature) on fixed
        arguments and folding the result into an i64 (bool 0/1, i64 itself, string/bytes/vector/document by a byte hash).
        Exports with a parameter or result type outside {i64 bool string vector-i64 bytes document keyword(args only)} and
        aborting exports (stage-0 refuses an import abort on native code) are listed as skipped. Prints
        "<ns> <cases> <skipped>" per module; writes <out-dir>/<ns>/cases.tsv (case, export, call text).
  r6_diff.py offsets kseed|kexe <container> <code.bin>   the code bytes of a seed container (KSEED1) or of a stage-0
        :kotoba.kexe/v1 into <code.bin>, then "name offset" per export on stdout.
"""
import os, re, sys

ARGS = {
    ':i64': ['0', '1', '7', '-3', '255', '100003'],
    ':bool': ['true', 'false'],
    ':string': ['""', '"a"', '"hello/world.txt"', '"123"', '"a.b"', '"../x//y"'],
    ':vector-i64': ['[]', '[1 2 3]', '[255 0 128 7]'],
    ':bytes': ['(string-to-utf8 "")', '(string-to-utf8 "abc")', '(string-to-utf8 "hello world")'],
    ':keyword': [':a', ':k/x'],
    ':document': ['(document-i64 3)', '(document-string "x")', '(document-map (document-keyword :a) (document-i64 1))',
                  '(document-vector-conj (document-vector) (document-i64 2))'],
}
DIGEST = {
    ':i64': '{x}', ':bool': '(if {x} 1 0)', ':string': '(r6d-str {x})', ':vector-i64': '(r6d-vec {x})',
    ':bytes': '(r6d-bytes {x})', ':document': '(r6d-str (document-edn-print {x}))',
}
DEFAULT = {':i64': '0', ':bool': 'false', ':string': '""', ':vector-i64': '[]', ':bytes': '(string-to-utf8 "")',
           ':document': '(document-null)'}
PRELUDE = '''(defn- r6d-bytes [b :bytes] :i64 (loop [i 0 h (bytes-count b)] (if (>= i (bytes-count b)) h (recur (+ i 1) (+ (* h 31) (bytes-at b i))))))
(defn- r6d-str [s :string] :i64 (r6d-bytes (string-to-utf8 s)))
(defn- r6d-vec [v :vector-i64] :i64 (loop [i 0 h (vector-count v)] (if (>= i (vector-count v)) h (recur (+ i 1) (+ (* h 31) (vector-at v i))))))
'''
# records (the module's own :schemas): a result of a record type, or a list of one, is folded field by field (keyword
# fields count 0: a keyword made at run time has no portable text); a [:ref :form/r] / [:list [:ref :form/r]] argument is
# built with kotoba.form's constructors (F = its alias) when the module's :form/r is kotoba.form's
FORM_ARGS = ['(F/int-form 7)', '(F/string-form "a.b")', '(F/vec2 (F/int-form 1) (F/string-form "x"))', '(F/nil-form)',
             '(F/call1 "f" (F/int-form 2))', '(F/keyword-form :k)']
FORM_LIST_ARGS = ['(typed-list-new [:list [:ref :form/r]])', '(typed-list-new [:list [:ref :form/r]] (F/int-form 1) (F/string-form "s"))']
FORM_FIELDS = [(':tag', ':i64'), (':s', ':string'), (':n', ':i64'), (':k', ':keyword'), (':kids', '[:list [:ref :form/r]]'),
               (':span', ':i64'), (':data', ':bytes')]
PER_EXPORT = 4      # argument tuples per export clause
MAX_CASES = 120     # per module


def clauses(line):
    # E 1 <off> name [p0 :t ..] :r (body)   |   E 2 <off> <off> name ([..] :r (body)) ([..] :r (body))
    toks = line.split(' ', 4) if line.startswith('E 1 ') else line.split(' ', 5)
    kind = line[2]
    name = toks[3] if kind == '1' else toks[4]
    rest = toks[4] if kind == '1' else toks[5]
    out = []
    for m in re.finditer(r'\[((?:p\d+ (?:\[[^\]]*(?:\[[^\]]*\][^\]]*)*\]|\S+) ?)*)\] (\[[^(]*\]|\S+) \((SEEDSELF|throw)', rest):
        params = re.findall(r'p\d+ (\[[^\]]*(?:\[[^\]]*\][^\]]*)*\]|\S+)', m.group(1))
        out.append((params, m.group(2), m.group(3) == 'throw'))
    return name, out


def balanced(t, i):
    # the index after the bracket form that starts at t[i] ([ { or (), strings skipped
    depth, k, ins = 0, i, False
    while k < len(t):
        c = t[k]
        if ins:
            if c == '\\': k += 1
            elif c == '"': ins = False
        elif c == '"': ins = True
        elif c in '([{': depth += 1
        elif c in ')]}':
            depth -= 1
            if depth == 0: return k + 1
        k += 1
    return len(t)


def schemas_of(src):
    # the module's (:schemas {..}) clause text and {kw: [(field, type-text)]}
    i = src.find('(:schemas {')
    if i < 0:
        return '', {}
    clause = src[i:balanced(src, i)]
    out = {}
    for m in re.finditer(r'(:[^\s\[\]{}()]+) \[:record \1 \[', clause):
        j = m.end() - 1
        fv = clause[j + 1:balanced(clause, j) - 1]
        fields, k = [], 0
        while True:
            a = fv.find('[', k)
            if a < 0: break
            b = balanced(fv, a)
            inner = fv[a + 1:b - 1].strip()
            nm, _, ty = inner.partition(' ')
            fields.append((nm, ty.strip()))
            k = b
        out[m.group(1)] = fields
    return clause, out


def record_digests(schemas):
    # (defn- r6d-r<i> ..) per schema and r6d-l<i> for a list of it; names by schema order
    idx = {kw: i for i, kw in enumerate(schemas)}
    out = []
    def fd(kw, nm, ty):
        get = f'(record-get [:ref {kw}] r {nm})'
        if ty in DIGEST and ty != ':document': return DIGEST[ty].format(x=get)
        m = re.fullmatch(r'\[:ref (:\S+)\]', ty)
        if m and m.group(1) in idx: return f'(r6d-r{idx[m.group(1)]} {get})'
        m = re.fullmatch(r'\[:list \[:ref (:\S+)\]\]', ty)
        if m and m.group(1) in idx: return f'(r6d-l{idx[m.group(1)]} {get})'
        return '0'
    for kw, i in idx.items():
        body = '0'
        for nm, ty in schemas[kw]:
            body = f'(+ (* {body} 31) {fd(kw, nm, ty)})'
        out.append(f'(defn- r6d-r{i} [r [:ref {kw}]] :i64 {body})')
        out.append(f'(defn- r6d-l{i} [xs [:list [:ref {kw}]]] :i64 (loop [i 0 h (vector-count xs)] (if (>= i (vector-count xs)) h '
                   f'(recur (+ i 1) (+ (* h 31) (r6d-r{i} (typed-list-nth [:list [:ref {kw}]] xs i)))))))')
    return idx, out


def gen(scan, outdir, only):
    rows = [l.rstrip('\n').split('\t') for l in open(os.path.join(scan, 'r6-scan.tsv')) if not l.startswith('#')]
    paths = {l.split()[0]: l.split()[1] for l in open(os.path.join(scan, 'order.txt')) if l.strip()}
    for r in rows:
        ns, st = r[0], r[1]
        if st != 'OK' or (only and ns not in only):
            continue
        kso = open(os.path.join(scan, 'o', ns + '.kso'), 'rb').read().decode('utf-8', 'replace')
        clause, schemas = schemas_of(open(paths[ns], encoding='utf-8').read())
        sidx, rdig = record_digests(schemas)
        form_ok = schemas.get(':form/r') == FORM_FIELDS
        F = 'm' if ns == 'kotoba.form' else 'kf'
        use_rec, use_form = False, False
        cases, skipped = [], []
        for line in kso.split('\n'):
            if not line.startswith('E '):
                continue
            name, cl = clauses(line)
            for params, res, aborts in cl:
                tag = f'{name}/{len(params)}'
                if aborts:
                    skipped.append(f'{tag} aborts'); continue
                om = re.fullmatch(r'\[:option (:[a-z0-9-]+)\]', res)
                if om and om.group(1) in DEFAULT:
                    t = om.group(1)
                    dig = (f'(let [o {{x}}] (if (option-some?-of [:option {t}] o) '
                           f'(+ 1 (* 2 {DIGEST[t].format(x=f"(option-value-of [:option {t}] o {DEFAULT[t]})")})) 0))')
                elif res in DIGEST:
                    dig = DIGEST[res]
                elif re.fullmatch(r'\[:ref (:\S+)\]', res) and res[6:-1] in sidx:
                    dig = f'(r6d-r{sidx[res[6:-1]]} {{x}})'; use_rec = True
                elif re.fullmatch(r'\[:list \[:ref (:\S+)\]\]', res) and res[13:-2] in sidx:
                    dig = f'(r6d-l{sidx[res[13:-2]]} {{x}})'; use_rec = True
                else:
                    dig = None
                if dig is None:
                    skipped.append(f'{tag} result {res}'); continue
                pargs = dict(ARGS)
                if form_ok:
                    pargs['[:ref :form/r]'] = [a.replace('F/', F + '/') for a in FORM_ARGS]
                    pargs['[:list [:ref :form/r]]'] = [a.replace('F/', F + '/') for a in FORM_LIST_ARGS]
                bad = [p for p in params if p not in pargs]
                if bad:
                    skipped.append(f'{tag} param {bad[0]}'); continue
                if any(p in ('[:ref :form/r]', '[:list [:ref :form/r]]') for p in params):
                    use_form = True; use_rec = True
                n = 1
                for p in params:
                    n *= len(pargs[p])
                for i in range(min(PER_EXPORT, n)):
                    args = [pargs[p][(i + j) % len(pargs[p])] for j, p in enumerate(params)]
                    call = f'(m/{name}' + ''.join(' ' + a for a in args) + ')'
                    cases.append((name, call, dig.format(x=call)))
        cases = cases[:MAX_CASES]
        d = os.path.join(outdir, ns)
        os.makedirs(d, exist_ok=True)
        ex = ' '.join(f'c{k}' for k in range(len(cases))) or 'c0'
        req = f'[{ns} :as m]' + (' [kotoba.form :as kf]' if use_form and F == 'kf' else '')
        sch = (' ' + clause) if use_rec else ''
        src = [f'(ns r6d.main (:require {req}) (:export [{ex}]){sch})', PRELUDE.rstrip('\n')] + (rdig if use_rec else [])
        for k, (_, _, body) in enumerate(cases):
            src.append(f'(defn c{k} [] :i64 {body})')
        if not cases:
            src.append('(defn c0 [] :i64 0)')
        open(os.path.join(d, 'main.kotoba'), 'w').write('\n'.join(src) + '\n')
        with open(os.path.join(d, 'cases.tsv'), 'w') as f:
            for k, (name, call, _) in enumerate(cases):
                f.write(f'c{k}\t{name}\t{call}\n')
            for s in skipped:
                f.write(f'-\tskipped\t{s}\n')
        print(ns, len(cases), len(skipped))


def offsets(kind, path, out):
    data = open(path, 'rb').read()
    if kind == 'kseed':
        head, rest = data.split(b'\n', 1)
        _, clen, nexp = head.split()
        names = []
        for _ in range(int(nexp)):
            line, rest = rest.split(b'\n', 1)
            n, off, _ar = line.split()
            names.append((n.decode(), int(off)))
        assert rest.startswith(b'\n')
        code = rest[1:1 + int(clen)]
    else:
        s = data.decode('utf-8')
        i = s.index(':code [') + len(':code [')
        code = bytes(int(x) for x in s[i:s.index(']', i)].split())
        names = [(m.group(1), int(m.group(2))) for m in re.finditer(r'([^\s{}\[\]]+) \{:offset (\d+), :length \d+, :arity 0\}', s)]
    open(out, 'wb').write(code)
    for n, off in names:
        print(n, off)


if __name__ == '__main__':
    if sys.argv[1] == 'gen':
        gen(sys.argv[2], sys.argv[3], set(sys.argv[4:]))
    elif sys.argv[1] == 'offsets':
        offsets(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        sys.exit(__doc__)
