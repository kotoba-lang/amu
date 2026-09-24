import io
p='~/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/jit-cosientist.md'
lines=open(p).read().split('\n')
add=" 2026-09-05 01:42 JST tick 7 (JIT): host measurably quieter (load1 4.8-7.1 on 10 CPUs, iostat idle 33-62% - first majority-idle window in 7 ticks; full quiet gate idle>=9/10 still not met). Deferred measurement ran: 3 consecutive runs, saving +6.2% / +7.0% / +6.7% (opaque 5.322/5.152/5.174 vs const 4.990/4.793/4.825 ns/elem, ratios 1.067/1.075/1.072), checksums agree (764266). Sign consistent for the first time, unlike the six prior busy-host runs. First positive separated signal: ~6-7% at/above the 5% bar; hypothesis still neither killed nor confirmed under a fully quiet host. ADR 0335. Next: quiet-host rerun for a perfgate-qualifiable number; if held, AOT constant-divisor specialization lever."
assert lines[21].startswith('| J-B'), lines[21][:20]
lines[21]+=add
open(p,'w').write('\n'.join(lines))
print('OK')
