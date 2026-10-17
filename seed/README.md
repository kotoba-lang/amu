# Adopted native seed compiler

The 2026-10-12 adoption is the 16-module compiler baseline at
`fc49cb2ee6fea1a41a5abbc8ed5b52aaa9f19471`, with an integration safety fix:
explicit `--policy` is refused with E2170 until structured policy checking is
qualified. Single-file and project `check` enforce the same refusal as
`compile`. The bounded pure byte-result lookup pass is adopted in `41-a64gen`;
it includes the cumulative qualified AArch64 optimizations and excludes the
pending descriptor witness and conditional-fallthrough vector view candidates.
`preserved-20261012/adoption.json` pins the preserved 16-module baseline.
`adoption-20261012.json` retains the later main m105 16-module source and its
qualification metadata; it is no longer the current source receipt.

The current `MANIFEST` has 17 modules. It adds the experimental
`43-wasm.kotoba` browser-Wasm backend and the project driver/lock changes
described below. The historical 16-module adoption receipt remains tied to its
original source. `adoption-20261017.json` pins the current 17-module source and
the G23 selfhost-built compiler image; the 2026-10-12 receipt is historical.
The current 17-module unity source used for the G23/G24 selfhost fixed-point
probe has SHA-256
`7b2786e18a6cf7677ef281ffd387bc084dea3e5ca0b591f4e1b545b74c881841`.

These changes do not change `bin/amu`, publish a release, or qualify the whole
Amu component as Q9.

## Native self-build

The source-derived, selfhost-built bootstrap image is
`bootstrap/adopted-20261012.bin` (macOS arm64, entry offset 0, arity 0). It is a
native code payload used by the pinned C loader, not a standalone OS executable.
The loader is trusted C bootstrap infrastructure; this is not a C-free claim.
The Python script orchestrates the native compiler and Clang loader build only;
it never compiles Kotoba through Python, Node, nbb, JVM or GraalVM.

Verify the immutable source and bootstrap pins on any host:

```sh
python3 scripts/seed/build-adopted.py --verify-only
```

On macOS arm64, rebuild three generations into a new, empty task workspace:

```sh
python3 scripts/seed/build-adopted.py \
  --output /Users/junkawasaki/github/workspaces/codex/seed-adopted-selfbuild-new
```

The script refuses existing outputs, places its host loader/logs outside the guest-writable artifacts directory,
refuses input or loader changes during an invocation, preserves original logs,
checks every generated native image against the adopted fixed-point digest,
and leaves compiler fuel disabled only for these self-build invocations.
This is correctness verification, not performance timing.

## Locked browser-Wasm project pilot (2026-10-17)

The selfhost seed compiler can compile a closed, content-addressed Kotoba
project for `wasm32-browser`:

```sh
<selfhost-seed-compiler> compile <root-namespace> \
  --target wasm32-browser \
  --module-lock <module-lock.edn> \
  --blocks <raw-cid-block-directory> \
  --output <package>
```

The lock uses the closed `:kotoba.module-lock/v1` schema with one root
namespace and a namespace-to-raw-CID map. The compiler reads each source block,
verifies its raw CID with SHA-256 before parsing it, and refuses source-path or
unpinned fallback on this route. Malformed or missing pins fail with E6027;
a source/CID mismatch fails with E6028. The native selfhost loader must grant
the required wires `3,35,37,38,39`; wire 3 supplies `:hash/sha256` for pin
verification.

A single-module root emits the direct Wasm module. A multi-module root emits a
`KOTOBAP1` package in dependency-first order; its module interfaces become
namespace-qualified Wasm imports. Target support is deliberately narrow:
unsupported source is refused with E6029 rather than widened or sent through a
bootstrap compiler. Host behavior must be supplied and qualified by the app's
typed adapter.

The 17-module source rebuilt G23 and G24 from a selfhost-produced compiler.
Both generations have byte-identical 2,593,280-byte native compiler images
(SHA-256
`2f8409005633506046c4df7e3eac1f7ad11acd40f092691c72afc2f7edce5dcd`). This
is a compile-only selfhost fixed-point result: it does not establish application
runtime parity, test-suite completion, deployment, or live behavior.
The current receipt records the G22 input, G23/G24 outputs, and source pins;
`scripts/seed/build-adopted.py` uses G23 to reproduce the fixed point in the
native CI path.

## Evidence and ongoing optimization

The original adopted source passed 39 native-image reviews, 483 paired original
comparisons (95 profile, 76 low-fuel, 312 interaction), 68 fresh generic pairs,
and 32 bootstrap success pairs. Historical validation is tied to the exact
source and artifact hashes; it is not silently relabeled a new main run.

Round 83 measured all 19 workloads using the upstream Embench speed driver
and formula. Kotoba execution time / C execution time has geometric mean
2.936403450579294, so C is faster overall. This translated-port measurement is
exploratory, not a certified official Kotoba score. It is not a released-CLI
performance result, and there is no minimum-percent adoption cutoff.

The C-or-faster optimization goal is **active and unmet**. Pending candidates
and their evidence remain in separate preserved worktrees.

`bounded-lookup-integration-20261012.json` records the adopted generic pass.
It admits only proven private, uncharged, pure byte-result threshold trees;
it preserves the old code, return registers and flags and adds a bounded
immutable lookup table. Both Pico and QR original/functional images passed
complete code/reference/pool/export audits. The candidate ran all 483 original
cases, 577 Pico domain/boundary pairs and 52 distinct generic acceptance/refusal
pairs. After composition with the latest main policy guards, all 39 native
images and containers were regenerated and proved whole-byte identical to
those tested images. The runtime cases are reused by that actual identity,
not claimed as another fresh 483-case run.

Fixed two-pair measurements on Joseph, with raw CPU idle at least 70%, gave
candidate/prior execution-time ratios 0.9791489779557238 for Pico and
0.9923011307968419 for QR. Both individual pairs improved in each workload.
These exploratory measurements support adopting small improvements without
a percentage cutoff; they are not confidence intervals or a new official
Embench score. Round 83 above remains the historical pre-lookup snapshot. The current-source
round 88 comparison is recorded below; separate cycles do not establish the
size of an individual optimization gain.

Public report: <https://kotoba-lang.org/ja/blog/embench-progress-20261012/>

The historical preservation branch is separately re-integrated under `preserved-20261012/`; see its README for the safety-fixed source and receipt. Current main optimization modules and public CLI/loader are retained.

Explicit `--policy` without a following value is also refused with E2170, never interpreted as policy-free.

## Certified scalar-call descriptor reuse (2026-10-13)

The reviewed source snapshot at `9b7816daf99bd65089e57edcc915e39595c120f7` preserves a checked vector descriptor after one complete typed scalar-call certificate. The second certificate band remains supported. Each vector read restarts the count, and writes to the tracked slot invalidate both bands. All original index checks and traps remain. Admission uses source types and emitted instruction effects; workload names do not select the optimization.

This snapshot has a native three-generation fixed point, 39 freshly generated images, the original 483 exact result/fuel/state observations, and 54 generic paired controls. Five original images contain 23 additional same-layout descriptor-check bypasses; the other 34 images are unchanged. Standard integration also passes 52 lookup controls, 480 comparison pairs, 34 policy refusals and all 19 archived native image hashes.

Round 87 fixed four-slot exploratory timing measured slre about 0.720157% shorter (mixed individual pair signs) and sglib-combined about 0.680174% shorter (both pairs improved). Round 88 measured all 19 translated workloads and a fresh C timing cycle using the unchanged upstream driver/formula: normalized Kotoba execution time / C is 2.946404197283788. C remains faster overall. These are exploratory translated-port results, not a certified official Embench score, per-MHz result or stable statistical gain. The overall C-level-or-better goal remains active and unmet. Small validated improvements have no minimum percentage cutoff.

`docs/evidence/onecall-descriptor-20261013/` preserves the previous two-argument receipt/bootstrap, qualification results and paired timing. The full round 88 raw logs and independent review are in `/Users/junkawasaki/github/workspaces/codex/embench-total-C-round88-onecall-20261013-v1/`. Earlier certified-call, lookup, golden-corpus and paused evidence remains historical. Integration is tracked by PR #1298 and remote-main readback; candidate qualification alone does not establish a merge.

## Bounded sequential zero scans (2026-10-13)

The source snapshot at `6194efcc` expands the existing certified private scan
for lengths 2 through 8. It retains every ordered load, pointer step,
flag-setting countdown and early exit. A shared nonzero bridge preserves the
old cold-path hook; the all-zero seven-read path executes six fewer
instructions. The existing JDF descriptor/fuel handoff recognizes the exact
expanded recipe and keeps its original entry and frame proofs. This introduces
compiler-local proof cells only; the runtime descriptor, fuel and arena ABI
remain unchanged.

All 39 images were freshly generated by the native G1/G2/G3/G4 fixed point.
The two Pico images changed by the declared scan and inline-table alignment;
the other 37 are whole-byte identical to the previous snapshot. Full physical
audits preserve every other instruction, reference, export and data word.
The original 483 runtime observations pass with exact result, fuel and all
17 arena counters. The changed machine recipes also pass 20,480 register,
NZCV and ordered-read comparisons.

Round 90 on Joseph used fixed N and OFF/ON/OFF/ON, with CPU idle at least 70%
and every attempt retained. Pico candidate/prior time was 0.9600493940364256
(about 3.995061% shorter), with pair ratios 0.9656418577683079 and
0.954484325981963. This supports adoption without a 5% cutoff. It is an
exploratory two-pair observation, not a stable statistical gain or a new
full19 C comparison. Round 88 above remains the latest full19 result, and
the C-level-or-better goal is active and unmet.

`docs/evidence/sequential-scan-20261013/` preserves the previous bootstrap,
qualification and timing evidence. Native acceptance/refusal controls run with:

```sh
python3 scripts/seed/check-sequential-scan.py --selfbuild-output <native-selfbuild-output>
```

## Proven nonnegative power-of-two quotients (2026-10-13)

Source snapshot `2b0293e3` adds a bounded final-code interval proof. A complete
low-bit mask, constant, move or multiplication chain may prove the dividend
nonnegative, with signed64 overflow refused. A two-word forward branch skips
the old signed bias only when all incoming roots are excluded and scratch x17
is dead before its next overwrite. The same-input/output ASR, instruction
layout, NZCV, fuel and arena behavior remain. Unknown definitions, incoming
edges, scratch reads and proof-budget exhaustion retain the original code.
The existing signed lowering and all earlier source-owned kernels are kept.

The native G1/G2/G3/G4 fixed point generated all39 images. Only the two Pico
images changed, with12 proved sites each; all other37 are whole-byte identical.
Original483 observations and152 independent full64 pairs pass with exact
result, fuel and17 arena fields. The admitted437,592 dividend values match,
and native compiler-local controls verify range, root, scratch, overflow and
budget refusals.

Round92 fixed4 timing on Joseph observed candidate/prior median time
0.979809938593011, about2.019006% shorter. Individual ratios were
1.0002118318409012 and0.9603658112450705: one was nearly equal and one improved.
This is exploratory evidence, with mixed pair signs and no stability claim.
There is no5% minimum cutoff. Round91's C tarfind failed its70% raw-idle gate
on all3 attempts, so no full19 C ratio was produced. Round88 remains the last
complete comparison at Kotoba/C2.946404197283788; the overall goal is active
and unmet. This snapshot does not claim a certified official Embench score.

Previous bootstrap, raw evidence and portable proofs are retained under
`docs/evidence/positive-quotient-20261013/`. Native controls run with
`scripts/seed/check-positive-quotient.py` and
`scripts/seed/check-positive-quotient-proof.py`, each taking
`--selfbuild-output <native-selfbuild-output>`.

The direct mask source snapshot fuses a mask writer's register copy into its low8-bit extraction.65 sites change in each Pico image; all other37 images are identical. Native four-generation identity, original483 observations and192 generic pairs (368 guests plus16 loader configuration refusals) pass. Fixed4 Joseph Pico timing was about1.767310% shorter, with both pair signs positive; this remains exploratory without a stability claim. Small validated gains have no5% cutoff. Full19 C parity remains unproven; incomplete rounds93/94 produce no total ratio. Evidence: [direct mask fusion](../docs/evidence/mask-direct-source-20261013/README.md).

Fully prepaid clamp/mask cores reuse initialized x8=CTX-FUEL. Both Pico images remove12 loads+12 stores under full paid-region/entry/index/nonalias/reference/export proofs;37 other images stay whole identical. Original483 observations,84 source-oracle pairs and512 fuel boundary pairs pass (1192 generic guests). Locked Pico fixed4 was2.815160% shorter with both pair signs positive, exploratory without a stability claim. No5% cutoff. Prior store-only round97 is preserved unadopted because both pairs were slower. At qualification preparation, last complete full19 is prior-main round96 ratio2.8739381568053983; this candidate's freshfull19 comparison is pending. Goal active/unmet. [Evidence](../docs/evidence/fuel-register-reuse-20261014/README.md).

## Same-algorithm m105 adoption (2026-10-16)

The adoption receipt pins the reviewed m105 source unity and fixed-point
bootstrap. The exported-tree review correction keeps the decision-tree source
rewrite private, so exported definitions retain their reviewed native body.
G1, G2 and G3 are byte-identical at SHA-256
`6b158aa8654706743462b8a730f189072ba05f364b00af28a3f6d23045add2eb`.
Rebuilding two generations from the adopted image reproduces the same digest.
The regenerated 19 policy-native golden images are pinned in the receipt.
Local validation covers 483/483 observations, 19/19 exact workload fuel/arena
checks, all ten adopted-native regression controls, and 30,888 differential
cases against the prior m105 image with zero mismatches. The main policy
integration also reproduced all 19 pinned original images and passed all 34
explicit policy refusals.

No official m105 Embench round was run. The published 0.8213 ratio remains
specific to the m104 compiler and its pinned images. See
[`docs/evidence/same-algo-m105-20261016/`](../docs/evidence/same-algo-m105-20261016/),
the historical 2026-10-12 receipt at `adoption-20261012.json`, and the current
17-module receipt at `adoption-20261017.json`.
