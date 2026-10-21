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
`a1a718388c55eaf8e9f749ea1829c17ae9d667dbc785194879b0abb8454602b3`.
`adoption-20261017.json` records the current source pins, bootstrap and
fixed-point image separately, artifact provenance, correctness scope, and
measurement boundaries. `adoption-20261012.json` remains the historical
receipt for the prior source closure. `HEADS`, `MEMORY-MAP`, and `SIR`
are the corresponding compiler contracts, copied without changes.

## Native self-build

The current source is bootstrapped from
`bootstrap/adopted-20261012.bin` (macOS arm64, entry offset 0, arity 0). The
current source's three-generation fixed-point image is recorded separately in
`adoption-20261017.json`; the bootstrap file remains unchanged. It is a native
code payload used by the pinned C loader, not a standalone OS executable.
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

## Seed lineage bootstrap (Kotoba tools, no script files)

The seed's own bootstrap tooling is Kotoba: `seed/tools/bootstrap.kotoba`
(the lineage), `seed/tools/package.kotoba` (a packaged seed command) and their
shared `seed/tools/lib.kotoba`. They are compiled by the committed seed and run
under the pinned C loader; the only programs they start are `cc`, `git` and
the lineage loader. No shell script, node, nbb, JVM or Python is on the route.
The former `scripts/seed/*.sh` files and the per-file verdicts are listed in
`docs/seed-tools-kotoba.md`. On macOS arm64, from the repository root:

```sh
# 1. the trusted C loader that runs the committed seed and the tools
mkdir -p build/seed-tools
cc -std=c11 -O2 seed/bootstrap/adopted-loader-20261012.c -o build/seed-tools/loader

# 2. the committed seed compiles the tool (project mode: seed/tools/lib.kotoba is found by its namespace)
KEXE_COMMAND=1 KEXE_CAP_RESOURCES_35=$PWD KEXE_STRING_POOL=1073741824 KEXE_PAIRS=16777216 KEXE_VECTORS=4194304 KEXE_VECTOR_ITEMS=134217728 \
  build/seed-tools/loader seed/bootstrap/adopted-20261012.bin 0 0 aarch64 35,37,38,39 -- \
  compile $PWD/seed/tools/bootstrap.kotoba --source-path $PWD/seed --unpinned --target aarch64-macos --output $PWD/build/seed-tools/bootstrap.kseed
KEXE_COMMAND=1 KEXE_CAP_RESOURCES_35=$PWD KEXE_STRING_POOL=1073741824 KEXE_PAIRS=16777216 KEXE_VECTORS=4194304 KEXE_VECTOR_ITEMS=134217728 \
  build/seed-tools/loader seed/bootstrap/adopted-20261012.bin 0 0 aarch64 35,37,38,39 -- \
  extract-native $PWD/build/seed-tools/bootstrap.kseed --symbol main --output $PWD/build/seed-tools/bootstrap.bin
#    -> {:ok true, ... :offset <OFFSET> ...}

# 3. run it: R0 -> every recorded rung, then the head unity
KEXE_COMMAND=1 KEXE_CAP_RESOURCES_35=$PWD \
KEXE_CAP_RESOURCES_20=/usr/bin/cc:/usr/bin/git:$PWD/build/seed-boot/kexe-loader-v11 KEXE_SPAWN_PATH_LOOKUP=1 \
KEXE_SPAWN_ENV=KEXE_COMMAND:KEXE_CAP_RESOURCES_35:KEXE_STRING_POOL:KEXE_PAIRS:KEXE_VECTORS:KEXE_VECTOR_ITEMS:KEXE_CPU_SECONDS:KEXE_WALL_SECONDS \
KEXE_STRING_POOL=1073741824 KEXE_PAIRS=16777216 KEXE_VECTORS=4194304 KEXE_VECTOR_ITEMS=134217728 \
KEXE_CPU_SECONDS=600 KEXE_WALL_SECONDS=600 \
  build/seed-tools/loader build/seed-tools/bootstrap.bin <OFFSET> 0 aarch64 3,20,35,37,38,39 -- $PWD
```

Step 3 grants the tool wires 3 (sha256), 20 (spawn), 35 (files inside the
repository), 37/38/39 (stdout, argv, stderr). The spawn grant names the three
programs by absolute path and lets the tool start them by name; the variables
in `KEXE_SPAWN_ENV` are the only environment the children see (the lineage
loader reads its budgets from them). The tool builds
`build/seed-boot/kexe-loader-v11` from `seed/bootstrap/seed-loader-v11.c`,
checks `seed/bootstrap/SHA256SUMS`, and for every `seed/rungs/*.record` in
lineage order rebuilds the unity from git, the optional bridge, seed-1 and
seed-2, and checks every recorded sha256, the size and the fixed point. It
ends with `bootstrap: r6n FIXED POINT == record b3f46d32a01780fe` and writes
the working tree's unity to `build/seed-boot/head/seed-unity.kotoba`, checked
against `sourceUnitySHA256` of `seed/adoption-20261017.json`. Options:
`--work DIR` (then name `DIR/kexe-loader-v11` in the grant), `--upto RUNG`,
`--head` (the lineage A/B/C head step for a source the last rung can compile,
e.g. with `--commit C`), `--image FILE` (sha256 of an image against the
receipt's `nativeImageSHA256`).

The current tree is the adopted compiler. The lineage's last seed cannot
compile it (E101, its tables are sized for the lineage) and one adopted
compile runs about a minute, longer than the loader's 10 s budget for a
spawned child, so its three generations are plain loader commands, each
checked by the tool:

```sh
KEXE_COMMAND=1 KEXE_CAP_RESOURCES_35=$PWD KEXE_FUEL=off KEXE_STRING_POOL=268435456 KEXE_PAIRS=16777216 \
KEXE_VECTORS=4194304 KEXE_VECTOR_ITEMS=134217728 KEXE_CPU_SECONDS=1800 KEXE_WALL_SECONDS=1800 \
  build/seed-tools/loader seed/bootstrap/adopted-20261012.bin 0 0 aarch64 35,37,38,39 -- \
  compile $PWD/build/seed-boot/head/seed-unity.kotoba --target aarch64-macos --output $PWD/build/seed-boot/head/G1.kseed
#   (same environment) ... -- extract-native $PWD/build/seed-boot/head/G1.kseed --symbol main --output $PWD/build/seed-boot/head/G1.bin
#   G2, G3: the same two commands with build/seed-boot/head/G1.bin (then G2.bin) in place of the committed seed
#   check each: the step-3 command with `-- $PWD --image $PWD/build/seed-boot/head/G1.bin` (G2.bin, G3.bin)
```

`seed/tools/package.kotoba` is built the same way (step 2 with
`package.kotoba`) and run with `KEXE_CAP_RESOURCES_20=/usr/bin/cc`:
`-- $PWD <seed.bin> [--offset N] [--out PATH] [--scope LIST] [--allow CSV]`.

## Selfbuild scan (gate S2)

`seed/tools/selfbuild.kotoba` (with `seed/tools/scan.kotoba`) is the Kotoba
port of `scripts/seed/selfbuild.sh --no-link`, `r6-scan.sh`,
`selfbuild-inputs.sh`, `farm-from-lock.py`, `reach-list.py`, `reach-twins.py`
and the summary of `selfbuild.py`. It answers: of the modules the amu commands
reach, which ones does seed r6n compile from source? It starts only `git` and
the lineage loader running the seed. Prerequisites: the lineage bootstrap above
(it leaves `build/seed-boot/kexe-loader-v11` and
`build/seed-boot/r6n/seed-1.bin`), and local clones of the lock's repositories
under one directory (`--repos`; `--gitlibs` names a second place to look).
Nothing is fetched: a missing clone or commit fails the run.

```sh
# build the tool: step 2 above with selfbuild.kotoba (-> build/seed-tools/selfbuild.bin, :offset <OFFSET>)
# run it (the work dir must not exist yet; stderr MUST go to the file named by --stderr)
KEXE_COMMAND=1 KEXE_CAP_RESOURCES_35=$PWD \
KEXE_CAP_RESOURCES_20=/usr/bin/git:$PWD/build/seed-boot/kexe-loader-v11 KEXE_SPAWN_PATH_LOOKUP=1 \
KEXE_SPAWN_ENV=KEXE_COMMAND:KEXE_CAP_RESOURCES_35:KEXE_STRING_POOL:KEXE_PAIRS:KEXE_VECTORS:KEXE_VECTOR_ITEMS:KEXE_CPU_SECONDS:KEXE_WALL_SECONDS \
KEXE_STRING_POOL=1073741824 KEXE_PAIRS=16777216 KEXE_VECTORS=4194304 KEXE_VECTOR_ITEMS=134217728 \
KEXE_CPU_SECONDS=3600 KEXE_WALL_SECONDS=3600 \
  build/seed-tools/loader build/seed-tools/selfbuild.bin <OFFSET> 0 aarch64 3,20,35,37,38,39 -- $PWD \
  --work $PWD/build/selfbuild --stderr $PWD/build/selfbuild.stderr \
  --lock $PWD/seed/selfbuild/integration-lock.edn \
  --repos $HOME/github/kotoba-lang --gitlibs $HOME/.gitlibs/_repos/https/github.com/kotoba-lang \
  --kotoba-lang-repo $HOME/github/kotoba-lang/kotoba-lang --kotoba-lang-rev 965c5f5b2f574f6be8f0b9572ca6cd6bac28ce97 \
  [--seed FILE] [--expect-ok N] \
  2> $PWD/build/selfbuild.stderr
```

Every path is absolute and, except the clones (read by `git` only), inside
`$PWD` (the wire-35 scope). The seed writes its refusals to stderr, which a
spawned child shares with the tool, so the tool reads them back from the
`--stderr` file (it checks the redirection with a marker first). Each module
compile is one spawn (at most 10 s; r6n needs at most about 1.5 s). Options:
`--lock` (default `deps-lock.edn`), `--seed` (default
`build/seed-boot/r6n/seed-1.bin`; its rung is named from `seed/rungs/*.record`),
`--kotoba-lang DIR` (an existing `lang/compat` parent instead of
`--kotoba-lang-repo/-rev`), `--expect-ok N`.

Exit status: 0 the scan ran (and seed OK >= `--expect-ok`), 1 an input or tool
failure or OK below `--expect-ok`, 2 usage. Refusals of modules are results,
not failures. The last stdout lines are
`selfbuild: modules N (L lines): seed OK n (..), REFUSED r, TRAP t, BLOCKED b`,
`selfbuild: verdict <work>/selfbuild.edn` and `selfbuild: OK`.

`seed/selfbuild/integration-lock.edn` is `deps-lock.edn` with the upstream PR
heads the integration needs: kotoba-mir#75 `8f34a78`, kotoba-sema#130
`a8fe662`, kotoba-native#204 `a7a7740`, osaho#122 `66519e4`, artifact
`619fc02`.

Work dir (`--work`):

| file | content |
| --- | --- |
| `selfbuild.edn` | the verdict (below) |
| `inputs.txt` | provenance: `amu <commit> src dirty <n>`, `seed <path> sha256 <h> (<rung>) offset <o>`, `lock <path> sha256 <h>`, `root <coordinate> <commit> src tree <git tree> clone <clone> -> <root>` per lock entry, `kotoba-lang <repo> <commit> lang/compat tree <git tree>`, `module <ns> <sha256> <source>` per module |
| `farm.txt`, `cp.txt`, `cp/<repo>/src` | the classpath farm (lock order) |
| `reach.txt`, `list.txt`, `list.err` | reach-list files; reach-twins `<ns>\t<file>` and its swaps / additions |
| `r6/order.txt`, `r6/src`, `r6/o` | `<ns> <file> <deps..or ->` dependency-first; the farm copies; the objects |
| `r6/r6-scan.tsv` | `ns  status  lines  code  text  -` (status `OK`, `REFUSED`, `TRAP`, `BLOCKED`) |
| `report.txt` | totals, first refusals grouped by code and text, the three command entries |

`selfbuild.edn` (format 1; one map):

```clojure
{:selfbuild/format 1
 :tool "seed/tools/selfbuild.kotoba"
 :seed {:file "<path>" :sha256 "<hex>" :rung "r6n"}
 :amu {:commit "<sha>" :src-dirty 0}
 :counts {:modules 269 :ok 97 :refused 49 :trap 0 :blocked 123 :lines 191467 :ok-lines 40538}
 :entries [{:command "check" :ns "kotoba.compiler.nbb.check-cli" :closure 104 :ok 34 :walls 12} ...]
 :inputs-file "inputs.txt"
 :modules [{:ns "<ns>" :status :ok|:refused|:trap|:blocked :lines n :file "<farm copy>" :origin "<source>"
            :sha256 "<source sha256>" :code "E2104" :text "<first refusal>"   ; :refused / :trap only
            :blocked-by "<ns>"}                                              ; :blocked only
           ...]}
```

A gate reads `:counts` (and `:entries` for the closure of each amu command),
compares `:ok` with its recorded floor, and lists the `:refused` modules.

Parity (2026-10-21, Mac arm64, seed r6n `b3f46d32`): on the same lock, the same
kotoba-lang `965c5f5` and the same amu tree, the old `.sh` route
(`selfbuild.sh --no-link`, run once in a scratch worktree from `15626731^`) and
this tool give the same farm (byte-identical `cp/`), reach list (260 files),
module list and order (269), the same verdict, code and text for every module,
and byte-identical objects: at this branch's head `7c8c8a4b` both give
**seed OK 97 / 269** (REFUSED 49, TRAP 0, BLOCKED 123); at `5bb54254` (the source
of the recorded scan) the tool gives **128 / 264** (REFUSED 51, BLOCKED 85),
module for module the recorded `.sh` result. The drop at the head comes from
amu's own `src/kotoba/form.kotoba` (and `frontend_tables`, `value_type`,
`validate_expr` `.kotoba`), restored by the main merge `43f881b7`: across roots
the single guest `.kotoba` stands in for kotoba-sema's `.cljk`, and amu's
`kotoba.form` does not export `tag-of` (E6004 at `kotoba.walk`,
`kotoba.verifier.seal`, `kotoba.wasm.core`, `kotoba.kir.kvalue`).

Not ported: the LINK step of `selfbuild.sh` (with `large-m.sh`) and the
stage-0 column (the JVM stage-0 is removed).

### Image front (gate S3, partial)

`seed/tools/image.kotoba front` is the port of `scripts/seed/image/front.sh`:
it recompiles every module the scan compiled (from the scan's farm sources, in
scan order, never reusing the scan objects), then the kotoba-lang project
twins and `seed/amu-front/check.cljk`. Same environment as the scan, spawn
grant `$PWD/build/seed-boot/kexe-loader-v11`:

```sh
  build/seed-tools/loader build/seed-tools/image.bin <OFFSET> 0 aarch64 3,20,35,37,38,39 -- $PWD front \
  --scan $PWD/build/selfbuild --twins $PWD/build/selfbuild/kotoba-lang/lang/compat/kotoba/compiler \
  --out $PWD/build/front0 --stderr $PWD/build/front0.stderr 2> $PWD/build/front0.stderr
```

On the integration sources it recompiles the 97 scan modules byte-identically
and then stops at the project twin (`kotoba.compiler.project`: E6025, its
`kotoba.sema` has no object): the image's `check` and `compile` closures are
not seed-compilable yet (check-cli 34/104, aarch64-cli 47/126 at the head;
62/100 and 78/122 at `5bb54254`, where `kotoba.compiler.frontend.analyze` is
BLOCKED behind `frontend.desugar` E2104 and `frontend.constant-eval` E6025).
The three-generation rebuild (`image/rebuild.sh`) and the launcher
(`launcher/build.sh`, `test.sh`, with their Python split helpers) stay
unported until the front completes.

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
