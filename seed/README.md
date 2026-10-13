# Adopted native seed compiler

This directory contains the complete 16-module source based on the adopted
compiler at `fc49cb2ee6fea1a41a5abbc8ed5b52aaa9f19471`, with an integration
safety fix: explicit `--policy` is refused with E2170 until structured policy
checking is qualified. Single-file and project `check` enforce the same explicit-policy refusal as `compile`. The bounded pure byte-result lookup pass is now adopted in `41-a64gen`, preserving every other module from main. It includes the cumulative qualified AArch64 optimizations; it
excludes the pending descriptor witness and conditional-fallthrough vector view
candidates. It does not change `bin/amu`, publish a
release, or qualify the whole Amu component as Q9.

`MANIFEST` fixes the unity order. Concatenating each module followed by one
newline gives SHA-256
`5d5f62e78cee595905b43df5d999ce71da3bdf97cb0bafdc7a6a99cb352cf844`.
`adoption-20261012.json` records all source pins, artifact provenance, the
correctness scope and measurement boundaries. `HEADS`, `MEMORY-MAP`, and `SIR`
are the corresponding compiler contracts, copied without changes.

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

## Fuel-load forwarding candidate (2026-10-13)

`42-layout` runs a post-fixup available-register pass (`flf-`): an exact context-fuel load
`ldr xD,[x7,#8]` becomes `mov xD,xS` or `nop` when every path proves `xS` still holds the
value last stored to or loaded from the counter. Every fuel store, charge, trap, call and
return is unchanged and nothing moves, so the published counter is identical at every
instant. On top of the sequential-scan main the native fixed point is `692b5653…`; 705
loads in the 39 stable images change, and differential runs over all exports, inputs and
fuel levels match main byte for byte (four runs that first hit the host time limit were
re-run without it and match). It is a candidate: speed results are local
exploratory CPU-time measurements on a busy host, recorded in
`docs/evidence/fuel-load-forwarding-20261013/README.md`. The total-C goal remains unmet.
