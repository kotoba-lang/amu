#!/usr/bin/env python3
"""Minimal self-build reach set: modules reachable from the check + compile(aarch64-macos) + refactor roots
through the ns :require graph (every reader branch), against the harness classpath.

Usage: reach-minimal.py <amu-root> <classpath-file> <kotoba-lang> [--full] [--edges] [--host] > list.txt
  default view: the KOTOBA reading of every ns form (#?(:kotoba ..) arms, else :default; :clj/:cljs arms
           dropped), which is what the self-built compiler loads;
  --host:  every reader branch (what nbb/JVM load).
  default: closure from the minimal roots (nbb/aarch64-cli, nbb/cli, nbb/refactor-cli, nbb/check-cli, sema,
           native/aarch64, project, project-files, module-lock, refactor-cli, refactor library);
  --full:  closure from every nbb/*_cli.cljk (the old reach list);
  --edges: also print every require edge on stderr;
  --roots=ns1,ns2: closure from exactly these namespaces.
Stdout: one source path per line. Stderr: summary (modules, lines, defn tokens)."""
import glob, os, re, sys
args = [a for a in sys.argv[1:] if not a.startswith('--')]
full = '--full' in sys.argv
amu, cpf, k = args[:3]
roots = [e for e in open(cpf).read().split(':') if e.endswith('/src')] + [amu + '/src', k + '/lang/compat']


def find(ns):
    rel = ns.replace('.', '/').replace('-', '_')
    for r in roots:
        for ext in ('.kotoba', '.cljk', '.cljc'):
            p = os.path.join(r, rel + ext)
            if os.path.exists(p):
                return p


rootsarg = [a for a in sys.argv if a.startswith('--roots=')]
if rootsarg:
    start = [find(n) for n in rootsarg[0][8:].split(',')]
    start = [p for p in start if p]
elif full:
    start = glob.glob(amu + '/src/kotoba/compiler/nbb/*_cli.cljk')
else:
    start = [find(n) for n in ('kotoba.compiler.nbb.aarch64-cli', 'kotoba.compiler.nbb.cli',
                               'kotoba.compiler.nbb.refactor-cli', 'kotoba.compiler.nbb.check-cli',
                               'kotoba.compiler.sema', 'kotoba.compiler.native.aarch64',
                               # The self-built binary needs a Kotoba body for these even though the Kotoba reading of
                               # their requirers is a placeholder today (nbb/project-source keeps the single-file read,
                               # nbb/refactor-cli is `#?(:kotoba nil)`), so the Kotoba view would lose them.
                               'kotoba.compiler.project', 'kotoba.compiler.project-files',
                               'kotoba.compiler.module-lock', 'kotoba.compiler.refactor-cli',
                               # the refactor library: refactor-cli requires it only on the host reading
                               'kotoba.compiler.refactor.core', 'kotoba.compiler.refactor.cst',
                               'kotoba.compiler.refactor.diff', 'kotoba.compiler.refactor.edit',
                               'kotoba.compiler.refactor.extract', 'kotoba.compiler.refactor.graph',
                               'kotoba.compiler.refactor.partition', 'kotoba.compiler.refactor.prelude',
                               'kotoba.compiler.refactor.rules', 'kotoba.compiler.refactor.verify')]
    start = [p for p in start if p]
host = '--host' in sys.argv


def resolve_conditionals(s):
    """Replace each #?(...) / #?@(...) by its :kotoba arm, else its :default arm, else nothing."""
    out, i, n = [], 0, len(s)
    def scan(j):  # j at an opening paren/bracket/brace; returns index after the matching close, and its inner text
        depth, k, instr = 0, j, False
        while k < n:
            c = s[k]
            if instr:
                if c == '\\': k += 1
                elif c == '"': instr = False
            elif c == '"': instr = True
            elif c == ';':
                while k < n and s[k] != '\n': k += 1
            elif c in '([{': depth += 1
            elif c in ')]}':
                depth -= 1
                if depth == 0: return k + 1
            k += 1
        return n
    while i < n:
        if s.startswith('#?', i) and i + 2 < n and (s[i + 2] == '(' or s[i + 2:i + 4] == '@('):
            at = s[i + 2] == '@'
            j = i + 3 if at else i + 2
            end = scan(j)
            inner = s[j + 1:end - 1]
            # split inner into top-level forms
            forms, k = [], 0
            while k < len(inner):
                if inner[k] in ' \t\r\n,': k += 1; continue
                if inner[k] == ';':
                    while k < len(inner) and inner[k] != '\n': k += 1
                    continue
                if inner[k] in '([{':
                    m = scan_in(inner, k)
                else:
                    m = k
                    while m < len(inner) and inner[m] not in ' \t\r\n,([{': m += 1
                forms.append(inner[k:m]); k = m
            pick = None
            for key in (':kotoba', ':default'):
                for q in range(0, len(forms) - 1, 2):
                    if forms[q] == key: pick = forms[q + 1]; break
                if pick is not None: break
            if pick is not None:
                out.append(resolve_conditionals(pick[1:-1] if at and pick[:1] in '[(' else pick))
            i = end
        else:
            out.append(s[i]); i += 1
    return ''.join(out)


def scan_in(s, j):
    depth, k, instr, n = 0, j, False, len(s)
    while k < n:
        c = s[k]
        if instr:
            if c == '\\': k += 1
            elif c == '"': instr = False
        elif c == '"': instr = True
        elif c == ';':
            while k < n and s[k] != '\n': k += 1
        elif c in '([{': depth += 1
        elif c in ')]}':
            depth -= 1
            if depth == 0: return k + 1
        k += 1
    return n


edges, seen, queue = {}, {}, list(start)
while queue:
    f = queue.pop()
    if f in seen:
        continue
    seen[f] = 1
    s = open(f, errors='ignore').read()
    m = re.search(r'\(ns\s.*?(?=\n\(def|\n\(ns|\Z)', s, re.S)
    if m and not host:
        class M:  # minimal match-like wrapper over the resolved ns text
            def __init__(self, g): self.g = g
            def group(self, _): return self.g
        m = M(resolve_conditionals(m.group(0)))
    out = []
    for n in re.findall(r'\[([a-z][\w.\-]*)(?:\s|\])', m.group(0) if m else s[:6000]):
        p = '.' in n and find(n)
        if p:
            out.append(p)
            if p not in seen:
                queue.append(p)
    edges[f] = out
files = sorted(seen)
print('\n'.join(files))
tot = sum(len(open(f, errors='ignore').read().split('\n')) for f in files)
dfn = sum(len(re.findall(r'\(defn-?\s', open(f, errors='ignore').read())) for f in files)
print('%d modules, %d lines, %d defn tokens' % (len(files), tot, dfn), file=sys.stderr)
if '--edges' in sys.argv:
    for f in files:
        for t in edges[f]:
            print('EDGE %s -> %s' % (f, t), file=sys.stderr)
