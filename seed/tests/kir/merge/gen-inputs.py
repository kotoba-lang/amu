#!/usr/bin/env python3
"""seed/tests/kir/merge/gen-inputs.py <out-dir> [scale] -- deterministic inputs of the merge test (agent KIR3, BOOTSTRAP-TOOL:
test data only, never in a seed's process tree). Writes <out-dir>/{case,kstring,posix}.in; the same bytes on every run
(random.Random(20261003)). scale (default 1) multiplies the random case counts (timing runs use 20). The answers are not computed here: the test compares the stage-0 native run with the seed's
native run of the same guest on these bytes (merge.sh).

  case.in     every Unicode scalar value (U+0000..U+10FFFF without surrogates) once, one per line, then 4,000 lines of
              3..40 random code points (ASCII, Latin-1, Greek, Cyrillic, CJK, astral) -- kotoba.string.case/upper-case-root
  kstring.in  20,000 cases "<op><a>\\t<b>\\t<c>" over the guest's 16 ops (kotoba.string, kotoba.compiler.decimal-text)
  posix.in    20,000 cases "<op><path>" / "j<a>\\t<b>" (kotoba.compiler.posix-path basename dirname normalize join)
"""
import os
import random
import sys

R = random.Random(20261003)
SCALE = int(sys.argv[2]) if len(sys.argv) > 2 else 1
ATOMS = ['a', 'b', 'x', '0', '1', '2', '9', '-', '.', ' ', '  ', '\r', '\x0b', '\x0c', 'é', '日', '　',
         ' ', '\U0001F600', 'ab', 'bc', 'abc']


def word(lo=0, hi=8):
    return ''.join(R.choice(ATOMS) for _ in range(R.randint(lo, hi)))


def number():
    k = R.random()
    if k < 0.5:
        return str(R.randint(-10**12, 10**12))
    if k < 0.6:
        return str(R.choice([0, 1, -1, 9223372036854775807, -9223372036854775807]))
    if k < 0.8:
        return ' '.join(str(R.randint(0, 999)) for _ in range(R.randint(0, 6)))
    return word(0, 5)


def case_in():
    out = [chr(c) for c in range(0x110000) if not 0xD800 <= c <= 0xDFFF and c != 10]
    pools = [(0x20, 0x7e), (0xa0, 0x24f), (0x370, 0x3ff), (0x400, 0x4ff), (0x1e00, 0x1fff), (0x4e00, 0x4e80),
             (0x10400, 0x1044f), (0x1f600, 0x1f64f)]
    for _ in range(4000 * SCALE):
        s = []
        for _ in range(R.randint(3, 40)):
            lo, hi = R.choice(pools)
            s.append(chr(R.randint(lo, hi)))
        out.append(''.join(s))
    return '\n'.join(out) + '\n'


def kstring_in():
    ops = 'seibtlrvxypukDPF'
    lines = []
    for _ in range(20000 * SCALE):
        op = R.choice(ops)
        if op in 'DF':
            a, b, c = number(), '', ''
        elif op == 'P':
            a, b, c = str(R.randint(-10**15, 10**15)), '', ''
        else:
            a = word(0, 10)
            b = word(1, 3) if R.random() < 0.6 else (a[R.randint(0, len(a)):] if a else 'a')
            if not b:
                b = 'a'
            c = word(0, 3)
        lines.append(op + a + '\t' + b + '\t' + c)
    return '\n'.join(lines) + '\n'


SEGS = ['', '.', '..', '...', 'a', 'bb', 'src', 'kotoba', 'x.cljk', '.hidden', 'é', '日本']


def path():
    p = '/'.join(R.choice(SEGS) for _ in range(R.randint(0, 6)))
    if R.random() < 0.4:
        p = '/' + p
    if R.random() < 0.3:
        p = p + '/'
    return p


def posix_in():
    lines = []
    for _ in range(20000 * SCALE):
        op = R.choice('bdnj')
        lines.append(op + (path() + '\t' + path() if op == 'j' else path()))
    return '\n'.join(lines) + '\n'


def main():
    d = sys.argv[1]
    os.makedirs(d, exist_ok=True)
    for name, f in (('case', case_in), ('kstring', kstring_in), ('posix', posix_in)):
        with open(os.path.join(d, name + '.in'), 'wb') as h:
            h.write(f().encode('utf-8'))


if __name__ == '__main__':
    main()
