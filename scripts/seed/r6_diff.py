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


def gen(scan, outdir, only):
    rows = [l.rstrip('\n').split('\t') for l in open(os.path.join(scan, 'r6-scan.tsv')) if not l.startswith('#')]
    for r in rows:
        ns, st = r[0], r[1]
        if st != 'OK' or (only and ns not in only):
            continue
        kso = open(os.path.join(scan, 'o', ns + '.kso'), 'rb').read().decode('utf-8', 'replace')
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
                else:
                    dig = None
                if dig is None:
                    skipped.append(f'{tag} result {res}'); continue
                bad = [p for p in params if p not in ARGS]
                if bad:
                    skipped.append(f'{tag} param {bad[0]}'); continue
                n = 1
                for p in params:
                    n *= len(ARGS[p])
                for i in range(min(PER_EXPORT, n)):
                    args = [ARGS[p][(i + j) % len(ARGS[p])] for j, p in enumerate(params)]
                    call = f'(m/{name}' + ''.join(' ' + a for a in args) + ')'
                    cases.append((name, call, dig.format(x=call)))
        cases = cases[:MAX_CASES]
        d = os.path.join(outdir, ns)
        os.makedirs(d, exist_ok=True)
        ex = ' '.join(f'c{k}' for k in range(len(cases))) or 'c0'
        src = [f'(ns r6d.main (:require [{ns} :as m]) (:export [{ex}]))', PRELUDE.rstrip('\n')]
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
