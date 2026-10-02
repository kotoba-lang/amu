#!/usr/bin/env python3
"""scripts/seed/a64enc-oracle.py -- BOOTSTRAP-TOOL oracle for seed/40-a64enc.kotoba (owner 40-a64enc).

One case table: (Kotoba encoder call, assembler text). The script
  1. writes seed/tests/unit/40-a64enc_t.kotoba: a seed-main that prints the encoder's word for every case as 8 hex
     digits (or "--------" for -1 = refused operand), one line per case, in table order;
  2. assembles the assembler column with `clang -c -target arm64-apple-macos` and reads the words back with
     `otool -t -X` (system tools, used as an ENCODING ORACLE only), and writes seed/tests/unit/40-a64enc.expected
     (+ "exit=0"), and seed/tests/unit/40-a64enc.cases (line i = case i, for reading a diff).
Cases whose assembler column is None must be refused by the encoder (expected "--------").
Then `scripts/seed/unit.sh 40-a64enc` compiles the encoder with stage-0, runs it, and diffs against clang's words.
usage: a64enc-oracle.py [--check]   (--check: only verify that the committed files are what this table generates)
"""
import os, subprocess, sys, tempfile

R = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
CASES = []

def c(expr, asm):
    CASES.append((expr, asm))

def xr(r):
    return 'xzr' if r == 31 else 'x%d' % r

REGS = [0, 1, 7, 9, 15, 16, 17, 29, 30]
TRIPLES = [(0, 1, 2), (9, 10, 11), (16, 17, 30), (29, 0, 15), (3, 31, 4), (31, 5, 6)]
# register forms (31 = xzr)
for fn, mn in [('add-r', 'add'), ('sub-r', 'sub'), ('adds-r', 'adds'), ('subs-r', 'subs'), ('and-r', 'and'),
               ('orr-r', 'orr'), ('eor-r', 'eor'), ('orn-r', 'orn'), ('sdiv', 'sdiv'), ('lslv', 'lsl'),
               ('lsrv', 'lsr'), ('asrv', 'asr'), ('mul', 'mul')]:
    for d, n, m in TRIPLES:
        if fn in ('add-r', 'sub-r', 'adds-r', 'subs-r') and (n == 31 or d == 31):
            continue  # 31 means sp in the operand position of the extended form; the seed never uses it there
        c('(enc-%s %d %d %d)' % (fn, d, n, m), '%s %s, %s, %s' % (mn, xr(d), xr(n), xr(m)))
for d, n, m, a in [(0, 1, 2, 3), (9, 10, 11, 12), (17, 16, 15, 14)]:
    c('(enc-madd %d %d %d %d)' % (d, n, m, a), 'madd x%d, x%d, x%d, x%d' % (d, n, m, a))
for d, m in [(0, 1), (9, 16), (16, 9), (1, 31), (30, 29)]:
    c('(enc-mov-r %d %d)' % (d, m), 'mov %s, %s' % (xr(d), xr(m)))
    c('(enc-mvn %d %d)' % (d, m), 'mvn %s, %s' % (xr(d), xr(m)))
for n, m in [(0, 1), (9, 10), (16, 17), (15, 31)]:
    c('(enc-cmp-r %d %d)' % (n, m), 'cmp x%d, %s' % (n, xr(m)))
    c('(enc-cmn-r %d %d)' % (n, m), 'cmn x%d, %s' % (n, xr(m)))
CONDS = [('eq', 0), ('ne', 1), ('hs', 2), ('lo', 3), ('vs', 6), ('vc', 7), ('ge', 10), ('lt', 11), ('gt', 12), ('le', 13)]
for name, cc in CONDS:
    c('(enc-cset 9 (enc-cond-%s))' % name, 'cset x9, %s' % name)
    c('(enc-cset 16 %d)' % cc, 'cset x16, %s' % name)
for d, n, m, cc in [(0, 1, 2, 0), (9, 10, 11, 11), (16, 31, 17, 13)]:
    c('(enc-csinc %d %d %d %d)' % (d, n, m, cc), 'csinc x%d, %s, x%d, %s' % (d, xr(n), m, CONDS[[x[1] for x in CONDS].index(cc)][0]))
    c('(enc-csel %d %d %d %d)' % (d, n, m, cc), 'csel x%d, %s, x%d, %s' % (d, xr(n), m, CONDS[[x[1] for x in CONDS].index(cc)][0]))
c('(enc-cset 1 14)', None)
c('(enc-csinc 1 2 3 16)', None)
for d, n in [(9, 9), (0, 1), (16, 17), (15, 31)]:
    c('(enc-eor-1 %d %d)' % (d, n), 'eor %s, %s, #1' % (xr(d), xr(n)))
# SIR CC mapping
for cc, name in [(1, 'eq'), (2, 'lt'), (3, 'gt'), (4, 'le'), (5, 'ge')]:
    c('(enc-cset 9 (enc-cond-of-cc %d))' % cc, 'cset x9, %s' % name)
c('(enc-cset 9 (enc-cond-of-cc 6))', None)

# add/sub immediate (31 = sp here)
def sp(r):
    return 'sp' if r == 31 else 'x%d' % r
for fn, mn in [('add-i', 'add'), ('sub-i', 'sub')]:
    for d, n in [(0, 1), (31, 31), (16, 29), (9, 9)]:
        for imm in [0, 1, 8, 4095, 4096, 8192, 4096 * 4095]:
            asm = '%s %s, %s, #%d' % (mn, sp(d), sp(n), imm) if imm < 4096 else \
                  '%s %s, %s, #%d, lsl #12' % (mn, sp(d), sp(n), imm >> 12)
            c('(enc-%s %d %d %d)' % (fn, d, n, imm), asm)
    for imm in [-1, 4097, 16777216, 4096 * 4096]:
        c('(enc-%s 1 2 %d)' % (fn, imm), None)
for fn, mn in [('adds-i', 'adds'), ('subs-i', 'subs')]:
    for d, n, imm in [(16, 16, 1), (0, 1, 4095), (9, 31, 7), (17, 3, 8192)]:
        asm = '%s x%d, %s, #%d' % (mn, d, sp(n), imm) if imm < 4096 else '%s x%d, %s, #%d, lsl #12' % (mn, d, sp(n), imm >> 12)
        c('(enc-%s %d %d %d)' % (fn, d, n, imm), asm)
for n, imm in [(9, 0), (16, 1), (10, 4095), (1, 4096)]:
    asm_imm = '#%d' % imm if imm < 4096 else '#%d, lsl #12' % (imm >> 12)
    c('(enc-cmp-i %d %d)' % (n, imm), 'cmp x%d, %s' % (n, asm_imm))
    c('(enc-cmn-i %d %d)' % (n, imm), 'cmn x%d, %s' % (n, asm_imm))
for d, n in [(29, 31), (31, 29), (1, 31)]:
    c('(enc-mov-sp %d %d)' % (d, n), 'mov %s, %s' % (sp(d), sp(n)))

# wide moves
for fn in ['movz', 'movk', 'movn']:
    for d in [0, 1, 9, 16, 30]:
        for imm, hw in [(0, 0), (1, 0), (65535, 0), (4660, 1), (43981, 2), (65535, 3), (32768, 3)]:
            c('(enc-%s %d %d %d)' % (fn, d, imm, hw), '%s x%d, #%d, lsl #%d' % (fn, d, imm, 16 * hw))
    c('(enc-%s 1 65536 0)' % fn, None)
    c('(enc-%s 1 -1 0)' % fn, None)
    c('(enc-%s 1 5 4)' % fn, None)

# loads/stores
for fn in ['ldr', 'str']:
    for t, n, off in [(0, 31, 0), (9, 31, 8), (16, 7, 8), (7, 31, 16), (15, 29, 32760), (17, 0, 4088), (30, 31, 200)]:
        c('(enc-%s %d %d %d)' % (fn, t, n, off), '%s x%d, [%s, #%d]' % (fn, t, sp(n), off))
    for off in [-8, 4, 32768]:
        c('(enc-%s 1 2 %d)' % (fn, off), None)
for fn in ['ldur', 'stur']:
    for t, n, off in [(0, 29, -8), (9, 29, -256), (16, 31, 255), (1, 2, 0), (3, 4, -1), (17, 29, 7)]:
        c('(enc-%s %d %d %d)' % (fn, t, n, off), '%s x%d, [%s, #%d]' % (fn, t, sp(n), off))
    c('(enc-%s 1 2 256)' % fn, None)
    c('(enc-%s 1 2 -257)' % fn, None)
for t1, t2, n, off in [(29, 30, 31, -16), (29, 30, 31, -512), (0, 1, 2, 504), (9, 10, 31, -8)]:
    c('(enc-stp-pre %d %d %d %d)' % (t1, t2, n, off), 'stp x%d, x%d, [%s, #%d]!' % (t1, t2, sp(n), off))
    c('(enc-stp %d %d %d %d)' % (t1, t2, n, off), 'stp x%d, x%d, [%s, #%d]' % (t1, t2, sp(n), off))
    c('(enc-ldp %d %d %d %d)' % (t1, t2, n, off), 'ldp x%d, x%d, [%s, #%d]' % (t1, t2, sp(n), off))
for t1, t2, n, off in [(29, 30, 31, 16), (29, 30, 31, 496), (0, 1, 2, -64)]:
    c('(enc-ldp-post %d %d %d %d)' % (t1, t2, n, off), 'ldp x%d, x%d, [%s], #%d' % (t1, t2, sp(n), off))
c('(enc-stp-pre 29 30 31 -520)', None)
c('(enc-ldp-post 29 30 31 12)', None)

# branches (offsets in words; adr in bytes). Each is assembled at its own position, so ". + k" is relative.
for off in [0, 1, 2, -1, -5, 100, 33554431, -33554432]:
    c('(enc-b %d)' % off, 'b . + %d' % (4 * off) if off >= 0 else 'b . - %d' % (-4 * off))
    c('(enc-bl %d)' % off, 'bl . + %d' % (4 * off) if off >= 0 else 'bl . - %d' % (-4 * off))
c('(enc-b 33554432)', None)
c('(enc-bl -33554433)', None)
for name, cc in CONDS:
    for off in [2, -3, 262143, -262144]:
        c('(enc-bcond %d %d)' % (cc, off), 'b.%s . %s %d' % (name, '+' if off >= 0 else '-', abs(4 * off)))
c('(enc-bcond 0 262144)', None)
c('(enc-bcond 16 1)', None)
for fn in ['cbz', 'cbnz']:
    for t, off in [(0, 2), (9, -3), (16, 262143), (15, -262144), (31, 7)]:
        c('(enc-%s %d %d)' % (fn, t, off), '%s %s, . %s %d' % (fn, xr(t), '+' if off >= 0 else '-', abs(4 * off)))
    c('(enc-%s 1 -262145)' % fn, None)
for d, off in [(1, 0), (2, 4), (3, 13), (16, -7), (17, 1048575), (0, -1048576)]:
    c('(enc-adr %d %d)' % (d, off), 'adr x%d, . %s %d' % (d, '+' if off >= 0 else '-', abs(off)))
c('(enc-adr 1 1048576)', None)
for n in [0, 16, 17, 30]:
    c('(enc-blr %d)' % n, 'blr x%d' % n)
    c('(enc-br %d)' % n, 'br x%d' % n)
c('(enc-ret)', 'ret')
c('(enc-nop)', 'nop')
for imm in [0, 1, 4103, 65535]:
    c('(enc-brk %d)' % imm, 'brk #%d' % imm)
c('(enc-brk 65536)', None)
# patching: a word encoded with offset 0, then patched, must equal the word encoded with the offset
for off in [5, -5, 33554431, -33554432]:
    c('(enc-patch-imm26 (enc-b 0) %d)' % off, 'b . %s %d' % ('+' if off >= 0 else '-', abs(4 * off)))
    c('(enc-patch-imm26 (enc-bl 7) %d)' % off, 'bl . %s %d' % ('+' if off >= 0 else '-', abs(4 * off)))
for off in [3, -3, 262143, -262144]:
    c('(enc-patch-imm19 (enc-bcond 11 0) %d)' % off, 'b.lt . %s %d' % ('+' if off >= 0 else '-', abs(4 * off)))
    c('(enc-patch-imm19 (enc-cbnz 9 -9) %d)' % off, 'cbnz x9, . %s %d' % ('+' if off >= 0 else '-', abs(4 * off)))
for imm in [0, 1, 65535, 4660]:
    c('(enc-patch-imm16 (enc-movz 1 0 0) %d)' % imm, 'movz x1, #%d' % imm)
    c('(enc-patch-imm16 (enc-movk 1 777 1) %d)' % imm, 'movk x1, #%d, lsl #16' % imm)
c('(enc-patch-imm26 (enc-b 0) 33554432)', None)
c('(enc-patch-imm19 (enc-cbz 1 0) 262144)', None)
c('(enc-patch-imm16 (enc-movz 1 0 0) 65536)', None)

GROUP = 24

def kotoba():
    out = [';; deps:',
           ';; seed/tests/unit/40-a64enc_t.kotoba -- GENERATED by scripts/seed/a64enc-oracle.py (do not edit). One line per',
           ';; case: the encoder word as 8 hex digits, "--------" for a refused operand. Oracle: clang + otool.',
           '(defn- t-hd [d :i64] :string',
           '  (cond (= d 0) "0" (= d 1) "1" (= d 2) "2" (= d 3) "3" (= d 4) "4" (= d 5) "5" (= d 6) "6" (= d 7) "7"',
           '        (= d 8) "8" (= d 9) "9" (= d 10) "a" (= d 11) "b" (= d 12) "c" (= d 13) "d" (= d 14) "e" :else "f"))',
           '(defn- t-hx [w :i64 k :i64] :string (t-hd (bit-and (u64-shift-right w (* 4 k)) 15)))',
           '(defn- t-hex [w :i64] :string',
           '  (if (< w 0) "--------"',
           '    (string-concat (string-concat (string-concat (t-hx w 7) (t-hx w 6)) (string-concat (t-hx w 5) (t-hx w 4)))',
           '                   (string-concat (string-concat (t-hx w 3) (t-hx w 2)) (string-concat (t-hx w 1) (t-hx w 0))))))',
           '(defn- t-p [w :i64] :i64',
           '  (let [o (typed-cap-call :io/write :string :string (string-concat (t-hex w) "\\n"))] (if (> w 4294967295) 1 0)))']
    groups = [CASES[i:i + GROUP] for i in range(0, len(CASES), GROUP)]
    for g, cs in enumerate(groups):
        out.append('(defn- t-g%d [] :i64' % g)
        out.append('  (+ 0')
        for expr, _ in cs:
            out.append('     (t-p %s)' % expr)
        out.append('     0))')
    out.append('(defn- seed-main [] :i64')
    out.append('  (let [a (typed-cap-call :cli/args :string :string "")')
    names = ['g%d (t-g%d)' % (g, g) for g in range(len(groups))]
    for n in names:
        out.append('        %s' % n)
    out.append('        bad (+ 0 %s)]' % ' '.join('g%d' % g for g in range(len(groups))))
    out.append('    bad))')
    return '\n'.join(out) + '\n'

def oracle():
    asms = [a for _, a in CASES if a is not None]
    with tempfile.TemporaryDirectory() as d:
        open(d + '/a.s', 'w').write('.text\n' + '\n'.join(asms) + '\n')
        subprocess.check_call(['clang', '-c', '-target', 'arm64-apple-macos', d + '/a.s', '-o', d + '/a.o'])
        out = subprocess.check_output(['otool', '-t', '-X', d + '/a.o'], text=True)
    words = [w for line in out.splitlines() for w in line.split()[1:]]
    assert len(words) == len(asms), (len(words), len(asms))
    it = iter(words)
    return ['--------' if a is None else next(it) for _, a in CASES]

def main():
    t = kotoba()
    exp = '\n'.join(oracle()) + '\nexit=0\n'
    cases = ''.join('%d\t%s\t%s\n' % (i + 1, e, a or 'REFUSED') for i, (e, a) in enumerate(CASES))
    files = {R + '/seed/tests/unit/40-a64enc_t.kotoba': t, R + '/seed/tests/unit/40-a64enc.expected': exp,
             R + '/seed/tests/unit/40-a64enc.cases': cases}
    if '--check' in sys.argv:
        bad = [p for p, s in files.items() if not os.path.exists(p) or open(p).read() != s]
        print('a64enc-oracle: %d cases, %s' % (len(CASES), 'stale: ' + ' '.join(bad) if bad else 'files current'))
        sys.exit(1 if bad else 0)
    for p, s in files.items():
        open(p, 'w').write(s)
    print('a64enc-oracle: %d cases (%d refusals) written' % (len(CASES), sum(1 for _, a in CASES if a is None)))

main()
