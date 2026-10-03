#!/usr/bin/env python3
"""seed/tests/f64/gen-cases.py -- writes parse.kir (KIR route) and parse.kotoba (source route) for decimal-f64-parse
(agent F64, 2026-10-04). Expected bits: Python float() (correctly rounded binary64) for inputs the sealed decimal subset
admits; none for the rest (empty, no digits, > 64 bytes, exponent with 0 or > 3 digits, overflow to infinity).
Export t answers 1 iff every case agrees, else 1000 + the index of the first disagreeing case."""
import os, struct
H = os.path.dirname(os.path.abspath(__file__))
CASES = ['0.1', '1.5', '-2.25', '3.141592653589793', '1e10', '1E-5', '2.2250738585072014e-308', '4.9e-324',
         '1.7976931348623157e308', '1.8e308', '123456789012345678901234567890', '0.000001', '-0', '0.0', '5e-325',
         'abc', '1.', '.5', '1e', '+7', '9007199254740993', '0.30000000000000004', '2.5e-3', '100', '-1e-400',
         '2.4703282292062328e-324', '2.4703282292062327e-324', '1e-1000', '1e+22', '1e23', '8.98846567431158e307',
         '0.1e1', '12345678901234567890123456789012345678901234567890123456789012345', '', '-', '1e1234', '7.5e-1', '1x']
def expect(c):
    import re
    m = re.fullmatch(r'[+-]?(\d*)(\.(\d*))?([eE][+-]?(\d*))?', c)
    if not c or len(c) > 64 or not m or (m.group(1) + (m.group(3) or '')) == '': return None
    if m.group(4) is not None and not (1 <= len(m.group(5)) <= 3): return None
    v = float(c)
    if v in (float('inf'), float('-inf')): return None
    return struct.unpack('<q', struct.pack('<d', v))[0]
def esc(c): return c.replace('\\', '\\\\').replace('"', '\\"')
kb = []; sb = []
for i, c in enumerate(CASES):
    e = expect(c)
    kb.append('(chk "%s" %d %s %d)' % (esc(c), 0 if e is None else e, 'false' if e is None else 'true', i))
sum_k = ' '.join(kb)
chk_body = ('(let [o (decimal-f64-parse s)] (if some (if (option-some?-of [:option :f64] o) (if (= (f64-to-bits (option-value-of [:option :f64] o (f64-from-bits 0))) want) 0 (+ 1000 i)) (+ 1000 i)) (if (option-some?-of [:option :f64] o) (+ 1000 i) 0)))')
# first failure: fold with max over (+ ..) is enough as a signal; t = 1 when all zero
kir = ('{:format :kotoba.kir/v4, :entry nil, :exports [t], :signature nil, :effects #{}, :functions ['
       '{:name chk, :params [s want some i], :result :i64, :effects #{}, :body %s, :param-types [:string :i64 :bool :i64]} '
       '{:name pick, :params [a b], :result :i64, :effects #{}, :body (if (= a 0) b a), :param-types [:i64 :i64]} '
       '{:name t, :params [], :result :i64, :effects #{}, :body (let [r %s] (if (= r 0) 1 r)), :param-types []}]}\n')
fold = '0'
for x in reversed(kb): fold = '(pick %s %s)' % (x, fold)
open(os.path.join(H, 'parse.kir'), 'w').write(kir % (chk_body, fold))
src = ['(ns f64.parse (:export [t]))',
       '(defn chk [s :string want :i64 some :bool i :i64] :i64', '  ' + chk_body + ')',
       '(defn pick [a :i64 b :i64] :i64 (if (= a 0) b a))',
       '(defn t [] :i64 (let [r %s] (if (= r 0) 1 r)))' % fold]
open(os.path.join(H, 'parse.kotoba'), 'w').write(('\n'.join(src) + '\n').replace(' true ', ' (= 0 0) ').replace(' false ', ' (= 0 1) '))
print('cases', len(CASES), 'some', sum(1 for c in CASES if expect(c) is not None))
