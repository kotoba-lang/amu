p='docs/jit-cosientist.md'
s=open(p,encoding='utf-8').read()
anchor='fully-quiet proxy window when available.\n| J-C |'
assert anchor in s, 'anchor missing'
add='2026-09-05 04:18 JST tick 12 (JIT): fourth window (load1 8.3\u21927.1 on 10 CPUs, iostat idle 60\u201384% pre-run \u2014 full quiet gate idle\u22659/10 again NOT met, moderate IO). 4000000 iters \u00d7 24 alternations ABBA, 2 runs: saving +6.4% / +6.9% (opaque 5.248/5.124 vs const 4.912/4.769 ns/elem, ratios 1.068/1.074), checksums agree (764266). Eleven consecutive positive runs across four windows; effect 6\u20137%, unchanged in sign and magnitude. Verdict unchanged: C-proxy kill attempt has failed 11 times; J-B survives, diagnostic only, not perfgate-qualified, not amu-end-to-end. No compiler change made. Next unchanged: real runtime specialization in kotoba-native via bench/runtime-comparison + perfgate.core/qualify. '
s=s.replace(anchor,'fully-quiet proxy window when available. '+add+'| J-C |',1)
open(p,'w',encoding='utf-8').write(s)
print('WROTE', 'tick 12' in s)
