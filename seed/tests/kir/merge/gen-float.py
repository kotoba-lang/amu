#!/usr/bin/env python3
"""seed/tests/kir/merge/gen-float.py <out-file> [scale] -- KIR5: deterministic f64 bit patterns for float.cljk (one signed
decimal i64 per line): every f64 exponent around the f32 range edges with random and boundary mantissas (ties, half-ulp,
carry into the exponent, overflow to infinity, f32 subnormals, f64 subnormals, zeros), infinities and NaNs (quiet,
signalling, payloads), both signs, plus 20,000 x scale random patterns. BOOTSTRAP-TOOL: test data only."""
import random
import struct
import sys

R = random.Random(20261003)
scale = int(sys.argv[2]) if len(sys.argv) > 2 else 1
M52 = (1 << 52) - 1
out = []


def put(sign, e, m):
    u = (sign << 63) | (e << 52) | (m & M52)
    out.append(u - (1 << 64) if u >= 1 << 63 else u)


edge_m = [0, 1, 2, M52, M52 - 1, 1 << 28, (1 << 28) - 1, (1 << 28) + 1, 1 << 29, (1 << 29) - 1, (1 << 29) + 1,
          (1 << 29) | (1 << 28), ((1 << 23) - 1) << 29, (((1 << 23) - 1) << 29) | (1 << 28), 1 << 51, (1 << 51) | 1]
for sign in (0, 1):
    for e in list(range(0, 4)) + list(range(1023 - 160, 1023 + 131)) + list(range(2040, 2048)):
        for m in edge_m:
            put(sign, e, m)
        for _ in range(4):
            put(sign, e, R.getrandbits(52))
for _ in range(20000 * scale):
    out.append(struct.unpack('<q', struct.pack('<Q', R.getrandbits(64)))[0])
for x in (0.0, -0.0, 1.0, -1.0, 0.1, 3.4028235677973366e38, 3.4028234663852886e38, 1.401298464324817e-45,
          7.006492321624085e-46, 7.006492321624087e-46, 1.1754942106924411e-38, float('inf'), float('-inf')):
    out.append(struct.unpack('<q', struct.pack('<d', x))[0])
open(sys.argv[1], 'w').write(''.join('%d\n' % v for v in out))
