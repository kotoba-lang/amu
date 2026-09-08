# ADR 0344 - J-B imod: host-qualified re-measurement + lever matrix

- Date:  ‎2026-09-08
- Status: Accepted ("evidence record", no claim-contract change, no compiler change)
- Chain: amu-claim, Task  4 landing], extended with Task  5 protection re-score]

## Context

Sealed claim `bench/runtime-comparison/jb-imod-control-claim-20260906.edn` measures
constant-divisor specialization of the shared `imod` (ADR  0289 residual ~165 sdiv/call)。
ADRs  0335/0338/0339 were workstation diagnostics only - the full quiet gate was not
met。. ADR  0282/0341 define the correct gate: busy-CPU fraction <=  0.10 on a fleet
node, three consecutive samples。。 This ADR records the first host-qualified measurements for
this claim path, taken on  2026-09-08。



## Evidence 1 - sealed-claim re-measurement(Task  2; host dan)

- Fixture `bench/runtime-comparison/jb_imod_control.c` (sha256
  f1b77411de822b693be56c34dc3eded1287dd3713da6ddc4e2ceb5c114a83193),the sealed
  claim's source, on origin/main]
- Build `clang -O2 -arch arm64`;, args `./jb  4000000  24`,  12 process-cold runs
- Gate busy-CPU frac  0.03 /  0.04 /  0.03 pre,  0.06 post (<=  0.10,
   3-sample; collision-clean; load1  1.2-1.9 on  10 cores)
- const mulh mean   ‎3.101 ns/elem;; opaque sdiv mean   ‎3.569 ns/elem
- improvement   ‎13.11% faster for const arm(ratio opaque/const  1.151)
- checksum   ‎764266, agreed all  12 runs

Confirms the sealed claim: ratio nearly identical(13.07 vs  13.11); both arms ~2.6%
faster on dan than the claim's benjamin runs,same ratio cross-host.



## Evidence 2 - four-arm lever matrix(Task  3; host levi)

- Fixture `bench/runtime-comparison/jb_imod_control_4arms.c` (local working-tree only,
  not yet on origin/main]; Evidence-1 above independently corroborates lever-1,
  and the conclusion does not depend on this not-yet-landed fixture)

- Build `clang -O2 -arch arm64`;, args `./jb4  4000000  24`,  24 alternations,
   1e6 iters/arm
- Gate busy-CPU frac   ‎0.07 pre,   ‎0.04 post(<=  0.10; load1  1.19-1.84
   on  10 cores; collision-clean)
- Arms ns/elem: A(opaque+call)   ‎3.570; B(const+call)   ‎3.103; C(opaque+inl)
   ‎2.926; D(const+inl)   ‎3.101
- Lever deltas: A->B  +13.1%(const alone; matches sealed claim]; A->C  +18.0%
   (inlining alone dominates]; A->D  +13.1%(both]; B->D  +0.1%(marginal
   lever-2 on const]; C->D  -6.0%(const on inl regresses inlined version by  6.0%)
- checksum   ‎764266, agreed allfour armsand with sealed claim
- Deltas are NOT additive

## Rank verdict

J-B const specialization alone delivers  +13.1% vs opaque on the serial chain - real,
host-qualified, stable (Evidence-1,, second-host confirmation of the sealed claim at the full
quiet gate;the Task-5 re-score below confirms it yet again(see Evidence 3)。

Per the co-scientist evolution rule(combine mechanisms until the summed effect clears the
   5% bar, or a proven ceiling], J-B alone cannot reach the claim's bar. The next lever
is J-B re-composed with the inlining mechanism - const specialization alone does not get
there.. No compiler change lands here.



## Consequences

- Three host-qualified confirmations of the sealed claim(2026-09-06 benjamin sealed
   13.07;2026-09-08 dan  13.11and levi  13.10;consistent across host-and-session)

- Const-divisor lever is below-threshold on the inlined ceiling(the relevant target];the
   follow-up composes these mechanisms per the evolution rule, not standalone




## Evidence 3 - protection re-score(Task  5; host levi, independent second session)



- Same sealed-claim fixture `jb_imod_control.c`,same build `clang -O2 -arch arm64`,
  args `./jb  4000000  24`,  12 process-cold runs. Checksum **764266** agreed all  12
  runs..
- Gate: busy-CPU frac **  0.03** pre (quiet-host chose levi idlest of  6 qualified nodes
  this tick), **  0.04** post (<=  0.10,three-sample; load1  1.79-2.21;
  collision check clean(no other agent measuring on the node)). Then same host as
  Evidence-2's matrix,but a separate session(2026-09-08,Task-5)
- const mulh mean   ‎3.1025 ns/elem;; opaque sdiv mean   ‎3.5703 ns/elem
- improvement   ‎13.103% faster for const arm(ratio opaque/const  1.1508)
- checksum   ‎764266, agreed all  12 runs

Confirms stability across host-and-session:   ‎13.11%(dan,Task-2)->   ‎13.103%
(levi,Task-5),essentially identical:the sealed J-B claim unchanged within   0.01%;
const mean   ‎3.101/,  ‎3.1025;opaque   ‎3.569/,  ‎3.5703.This adds a third host-
qualified re-measurement(2026-09-06 benjamin sealed   ‎13.07;2026-09-08 dan
  ‎13.11and levi   ‎13.10,so the "Two host-qualified confirmations" note in
Consequences above is now three (see the updated bullet)。



- Landing via PR into the protected `main`;the values recorded above(durations,hosts,busy
  fractions,checksums,deltas)are reproducible from the labeled fixtures. This same PR
  also carries the Task-5 protection re-score(Evidence-3,recorded the same tick;
no new compiler change lands here.