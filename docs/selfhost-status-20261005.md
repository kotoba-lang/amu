# Selfhost status, one page (2026-10-05, agent CHECKFULL)

Tree: `agent/dual-runtime-port` after `68dfbf714` (CHECKFULL) on top of `1f1e69a62` (rung r6m). Everything below is
measured unless marked **E** (estimate). Stage-0 = `build/native-image/amu-native` (sha256 `d2cb84f6`), the JVM-built
BOOTSTRAP-REFERENCE: an oracle of parity runs, never in an amu image's process tree. The host was loaded the whole wave
(1-minute load 15-60): **no time on this page is a result**; equality, fixed points, counts and sizes are.

## 1. What 100% means (docs/selfhost-priority.md rules 8-11)

`amu`, built by `amu` (no GraalVM, JVM, node or nbb at build or run time), runs the full `check`, `refactor` and `compile`
on its own sources, with no host process (rule 11 trace); then a QUIET Embench on that binary. Stubs never count.

## 2. Where it stands

| part | state | evidence |
|---|---|---|
| seed rungs | r0 .. **r6m** (22 records), each its own fixed point, no bridge since r6d; r6m `8d3338e1` 787,232 B, unity 17,890 lines | `seed/rungs/*.record`; r6m: bootstrap r0..r6l == records, gates 14/14 PASS (SEEDLANG) |
| seed compiles the compiler from source (selfbuild `--no-link`, 138 modules) | **138 / 138 in place** on r6m: amu's own sources, the refactor library with its own `:kotoba` readings (2026-10-10: 143/143 = the 138 + finding, cljs-order, rules.fnlit, native-artifact, native-admission; kotoba-lang 965c5f5 with no refactor twins, osaho d2cc281 interp/target). The kotoba-lang refactor twins (1c7260f, 143/143 the same day) are folded in and can be retired. Before: in place 122 / 138 (124/141), 120 (WALL2), 113 (FRONTSRC), 111 (FOLD) | `docs/selfhost-selfbuild-20261004.md` section 8.0; `SB_KL_REV=965c5f5 scripts/seed/selfbuild-inputs.sh` + `selfbuild.sh --no-link`; walls left: none (REFAC's in-process `rf_compile` of the whole entry: E5001, the separate-mode `rf_compile_sep` builds it) |
| frontend from source | 33 modules / 64,457 lines compiled by the seed, no kir-dump; amu-one-src rebuilds itself byte-identically for 3 generations on r6l | REBUILD `cf201da75`, `scripts/seed/launcher/rebuild-r6l.record` |
| native `amu` (one Mach-O, C loader + seed-built code, libSystem only, wires 3,34,35,37,38,39, never 20) | unified image = launcher + check + compile + refactor; REBUILD's `fc691d84` rebuilds itself 3 generations; CHECKFULL's `994fb5ed` (6,043,128 B) adds check's policy/project route | `launcher/test.sh` on `994fb5ed`: L1 34 SAME + 3 DECLARED, L2 Embench 19/19 (114 export runs, 19 kexe/v1 seals), L3 0 exec/spawn/system/popen in 6 runs, L4 PASS |
| `check` | **391/391** corpus programs = stage-0 (verdict, line, exit) without a policy and with two policies (grants 35,37,38,39; all 42 catalog names); `--policy`/`--profile` 150 SAME + 9 SAME-NORM + 5 DECLARED + 9 STUB, 0 DIFF; `--source-path`: WALL2's 17 trees x 2 = **34/34 byte-identical**, CHECKFULL's 9 trees x 2 = 14/18 | `seed/amu-main/CHECK.md`, `seed/tests/checkfull/*.sh` |
| `compile` (aarch64-macos) | 264 of 315 stage-0-compilable programs behaviour-same, 646 export runs SAME, 0 DIFF (launcher on r6l); r6m compiles 35 of the 47 refusals seed-direct (33 behaviour-same), **not yet in an image** | REBUILD record; SEEDLANG `1f1e69a62` |
| `refactor` | every sub-command real on the Kotoba route except `verify`'s process runs (needs wire 20, never granted); 0 differ in 10 suites vs bin/amu (args 31, graph 20, plan 18, partition 19, dynvars 44, graph-src 109, plan-src 128, apply 40, split 10, verify twin 5); content holding `WRITE_SEP` now applies (6/6 SAME; was SIGILL); 2026-10-10: the same 0 differ in all 10 suites (and rule g: fnlit plan 30/30, apply 27/27) with the library built from amu's own `:kotoba` readings, no kotoba-lang twin | `scripts/seed/refactor/all.sh` on CHECKFULL's code; `seed/tests/checkfull/refactor-writesep.sh`; selfbuild doc section 8.0 (`rf_compile_sep`, entry `8c418e0c3c39`) |
| product boundary (`bootstrap-boundary.sh`) | 4 launchers (bin/amu still node + nbb), 16 nbb entries (7 with no `:kotoba` arm; 5 since 2026-10-09 compile-cli), union **58** PRODUCT src files | measured this wave; the native image is not yet what `bin/amu` runs |

## 3. Declared stubs and differences of the native `amu` (never counted)

- check: `--source-path` with a RELATIVE entry or root (the image cannot learn its cwd: the loader answers no wire 40),
  `--json` (the `:kotoba.check/v1` envelope + definition CIDs), `--module-lock`, `--package-lock`, policies with
  `:abac`/`:attributes`/`:information-flow`/`:crypto-*`/`:hardware-signing-*` keys that would admit; a non-map policy and
  `--jvm-free` before the source are declared differences; 4 proj cases: the project twin does not attribute a refused
  qualified call to its module (filed to WALL2). `bin/amu check` (nbb) prints the `:kotoba.check/v1` map; the native
  command prints stage-0's human line, as LAUNCHER.md decided; WALL2's `nbb.check-cli` Kotoba entry is the nbb contract.
- paths: relative paths work when the loader scope covers the cwd (it resolves them against the start directory); a
  path outside the baked scope (repo, amu-embench, /private/tmp, /tmp) now reads as absent, not SIGILL. `$PWD` in the
  scope is filed to REBUILD. A non-ASCII OUTPUT path of `compile` still traps in seed.io (filed to 02-io).
- 21 bin/amu commands (module-lock, package-*, inspect, test, run, sign, verify, ...) answer the named stub (69).

## 4. Open, ranked (by what it unblocks)

1. **Flip the product path**: `bin/amu` is node + nbb; the native image passes L1-L4. Owner decision once the unified
   image (with check's project route, r6m's compile) is rebuilt and its parity re-run (REBUILD).
2. **Loader wire 40 (:sys/cwd)**: one provider over the cwd the loader already captures; removes the relative
   `--source-path` stub and the refactor path difference (filed).
3. **Rebuild on r6m**: compile parity should move from 264 toward ~297 of 315 (**E**: 33 more seed-direct behaviour-same).
4. **Remaining compile gaps** (12 of the 47): protocols/multimethods (20-names), multi-arity export names (50-out), pinned
   f64 narrowings (R6C/R3 decision).
5. ~~**nbb.cli / aarch64-cli from source**~~ (done 2026-10-09: compile-cli addendum; 291/291 accepted programs give the
   host's seal, provenance and answer) and the 5 nbb entries still with no `:kotoba` arm: rule 10.
6. **Rule 11 on the self-built binary over its own sources** (`check` and `refactor` of src/**, `compile` of the seed):
   per-command traces exist (L3, frontsrc T6) but not the full-source run.
7. A QUIET Embench of the native image (needs a reserved window; this wave never saw load < 15).

## 5. ETA (**E**, low confidence)

| milestone | range | assumptions |
|---|---|---|
| native image is the product `amu` for check / compile / refactor | 1-2 weeks | wire 40 lands, r6m image rebuilt with parity, owner flips bin/amu |
| no nbb entry on the product path (rule 10) | 3-6 weeks | nbb.cli `#(` rewrite, 7 entries ported or retired |
| full rule 11 + QUIET Embench | 4-8 weeks | the above, plus a quiet machine window |

## 6. Reproduce

`zsh scripts/seed/bootstrap.sh`; `LAUNCHER_REFACTOR=<kotoba-lang> zsh scripts/seed/launcher/build.sh --front <objects with
kotoba.sema + project twins> --worktree <dir>`; `zsh scripts/seed/launcher/test.sh <dir>/amu`; the check suites in
`seed/amu-main/CHECK.md`; `zsh scripts/seed/refactor/all.sh <rf-prefix> <out>`; `scripts/selfhost-wall/bootstrap-boundary.sh`.
Open contract items: `seed/CONTRACT-REQUESTS.md` (CHECKFULL lines: loader wire 40, launcher scope + check objects,
project-twin attribution, seed.io non-ASCII paths).

## 7. Addendum 2026-10-10: the unified image rebuilds itself on the integration sources (agent claude, fixed point)

**Inputs** (`scripts/seed/selfbuild-inputs.sh` with `SB_KL_REV=965c5f5`, then `selfbuild.sh --no-link`: 143/143 OK, 0
refused, 0 blocked): amu `claude/selfbuild-fixed-point` = integration d9215ff91 (the refactor fold a10f588a8: the 20
`kotoba.compiler.refactor.*` modules are amu's own `src/` files, no kotoba-lang refactor twin on the path) + this
branch's build-script changes; classpath = the seed17 farm (67 files, order sha256 `6e9adfc0`) with osaho d2cc281
`kir/interp.cljk` and `kir/target.cljk`; kotoba-lang 965c5f5 `lang/compat` (project, project-files and kotoba-reader
twins only). Seed r6m `8d3338e1`. Rebuild input manifest sha256 `ee0eacea`.

**Command**: `zsh scripts/seed/image/rebuild.sh <inputs> build/fixedpoint` (inputs = the scan's `r6/{src,order.txt,o}`
as `scan/` + `kotoba-lang/`). The output dir must lie inside the launcher's baked scope (repo, amu-embench, /private/tmp,
/tmp), so it is the worktree's `build/`. Script changes: `front.sh` no longer skips the effect modules and compiles the
project twins at their place in the scan order (nbb.cli's twin needs effect-row via native-artifact, and the project
twins); `rebuild.sh` adds a seed-built generation 0 and picks the refactor library from the farm when the kotoba-lang
snapshot has no refactor twins; `launcher/build.sh` takes `LAUNCHER_REFACTOR_SRC=<farm>` (the refactor closure's 19
modules then come from `--front`, compiled from the same farm files by the same compiler).

| gen | built by | objects (170) manifest | kseed | native code | command |
|---|---|---|---|---|---|
| g0 | seed r6m | `bfd35ae4` | `948bc14a` 6,585,329 B | `91a67121` 6,585,296 B | `2e33ef22` 6,819,336 B |
| g1 | g0's image | `ebcff3bc` | `e5dbcf10` 6,578,329 B | `4c37da6d` 6,578,296 B | `d23a21ec` 6,819,336 B |
| g2 | g1's image | `ebcff3bc` | `e5dbcf10` | `4c37da6d` | `d23a21ec` |
| g3 | g2's image | `ebcff3bc` | `e5dbcf10` | `4c37da6d` | `d23a21ec` |

**Fixed point: yes**: g1 = g2 = g3 byte for byte (objects, container, native code, command). In each of g1-g3, the
previous image compiles all 142 front objects (the frontend, kotoba.sema, nbb.cli's closure, project twins,
amu-front.check), the 14 seed-split modules, the 13 amu modules and amu.main, then links and runs extract-native. g0
differs from g1 (168 of 170 objects): the image's compiler is the tree's `seed/` source. Since r6m it has changed
(`seed/41-a64gen.kotoba` +1084 lines, `42-layout`, `60-proj`), so it is a newer compiler than the r6m binary. The
first image-built generation is already its fixed point. An earlier run on a8bb187da with the kotoba-lang 1c7260f
refactor twins also reached a fixed point: g1 = g2 = g3, command `b9bc367a`, kseed 5,961,937 B, objects `a6b69ea9`.

**Which `compile`**: the image builds itself with the **seed compiler linked into it** (`seed/amu-main/l/amu/compile.kotoba`
-> `seed.main/drv-compile-file`; the seed split of the tree's `seed/`), **not** the nbb.cli Kotoba twin. The twin's
modules (`kotoba.compiler.nbb.cli`, `aarch64-cli`, cli-support, native-artifact, ...) are compiled by the image as part
of the object fixed point. They are not linked, because no module that `amu.main` reaches requires a `kotoba.compiler.nbb.*` module.

**Size**: the kseed (read back whole as one `:bytes` value by `extract-native`) is 6,578,329 B. That is 78.4% of the
8 MiB (8,388,608 B) value bound, with 1,810,279 B of headroom. The refactor fold added 616 KB against the twins build.
The image fits; the seed is unchanged. Removing the bound would need a new seed rung (the loader's
`KEXE_BYTES_VALUE_LIMIT` and the seed's `io-read-bytes`/`io-write-bytes` contract), with ADR 0362 amended by measurement.

**prove-100** (`scripts/seed/prove-100.sh build/fixedpoint/g3/amu build/fixedpoint`): 5 PASS, 10 FAIL.

| row | verdict | cause |
|---|---|---|
| INPUTS | PASS | manifest `ee0eacea` |
| G4 | PASS | 3 generations equal, builder receipts present |
| PRODUCT | FAIL | `bin/amu` is still node + nbb |
| ENTRIES | FAIL | `nbb.check-cli` is skipped by front.sh (and is not linked); `aarch64-cli`'s object is present in g3/o, check-cli's is not |
| STATIC | PASS | libSystem only; wires 3,34,35,37,38,39 |
| G1 | FAIL | L2 Embench 0/19: `/Users/junkawasaki/github/kotoba-lang/amu-embench` is absent on this machine (L1 34 SAME + 3 DECLARED, L4 PASS) |
| INTERPOSER | FAIL | L3: `build/seed/noproc/noproc.dylib` not built in this worktree |
| G2 | FAIL | every case is the same as the reference (none 339+33, policy 340+32, all 347+25), but there are 372 rows, not the 391 the gate needs: the 19 Embench programs are missing |
| COMPILE_FULL | FAIL | 372 programs: 281 BEHAVIOUR-SAME, 49 BOTH-REFUSE, 27 AMU-ACCEPTS, 12 AMU-REFUSES, 3 BOTH-OK-DIFF; 776 export runs (761 SAME, 15 DIFF, 1 MISSING); 311 seals ok |
| G3 | PASS | 150 SAME, 9 SAME-NORM, 5 DECLARED, 9 STUB, 0 DIFF |
| CHECK_FULL | FAIL | the 5 DECLARED + 9 STUB check paths |
| G5 | FAIL | rule 11 trace: `sudo -n dtruss` needs a password (fail closed) |
| REFACTOR_VERIFY | FAIL | declared stub (needs wire 20) |
| QUIET_BENCH | FAIL | load1 10.85 (> 4) |

The twins build's prove-100 rows were the same (5 PASS, the same 10 FAIL, and the same corpus counts). The stage-0
reference for G2, G3 and COMPILE_FULL is `d2cb84f6` (BOOTSTRAP-REFERENCE, a link to the seed17 worktree's copy).
