# Adopted native seed compiler

> **2026-10-22: the trusted C loader was removed.** Instructions below that build
> or run it (clang, `kexe-loader`, `scripts/seed/build-*.py`, `check-*.py`) are
> historical and no longer runnable; see `scripts/seed/RETIRED.md`. The current
> route is `scripts/seed/selfhost-bootstrap.py` on arm64 Linux.


This directory contains the complete 16-module source based on the adopted
compiler at `fc49cb2ee6fea1a41a5abbc8ed5b52aaa9f19471`, with an integration
safety fix: explicit `--policy` is refused with E2170 until structured policy
checking is qualified. Single-file and project `check` enforce the same explicit-policy refusal as `compile`. The bounded pure byte-result lookup pass is now adopted in `41-a64gen`, preserving every other module from main. It includes the cumulative qualified AArch64 optimizations; it
excludes the pending descriptor witness and conditional-fallthrough vector view
candidates. It does not change `bin/amu`, publish a
release, or qualify the whole Amu component as Q9.

`MANIFEST` fixes the unity order. Concatenating each module followed by one
newline gives SHA-256
`a1a718388c55eaf8e9f749ea1829c17ae9d667dbc785194879b0abb8454602b3`.
`adoption-20261017.json` records the current source pins, bootstrap and
fixed-point image separately, artifact provenance, correctness scope, and
measurement boundaries. `adoption-20261012.json` remains the historical
receipt for the prior source closure. `HEADS`, `MEMORY-MAP`, and `SIR`
are the corresponding compiler contracts, copied without changes.

## Current selfhost acceptance

The accepted compiler/build/runner closure is canonical Kotoba plus an
Amu-built, loaderless native compiler. It must build and rebuild the complete
compiler without C compiler/loader/runtime, Node/NBB/KBB or JVM dependencies.
The required Linux CDCI artifact is `x86_64-linux-static`; the controller has
the same native-only requirement. See `../docs/selfhost-priority.md` and
`../AGENTS.md`.

The recorded CLI image paths from the 2026-10-19 selfhost reports were absent
when checked on 2026-10-22. The checked-in bootstrap below is a raw payload,
and the raw-ELF runner evidence is a probe, not a whole compiler. A currently
available independent compiler/runner and exact full-closure native
build/execution evidence remain open. Do not report this source checkout or
the historical pin checks as native selfhost qualification.

## Durable file replace and sleep in the static runtimes (2026-10-23, JUN-359, JUN-360)

seed/76 and seed/77 answer wire 35's `FSYNC_SEP` (a file or directory, opened beneath the scope) and `RENAME_SEP`
(each parent opened beneath the scope, `renameat` of the last component), so a file can be replaced durably, and
wire 7 `:clock/now` takes `sleep <ms>` (0..60000, `clock_nanosleep` in the seccomp filter only with the wire
granted). The root is re-pinned (previous root -> F1, F1 -> F2, F2 -> F3 = F2). Verification and what stays open:
[`../docs/durable-sleep.md`](../docs/durable-sleep.md).

## Stdin in the static runtimes (2026-10-23, JUN-354, JUN-357)

seed/76 and seed/77 answer wire 41 `:io/read` (stdin to end of file, or one read of at most n bytes, completed
to a whole UTF-8 character; `read(0)` is in the seccomp filter only with the wire granted), and wire 20 takes an
optional stdin payload after `STDIN_SEP`, written to the child's stdin without blocking past the deadline. The
root is re-pinned (previous root -> F1, F1 -> F2, F2 -> F3 = F2). Verification, receipts and what stays open:
[`../docs/static-stdin.md`](../docs/static-stdin.md).

## Historical C-loader bootstrap provenance

The current source is bootstrapped from
`bootstrap/adopted-20261012.bin` (macOS arm64, entry offset 0, arity 0). The
current source's three-generation fixed-point image is recorded separately in
`adoption-20261017.json`; the bootstrap file remains unchanged. It is a native
code payload used by the pinned C loader, not a standalone OS executable.
This is historical bootstrap infrastructure, outside the accepted selfhost
and CDCI closure. The Python script orchestrates the native payload and Clang loader build only;
it never compiles Kotoba through Python, Node, nbb, JVM or GraalVM.

`scripts/seed/build-adopted.py` preserves historical reproduction, including
its source/loader pin checks. Neither its verify-only mode nor its C-loader
build is a current acceptance prerequisite or a replacement native gate.

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

The 2026-10-16 receipt pins the earlier m105 source and fixed-point bootstrap.
The current source closure adds the `enc-smulh` lowering and is pinned by
`adoption-20261017.json`. Starting from the historical bootstrap, its G1, G2,
and G3 images are byte-identical at SHA-256
`b10e381344a1f5a8b82cac981c0011bd20ecbcc4b48dd5f5dce97364c74e8a00`. The 19
policy-native golden images remain pinned to their historical source and
compiler; the current receipt records those reference hashes separately.
The main-source correctness check also pins the current M105 build report,
image manifest, and exactness record so rebuilt images are compared with the
current source outputs while the historical archive keeps its original hashes.
The earlier adoption's local validation covered 483/483 observations, 19/19
exact workload fuel/arena checks, all ten adopted-native regression controls,
and 30,888 differential cases against the prior m105 image with zero
mismatches. The new source's self-host rebuild evidence records G1/G2/G3
identity; CI validates its source pins and integrations.

No official m105 Embench round was run. The published 0.8213 ratio remains
specific to the m104 compiler and its pinned images. See
[`docs/evidence/same-algo-m105-20261016/`](../docs/evidence/same-algo-m105-20261016/),
the historical receipt at `adoption-20261012.json`, and the current receipt at
`adoption-20261017.json`.

## Loaderless bootstrap (2026-10-22)

The C loader is no longer needed to build or rebuild anything here. The root
is `bootstrap/aarch64-linux-static-root.elf` (receipt
`bootstrap/aarch64-linux-static-root.json`), an Amu-produced
`aarch64-linux-static` compiler. On arm64 Linux,
`scripts/seed/selfhost-bootstrap.py` rebuilds the Linux selfhost closure from
it (S1 = S2 = S3 = root), builds the aarch64/x86_64 runners and the x86_64
compiler, then builds the adopted compiler core (ADR 0370) from source: S3
compiles `CORE-STATIC-MANIFEST` (the core with the static-profile namespace
`00-ns-static.kotoba`) to a static image C0, C0 compiles `MANIFEST` to G1,
and the aarch64 runner takes G1 and G2 to G2 and G3: G1 = G2 = G3 = the
adoption fixed point. `bootstrap/adopted-20261012.bin` is no longer an input
of any build. S3 then packs G3 (`--format packed`) into
`P-aarch64.elf`, a standalone static image of the optimized core, which
rebuilds the core to the same container. It then checks the runtime cases
against `static-cases.json`, and probes seccomp and the resource limits.
Receipt: `../docs/evidence/selfhost-bootstrap-aarch64-20261022/`.

## wasm32-browser-static/v1 (JUN-353)

F compiles `compile SRC --target wasm32-browser --output OUT.wasm` to one
self-contained WebAssembly module that holds the guest and the Kotoba runtime,
both compiled from SIR:

- `81-wasm32.kotoba` is the emitter. It encodes the module itself (sections,
  LEB128, opcodes) and is a plain emitter over SIR, like `80-aarch64-linux`.
  - Values are i64 locals.
  - Each function is a `loop` over a `br_table` of its basic blocks.
  - Tail positions use `return_call`.
  - Function values are indices into a funcref table of five-argument thunks.
  - RET2's second word is a global.
  - Fuel is charged at context +8, exactly as natively.
  - Floats and the `syscall` and `call-at` intrinsics are refused (E7101).
- `82-wasm32-rt.kotoba` is the runtime. Its shared sections are cut out of the
  current `77-aarch64-static-rt` text at compile time, by their section
  markers; a missing marker is refused (E7106). The wasm-specific parts are:
  - the `kotoba:host` imports `write`, `cap`, `now`, `exit` and `input`;
  - a bump allocator over `memory.grow` (smaller arena capacities than native:
    pairs 4M, string pool 64 MiB, vectors 512K, vector items 16M);
  - `start(fuel)`, which always writes the structured report.

  There are no seccomp filters, rlimits or signal handlers: the browser Worker
  is the sandbox. `kotoba:host/cap` refuses every capability by name until the
  consent broker lands (Phase 2).
- `../runtime/wasm32-browser-static-host.js` is the dependency-free Worker host.
  `../runtime/wasm32-browser-static-run.html` is the static run page, whose CSP
  sets `connect-src 'none'`.
- `../scripts/seed/check-wasm32-browser.py` runs modules in headless Chromium.
  It talks to the DevTools protocol on a pipe and reads the result lines from
  the DOM. There is no Node, npm or Playwright.

The pr tier of `selfhost-bootstrap.py` compiles the 24 runtime cases and three
probes with F, and checks that the float cases are refused. When a Chromium is
installed, it also runs the modules. The `ubuntu-24.04-arm` image has none, so
in CI the `qualify-x86_64` job runs them in the image's Chrome. Each case must
match its pinned result, trap and remaining fuel.

The consent broker (`kotoba:host/cap`) is Phase 2 (JUN-353).

### The entry ABI (Phase 3)

A guest gets its input and gives its output through the same wires as a native
command, so one source runs natively and in the browser unchanged:

| wire | native | wasm32-browser |
|---|---|---|
| 37 `:io/write`, 39 `:io/write-error` | fd 1, 2 | `kotoba:host/write` fd 1, 2 (the same runtime text) |
| 38 `:cli/args` | the command line | `kotoba:host/input(0, i, ..)`: the page's argument list |
| 35 `:fs/app-data` | files under `KEXE_CAP_RESOURCES_35` | `kotoba:host/input(1, 0, path, ..)`: read-only files the page holds in memory (plain read and `EXISTS_SEP`; every other `_SEP` request is refused by name) |

- **Grants.** As `KEXE_ALLOW` grants wires natively, the page grants them: at
  start the runtime asks `kotoba:host/input(2, wire, ..)` for each of 35, 37,
  38 and 39 and sets the allow bitmap's bit when the answer is 1. No other bit
  can be set, so without the page's grant every wire is refused, as in Phase 1
  (the `capability-denied` case).
- **Copying.** `input(kind, i, ptr, len, dst, cap)` answers the input's length,
  or -1 when there is none, and copies the bytes to `dst` only when
  `cap >= length`. The runtime asks twice: the length, then the bytes straight
  into the string pool. The result is an ordinary string handle (i64).
- **None of this is a capability.** The data never leaves the page: the host
  serves only what the page passed in (`{allow, args, files}` in the Worker
  message) and what the run writes. A guest that reaches a service still goes
  through `kotoba:host/cap`, which refuses.

The pr tier's `probe-entry` reads argument 0, reads that file and writes it:
with the grants it echoes the file and returns its length; without them
`:cli/args` is refused by name. `check-wasm32-browser.py --app MODULE.wasm
[--allow ..] [--file MOUNT=DIR].. -- ARGS..` runs an application's module the
same way (kumitate's fixture selftest, JUN-346).
