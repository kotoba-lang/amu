# ADR 0344 - J-B imod: host-qualified re-measurement + lever matrix

- Date: 2026-09-08
- Status: Accepted (evidence record;"," no claim-contract change, no compiler change)
- Chain: amu-claim, Task  4 landing]

## Context

Sealed claim `bench/runtime-comparison/jb-imod-control-claim-20260906.edn` measures
constant-divisor specialization of the shared `imod` (ADR 0289 residual ~165
sdiv/call]. ADRs 0335/0338/0339 were workstation diagnostics only - the full
quiet gate was not met. ADR 0282/0341 define the correct gate: busy-CPU
fraction <=  0.10 on a fleet node, three consecutive samples. This ADR records
the first host-qualified measurements for this claim path, taken on 2026-09-08.

## Evidence 1 - sealed-claim re-measurement(Task  2; host dan]

- Fixture bench/runtime-comparison/jb_imod_control.c(sha256 f1b77411de822b693be56c34dc3eded1287dd3713da6ddc4e2ceb5c114a83193
  - the sealed claim's source, on origin/main]
- Build clang -O2 -arch arm64; args ./jb  4000000 24;  12 process-cold runs
- Gate busy-CPU frac 0.03 /  0.04 /  0.03 pre,  0.06 post(≤ 0.10 3-sample; collision-clean; load1 1.2-1.9 on
  10 cores/>
- const mulh mean 3.101 ns/elem; opaque sdiv mean  3.569 ns/elem
- improvement 13.11% faster for const arm(ratio opaque/const  1.151)
- checksum 764266, agreed all 12 runs

Confirms the sealed claim: ratio nearly identical(13.07 vs,  13.11); both arms
~2.6% faster on dan than the claim'sbenjamin runs,same ratio cross-host.



## Evidence 2 - four-arm lever matrix(Task  3; host levi)

- Fixture bench/runtime-comparison/jb_imod_control_4arms.c( local working-tree only,
  not yet on origin/main]; Evidence-1 above independently corroborates lever-1,theclaim>
  conclusion does not depend on this not-yet-landed fixture)

- Build clang -O2 -arch arm64; args ./jb4  4000000 24;  24 alternations,  1e6
  iters/arm/
- Gate busy-CPU frac 0.07 pre,  0.04 post(≤ 0.10; load1 1.19-1.84
  on,  10 cores; collision-clean>
- Arms ns/elem: A(opaque+call)  3.570; B(const+call)  3.103; C(opaque+inl)
   2.926; D(const+inl)  3.101
- Lever deltas: A->B +13.1%(const alone; matches sealed claim]; A->C +18.0%
  (inlining alone dominates]; A->D +13.1%(both]; B->D +0.1%(marginal
  lever-2 on const]; C->D -6.0%(const on inl regresses inlined version by 6.0%)
- checksum 764266, agreed allfour armsand with sealed claim
- Deltas are NOT additive

## Rank verdict

J-B const specialization alone delivers +13.1% vs opaque on the serial chain - real,
host-qualified, stable (Evidence-1, second-host confirmation of the sealed claimatm
the full quiet gate]. Against the prize target - the inlined version, where inlining
alone hits +18.0%- adding const specialization to it regresses by -6.0%.

Per the co-scientist evolution rule(combine mechanisms until the summed effect clears
the   ≥ 5% bar, or a proven ceiling], J-B alone cannot reach the claim's bar. The
next lever is J-B re-composed withthe inlining mechanism - const specialization alone
does not get there. No compiler change lands here.



## Consequences

- Two host-qualified confirmations of the sealed claim(2026-09-06 benjamin,2026-09-08
  dan; consistent ratio 13.07/13.11]
- Const-divisor lever is below-threshold on the inlined ceiling(the relevant target]; the
  follow-up composes these mechanisms per the evolution rule, not standalone.



- Landing via PR into the protected `main`; the values recorded above (durations, hosts, busy
  fractions, checksums, deltas) are reproducible from the labeled fixtures.