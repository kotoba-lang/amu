import sys
p='~/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/jit-cosientist.md'
s=open(p,encoding='utf-8').read()
add='''## Tick log (falsify — appended evidence notes)

- 2026-09-05 11:15 JST tick 9 (JIT): quiet gate failed an 8th consecutive time
  — load1 16.4–23.5 on 10 CPUs (falling trend through the tick), iostat cpu
  idle 65–79% across probes ~3 min apart, below the required ≥90%.
  J-B measurement again deferred, no compiler change, control unchanged at
  `bench/runtime-comparison/jb_imod_control.c`. Next: on a quiet host add the
  third (non-inlined mulh) arm to separate lever 1 from lever 2.

'''
marker='## Policy note (standing)'
assert s.count(marker)==1, s.count(marker)
s=s.replace(marker, add+marker, 1)
open(p,'w',encoding='utf-8').write(s)
print('OK appended')
