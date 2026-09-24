#!/usr/bin/env python3
"""tick 11 (JIT): append J-B evidence to docs/jit-cosientist.md (append-only, single anchor)."""
P = '~/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/jit-cosientist.md'
ANCHOR = 'NEXT unchanged: idle>=9/10 rerun.'
ADD = (
    ' 2026-09-05 03:41 JST tick 11 (JIT): third window, quieter still (load1 6.3\u20137.8 on 10 CPUs,'
    ' iostat idle 45\u201381% \u2014 full gate idle\u22659/10 again NOT met, moderate concurrent IO).'
    ' 4000000 iters \u00d7 24 alternations ABBA, 3 runs: saving **+6.7% / +6.9% / +7.1%**'
    ' (opaque 5.118/5.130/5.161 vs const 4.775/4.776/4.796 ns/elem, ratios 1.072/1.074/1.076),'
    ' checksums agree (764266). **Nine consecutive positive runs across three windows**;'
    ' effect ~6\u20137%, stable. Verdict: the C-proxy falsification attempt has failed 9 times'
    ' \u2014 J-B survives every proxy-level kill attempt. Still **diagnostic only, not perfgate-qualified**'
    ' (no fully quiet window) and not amu-end-to-end. Next: real runtime specialization in kotoba-native'
    ' measured via bench/runtime-comparison + perfgate.core/qualify; fully-quiet proxy window when available.'
)
s = open(P, encoding='utf-8').read()
n = s.count(ANCHOR)
assert n == 1, f'anchor count {n}'
i = s.index(ANCHOR) + len(ANCHOR)
open(P, 'w', encoding='utf-8').write(s[:i] + ADD + s[i:])
print('appended ok')
