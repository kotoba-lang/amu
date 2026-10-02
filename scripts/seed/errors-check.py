#!/usr/bin/env python3
"""scripts/seed/errors-check.py -- gate ERR: the error-code table of seed/HEADS :errors against (a) the text tables of
seed/90-drv.kotoba (drv-et0/1/2 pieces + drv-ek0/1 placeholders, and drv-kir-text for E12xx) and (b) the error codes the
modules define locally (`(def xx-e-name NNNN)`, `(defn- xx-e-name [] :i64 NNNN)`). BOOTSTRAP-TOOL (python3), owner HOUSE.
Fails (exit 1) when a code is in a module or in HEADS but not in the other places, or when the printed text differs from
the HEADS text. Pure text; no compiler is run."""
import re, sys, os
R = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
heads = open(R + '/seed/HEADS').read()
drv = open(R + '/seed/90-drv.kotoba').read()
bad = []

# HEADS :errors
H = {}
for m in re.finditer(r'\[:c (E-[A-Z0-9-]+) (\d+) "((?:[^"\\]|\\.)*)"\]', heads[heads.index(' :errors'):]):
    H[int(m.group(2))] = (m.group(1), m.group(3))

def fn_cases(name):
    """{code: value-literal} of a `(defn- name [c :i64] ... (cond (= c N) X ...))` table"""
    i = drv.index('(defn- %s [' % name)
    j = drv.index('\n(defn', i + 5) if '\n(defn' in drv[i + 5:] else len(drv)
    j = min(j, drv.index('\n;;', i + 5)) if '\n;;' in drv[i + 5:] else j
    body = drv[i:j]
    out = {}
    for m in re.finditer(r'\(= c (\d+)\) ("(?:[^"\\]|\\.)*"|\d+)', body):
        out[int(m.group(1))] = m.group(2)
    return out

et = [fn_cases('drv-et%d' % k) for k in range(3)]
ek = [fn_cases('drv-ek%d' % k) for k in range(2)]
kir = fn_cases('drv-kir-text')
PH = {'0': '', '1': '{name}', '2': '{n}', '3': '{t}'}

def unq(s): return s[1:-1].replace('\\"', '"').replace('\\\\', '\\')

printed = {}
for c in set(et[0]) | set(kir):
    if c in kir:
        printed[c] = unq(kir[c]) + '{name}' + "'"   # drv-kir-say: text + span + "'"
        continue
    t = unq(et[0][c]) + PH[ek[0].get(c, '0')] + (unq(et[1][c]) if c in et[1] else '') + PH[ek[1].get(c, '0')] + (unq(et[2][c]) if c in et[2] else '')
    printed[c] = t

for c, (name, text) in sorted(H.items()):
    if c not in printed:
        bad.append('E%d %s: in HEADS, no text in 90-drv (the driver prints the code with an empty text)' % (c, name))
    elif printed[c] != text:
        bad.append('E%d %s: text differs\n    HEADS: %s\n    90-drv: %s' % (c, name, text, printed[c]))
for c in sorted(printed):
    if c not in H:
        bad.append('E%d: printed by 90-drv, not in HEADS :errors' % c)

# codes local to modules
for fn in sorted(os.listdir(R + '/seed')):
    if not fn.endswith('.kotoba'): continue
    s = open(R + '/seed/' + fn).read()
    for m in re.finditer(r'\(def ([a-z]+-e-[a-z0-9-]+) (\d{3,4})\)|\(defn- ([a-z]+-e-[a-z0-9-]+) \[\] :i64 (\d{3,4})\)', s):
        c = int(m.group(2) or m.group(4))
        if c not in H:
            bad.append('E%d (%s in %s): not in HEADS :errors' % (c, m.group(1) or m.group(3), fn))

if bad:
    print('ERR: %d problem(s)' % len(bad))
    for b in bad: print('  ' + b)
    sys.exit(1)
print('ERR: %d HEADS error codes, every one has the same text in 90-drv, no module-local code is unregistered' % len(H))
