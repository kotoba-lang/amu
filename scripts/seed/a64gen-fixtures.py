#!/usr/bin/env python3
"""scripts/seed/a64gen-fixtures.py -- BOOTSTRAP-TOOL fixtures for seed/41-a64gen.kotoba (owner 41-a64gen).

One table of hand-written SIR functions (FIXTURES) and of runs with hand-computed results (RUNS).
  gen : writes seed/tests/unit/41-a64gen_t.kotoba. That test (compiled by stage-0 through scripts/seed/unit.sh)
        loads the SIR, FN and LIT records into M, runs gn-run, resolves the fixups with a 40-line test-only layout
        (the real one is 42-layout, later in MANIFEST), and prints the code blob: `fn <f> <byte offset>`,
        `w <8 words in hex>` lines, `lit <pool offset> <bytes in hex>`, `end <total bytes>`.
  run : runs `scripts/seed/unit.sh 41-a64gen` (golden = the printed blob, a determinism/regression check), then
        rebuilds the blob from that stdout and runs every RUNS entry under the C loader (tools/kexe_loader.c):
        result value, trap, fuel boundary, stdout of wire 37, command-mode exit status, files written by wire 35.
usage: a64gen-fixtures.py gen | run [--update]
"""
import json, os, re, subprocess, sys, tempfile

R = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
C = {}
for f in ('seed/SIR', 'seed/HEADS', 'seed/MEMORY-MAP'):
    for m in re.finditer(r'\[:c (\S+) (-?\d+)', open(os.path.join(R, f)).read()):
        C[m.group(1)] = int(m.group(2))
MIN, MAX = -(1 << 63), (1 << 63) - 1

def s64(x):
    x &= (1 << 64) - 1
    return x - (1 << 64) if x >> 63 else x

# ---------------------------------------------------------------------------------------------------------------
# fixtures: name -> (nparams, nslots, depth given to FF-DEPTH or None = computed, [instructions])
# instruction = (OPNAME, a, b, c); label operands are names, FN operands are fixture names, LIT operands strings.
# ---------------------------------------------------------------------------------------------------------------
FIX = []                     # (name, np, ns, dp, body)

def fx(name, np, ns, body, dp=None):
    FIX.append((name, np, ns, dp, body))

BOPS = ['ADD', 'SUB', 'MUL', 'QUOT', 'AND', 'OR', 'XOR', 'SHL', 'USHR', 'SSHR']
for b in BOPS:
    fx('bin_' + b, 2, 2, [('LGET', 0, 1), ('LGET', 1, 2), ('BIN', 'BOP-' + b, 0), ('RET', 0)])
for cc in ['EQ', 'LT', 'GT', 'LE', 'GE']:
    fx('cmp_' + cc, 2, 2, [('LGET', 0, 1), ('LGET', 1, 2), ('CMP', 'CC-' + cc, 0), ('RET', 0)])
fx('un_NOT', 1, 1, [('LGET', 0, 1), ('UN', 'UOP-NOT', 0), ('RET', 0)])
fx('un_BITNOT', 1, 1, [('LGET', 0, 1), ('UN', 'UOP-BITNOT', 0), ('RET', 0)])
KS = [0, 1, -1, 65535, 65536, -65536, MIN, MAX, 0x123456789abcdef0, -0x123456789abcdef0,
      s64(0xffff0000ffff0000), 0x0000ffff00000000, 0x7fffffffffff0000, s64(0xffff12340000ffff), -2, 4096]
for i, k in enumerate(KS):
    fx('k%d' % i, 0, 0, [('CONST', 0, k), ('RET', 0)])
fx('sum', 1, 2, [('CONST', 0, 0), ('LSET', 2, 0),
                 ('LABEL', 'sum_h'), ('LGET', 0, 1), ('CONST', 1, 0), ('CMP', 'CC-GT', 0), ('BRZ', 0, 'sum_x'),
                 ('LGET', 0, 2), ('LGET', 1, 1), ('BIN', 'BOP-ADD', 0), ('LSET', 2, 0),
                 ('LGET', 0, 1), ('CONST', 1, 1), ('BIN', 'BOP-SUB', 0), ('LSET', 1, 0),
                 ('FUEL',), ('BR', 'sum_h'),
                 ('LABEL', 'sum_x'), ('LGET', 0, 2), ('RET', 0)])
fx('fib', 1, 1, [('FUEL',), ('LGET', 0, 1), ('CONST', 1, 2), ('CMP', 'CC-LT', 0), ('BRZ', 0, 'fib_r'),
                 ('LGET', 0, 1), ('RET', 0),
                 ('LABEL', 'fib_r'), ('LGET', 0, 1), ('CONST', 1, 1), ('BIN', 'BOP-SUB', 0), ('CALL', 'fib', 0, 1),
                 ('LGET', 1, 1), ('CONST', 2, 2), ('BIN', 'BOP-SUB', 1), ('CALL', 'fib', 1, 1),
                 ('BIN', 'BOP-ADD', 0), ('RET', 0)])
fx('id', 1, 1, [('LGET', 0, 1), ('RET', 0)])
fx('deep', 1, 1, [('CONST', t, t + 1) for t in range(8)] + [('LGET', 8, 1), ('CALL', 'id', 8, 1),
                  ('BIN', 'BOP-MUL', 7)] + [('BIN', 'BOP-ADD', t) for t in range(6, -1, -1)] + [('RET', 0)])
fx('deep2', 1, 2, [('CONST', t, 0) for t in range(7)] + [
    ('LGET', 7, 1), ('CONST', 8, 5), ('CMP', 'CC-LT', 7), ('BRZ', 7, 'd2_else'),
    ('STR', 7, 'hello, seed'), ('CONST', 8, 1), ('RT', 'RT-STRING-CODE-POINT-AT', 7, 2), ('LSET', 2, 7), ('BR', 'd2_join'),
    ('LABEL', 'd2_else'), ('CONST', 7, 3), ('UN', 'UOP-BITNOT', 7), ('LSET', 2, 7),
    ('LABEL', 'd2_join'), ('CONST', 7, 11), ('CONST', 8, 22), ('CONST', 9, 33), ('VEC', 7, 3), ('CONST', 8, 2),
    ('RT', 'RT-VECTOR-AT', 7, 2), ('LGET', 8, 2), ('BIN', 'BOP-ADD', 7), ('LGET', 8, 1), ('BRNZ', 8, 'd2_nz'),
    ('TRAP', 9), ('LABEL', 'd2_nz')] + [('BIN', 'BOP-ADD', t) for t in range(6, -1, -1)] + [('RET', 0)], dp=0)
fx('g5', 5, 5, [('LGET', 0, 1), ('LGET', 1, 2), ('BIN', 'BOP-SUB', 0), ('LGET', 1, 3), ('BIN', 'BOP-MUL', 0),
                ('LGET', 1, 4), ('BIN', 'BOP-ADD', 0), ('LGET', 1, 5), ('BIN', 'BOP-XOR', 0), ('RET', 0)])
fx('call5', 1, 1, [('CONST', 0, 100), ('LGET', 1, 1), ('CONST', 2, 7), ('CONST', 3, 3), ('CONST', 4, 5),
                   ('CONST', 5, 9), ('CALL', 'g5', 1, 5), ('BIN', 'BOP-ADD', 0), ('RET', 0)])
fx('call5b', 1, 1, [('CONST', t, 0) for t in range(6)] + [('LGET', 6, 1), ('CONST', 7, 7), ('CONST', 8, 3),
                    ('CONST', 9, 5), ('CONST', 10, 9), ('CALL', 'g5', 6, 5)] +
                   [('BIN', 'BOP-ADD', t) for t in range(5, -1, -1)] + [('RET', 0)])
fx('vlit', 1, 1, [('CONST', 0, 10), ('CONST', 1, 20), ('CONST', 2, 30), ('VEC', 0, 3), ('LGET', 1, 1),
                  ('RT', 'RT-VECTOR-AT', 0, 2), ('RET', 0)])
fx('vlit10', 1, 1, [('CONST', 0, 1000)] + [('CONST', 1 + i, i * i - 7) for i in range(10)] +
                   [('VEC', 1, 10), ('LGET', 2, 1), ('RT', 'RT-VECTOR-AT', 1, 2), ('BIN', 'BOP-ADD', 0), ('RET', 0)])
fx('vops', 1, 5, [('LGET', 0, 1), ('RT', 'RT-VECTOR-ALLOC', 0, 1), ('LSET', 2, 0), ('CONST', 0, 0), ('LSET', 3, 0),
                  ('LABEL', 'vo_h'), ('LGET', 0, 3), ('LGET', 1, 1), ('CMP', 'CC-LT', 0), ('BRZ', 0, 'vo_x'),
                  ('LGET', 0, 2), ('LGET', 1, 3), ('LGET', 2, 3), ('LGET', 3, 3), ('BIN', 'BOP-MUL', 2),
                  ('RT', 'RT-VECTOR-ASSOC-IN-PLACE', 0, 3), ('LSET', 2, 0),
                  ('LGET', 0, 3), ('CONST', 1, 1), ('BIN', 'BOP-ADD', 0), ('LSET', 3, 0), ('FUEL',), ('BR', 'vo_h'),
                  ('LABEL', 'vo_x'), ('LGET', 0, 2), ('CONST', 1, 1000), ('RT', 'RT-VECTOR-CONJ', 0, 2), ('LSET', 4, 0),
                  ('LGET', 0, 4), ('CONST', 1, 0), ('CONST', 2, 5), ('RT', 'RT-VECTOR-ASSOC', 0, 3), ('LSET', 5, 0),
                  ('LGET', 0, 5), ('CONST', 1, 0), ('RT', 'RT-VECTOR-AT', 0, 2), ('CONST', 1, 1000000),
                  ('BIN', 'BOP-MUL', 0),
                  ('LGET', 1, 4), ('LGET', 2, 1), ('RT', 'RT-VECTOR-AT', 1, 2), ('BIN', 'BOP-ADD', 0),
                  ('LGET', 1, 2), ('LGET', 2, 1), ('CONST', 3, 1), ('BIN', 'BOP-SUB', 2), ('RT', 'RT-VECTOR-AT', 1, 2),
                  ('BIN', 'BOP-ADD', 0),
                  ('LGET', 1, 4), ('CONST', 2, 0), ('RT', 'RT-VECTOR-AT', 1, 2), ('CONST', 2, 7), ('BIN', 'BOP-MUL', 1),
                  ('BIN', 'BOP-ADD', 0), ('RET', 0)])
fx('str', 1, 2, [('STR', 0, 'hello, seed'), ('LSET', 2, 0), ('LGET', 0, 2), ('LGET', 1, 1),
                 ('RT', 'RT-STRING-CODE-POINT-AT', 0, 2), ('LGET', 1, 2), ('RT', 'RT-STRING-LENGTH-VIA', 1, 1),
                 ('CONST', 2, 1000), ('BIN', 'BOP-MUL', 1), ('BIN', 'BOP-ADD', 0), ('RET', 0)])
fx('slen0', 0, 0, [('STR', 0, ''), ('RT', 'RT-STRING-LENGTH-VIA', 0, 1), ('RET', 0)])
fx('concat', 0, 1, [('STR', 0, 'hello, seed'), ('STR', 1, 'xyz'), ('RT', 'RT-STRING-CONCAT', 0, 2), ('LSET', 1, 0),
                    ('LGET', 0, 1), ('RT', 'RT-STRING-LENGTH-VIA', 0, 1), ('CONST', 1, 1000), ('BIN', 'BOP-MUL', 0),
                    ('LGET', 1, 1), ('CONST', 2, 12), ('RT', 'RT-STRING-CODE-POINT-AT', 1, 2), ('BIN', 'BOP-ADD', 0),
                    ('RET', 0)])
fx('capw', 0, 1, [('STR', 0, 'cap-ok\n'), ('CAP', 37, 1, 0), ('LSET', 1, 0), ('LGET', 0, 1), ('CONST', 1, 0),
                  ('RT', 'RT-STRING-CODE-POINT-AT', 0, 2), ('CONST', 1, 10), ('BIN', 'BOP-MUL', 0),
                  ('LGET', 1, 1), ('RT', 'RT-STRING-LENGTH-VIA', 1, 1), ('BIN', 'BOP-ADD', 0), ('RET', 0)])
fx('cli', 0, 0, [('STR', 0, ''), ('CAP', 38, 1, 0), ('CONST', 1, 0), ('RT', 'RT-STRING-CODE-POINT-AT', 0, 2),
                 ('CONST', 1, 48), ('BIN', 'BOP-SUB', 0), ('STR', 1, '1'), ('CAP', 38, 1, 1), ('CONST', 2, 0),
                 ('RT', 'RT-STRING-CODE-POINT-AT', 1, 2), ('CONST', 2, 48), ('BIN', 'BOP-SUB', 1), ('CONST', 2, 10),
                 ('BIN', 'BOP-MUL', 1), ('BIN', 'BOP-ADD', 0), ('RET', 0)])
# bw: argv[0] = path; writes path WRITE_SEP + bytes 0..255 through wire 35 kind 8 (bytes_from_vector)
fx('bw', 0, 5, [('STR', 0, '0'), ('CAP', 38, 1, 0), ('STR', 1, 'WRITE_SEP'), ('RT', 'RT-STRING-CONCAT', 0, 2),
                ('LSET', 1, 0), ('LGET', 0, 1), ('RT', 'RT-STRING-LENGTH-VIA', 0, 1), ('LSET', 2, 0),
                ('LGET', 0, 2), ('CONST', 1, 256), ('BIN', 'BOP-ADD', 0), ('RT', 'RT-VECTOR-ALLOC', 0, 1), ('LSET', 3, 0),
                ('CONST', 0, 0), ('LSET', 4, 0),
                ('LABEL', 'bw_a'), ('LGET', 0, 4), ('LGET', 1, 2), ('CMP', 'CC-LT', 0), ('BRZ', 0, 'bw_b'),
                ('LGET', 0, 3), ('LGET', 1, 4), ('LGET', 2, 1), ('LGET', 3, 4), ('RT', 'RT-STRING-CODE-POINT-AT', 2, 2),
                ('RT', 'RT-VECTOR-ASSOC-IN-PLACE', 0, 3), ('LSET', 3, 0),
                ('LGET', 0, 4), ('CONST', 1, 1), ('BIN', 'BOP-ADD', 0), ('LSET', 4, 0), ('BR', 'bw_a'),
                ('LABEL', 'bw_b'), ('CONST', 0, 0), ('LSET', 4, 0),
                ('LABEL', 'bw_c'), ('LGET', 0, 4), ('CONST', 1, 256), ('CMP', 'CC-LT', 0), ('BRZ', 0, 'bw_d'),
                ('LGET', 0, 3), ('LGET', 1, 4), ('LGET', 2, 2), ('BIN', 'BOP-ADD', 1), ('LGET', 2, 4),
                ('RT', 'RT-VECTOR-ASSOC-IN-PLACE', 0, 3), ('LSET', 3, 0),
                ('LGET', 0, 4), ('CONST', 1, 1), ('BIN', 'BOP-ADD', 0), ('LSET', 4, 0), ('BR', 'bw_c'),
                ('LABEL', 'bw_d'), ('LGET', 0, 3), ('RT', 'RT-BYTES-FROM-VECTOR', 0, 1), ('CAP', 35, 8, 0),
                ('LSET', 5, 0), ('CONST', 0, 0), ('RET', 0)])
# rd: argv[0] = path; reads it through wire 35 kind 1 and answers its byte length (pair_second on a cap result)
fx('rd', 0, 0, [('STR', 0, '0'), ('CAP', 38, 1, 0), ('CAP', 35, 1, 0), ('RT', 'RT-STRING-LENGTH-VIA', 0, 1),
                ('CONST', 1, 1000), ('BIN', 'BOP-QUOT', 0), ('RET', 0)])
fx('trap', 0, 0, [('TRAP', 5), ('CONST', 0, 1), ('RET', 0)])
fx('bigframe', 1, 600, [('LGET', 0, 1), ('CONST', 1, 2), ('BIN', 'BOP-MUL', 0), ('LSET', 599, 0),
                        ('LGET', 0, 599), ('CALL', 'id', 0, 1), ('CONST', 1, 1), ('BIN', 'BOP-ADD', 0), ('LGET', 1, 599),
                        ('BIN', 'BOP-ADD', 0), ('RET', 0)])

# ---- R2 (2026-10-02): register allocation, deferred temps, folding, fusion, inline runtime operations ------------
# inline vector ops: alloc n (param), assoc! i := i*i for i < n via a counted loop, assoc! of a constant 0 (xzr),
# vector-count, then v[k] (param 2) -- out-of-range index or assoc! traps (udf, SIGILL)
fx('r2_vec', 2, 4, [('LGET', 0, 1), ('RT', 'RT-VECTOR-ALLOC', 0, 1), ('LSET', 3, 0), ('CONST', 0, 0), ('LSET', 4, 0),
                    ('LABEL', 'rv_h'), ('LGET', 0, 4), ('LGET', 1, 1), ('CMP', 'CC-LT', 0), ('BRZ', 0, 'rv_x'),
                    ('LGET', 0, 3), ('LGET', 1, 4), ('LGET', 2, 4), ('LGET', 3, 4), ('BIN', 'BOP-MUL', 2),
                    ('RT', 'RT-VECTOR-ASSOC-IN-PLACE', 0, 3), ('LSET', 3, 0),
                    ('LGET', 0, 4), ('CONST', 1, 1), ('BIN', 'BOP-ADD', 0), ('LSET', 4, 0), ('FUEL',), ('BR', 'rv_h'),
                    ('LABEL', 'rv_x'), ('LGET', 0, 3), ('CONST', 1, 0), ('CONST', 2, 0), ('RT', 'RT-VECTOR-ASSOC-IN-PLACE', 0, 3),
                    ('RT', 'RT-VECTOR-COUNT', 0, 1), ('CONST', 1, 1000), ('BIN', 'BOP-MUL', 0),
                    ('LGET', 1, 3), ('LGET', 2, 2), ('RT', 'RT-VECTOR-AT', 1, 2), ('BIN', 'BOP-ADD', 0), ('RET', 0)])
fx('r2_vset', 2, 2, [('LGET', 0, 1), ('RT', 'RT-VECTOR-ALLOC', 0, 1), ('LGET', 1, 2), ('CONST', 2, 7),
                     ('RT', 'RT-VECTOR-ASSOC-IN-PLACE', 0, 3), ('LGET', 1, 2), ('RT', 'RT-VECTOR-AT', 0, 2), ('RET', 0)])
# pair ops in line: pair_new(a, b) then first - second; a bad handle traps
fx('r2_pair', 2, 3, [('LGET', 0, 1), ('LGET', 1, 2), ('RT', 'RT-PAIR-NEW', 0, 2), ('LSET', 3, 0),
                     ('LGET', 0, 3), ('RT', 'RT-PAIR-FIRST', 0, 1), ('LGET', 1, 3), ('RT', 'RT-PAIR-SECOND', 1, 1),
                     ('BIN', 'BOP-SUB', 0), ('RET', 0)])
fx('r2_pbad', 1, 1, [('LGET', 0, 1), ('RT', 'RT-PAIR-FIRST', 0, 1), ('RET', 0)])
# string literals read only by string-length / string-code-point-at: no pair (folded), bytes from the pool
fx('r2_lit', 1, 1, [('STR', 0, 'hello'), ('RT', 'RT-STRING-LENGTH-VIA', 0, 1), ('CONST', 1, 1000), ('BIN', 'BOP-MUL', 0),
                    ('STR', 1, 'hello'), ('LGET', 2, 1), ('RT', 'RT-STRING-CODE-POINT-AT', 1, 2), ('BIN', 'BOP-ADD', 0),
                    ('RET', 0)])
fx('r2_lit8', 1, 1, [('STR', 0, 'h\u00e9llo'), ('LGET', 1, 1), ('RT', 'RT-STRING-CODE-POINT-AT', 0, 2), ('RET', 0)])
# and / or / not in branch tests (cmp + b.cond fusion, branch threading), and an `and` used as a value
def andif(name, cc1, cc2, op):
    br = 'BRZ' if op == 'and' else 'BRNZ'
    fx(name, 3, 3, [('LGET', 0, 1), ('LGET', 1, 2), ('CMP', cc1, 0), (br, 0, name + '_x'),
                    ('LGET', 0, 2), ('LGET', 1, 3), ('CMP', cc2, 0), ('LABEL', name + '_x'), ('BRZ', 0, name + '_e'),
                    ('CONST', 0, 111), ('BR', name + '_j'), ('LABEL', name + '_e'), ('CONST', 0, 222), ('LABEL', name + '_j'),
                    ('RET', 0)])
andif('r2_and', 'CC-LT', 'CC-LT', 'and')
andif('r2_or', 'CC-EQ', 'CC-GT', 'or')
fx('r2_andv', 3, 3, [('LGET', 0, 1), ('LGET', 1, 2), ('CMP', 'CC-LT', 0), ('BRZ', 0, 'av_x'),
                     ('LGET', 0, 2), ('LGET', 1, 3), ('CMP', 'CC-LE', 0), ('LABEL', 'av_x'), ('RET', 0)])
fx('r2_not', 2, 2, [('LGET', 0, 1), ('LGET', 1, 2), ('CMP', 'CC-GE', 0), ('UN', 'UOP-NOT', 0), ('BRZ', 0, 'nt_e'),
                    ('CONST', 0, 5), ('RET', 0), ('LABEL', 'nt_e'), ('CONST', 0, 6), ('RET', 0)])
# constant folding (and its limits: quot by a constant 0 or MIN / -1 still traps at run time)
fx('r2_fold', 0, 0, [('CONST', 0, 3), ('CONST', 1, 4), ('BIN', 'BOP-MUL', 0), ('CONST', 1, 5), ('CONST', 2, 70),
                     ('CONST', 3, 7), ('BIN', 'BOP-QUOT', 2), ('BIN', 'BOP-SUB', 1), ('BIN', 'BOP-ADD', 0),
                     ('CONST', 1, 1), ('CONST', 2, 66), ('BIN', 'BOP-SHL', 1), ('BIN', 'BOP-XOR', 0),
                     ('CONST', 1, 9), ('CONST', 2, 9), ('CMP', 'CC-EQ', 1), ('BRZ', 1, 'fo_t'), ('UN', 'UOP-BITNOT', 0),
                     ('RET', 0), ('LABEL', 'fo_t'), ('TRAP', 3)])
fx('r2_q0', 1, 1, [('LGET', 0, 1), ('CONST', 1, 0), ('BIN', 'BOP-QUOT', 0), ('RET', 0)])
fx('r2_qmin', 0, 0, [('CONST', 0, MIN), ('CONST', 1, -1), ('BIN', 'BOP-QUOT', 0), ('RET', 0)])
# immediate forms against a parameter x: (op x k) and (op k x)
IMM = [('ADD', 4095), ('ADD', -4095), ('ADD', 4096), ('SUB', 4095), ('SUB', -1), ('SUB', 0), ('SHL', 0), ('SHL', 1),
       ('SHL', 63), ('SHL', 64), ('USHR', 65), ('USHR', 63), ('SSHR', 63), ('SSHR', 4), ('AND', 255),
       ('AND', s64(0xffffffff00000000)), ('AND', MIN), ('OR', 0x7ff0), ('XOR', MAX), ('AND', 0x5555), ('MUL', 16),
       ('MUL', 1 << 62), ('MUL', 3), ('QUOT', 3), ('QUOT', -7), ('QUOT', -1), ('QUOT', 1 << 40), ('QUOT', 1)]
for n, (b, k) in enumerate(IMM):
    fx('r2_i%d' % n, 1, 1, [('LGET', 0, 1), ('CONST', 1, k), ('BIN', 'BOP-' + b, 0), ('RET', 0)])
    fx('r2_j%d' % n, 1, 1, [('CONST', 0, k), ('LGET', 1, 1), ('BIN', 'BOP-' + b, 0), ('RET', 0)])
CIMM = [('LT', 4095), ('LT', -4095), ('EQ', 0), ('GE', 4096), ('GT', -1)]
fx('quot_one_alias', 1, 1, [('LGET', 0, 1), ('CONST', 1, 1), ('BIN', 'BOP-QUOT', 0),
                           ('LSET', 1, 0), ('LGET', 0, 1), ('RET', 0)])
fx('quot_one_deep', 1, 1, [('CONST', t, 0) for t in range(7)] +
   [('LGET', 7, 1), ('CONST', 8, 1), ('BIN', 'BOP-QUOT', 7)] +
   [('BIN', 'BOP-ADD', t) for t in range(6, -1, -1)] + [('RET', 0)])
for n, (cc, k) in enumerate(CIMM):
    fx('r2_c%d' % n, 1, 1, [('LGET', 0, 1), ('CONST', 1, k), ('CMP', 'CC-' + cc, 0), ('RET', 0)])
# a leaf with 12 locals (x0..x6 + callee-saved x19..), called by a non-leaf that keeps a value in x19 across the call
fx('r2_many', 1, 12, [('LGET', 0, 1), ('CONST', 1, 1), ('BIN', 'BOP-ADD', 0), ('LSET', 2, 0)] +
   [x for k in range(3, 13) for x in [('LGET', 0, k - 1), ('LGET', 1, k - 2), ('BIN', 'BOP-ADD', 0), ('LSET', k, 0)]] +
   [('LGET', 0, 12), ('RET', 0)])
fx('r2_keep', 1, 3, [('LGET', 0, 1), ('CONST', 1, 3), ('BIN', 'BOP-MUL', 0), ('LSET', 2, 0),
                     ('LGET', 0, 1), ('CONST', 1, 7), ('BIN', 'BOP-XOR', 0), ('LSET', 3, 0),
                     ('LGET', 0, 2), ('LGET', 1, 1), ('CALL', 'r2_many', 1, 1), ('BIN', 'BOP-ADD', 0),
                     ('LGET', 1, 3), ('BIN', 'BOP-SUB', 0), ('RET', 0)])
# fuel held in x8 by a leaf loop and stored back at ret: h(n) = sum(n) + sum(n) needs 1 + 2n units
fx('r2_fuel2', 1, 1, [('FUEL',), ('LGET', 0, 1), ('CALL', 'sum', 0, 1), ('LGET', 1, 1), ('CALL', 'sum', 1, 1),
                      ('BIN', 'BOP-ADD', 0), ('RET', 0)])
# a result folded into a local while a lower temp still reads that local's old value; a parallel swap
fx('r2_prot', 2, 2, [('LGET', 0, 1), ('LGET', 1, 2), ('CONST', 2, 5), ('BIN', 'BOP-ADD', 1), ('LSET', 1, 1),
                     ('LGET', 1, 1), ('BIN', 'BOP-SUB', 0), ('RET', 0)])
fx('r2_swap', 2, 2, [('LGET', 0, 2), ('LGET', 1, 1), ('LSET', 1, 0), ('LSET', 2, 1), ('LGET', 0, 1),
                     ('CONST', 1, 1000), ('BIN', 'BOP-MUL', 0), ('LGET', 1, 2), ('BIN', 'BOP-ADD', 0), ('RET', 0)])
# branches on constants: the dead side is not emitted
fx('r2_cbr', 1, 1, [('CONST', 0, 1), ('BRZ', 0, 'cb_a'), ('CONST', 0, 0), ('BRNZ', 0, 'cb_a'), ('LGET', 0, 1),
                    ('CONST', 1, 0), ('BRZ', 1, 'cb_b'), ('TRAP', 7), ('LABEL', 'cb_b'), ('RET', 0),
                    ('LABEL', 'cb_a'), ('TRAP', 8)])

# ---------------------------------------------------------------------------------------------------------------
# runs: (fixture, args, expect, opts) ; expect = int result | 'trap' ; opts: fuel, cmd (argv list), stdout, file
# ---------------------------------------------------------------------------------------------------------------
# Direct scalar tail-call regression: argument permutation, high operand temp,
# caller-frame restoration and fuel crossing the direct branch.
fx('tail_target3', 3, 3, [('FUEL',), ('LGET', 0, 1), ('LGET', 1, 2),
                         ('BIN', 'BOP-MUL', 0), ('LGET', 1, 3), ('BIN', 'BOP-ADD', 0), ('RET', 0)])
fx('tail_direct3', 3, 3, [('FUEL',), ('LGET', 0, 3), ('LGET', 1, 1), ('LGET', 2, 2),
                         ('CALL', 'tail_target3', 0, 3), ('RET', 0)])
fx('tail_high3', 3, 3, [('CONST', t, 99) for t in range(6)] +
                      [('FUEL',), ('LGET', 6, 3), ('LGET', 7, 1), ('LGET', 8, 2),
                       ('CALL', 'tail_target3', 6, 3), ('RET', 6)])
RUNS = []

def run(name, args, expect, **o):
    RUNS.append((name, args, expect, o))

for tail_fixture in ('tail_direct3', 'tail_high3'):
    run(tail_fixture, [3, 5, 7], 26, fuel=2)
    run(tail_fixture, [-3, 5, 7], -16, fuel=2)
    run(tail_fixture, [3, 5, 7], 'trap', fuel=1)

def q(a, b):
    if b == 0 or (a == MIN and b == -1):
        return 'trap'
    r = abs(a) // abs(b)
    return r if (a < 0) == (b < 0) else -r

REF = {'ADD': lambda a, b: s64(a + b), 'SUB': lambda a, b: s64(a - b), 'MUL': lambda a, b: s64(a * b), 'QUOT': q,
       'AND': lambda a, b: s64(a & b), 'OR': lambda a, b: s64(a | b), 'XOR': lambda a, b: s64(a ^ b),
       'SHL': lambda a, b: s64(a << (b & 63)), 'USHR': lambda a, b: s64((a & ((1 << 64) - 1)) >> (b & 63)),
       'SSHR': lambda a, b: s64(a >> (b & 63))}
PAIRS = [(7, -2), (-7, 2), (0, 5), (MAX, 1), (MIN, -1), (1 << 62, 4), (-1, 0), (12345, 64), (-8, 65), (1, -1),
         (-1, 63), (MIN, 1), (0x5555, 0x0ff0)]
for b in BOPS:
    for x, y in PAIRS:
        run('bin_' + b, [x, y], REF[b](x, y))
CMPS = {'EQ': lambda a, b: a == b, 'LT': lambda a, b: a < b, 'GT': lambda a, b: a > b, 'LE': lambda a, b: a <= b,
        'GE': lambda a, b: a >= b}
for cc, f in CMPS.items():
    for x, y in [(3, 4), (4, 4), (5, 4), (-1, 0), (MIN, MAX), (MAX, MIN)]:
        run('cmp_' + cc, [x, y], int(f(x, y)))
run('un_NOT', [0], 1); run('un_NOT', [1], 0)
for x in [0, -1, 12345, MIN]:
    run('un_BITNOT', [x], s64(~x))
for i, k in enumerate(KS):
    run('k%d' % i, [], k)
for n in [0, 1, 10, 100000]:
    run('sum', [n], n * (n + 1) // 2)
run('sum', [10], 55, fuel=10)
run('sum', [10], 'trap', fuel=9)
def fib(n): return n if n < 2 else fib(n - 1) + fib(n - 2)
for n in [0, 1, 2, 10, 15]:
    run('fib', [n], fib(n))
run('fib', [10], 55, fuel=177)
run('fib', [10], 'trap', fuel=176)
for a in [0, 1, -3, 1000]:
    run('deep', [a], 28 + 8 * a)
run('deep2', [1], 134)
run('deep2', [9], 29)
for a in [0, 1, -5, 1 << 40]:
    run('call5', [a], s64(100 + (((a - 7) * 3 + 5) ^ 9)))
    run('call5b', [a], s64((((a - 7) * 3 + 5) ^ 9)))
run('vlit', [0], 10); run('vlit', [2], 30); run('vlit', [3], 'trap'); run('vlit', [-1], 'trap')
for i in [0, 4, 9]:
    run('vlit10', [i], 1000 + i * i - 7)
run('vops', [5], 5001016)
run('vops', [1], 5001000)
run('str', [0], 104 + 11000)
run('str', [10], 100 + 11000)
run('str', [11], 'trap')
run('slen0', [], 0)
run('concat', [], 14121)
run('capw', [], 551, stdout='cap-ok\n')
run('cli', [], 72, cmd=['x', '7'])
run('bw', [], 0, cmd=['@OUT/bw.bin'], file=('bw.bin', bytes(range(256))))
run('rd', [], 54, cmd=['@OUT/in.txt'], mkfile=('in.txt', b'abcdefghij' * 5432))
run('trap', [], 'trap')
for a in [0, 21]:
    run('bigframe', [a], 4 * a + 1)

# ---- R2 runs
for n, k in [(5, 4), (5, 0), (1, 0)]:
    run('r2_vec', [n, k], n * 1000 + (0 if k == 0 else k * k))
run('r2_vec', [5, 5], 'trap'); run('r2_vec', [5, -1], 'trap'); run('r2_vec', [0, 0], 'trap')
run('r2_vset', [3, 2], 7); run('r2_vset', [3, 3], 'trap'); run('r2_vset', [3, -1], 'trap')
for a, b in [(10, 3), (MIN, 1), (-5, MAX)]:
    run('r2_pair', [a, b], s64(a - b))
run('r2_pbad', [0], 'trap'); run('r2_pbad', [99999], 'trap'); run('r2_pbad', [-1], 'trap')
for i, c in enumerate(b'hello'):
    run('r2_lit', [i], 5000 + c)
run('r2_lit', [5], 'trap'); run('r2_lit', [-1], 'trap')
run('r2_lit8', [0], 104); run('r2_lit8', [1], 233); run('r2_lit8', [2], 'trap'); run('r2_lit8', [3], 108)
for a, b, c in [(1, 2, 3), (2, 1, 3), (1, 3, 2), (3, 3, 3), (MIN, 0, MAX)]:
    run('r2_and', [a, b, c], 111 if (a < b and b < c) else 222)
    run('r2_or', [a, b, c], 111 if (a == b or b > c) else 222)
    run('r2_andv', [a, b, c], 1 if (a < b and b <= c) else 0)
for a, b in [(1, 2), (2, 2), (3, 2)]:
    run('r2_not', [a, b], 5 if not (a >= b) else 6)
run('r2_fold', [], s64(~((12 + (5 - 10)) ^ (1 << 2))))
run('r2_q0', [5], 'trap'); run('r2_qmin', [], 'trap')
for n, (b, k) in enumerate(IMM):
    for x in [0, 1, -1, 12345, -98765, MIN, MAX, 1 << 40]:
        run('r2_i%d' % n, [x], REF[b](x, k))
        run('r2_j%d' % n, [x], REF[b](k, x))
for n, (cc, k) in enumerate(CIMM):
    for x in [k - 1, k, k + 1, MIN, MAX, 0]:
        run('r2_c%d' % n, [x], int(CMPS[cc](x, k)))
for x in [MIN, MAX, -1, 0, 1, -98765, 12345]:
    run('quot_one_alias', [x], x)
    run('quot_one_deep', [x], x)
def many(a):
    v = [0, a, a + 1]
    for k in range(3, 13): v.append(v[k - 1] + v[k - 2])
    return s64(v[12])
for a in [0, 1, -7, 1 << 33]:
    run('r2_many', [a], many(a))
    run('r2_keep', [a], s64(a * 3 + many(a) - (a ^ 7)))
run('r2_fuel2', [10], 110, fuel=21); run('r2_fuel2', [10], 'trap', fuel=20)
for a, b in [(1, 2), (100, -5), (MIN, 3)]:
    run('r2_prot', [a, b], s64(a - (b + 5)))
    run('r2_swap', [a, b], s64(b * 1000 + a))
run('r2_cbr', [42], 42)

# ---------------------------------------------------------------------------------------------------------------
def layout_tables():
    """number functions (FN index = position + 1), labels, literals; return the flat SIR words and records."""
    fns = {name: i + 1 for i, (name, *_) in enumerate(FIX)}
    labels, lits, sir, fnrecs = {}, [], [], []
    def lab(x):
        if x not in labels:
            labels[x] = len(labels) + 1
        return labels[x]
    def lit(s):
        lits.append(s)
        return len(lits)
    for name, np, ns, dp, body in FIX:
        f = fns[name]
        maxt = 0
        sir.append([C['OP-FN'], f, np, ns])
        for ins in body:
            op = ins[0]
            ops = list(ins[1:])
            if op == 'BIN': ops[0] = C[ops[0]]
            if op == 'CMP': ops[0] = C[ops[0]]
            if op == 'UN': ops[0] = C[ops[0]]
            if op == 'RT': ops[0] = C[ops[0]]
            if op in ('LABEL', 'BR'): ops[0] = lab(ops[0])
            if op in ('BRZ', 'BRNZ'): ops[1] = lab(ops[1])
            if op == 'CALL': ops[0] = fns[ops[0]]
            if op == 'STR': ops[1] = lit(ops[1])
            ops = (ops + [0, 0, 0])[:3]
            sir.append([C['OP-' + op]] + ops)
            t = {'CONST': ops[0] + 1, 'LGET': ops[0] + 1, 'STR': ops[0] + 1, 'RET': ops[0] + 1, 'BRZ': ops[0] + 1,
                 'BRNZ': ops[0] + 1, 'LSET': ops[1] + 1, 'UN': ops[1] + 1, 'BIN': ops[1] + 2, 'CMP': ops[1] + 2,
                 'CAP': ops[2] + 1, 'CALL': ops[1] + max(ops[2], 1), 'RT': ops[1] + max(ops[2], 1),
                 'VEC': ops[0] + max(ops[1], 1)}.get(op, 0)
            maxt = max(maxt, t)
        sir.append([C['OP-END'], f, 0, 0])
        fnrecs.append((f, np, ns, maxt if dp is None else dp))
    return fns, labels, lits, sir, fnrecs

def kotoba(real_layout=False):
    fns, labels, lits, sir, fnrecs = layout_tables()
    o = [';; deps: 40-a64enc',
         ';; seed/tests/unit/41-a64gen_t.kotoba -- GENERATED by scripts/seed/a64gen-fixtures.py gen (do not edit).',
         ';; Loads hand-written SIR fixtures into M, runs gn-run, resolves fixups with a test-only layout and prints the',
         ';; code blob. scripts/seed/a64gen-fixtures.py run executes the blob under the C loader.',
         '(defn- t-hd [d :i64] :string',
         '  (cond (= d 0) "0" (= d 1) "1" (= d 2) "2" (= d 3) "3" (= d 4) "4" (= d 5) "5" (= d 6) "6" (= d 7) "7"',
         '        (= d 8) "8" (= d 9) "9" (= d 10) "a" (= d 11) "b" (= d 12) "c" (= d 13) "d" (= d 14) "e" :else "f"))',
         '(defn- t-hx [w :i64 k :i64] :string (t-hd (bit-and (u64-shift-right w (* 4 k)) 15)))',
         '(defn- t-hex8 [w :i64] :string',
         '  (string-concat (string-concat (string-concat (t-hx w 7) (t-hx w 6)) (string-concat (t-hx w 5) (t-hx w 4)))',
         '                 (string-concat (string-concat (t-hx w 3) (t-hx w 2)) (string-concat (t-hx w 1) (t-hx w 0)))))',
         '(defn- t-dec [n :i64] :string',
         '  (if (< n 10) (t-hd n) (string-concat (t-dec (quot n 10)) (t-hd (- n (* 10 (quot n 10)))))))',
         '(defn- t-sdec [n :i64] :string (if (< n 0) (string-concat "-" (t-dec (- 0 n))) (t-dec n)))',
         '(defn- t-out [s :string] :i64 (let [o (typed-cap-call :io/write :string :string s)] 0))',
         '(defn- t-put [M :vector-i64 a :i64 w :i64] :vector-i64 (vector-assoc! M a w))',
         ';; M[at+i] := v[i] for i < n',
         '(defn- t-copy [M :vector-i64 at :i64 v :vector-i64 i :i64 n :i64] :vector-i64',
         '  (if (>= i n) M (t-copy (t-put M (+ at i) (vector-at v i)) at v (+ i 1) n)))',
         '(defn- t-sir [M :vector-i64 v :vector-i64 n :i64] :vector-i64',
         '  (let [k (vector-at M MM-SIR-N)',
         '        M1 (t-copy M (+ MM-SIR-BASE (* k MM-SIR-W)) v 0 n)]',
         '    (t-put M1 MM-SIR-N (+ k (quot n 4)))))',
         '(defn- t-fnrec [M :vector-i64 f :i64 np :i64 ns :i64 dp :i64] :vector-i64',
         '  (let [b (+ MM-FN-BASE (* f MM-FN-W))',
         '        M1 (t-put M (+ b FF-NPARAMS) np)',
         '        M2 (t-put M1 (+ b FF-NSLOTS) ns)',
         '        M3 (t-put M2 (+ b FF-DEPTH) dp)',
         '        M4 (t-put M3 (+ b FF-KIND) FK-PRIV)]',
         '    (t-put M4 MM-FN-N (+ f 1))))',
         '(defn- t-lit [M :vector-i64 l :i64 b :i64 len :i64] :vector-i64',
         '  (let [a (+ MM-LIT-BASE (* l MM-LIT-W))',
         '        M1 (t-put M (+ a LF-B) b)',
         '        M2 (t-put M1 (+ a LF-LEN) len)',
         '        M3 (t-put M2 MM-LIT-N (+ l 1))]',
         '    (t-put M3 MM-LITB-N (+ b len))))',
         '(defn- t-init [] :vector-i64',
         '  (let [M0 (vector-alloc MM-WORDS)',
         '        M1 (t-put M0 MM-SIR-N 1)',
         '        M2 (t-put M1 MM-CODE-N 1)',
         '        M3 (t-put M2 MM-FIX-N 1)',
         '        M4 (t-put M3 MM-FN-N 1)',
         '        M5 (t-put M4 MM-LIT-N 1)',
         '        M6 (t-put M5 MM-LITB-N 1)]',
         '    (t-put M6 MM-LABEL-N %d)))' % (len(labels) + 1),
         ';; ---- test-only layout: pool after the code (8-aligned), fixups patched in FIX order',
         '(defn- t-a8 [x :i64] :i64 (bit-and (+ x 7) -8))',
         '(defn- t-litf [M :vector-i64 l :i64 f :i64] :i64 (vector-at M (+ MM-LIT-BASE (* l MM-LIT-W) f)))',
         '(defn- t-pool [M :vector-i64 l :i64 cur :i64] :vector-i64',
         '  (let [nl (vector-at M MM-LIT-N)',
         '        len (t-litf M l LF-LEN)]',
         '    (if (>= l nl)',
         '      (t-put M MM-CODE-BYTES cur)',
         '      (t-pool (t-put M (+ MM-LIT-BASE (* l MM-LIT-W) LF-POOL) cur) (+ l 1) (t-a8 (+ cur len))))))',
         '(defn- t-fixf [M :vector-i64 i :i64 f :i64] :i64 (vector-at M (+ MM-FIX-BASE (* i MM-FIX-W) f)))',
         '(defn- t-code [M :vector-i64 i :i64] :i64 (vector-at M (+ MM-CODE-BASE i)))',
         '(defn- t-patch1 [M :vector-i64 at :i64 w :i64] :vector-i64',
         '  (if (< w 0) (t-put M MM-ERR 9999) (t-put M (+ MM-CODE-BASE at) w)))',
         '(defn- t-fix1 [M :vector-i64 i :i64] :vector-i64',
         '  (let [at (t-fixf M i XF-AT)',
         '        k (t-fixf M i XF-KIND)',
         '        g (t-fixf M i XF-TARGET)',
         '        w (t-code M at)',
         '        w2 (t-code M (+ at 1))',
         '        lab (vector-at M (+ MM-LABEL-BASE g))',
         '        fnc (vector-at M (+ MM-FN-BASE (* g MM-FN-W) FF-CODE))',
         '        pool (t-litf M g LF-POOL)]',
         '    (cond (= k FX-B26) (t-patch1 M at (enc-patch-imm26 w (- lab at)))',
         '          (= k FX-BL26) (t-patch1 M at (enc-patch-imm26 w (- fnc at)))',
         '          (= k FX-CB19) (t-patch1 M at (enc-patch-imm19 w (- lab at)))',
         '          (= k FX-BC19) (t-patch1 M at (enc-patch-imm19 w (- lab at)))',
         '          (= k FX-LIT32) (t-patch1 (t-patch1 M at (enc-patch-imm16 w (bit-and pool 65535)))',
         '                                   (+ at 1) (enc-patch-imm16 w2 (u64-shift-right pool 16)))',
         '          :else (t-put M MM-ERR 9998))))',
         '(defn- t-fix [M :vector-i64 i :i64] :vector-i64',
         '  (let [nf (vector-at M MM-FIX-N)]',
         '    (if (>= i nf) M (t-fix (t-fix1 M i) (+ i 1)))))',
         ';; ---- printing',
         '(defn- t-wl [M :vector-i64 i :i64 n :i64 s :string] :string',
         '  (if (>= i n) s (t-wl M (+ i 1) n (string-concat s (string-concat " " (t-hex8 (t-code M i)))))))',
         '(defn- t-min [a :i64 b :i64] :i64 (if (< a b) a b))',
         '(defn- t-pw [M :vector-i64 i :i64 n :i64] :i64',
         '  (if (>= i n)',
         '    0',
         '    (let [e (t-min (+ i 8) n)',
         '          o (t-out (string-concat (t-wl M i e "w") "\\n"))]',
         '      (t-pw M e n))))',
         '(defn- t-bl [M :vector-i64 b :i64 n :i64 s :string] :string',
         '  (if (>= b n) s (t-bl M (+ b 1) n (string-concat s (string-concat (t-hx (vector-at M (+ MM-LITB-BASE b)) 1)',
         '                                                                     (t-hx (vector-at M (+ MM-LITB-BASE b)) 0))))))',
         '(defn- t-pl [M :vector-i64 l :i64] :i64',
         '  (if (>= l (vector-at M MM-LIT-N))',
         '    0',
         '    (let [b (t-litf M l LF-B)',
         '          o (t-out (string-concat (string-concat (string-concat "lit " (t-dec (t-litf M l LF-POOL)))',
         '                                             (if (= (t-litf M l LF-LEN) 0) "" " "))',
         '                                  (string-concat (t-bl M b (+ b (t-litf M l LF-LEN)) "") "\\n")))]',
         '      (t-pl M (+ l 1)))))',
         '(defn- t-pf [M :vector-i64 f :i64] :i64',
         '  (if (>= f (vector-at M MM-FN-N))',
         '    0',
         '    (let [o (t-out (string-concat (string-concat (string-concat "fn " (t-dec f)) " ")',
         '                                  (string-concat (t-dec (* 4 (- (vector-at M (+ MM-FN-BASE (* f MM-FN-W) FF-CODE)) 1))) "\\n")))]',
         '      (t-pf M (+ f 1)))))']
    # loaders: SIR words in chunks of 16 instructions, FN and LIT records
    flat = [w for ins in sir for w in ins]
    stmts = []
    for i in range(0, len(flat), 64):
        ch = flat[i:i + 64]
        stmts.append('(t-sir M%%d [%s] %d)' % (' '.join(str(x) for x in ch), len(ch)))
    for f, np, ns, dp in fnrecs:
        stmts.append('(t-fnrec M%%d %d %d %d %d)' % (f, np, ns, dp))
    b = 1
    for l, s in enumerate(lits, start=1):
        bs = s.encode()
        stmts.append('(t-lit M%%d %d %d %d)' % (l, b, len(bs)))
        for j in range(0, len(bs), 64):
            ch = bs[j:j + 64]
            stmts.append('(t-copy M%%d %d [%s] 0 %d)' % (C['MM-LITB-BASE'] + b + j, ' '.join(str(x) for x in ch), len(ch)))
        b += len(bs)
    groups = [stmts[i:i + 12] for i in range(0, len(stmts), 12)]
    for g, ss in enumerate(groups):
        o.append('(defn- t-load%d [M0 :vector-i64] :vector-i64' % g)
        o.append('  (let [' + '\n        '.join('M%d %s' % (k + 1, s % k) for k, s in enumerate(ss)) + ']')
        o.append('    M%d))' % len(ss))
    o.append('(defn- t-load [M :vector-i64] :vector-i64')
    expr = 'M'
    for g in range(len(groups)):
        expr = '(t-load%d %s)' % (g, expr)
    o.append('  %s)' % expr)
    o += ['(defn- seed-main [] :i64',
          '  (let [a (typed-cap-call :cli/args :string :string "")',
          '        M0 (t-load (t-init))',
          '        M1 (gn-run M0)',
          '        nw (vector-at M1 MM-R0)',
          '        e1 (vector-at M1 MM-ERR)',
          '        o1 (t-out (string-concat (string-concat (string-concat "gen err " (t-dec e1)) " words ")',
          '                                 (string-concat (t-dec nw) "\\n")))',
          ] + (['        M3 (ly-run M1)'] if real_layout else ['        M2 (t-pool M1 1 (t-a8 (* 4 nw)))',
          '        M3 (t-fix M2 1)']) + [
          '        e3 (vector-at M3 MM-ERR)',
          '        o2 (t-out (string-concat (string-concat "layout err " (t-dec e3)) "\\n"))',
          '        o3 (t-pf M3 1)',
          '        o4 (t-pw M3 1 (+ nw 1))',
          '        o5 (t-pl M3 1)',
          '        o6 (t-out (string-concat (string-concat "end " (t-dec (vector-at M3 MM-CODE-BYTES))) "\\n"))]',
          '    (if (= e3 0) 0 1)))']
    return '\n'.join(o) + '\n'

def gen():
    p = os.path.join(R, 'seed/tests/unit/41-a64gen_t.kotoba')
    open(p, 'w').write(kotoba())
    json.dump({'fixtures': [f[0] for f in FIX]}, open(os.path.join(R, 'seed/tests/unit/41-a64gen.fixtures.json'), 'w'))
    print('a64gen-fixtures: %d fixtures, %d SIR instructions, %d runs -> %s' %
          (len(FIX), len(layout_tables()[3]), len(RUNS), p))

def loader():
    return subprocess.check_output(['zsh', '-c', 'source %s/scripts/seed/lib.sh; seed_loader' % R], text=True).strip()

def blob_from(stdout):
    words, lits, fns, end = [], [], {}, None
    for line in stdout.splitlines():
        p = line.split()
        if not p: continue
        if p[0] == 'w': words += [int(x, 16) for x in p[1:]]
        elif p[0] == 'lit': lits.append((int(p[1]), bytes.fromhex(p[2]) if len(p) > 2 else b''))
        elif p[0] == 'fn': fns[int(p[1])] = int(p[2])
        elif p[0] == 'end': end = int(p[1])
    blob = bytearray(b''.join(w.to_bytes(4, 'little') for w in words))
    blob += b'\0' * (end - len(blob))
    for off, bs in lits:
        blob[off:off + len(bs)] = bs
    return bytes(blob), fns

def build_with_layout():
    """00-ns + 40 + 41 + 42 + the same fixtures, laid out by the REAL ly-run; returns its stdout."""
    w = os.path.join(os.environ.get('SEED_BUILD', os.path.join(R, 'build/seed')), 'a64gen-ly')
    os.makedirs(w, exist_ok=True)
    src = ''.join(open(os.path.join(R, f)).read() + '\n' for f in
                  ['seed/00-ns.kotoba', 'seed/01-mem.kotoba', 'seed/02-io.kotoba',
                   'seed/40-a64enc.kotoba', 'seed/41-a64gen.kotoba', 'seed/42-layout.kotoba'])
    open(w + '/unit.kotoba', 'w').write(src + kotoba(real_layout=True))
    sh = ('source %s/scripts/seed/lib.sh; seed_modbuild %s/unit.kotoba %s/unit || exit 1; '
          'cd %s; seed_run %s/unit.bin $(cat %s/unit.offset) %s %s > %s/stdout 2> %s/stderr; echo exit=$? >> %s/stdout'
          % (R, w, w, w, w, w, R, w, w, w, w))
    r = subprocess.run(['zsh', '-c', sh], capture_output=True, text=True)
    if r.returncode != 0:
        print('with-layout build FAILED:', open(w + '/unit.log').read()[-300:])
        return None
    return open(w + '/stdout').read()

def runs(update):
    env = dict(os.environ)
    env.setdefault('SEED_MANIFEST', '')
    if not env['SEED_MANIFEST']:
        del env['SEED_MANIFEST']
    u = subprocess.run(['zsh', os.path.join(R, 'scripts/seed/unit.sh'), '41-a64gen'] + (['--update'] if update else []),
                       env=env, text=True, capture_output=True)
    print(u.stdout.strip().splitlines()[-1] if u.stdout.strip() else u.stderr.strip())
    out = open(os.path.join(os.environ.get('SEED_BUILD') or os.path.join(R, 'build/seed'), 'unit/41-a64gen/stdout')).read()
    if '--with-layout' in sys.argv:
        lo = build_with_layout()
        if lo is None:
            return 1
        # the test layout pads the last literal to 8 bytes; 42-layout ends at the last literal byte
        same = blob_from(lo)[0].rstrip(b'\0') == blob_from(out)[0].rstrip(b'\0') and blob_from(lo)[1] == blob_from(out)[1]
        print('  with 42-layout ly-run: %s | blob %s the test layout\'s' %
              (' | '.join(lo.splitlines()[:2]), 'IDENTICAL to' if same else 'DIFFERS from'))
        out = lo
    head = out.splitlines()[:2]
    print('  ' + ' | '.join(head))
    blob, fns = blob_from(out)
    names = [f[0] for f in FIX]
    L = loader()
    d = tempfile.mkdtemp(prefix='a64gen-')
    bp = os.path.join(d, 'gen.bin')
    open(bp, 'wb').write(blob)
    ok = bad = 0
    for name, args, expect, o in RUNS:
        off = fns[names.index(name) + 1]
        e = dict(os.environ, KEXE_CAP_RESOURCES_35=d)
        if 'fuel' in o: e['KEXE_FUEL'] = str(o['fuel'])
        if 'mkfile' in o: open(os.path.join(d, o['mkfile'][0]), 'wb').write(o['mkfile'][1])
        if 'cmd' in o:
            e['KEXE_COMMAND'] = '1'
            argv = [L, bp, str(off), '0', 'aarch64', '35,37,38,39', '--'] + [a.replace('@OUT', d) for a in o['cmd']]
        else:
            argv = [L, bp, str(off), str(len(args)), 'aarch64', '35,37,38,39'] + [str(a) for a in args]
        p = subprocess.run(argv, env=e, capture_output=True)
        so = p.stdout.decode('latin1')
        if expect == 'trap':
            good = p.returncode != 0 and b'KEXE_TRAP' in p.stderr
            got = 'exit %d %s' % (p.returncode, p.stderr.decode('latin1').strip()[:60])
        elif 'cmd' in o:
            good = p.returncode == (expect & 255)
            got = 'exit %d' % p.returncode
        else:
            lines = so.splitlines()
            good = p.returncode == 0 and lines and lines[-1] == str(expect)
            got = 'exit %d out %r err %r' % (p.returncode, so[-40:], p.stderr.decode('latin1')[:80])
        if good and 'stdout' in o:
            good = so.startswith(o['stdout'])
        if good and 'file' in o:
            fp = os.path.join(d, o['file'][0])
            good = os.path.exists(fp) and open(fp, 'rb').read() == o['file'][1]
            if not good: got += ' file mismatch'
        if good: ok += 1
        else:
            bad += 1
            print('  FAIL %s %s expect %s: %s' % (name, args, expect, got))
    print('a64gen run: %d/%d runs pass (%d fixtures, %d code bytes incl. pool)' % (ok, ok + bad, len(FIX), len(blob)))
    return 0 if bad == 0 and u.returncode == 0 else 1

if __name__ == '__main__':
    if sys.argv[1:2] == ['gen']:
        gen()
    elif sys.argv[1:2] == ['run']:
        sys.exit(runs('--update' in sys.argv))
    else:
        print(__doc__); sys.exit(2)
