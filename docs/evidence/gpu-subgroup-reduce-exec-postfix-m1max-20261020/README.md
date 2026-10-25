# gpu-subgroup-reduce-exec-postfix-m1max-20261020 — the FIXED :subgroup-reduce emission, executed (tick 20261020-0556, JUN-59/60 on the JUN-58 host)

## The finding this tick

**The post-fix `:subgroup-reduce` GLSL emission (4b7a1ccb: per-feature
extensions, `gl_SubgroupInvocationID`, strided cross-subgroup fold, infinite
extrema identities) executes on Apple M1 Max / MoltenVK and verifies
bit-exactly on all 14 cases — `RESULT ran=14 failed=0 not-admitted=0`** —
including the four cases that DISCRIMINATE the extrema-identity fix. This is
the first device execution of the fixed bytes; before this tick they had
glslang-compile evidence only (4b7a1ccb's message).

| shape | cases (x[i] unless `fill=`) | result |
|---|---|---|
| W64-sum | n=64 → 2080; n=50 → 1275 | OK, bits exact |
| W64-max | n=64 → 64; n=50 → 50; n=50 **fill=-Inf → -Inf (bits 4286578688)** | OK |
| W64-min | n=64 → 1; n=50 → 1; n=50 **fill=+Inf → +Inf (bits 2139095040)** | OK |
| W256-sum | n=256 → 32896; n=200 → 20100 | OK |
| W256-max | n=256 → 256; n=200 **fill=-Inf → -Inf** | OK |
| W256-min | n=256 → 1; n=200 **fill=+Inf → +Inf** | OK |

All six shapes compiled as-emitted (no rung patches — the fix made the
emitter produce exactly the form PR #1346's `:categories+id` rung measured).
The identity discriminators are the fix's proof: with x[i] = -Inf for all
i < n at n < W, the pre-fix finite `-FLT_MAX` identity answers -FLT_MAX
(bits 4286578687) and the answer must be -Inf; the verifier self-tests prove
the pre-fix pattern is refused by name before the first dispatch.

## Provenance (run-time, in-process)

- bytes generated in the probe process by the real `emit-glsl` (ns required
  from `src/`), each shape emitted twice and compared before dispatch;
- `head=e7a5b164d6d1eedd126d5cb20892094a80e4fca8`,
  `emitter-sha256=ce3d52dd6c30d1baf97458e7011456f920ced0f707d082fd8f97185a661aed6f`;
- per-shape sha256 in the log header (W64-sum = `5d9b4bfc…`; note it differs
  from the pinned pre-fix fixture `a25a6931…`, as it must).

## Honest scope

- **Correctness only. No timing line is printed and none may be claimed.**
  (Host load1 was 48–59 during this tick — the same confound that made tick
  0530's sign-probe anchor INCONCLUSIVE.)
- **The cross-subgroup fold fix is UNEXERCISABLE on this host**: the buggy
  form misfolds only when the cross stage's first stride d = nsub/2 exceeds
  the subgroup size S, i.e. W > 2·S² — S=32 on M1 Max means W > 2048, above
  KIR's admitted ceiling of 1024. The fix targets small-S devices (Intel
  8/16, Mali 4–32): JUN-59/JUN-60 hardware this bot does not have.
- **Replication: 1 fresh process this tick** (run-1.log, sha256
  `77c0a8f9…`). The PR #1346 three-process byte-identical protocol is
  STARTED, NOT FINISHED — the cron run budget ran out; runs 2–3 are the next
  tick's first command.
- **Fixture regeneration remains OPEN.** This tick is the execution half of
  the evidence-chain follow-up named in 4b7a1ccb. Regenerating
  `test/fixtures/gpu/subgroup-reduce-w*-sum.emitted.glsl` is deliberately NOT
  done here: the pinned cross-tick sign-probe chain (PR #1390,
  `scripts/gpu-subgroup-reduce-chunksweep-pinned-3696ca0d.cljk`) sha256-pins
  the pre-fix fixture bytes at those paths and would refuse (COULD-NOT-RUN)
  if they changed. The chain must carry its own fixture copies (or re-pin)
  before regeneration lands — recorded here so the trade is visible.
- Nothing flips `:measured?` in `kotoba.compiler.accelerator-targets`; the
  variant basis stays `:measured? false`. One device, one vendor.
- nbb quirk measured this tick: the literal `js/-Infinity` resolves to NaN
  (0x7FF80000) on this engine; the probe spells -Inf as `(- js/Infinity)`.

## Tests / gate

Evidence + one probe script: no src/test namespace, no `run-tests.cljk`
change — **gate not run** (nothing to gate). Base suite state as measured on
PR #1388 (exact base cc2b2362): 311 tests / 4973 assertions, 16 failures /
17 errors, red set outside every amu-gpu diff — not green, and not claimed
green here.
