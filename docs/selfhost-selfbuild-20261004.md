# Milestone (f), first attempt: the seed builds the big amu image from source (agent SELF, 2026-10-04)

Question: how far does the SEED (rung r6e, `9490ecf7`, its own fixed point, no stage-0 in its lineage beyond seed-0)
get toward building the big `amu` image from source, with no node/JVM/nbb, and what blocks it, ranked by what a fix
unblocks. Script: `scripts/seed/selfbuild.sh [--stage0]` (analysis `scripts/seed/selfbuild.py`). Every number below is
measured on this tree unless marked **E**. Host load 23-92 during the runs: no time on this page is a result.
Stage-0 (`build/native-image/amu-native`, sha256 `d2cb84f6`) appears only in the `--stage0` column and is
BOOTSTRAP-REFERENCE; it classifies walls, it does not build anything here.

## 0. Result

| step | how far | measured |
|---|---|---|
| the image's module list | 138 files (the 126 of the minimal reach set, loader-faithful twins, closed over the twins' requires; `reach-twins.py`) | 131,935 lines |
| compile from source, per module (separate mode) | **54 of 138 OK** (34,070 lines, 25.8%), 25 REFUSED, 59 BLOCKED, 0 traps | seed r6e |
| the same farm under stage-0 `check` | **97 of 138 OK**; 39 refused at 9 source walls (+2 templates checked alone) | stage-0 cannot build this image either |
| link the OK modules | **all 54 linked, in 2 packaged images** (44 modules / 1,888,872 code bytes; 14 modules / 618,472 B); both are libSystem-only Mach-O and run (`main` = 0, exit 0) | large-M profile of r6e (`801372e0`, fixed point) |
| the amu entries | **no command entry has a Kotoba `main`** that runs the command: `check_cli` / `aarch64_cli` are top-level `support/execute!` / `let` forms; `refactor_cli`'s Kotoba `main` prints "not available" (64) | text check of the Kotoba reading |
| the big amu image | **not built.** Blocked by 28 module walls (19 seed, 9 source), the entry gap, and the link capacity (the whole image is ~4.5x the seed's link buffer) | |

So the seed today: compiles a quarter of the image's source, links all of what it compiles into runnable native
images (the link stops at its buffer, by trap), and has no entry to call. Stage-0, the JVM-built reference, refuses 39 of
the 138 modules too: the image's source is not yet a program that any compiler builds.

## 1. Reproduce

```
zsh scripts/seed/selfbuild.sh --stage0 build/selfbuild-run     # LIST, SCAN, S0, LINK (+package +run), REPORT
cat build/selfbuild-run/report.txt                              # the tables below; provenance (every source root's head) on top
```

Inputs are live worktrees (kotoba-sema `15e45a3`, kotoba-lang `601affa`, amu `74e52b77e` with 8 files dirty from other
agents, ...): `report.txt` records each root's head and dirty count. The scan takes ~1 min, the stage-0 column ~15 min
(2 at a time, nice), the link ~3 min (loaded host).

## 2. Walls ranked by modules made attemptable (greedy, cumulative, upper bounds)

A wall is a module where a refusal is located: every module the seed refuses, and every module where stage-0's check of
a BLOCKED module stops (its `:source`). SEED = stage-0 accepts it, the seed refuses it (seed work); SOURCE = stage-0
refuses it too (source work). "+mods" = modules whose whole require closure becomes wall-free when this wall (and the ones
above it) is fixed: an upper bound, since the seed has never seen a BLOCKED module and may refuse it for its own reason.

| # | wall | kind | +mods | cum | seed's first refusal | owner (this wave) |
|---:|---|---|---:|---:|---|---|
| 1 | kotoba.lang.coll | SEED | 6 | 60 | E2105 template `[:set elem]` in separate mode | TMPL |
| 2 | kotoba.compiler.kotoba-reader | SEED | 6 | 66 | E2102 `0.0` (float literal on the source route) | F64 |
| 3 | kotoba.lang.json | SOURCE | 2 | 68 | E2104; stage-0: pre-ADR-0363 `[:result ..]` interface | json owner |
| 4 | kotoba.compiler.nbb.io | SEED | 4 | 72 | E2124 non-literal `def` (`max-bytes`) | TMPL (r6-scan order) |
| 5 | kotoba.compiler.diagnostic | SEED | 3 | 75 | E2124 non-literal `def` | TMPL |
| 6 | kotoba.security.information-flow | SEED | 2 | 77 | E2104 `reduce` over `[:list :keyword]` | TMPL |
| 7 | kotoba.security.hardware | SEED | 2 | 79 | E2105 type `:hardware/qualified?` | TMPL |
| 8 | kotoba.kir.definition-identity | SEED | 2 | 81 | E2123 `=` on non-i64/bool | TMPL |
| 9 | kotoba.compiler.process-wire | SEED | 2 | 83 | E2104 `reduce` | TMPL |
| 10 | kotoba.verifier.kirx | SEED | 1 | 84 | E2123 | TMPL |
| 11 | kotoba.kir.interp | SEED | 3 | 87 | E2105 `:f32` | F64 / TMPL |
| 12 | kotoba.kir.value | SEED | 8 | 95 | E2105 `:f32` | F64 / TMPL |
| 13 | kotoba.compiler.frontend | SOURCE | 7 | 102 | (blocked) stage-0: frontend.cljk:418 `(def ^:private f closure-types/f)` "constant alias must name a declared constant" | kotoba-sema |
| 14 | kotoba.compiler.refactor.cst | SOURCE | 1 | 103 | E2003 `declare`; stage-0 "unknown operation: set" | PORT |
| 15 | kotoba.compiler.refactor.edit | SOURCE | 8 | 111 | E1005 `#`; stage-0: variadic export | PORT |
| 16 | clojure.set | SEED | 4 | 115 | E2105 template | TMPL |
| 17 | kotoba.compiler.refactor.prelude | SOURCE | 2 | 117 | E6009 exports nothing (stage-0 the same) | PORT |
| 18 | kotoba.verifier.ops | SEED | 1 | 118 | E2123 | TMPL |
| 19 | kotoba.verifier.fx | SEED | 5 | 123 | E2001 duplicate definition '' (empty name: a seed defect, stage-0 OK) | TMPL |
| 20 | kotoba.native.interrupt-abi | SEED | 1 | 124 | E2104 `contains?` | TMPL |
| 21 | kotoba.native.machine-ir | SOURCE | 2 | 126 | (blocked) stage-0: call to an aborting import not caught (ADR 0363) | kotoba-native |
| 22 | kotoba.lang.package-contract | SEED | 1 | 127 | E2101 `hetero-vector` | TMPL |
| 23 | kotoba.compiler.nbb.fs-tree | SEED | 4 | 131 | E2123 | TMPL |
| 24 | kotoba.compiler.uefi-operations | SOURCE | 1 | 132 | (blocked) stage-0: `[:set :symbol]` where vector-i64 | amu src |
| 25 | kotoba.compiler.kexe-fs-forms | SEED | 3 | 135 | E2104 `contains?` | TMPL |
| 26 | kotoba.kir.iq-codebook | SEED | 1 | 136 | E2124 | TMPL |
| 27 | kotoba.compiler.refactor.verify | SOURCE | 1 | 137 | E1005; stage-0 `str/replace` not an admitted import | PORT |
| 28 | kotoba.compiler.refactor.diff | SOURCE | 1 | 138 | E1005; stage-0 `str/split` | PORT |

By kind of work: E2123 equality on strings/keywords (4 modules: kirx, definition-identity, ops, fs-tree), E2104
`reduce`/`contains?` over non-vector collections (4), E2124 non-literal `def` values (3), templates in separate mode (2),
`:f32` (2), float literals (1), then singles. Stage-0's own walls: frontend.cljk:418 blocks 11 modules (sema, cli,
project, project-files, check-driver, both entries, ...), refactor 15 modules (cst 11, prelude 2, edit, diff/verify),
json 9, machine-ir 2 (machine-ir, native.aarch64), uefi-operations 1. **The frontend.cljk:418 wall was not on this wave's
list** and gates every entry.

## 3. Per amu command: the smallest next set

| command | entry | closure | seed OK | walls in the closure (all must go; more may appear behind them) | entry main |
|---|---|---:|---:|---|---|
| check | nbb.check-cli | 80 | 33 | 15: SEED coll, kotoba-reader, nbb.io, diagnostic, process-wire, fs-tree, definition-identity, kirx, kir.interp, kir.value, package-contract, hardware, information-flow; SOURCE frontend, json | none (top-level `support/execute!`) |
| compile (aarch64-macos) | nbb.aarch64-cli | 98 | 41 | 18: SEED coll, kotoba-reader, nbb.io, diagnostic, kexe-fs-forms, definition-identity, kirx, ops, fx, kir.interp, kir.value, interrupt-abi, hardware, information-flow; SOURCE frontend, json, machine-ir, uefi-operations | none (top-level `let`) |
| refactor | nbb.refactor-cli | 22 | 13 | 5: diagnostic, kotoba-reader, nbb.io, process-wire (SEED), json (SOURCE); its Kotoba closure does not reach the refactor library (cst/rules) at all | stub (prints "not available") |

The exact lists are in `report.txt` (section "entries"). Smallest next set toward ONE command: `refactor`'s 5 walls, but
its Kotoba route has no implementation behind them (PORT's typed refactor.cst is the real work). Toward `check`: 15 walls,
of which kotoba-reader, coll, nbb.io, diagnostic and the 4 E2123 modules are shared with `compile`; the two SOURCE walls
(frontend.cljk:418, json) are one-line-class fixes upstream and gate both.

## 4. Link and package (what works today)

`selfbuild.sh` packs the 32 OK modules that no OK module requires ("tops") greedily into probe entries, each
`(ns selfbuild.probe (:require [top :as mN] ..)) (defn main [] :i64 0)`, compiled with `--emit-module --entry` and linked
with `seed link`:

| image | tops | modules | lines | code bytes | run | next top |
|---|---:|---:|---:|---:|---|---|
| img1 | 22 | 44 | 28,873 | 1,888,872 | exit 0 | +string-index: link TRAPS (SIGILL) |
| img2 | 10 | 14 | 5,966 | 618,472 | exit 0 | |

Two capacity walls, both measured:
- **default profile**: `seed link` / `extract-native` of a 1.46 MB image answer `E5001 output buffer full` (OUT region);
  the large-M profile (`scripts/seed/large-m.sh --rung r6e`, seed `801372e0`, its own fixed point, 700,128 B) removes it.
- **60-proj's link vector L** (`pj-l-cap` 2,097,152 words, image from word 200,704, one byte per word) holds at most
  1,896,448 image bytes; img1 is 7,576 bytes under it. Past it the link writes beyond L before its `E-PROJ-IMAGE` check
  and the loader traps (SIGILL): a refusal by trap, not by name. Not part of the large-M profile (the constant is in
  60-proj, not the MEMORY-MAP).
- Size of the whole image (**E**): 65 code bytes per source line on img1 -> ~8.6 MB for 131,935 lines (range 6-12 MB;
  amu-front alone, the frontend via the KIR route, is 2.34 MB). That is ~4.5x L and above the large-M OUT (3 Mi) and CODE
  (1 Mi words = 4 MiB) regions. M itself is at the loader's 16 Mi items per vector, so the image cannot be held one byte
  per word in M or L at that size: 50-out/60-proj need a packed image (8 bytes per word) or a streamed write. Request filed.

The probe images prove link + package + run for 54 seed-compiled modules; they do not prove behaviour (main calls
nothing). Behaviour per module is r6-diff's (1,200/1,200 cases agree on the TEXT record).

## 5. Native launcher replacing bin/amu (design)

Today `bin/amu` is node (677 lines): it routes `check` to nbb `check_cli` (or to `AMU_FRONT` for a flagless single file,
ADR 0366), `compile --target aarch64-macos` to nbb `aarch64_cli`, `refactor` to nbb `refactor_cli`, other targets to other
nbb entries. Two designs:

| | A. C launcher | B. one seed-built image with a Kotoba dispatcher |
|---|---|---|
| shape | `tools/amu_launcher.c` (~200 lines, cc): reads argv[1], `execv`s a sibling packaged command (`amu-check`, `amu-compile`, `amu-refactor`), each a seed-built image | `seed/amu/main.kotoba`: `(defn main [] :i64 (case (arg 0) "check" (check/run) "compile" (compile/run) "refactor" (refactor/run) (usage)))`, linking the three drivers; packaged once with `KEXE_EMBEDDED` (scripts/seed/package.sh) |
| rule 11 trace | one exec of a sibling binary per command: an exec of a self-built program, but G5's interposer counts it as a program start | zero program starts (the loader's supervisor fork only), as G5 measures for the seed today |
| link size | each image carries one command's closure (check 80 modules, compile 98) | one image with the union (138 modules, ~8.6 MB **E**): needs the packed link image first (section 4) |
| available | as soon as one command image exists (amu-front is one today: `check <one file>`) | after every entry has a Kotoba `main` and the link capacity is fixed |
| stage-0 / node at run time | none | none |

**Recommendation: B is the target, A is the bridge.** Step 1 (now): give each command a Kotoba-route driver with an
arity-0 `main` in the pattern of `seed/amu-front/check.cljk` (argv via wire 38, files via 35, report on 37/39, exit
status as the result), next to the nbb entries, so the seed can compile it (entries cannot stay top-level
`support/execute!` forms: the seed refuses top-level expressions, and the Kotoba route has no top-level effects).
Step 2: a C launcher identical in routing to bin/amu for the commands that have a native image (check today), falling
back to `bin/amu` by name otherwise, so the product path loses node one command at a time and the boundary count
measures it. Step 3: one image (B) when the link holds it; the launcher then shrinks to the loader's `KEXE_EMBEDDED`
main and is deleted. Capabilities of the image: 3 (hash, record/closure identities: amu-front showed every record program
needs it), 35, 37, 38, 39; refactor `verify` needs 20 (spawn): it stays a separate, labelled command until verify is
redesigned, so the main image never holds wire 20.

## 6. Targets beyond aarch64-macos

Draft ADR 0367 (docs/adr/0367-seed-targets-linux-and-aiueos.md): keep the nbb route for linux-static / aiueos labelled
bootstrap until (f) holds; then Linux through the same loader ABI (the seed's code bytes are OS-independent; the loader
already has `__linux__` paths, unbuilt here), aiueos only with a freestanding runtime, x86-64 not planned.

## 7. Open risks

- Every "+mods" count is an upper bound: 59 modules have never been seen by the seed.
- The 2 probe images link modules but run nothing of them; an image-level differential (a probe that calls one export per
  module, r6-diff's drivers linked together) is the next measurement of the link.
- Inputs are live worktrees, some dirty (amu src had 8 dirty files from other agents during the run); `report.txt`
  records heads, not content hashes.
- Stage-0 `check` OK is frontend acceptance, not native-compile admission (amu-front's README: stage-0 refuses the
  linked frontend at target admission); SEED vs SOURCE is therefore an optimistic split for the seed.
- The size estimate (8.6 MB) extrapolates from 28,873 lines of mostly small library modules; the frontend/backend
  modules may be denser.
