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

## 8. Addendum 2026-10-10: the image carries the product entries (agent claude, branch claude/image-product-entries)

**Routing** (`seed/amu-main`): `amu.main` sends `compile` to `amu.compile` = `nbb.aarch64-cli`'s Kotoba `run` (the body
of its `main`, i.e. `nbb.cli`'s Kotoba `run!`), and `check` to `amu.check` = `nbb.check-cli`'s Kotoba `run`, both over
`amu.launch/args` (bin/amu's launcher layer: `--jvm-free` dropped, `--target aarch64-macos` appended to compile/worker
without one). `compile .. --emit-module` is the **internal module compiler** of the self-build (`seed.main`, the seed
compiler linked in), routed before `amu.compile`; `link`, `modules` and the KSEED1 arm of `extract-native` are unchanged.
So the self-build path (front.sh, launcher/build.sh `--builder`) is untouched, and the product `compile` is one
implementation with `bin/amu compile`. Both entries now export `run [args]` (their `main` = `(run (command-line-args))`);
check-cli's refusals use cli-support's phase/exit table like aarch64-cli's, and check-driver keeps the frontend
error's phase (w1-denial-ceiling: 70, as the host). front.sh no longer skips check-cli/check-driver. The old seed
artifact compile and `amu.check-full` (stage-0's texts) are no longer linked.

**Size and the 8 MiB limit**: the image's kseed is **10,978,347 B** (was 6,578,329 B). Sharing does not close it: the
closure is 159 modules, and the parts only one command reaches are different programs (compile ~2.4 MB, refactor
~1.3 MB, seed compiler ~0.8 MB, check ~0.6 MB of code). The limit was the seed's `extract-native` reading the container
as one `:bytes` value. Rung **r6n** (record `seed/rungs/r6n.record`, unity 1cf67ec9a, bridge by r6m f11b6ce3, fixed point
`b3f46d32`, 860,296 B; gates 14/14 PASS; `bootstrap.sh --no-head` reproduces r0..r6n) reads a file over 4 MiB in RANGE
windows into one vector: extract input bound 16 Mi bytes (one vector), the 8 MiB value bound unchanged (ADR 0362
addendum). rebuild.sh / launcher/build.sh default to r6n.

**Fixed point** (`zsh scripts/seed/image/rebuild.sh build/rin build/fp`, inputs = a fresh `selfbuild.sh --no-link` scan
143/143 of this branch's sources + kotoba-lang 965c5f5, manifest `9b8dee8d`): **g0 = g1 = g2 = g3**.

| gen | built by | objects (172) manifest | kseed | native code | command |
|---|---|---|---|---|---|
| g0 | seed r6n `b3f46d32` | `eee918f3` (25,355,529 B) | `f3fbc62a` 10,978,347 B | `91c374de` 10,978,312 B | `27ffb605` 11,244,552 B |
| g1 | g0's image | `eee918f3` | `f3fbc62a` | `91c374de` | `27ffb605` |
| g2 | g1's image | `eee918f3` | `f3fbc62a` | `91c374de` | `27ffb605` |
| g3 | g2's image | `eee918f3` | `f3fbc62a` | `91c374de` | `27ffb605` |

g0 equals g1 now because r6n's seed IS the tree's seed compiler (at r6m it was older).

**Corpus through the image's `compile`** (`seed/tests/compile-cli/run.sh --image build/fp/g3/amu`, 372 programs vs
`bin/amu compile --target aarch64-macos`, `KOTOBA_VERDICT_CACHE=off`): BOTH-ACCEPT **293** (seal, artifact keys,
provenance and answer SAME on all; publication 290 same shape + 3 size only, `#:ns{}` printing), BOTH-REFUSE same exit
**62**, CLASS-DIFF **1** (w1-effect-named, named: kotoba-sema lines), HOST-ONLY **16** (verifier strictness, owner: keep),
GUEST-ONLY **0** = the combined measurement's classes. Embench ports (not in that corpus; `bench/embench/ports`): 17 / 19
BOTH-ACCEPT SAME; **crc32 and matmult-int trap the 64 Mi pair ceiling** (exit 120; the host compiles them; the loader
refuses `KEXE_PAIRS` above 67,108,864).

**`check` through the image** (`seed/tests/check-cli/image.sh`, same 372 vs `bin/amu check`): no policy 337 SAME (answer
equal but check-driver's named `:definitions` marker), 24 SAME-REFUSE, 9 REFUSE-DIFF (same exit, frontend-snapshot
message wording), 2 BOTH-ACCEPT-DIFF (`:exports`: synthetic helper names of the frontend snapshot), 0 exit-code
differences; `corpus-policy` (wires 35..39) 338 / 23 / 9 / 2. **`corpus-policy-all` (42 grants): 347 HOST-ONLY, all
SIGTRAP exit 120**: any `--policy` whose `:allow` holds more than 32 entries traps, in `check` and in `compile` (measured:
32 grants answer, 33 trap). Cause: effect-row hands the policy to `kotoba.kir.admission`'s typed reading as a
`:document`, whose containers hold at most 32 items. The previous image's check (amu.check-full) answered these.

**L1-L4** (`scripts/seed/launcher/test.sh`): L1 PASS (39 cases: 11 SAME, 17 SAME-DATA, 11 DECLARED, 0 DIFF; compile/check
cases now take `bin/amu` as oracle, see usage-parity.sh), L2 FAIL (the amu-embench checkout is absent here; see the
Embench line above), L3 PASS (6 runs, 0 exec/spawn), L4 PASS.

**prove-100** (`scripts/seed/prove-100.sh build/fp/g3/amu build/fp`): 5 PASS, 9 FAIL (14 rows).

| row | verdict | cause |
|---|---|---|
| INPUTS | PASS | manifest `9b8dee8d` |
| G4 | PASS | 3 generations equal, builder receipts present |
| PRODUCT | FAIL | `bin/amu` is still node + nbb |
| ENTRIES | PASS | check-cli and aarch64-cli objects in g3/o (both linked and routed) |
| STATIC | PASS | libSystem only; wires 3,34,35,37,38,39 |
| G1 | FAIL | L2: amu-embench absent (L1 PASS, L3 PASS, L4 PASS) |
| INTERPOSER | PASS | L3 |
| G2 | FAIL | reference is stage-0's human `check` line; the image now prints bin/amu's `:kotoba.check/v1` map, so corpus.sh finds no report line: 339 / 340 / 347 AMU-TRAP + 33 / 32 / 25 REFUSE-DIFF in the three modes; vs bin/amu see the check line above |
| COMPILE_FULL | FAIL | now judged against bin/amu artifacts (gate changed: seal/provenance/answer, not export runs vs stage-0): 293 + 62 agree, 1 CLASS-DIFF + 16 HOST-ONLY named |
| G3 | FAIL | checkfull/diff.sh compares with stage-0's check texts: 168 DIFF, 5 DECLARED (format change, as G2) |
| CHECK_FULL | FAIL | the same diff: DECLARED rows remain |
| G5 | FAIL | `sudo -n dtruss` needs a password |
| REFACTOR_VERIFY | FAIL | declared stub (needs wire 20) |
| QUIET_BENCH | FAIL | load1 167.87 |

**Open (owner decisions)**: (1) policies over 32 grants trap in both product entries (kir.admission's document-typed
reading, osaho; or the document container bound); (2) crc32 / matmult-int exceed the loader's 64 Mi pair ceiling on the
Kotoba compile route (cause and upstream fix measured in docs/selfhost-compile-pairs-20261010.md: kotoba-mir key-Form
lookups + kotoba-native copied vreg tables; with both, 46.5 M pairs and SAME artifacts; landed on the
dual-runtime-port-D branches as kotoba-mir e2cf973 and kotoba-native ca8bb09); (3) G2/G3/CHECK_FULL still reference
stage-0's check texts, not bin/amu's (done in section 9).

## 9. Addendum 2026-10-10: G2, G3 and CHECK_FULL judged against bin/amu (agent claude, branch claude/prove-100-host-reference)

**Why the reference changed**: since section 8 the image's `check` is nbb.check-cli's Kotoba `run` and prints bin/amu's
`:kotoba.check/v1` map. Stage-0 `d2cb84f6` prints a human `ok ...` / `error: ...` line, so against it every case failed
on format (section 8: G2 AMU-TRAP, G3 168 DIFF). The product the image replaces is `bin/amu`, so it is now the reference
for G2, G3 and CHECK_FULL (BOOTSTRAP-REFERENCE, the nbb route of the same entry), as COMPILE_FULL already was.
Stage-0 is no longer the oracle of any check gate. It is still the oracle of G1 only (launcher/test.sh: L1's `S:`/`T:`
argument cases, L2's Embench export runs); this branch does not change G1.

**How a case is judged** (`seed/tests/check-cli/judge.py`, used by `image.sh` for G2 and `args.sh` for G3):
1. The exit code is compared first.
2. If both accept, the stdout answer maps are compared as EDN data. If both refuse, the `:kotoba.cli-error/v1` reports
   are compared as data, on the same stream.
3. A difference passes only when it matches a row of `seed/tests/check-cli/named.tsv`. A row fixes the case, the key
   and both values; there is no key-only ignore.
4. A trap (exit 120) is always DIFF. Exit 69 `:not-available` is STUB.

Row kinds: **NORM** means the verdict, exit and phase are the same and only the text or a marker differs. **GAP** means
the behaviour differs. A GAP row may name a split between two refusals (exit or phase) or a declared missing
capability. A verdict split caused by a bug is never named; neither is a trap.

The gates:
- **G2** = 391 rows per policy mode (372 corpus programs + the 19 Embench ports, which `image.sh` now includes when the
  checkout exists), all SAME, SAME-DATA or NORM.
- **G3** = no DIFF in the 173 argument cases (`cases-args.txt` + 34 policy files x 4 programs, run in `checkfull/fx`).
- **CHECK_FULL** = no STUB and no GAP in those cases.

**Named differences** (39 rows, 13 ids):

| id | kind | where | what |
|---|---|---|---|
| definitions-marker | NORM | every accept | `:definitions` is `{:contract :kotoba.definition-identity/v1, :entries :unavailable, :reason :no-typed-kir}` (no typed KIR in check-driver's Kotoba reading). The host's `:contract` must be the same |
| reduced-report-diagnostic / -details | NORM | every refusal | cli-support's reduced report has no `:diagnostic` / `:details` |
| msg-effect-ceiling-set | NORM | examples/w1-denial-ceiling | the unrefined message keeps `: #{:log/append}`. kotoba.compiler.diagnostic is not on the Kotoba route |
| msg-require-module | NORM | conformance/stdlib/{basic,extended,i64set,keyed,ordered}, fx proj/app/main | the frontend snapshot says "only a bounded :export vector ..." where the host gives its multi-file module text |
| msg-set-literal-wording | NORM | conformance/collections/set_heterogeneous | the snapshot's wording of the same set-item refusal |
| msg-doseq-first-rule | NORM | conformance/control/doseq | the snapshot hits an `:i64` if-test refusal before the host's reserved `__kotoba_` rule |
| msg-nth-unlowered | NORM | conformance/functions/lazy_sequences | "named by the grammar, no lowering" vs "unknown operation" |
| exports-doc-helpers | NORM | nbb/fixtures/{callable-values,typed-closure-parameters} | the snapshot appends 7 synthetic `__kotoba_doc_*` helpers to `:exports` |
| check-missing-source | NORM | fx `check` | "missing source input" vs the host's extension refusal, both exit 64 |
| source-path-relative | GAP | fx `--source-path proj` | no cwd wire 40: the image refuses a relative root with `:project-link` (exit 65); bin/amu accepts |
| policy-not-a-map | GAP | fx p12 x 4 | bin/amu answers an internal error (exit 70); the image answers malformed capability policy (exit 65) |
| profile-phase | GAP | fx p33 x 4 | same refusal text; the current frontend tags it `:hir-validation` (exit 70), the snapshot `:subset` (exit 65) |

The image-agent's harness reported "9 message-wording + 2 `:exports`". These are the msg-* and exports-doc-helpers
rows. All of them except msg-effect-ceiling-set come from the frontend snapshot the image links (the seed17 farm), not
from amu's check entry.

**Product fix (this branch, 192bc71b0)**: check-driver's Kotoba `read-policy!` read `--policy` with bounded-edn
`read-file` (`fs/app-data-bytes`), which traps on a missing path or a directory. It now uses cli-support's
`read-policy` (nbb-io `read-text-file`, which refuses by name with `:decode` "input could not be read", exit 65), the
reading the host and nbb.cli already use.

To measure the fix without a new generation, a test image was made from g3's objects with only check-driver recompiled
by g3's `compile --emit-module` (the unchanged file reproduces g3's object byte for byte), then linked and packaged the
launcher's way (command `6218eaa6`; not a qualified image). On it args.sh gives **22 DIFF + 151 NAMED** (g3: 24 + 149):
`--policy nosuch.edn` and `--policy sub` now answer as bin/amu does. The qualified image carries the fix only after the
next fixed-point rebuild.

**prove-100** (`scripts/seed/prove-100.sh build/fp/g3/amu build/fp`, at 192bc71b0, g3 `27ffb605`, load1 191-248):
4 PASS, 10 FAIL.

The run used a detached checkout of this branch under `/private/tmp`, because the image's baked fs scope is
`amu-image-entries:amu-embench:/private/tmp:/tmp`: run from another worktree, every file read traps. In that checkout
`build/seed/noproc` had not been built, so INTERPOSER failed. After building it, `launcher/test.sh` gave L3 PASS (6
runs, 0 exec/spawn).

| row | verdict | cause |
|---|---|---|
| INPUTS | PASS | manifest `9b8dee8d` |
| G4 | PASS | 3 generations equal, builder receipts present |
| PRODUCT | FAIL | `bin/amu` is still node + nbb |
| ENTRIES | PASS | check-cli and aarch64-cli objects present |
| STATIC | PASS | libSystem only; wires 3,34,35,37,38,39 |
| G1 | FAIL | L2: amu-embench absent (0/19); L1 PASS (39: 11 SAME, 17 SAME-DATA, 11 DECLARED), L4 PASS |
| INTERPOSER | FAIL | run checkout lacked noproc.dylib; rerun with it: L3 PASS |
| G2 | FAIL | vs bin/amu: no policy **372 NAMED**, corpus-policy **372 NAMED**, corpus-policy-all **347 DIFF** (all SIGTRAP exit 120: the 42-grant policy, the known more-than-32-grants trap) + 25 NAMED. Each mode has 372 rows, not 391 (Embench absent) |
| COMPILE_FULL | FAIL | unchanged: 293 BOTH-ACCEPT SAME + 62 BOTH-REFUSE; 1 CLASS-DIFF (w1-effect-named) + 16 HOST-ONLY (verifier strictness) |
| G3 | FAIL | vs bin/amu: 149 NAMED, **24 DIFF**: 4 SIGILL on a missing or directory policy and on paths outside the baked scope (the 2 missing/directory ones are fixed by 192bc71b0); 4 SIGTRAP on p32 (`{:a }`, an odd map); 4 SIGILL on p34 (invalid UTF-8: nbb-io's read still traps); p05 (`:allow` as a vector) and p27 (`nil`): bin/amu refuses with malformed policy, the image admits 3 of p05 and 2 of p27, and refuses the rest with a different message (1 and 2); p20 (`#_` discard): bin/amu reads it, the image's bounded-edn refuses dispatch forms (3 exit splits + 1 :error) |
| CHECK_FULL | FAIL | 0 STUB, 9 GAP cases (source-path-relative 1, policy-not-a-map 4, profile-phase 4) |
| G5 | FAIL | `sudo -n dtruss` needs a password |
| REFACTOR_VERIFY | FAIL | declared stub (needs wire 20) |
| QUIET_BENCH | FAIL | load1 247.95 |

**Open**:
1. The policy reading of the Kotoba route differs from the host on malformed input. p05 and p27 are admitted:
   kir.admission's typed reading (osaho) does not refuse a vector `:allow` or a `nil` policy. p20 is refused, because
   bounded-edn has no `#_`. p32 and p34 trap. These stay DIFF in G3.
2. The more-than-32-grants trap (G2 corpus-policy-all) and crc32 / matmult-int are being fixed elsewhere.
3. The frontend snapshot's rows go away with a newer farm.

## 10. Addendum 2026-10-10: final round, malformed input refused by name, upstream fixes in the farm, rebuilt and measured (agent claude, branch claude/image-product-entries)

**Inputs** (`scripts/seed/selfbuild-inputs.sh`, defaults now pinned by full commit; then `selfbuild.sh --no-link`
with seed r6m: 143/143 OK; then `rebuild.sh` with seed r6n `b3f46d32`). Source tree amu 665594a11. Classpath = the
seed17 farm (order sha256 `6e9adfc0`, 67 classpath files) with these overlays, each taken by `git show <commit>:<path>`
(the repos' local branch refs lag their remotes, so the commit, not a branch or a /private/tmp path, is the input):

| repo | commit (agent/dual-runtime-port-D) | file | sha256 |
|---|---|---|---|
| osaho | 3d29ca9e56320837567d65120fc53b09bd88c83f | src/kotoba/kir/admission.cljk | `e3ebd5c5` |
| osaho | 3d29ca9e (as d2cc281) | src/kotoba/kir/interp.cljk, target.cljk | `977b1c44`, `2c702939` |
| kotoba-mir | e2cf973cdda3c88d84f34b0a6e84d6ded93ed763 | src/kotoba/mir.cljk | `c7f56572` |
| kotoba-native | ca8bb098e349226d623c48c7eb267f44de52d711 | src/kotoba/native/machine_ir.cljk | `e7c3fdb5` |
| kotoba-lang | 965c5f5b2f574f6be8f0b9572ca6cd6bac28ce97 | lang/compat (project and reader twins) | |

Rebuild input manifest (`build/fp/inputs.sha256`) sha256 `85308ab7`; scan order (143 modules) `3e74a33c`.

**Part 1: malformed input** (commit 665594a11; Kotoba readings only). Each changed `.cljk` file was read with the
`:clj` features and again with `:cljs`, at HEAD and in the tree. The forms are the same, compared as printed data, so
the host readings are unchanged. Host `bin/amu` vs the image, through `check` (io/pure/two/abort) and `compile`:

| case | before (image on the same new inputs, without part 1) | after (g3 `293ea98e`) | bin/amu |
|---|---|---|---|
| p34: invalid UTF-8 in the policy | SIGILL 120 | 65 `:decode` "input is not valid UTF-8" | same |
| bad-utf8.kotoba: invalid UTF-8 source (new fixture) | SIGILL 120 | 65 `:decode`, same text | same |
| `/Users/junkawasaki/nonexistent-checkfull.{kotoba,edn}` (outside the baked scope) | SIGILL 120 | 65 `:decode` "input could not be read" | same |
| p20: `#_` discard in the policy | 65 "EDN dispatch forms are forbidden" | accept io/pure/abort, two 65 denied | same |
| p27: `nil` policy | pure/abort admitted (0), io/two "denies required effects" | 65 `:admission` "malformed capability policy" | same |
| p32: `{:a <U+0007>}` | 65 malformed (SIGTRAP on g3 `27ffb605`; osaho 3d29ca9 fixed it) | same | same |
| p05: vector `:allow` | 65 malformed (osaho 3d29ca9 fixed it) | same | same |

- p32 is not an odd map. Its value is the one-character symbol U+0007 (BEL is a token character for both readers).
  The host's kotoba reader reads `{:a \u0007}` and admission refuses it. The trap was in admission's document-typed
  reading, which osaho 3d29ca9 replaced.
- nbb.io `read-text-file` (source, `--policy`, `.kexe`): first EXISTS, because STAT and READ trap outside the scope
  and EXISTS answers "0" there. Then STAT (directory, size), then a bytes READ. Then `text-bytes/utf8-valid?` (new,
  Kotoba only; the same walk as the loader's `string-from-utf8`) runs before the bytes become a string.
- bounded-edn: its own READ gets the same guards. New `read-reader-text-limits` = the host's cli-support
  `read-edn-form!` (the kotoba reader with no dispatch preflight). cli-support reads `--policy`, `.kexe` and module
  locks through it, because the host reader admits `#_` and sets. So p20 is decided by reading it, not by a NORM/GAP
  row. bounded-edn's own `read-edn-text` keeps its preflight contract.
- `nil` policy: kotoba.form's `dissoc-form` made a map out of any Form's kids. cli-support `capability-policy`,
  check-driver `cd-capability-policy` and native-artifact's two dissocs now hand on a non-map policy unchanged, as the
  host's `dissoc` does.
- Regression lists: `seed/tests/checkfull/cases-args.txt` (used by check-cli/args.sh) gains `check bad-utf8.kotoba`
  and 7 malformed-input `compile` cases. `seed/tests/compile-cli/refusals.sh` gains 8 cases. p05/p20/p27/p32/p34 already
  run in every args.sh pass (p*.edn x 4).
- refusals.sh's build-from-source guest no longer builds: the seed refuses aarch64-cli's `run` (E2104, `expected :i64`,
  with r6m and with r6n). The cause is the `run [args]` export of section 8, not this change. Its host column gives the
  expected codes for the 8 new cases: 65 x 7 and 0 for p20. The image answers all of them through args.sh (below).

**Generations** (`zsh scripts/seed/image/rebuild.sh build/rin build/fp`, 138 s): **fixed point, g0 = g1 = g2 = g3**.

| gen | built by | objects (172) manifest | kseed | native code | command |
|---|---|---|---|---|---|
| g0 | seed r6n `b3f46d32` | `9d7a6966` (25,387,078 B) | `02f5630b` 10,993,179 B | `6076a455` 10,993,144 B | `293ea98e` 11,261,064 B |
| g1 | g0's image | `9d7a6966` | `02f5630b` | `6076a455` | `293ea98e` |
| g2 | g1's image | `9d7a6966` | `02f5630b` | `6076a455` | `293ea98e` |
| g3 | g2's image | `9d7a6966` | `02f5630b` | `6076a455` | `293ea98e` |

Full hashes: kseed 02f5630be78e59f8e1da7ef7084d6db09a053ab7b8f44b8d5834842451b774ca, code
6076a45566456c68340d164ee91f10874beffb8d3f39cb057c68f40ee9fec49f, command
293ea98e92cec0a319011fc4e4cec9217fc8908dba333aba5055c892595500f6. A test image built before the commit, which differed
only in two host `nil` forms, gave the same command `293ea98e`. So the Kotoba objects do not see the host readings.

**Size**: the kseed is 10,993,179 B (+14,832 B against section 8). That is 65.5% of r6n's 16 Mi extract input bound
(16,777,216 B), with 5,784,037 B of headroom.

**Corpus through the image** (g3, load1 50-190):
- `compile` vs bin/amu (`seed/tests/compile-cli/run.sh --image`):
  - 372 corpus programs: BOTH-ACCEPT **293** (seal, provenance and answer SAME on all; publication 290 SAME-SHAPE and
    3 SIZE-DIFF). BOTH-REFUSE with the same exit **62**. BOTH-REFUSE-CLASS-DIFF **1** (examples/w1-effect-named:
    host 65 `:admission`, image 70 `:target`, native-admission; named in section 8). HOST-ONLY **16** (the verifier
    twin's kept strictness: 8 "unsupported effect" abort programs, 8 "runtime KIR shape/operation rejected").
    GUEST-ONLY **0**. These are section 8's classes, unchanged.
  - 19 in-repo Embench ports (`bench/embench/ports`): **19 BOTH-ACCEPT SAME** (seal, provenance, answer;
    publication SAME-SHAPE). **crc32 and matmult-int are now SAME** (section 8: HOST-ONLY, exit 120 at the 64 Mi pair
    ceiling). That is kotoba-mir e2cf973 + kotoba-native ca8bb09.
- `check` vs bin/amu (`seed/tests/check-cli/image.sh`, 391 = 372 + 19 ports; image.sh, corpus.sh and launcher L2 now
  take the in-repo ports when the amu-embench checkout is absent): **0 traps, 0 DIFF** in all three modes.
  - none: 358 accept + 33 refuse.
  - corpus-policy: 359 + 32.
  - corpus-policy-all (42 grants): 366 + 25 (section 8: 347 SIGTRAP).
  - Every row is NAMED with NORM rows only: definitions-marker on every accept, reduced-report on every refusal, and
    the snapshot rows msg-require-module 5, exports-doc-helpers 2, msg-effect-ceiling-set, msg-set-literal-wording,
    msg-doseq-first-rule and msg-nth-unlowered 1 each.

**L1-L4** (`scripts/seed/launcher/test.sh build/fp/g3/amu`): all PASS.
- L1: 39 cases, 11 SAME, 17 SAME-DATA, 11 DECLARED.
- L2: Embench 19/19 BEHAVIOUR-SAME against stage-0, 114 export runs SAME, 19 seals ok, in-repo ports.
- L3: 6 runs, 0 exec/spawn.
- L4: libSystem only.

The first L2 run failed 0/19, because of stale stage-0 failure records in `build/seed-kir/census/kexe/*.fail` from an
earlier run ("input must be a regular file"). Those records were removed and the run repeated.

**prove-100** (`scripts/seed/prove-100.sh build/fp/g3/amu build/fp`, at 665594a11, g3 `293ea98e`, load1 50-210):
**8 PASS, 6 FAIL** (section 9: 4 PASS, 10 FAIL).

| row | verdict | cause |
|---|---|---|
| INPUTS | PASS | manifest `85308ab7` |
| G4 | PASS | 3 generations equal (objects, container, code, command), builder receipts present |
| PRODUCT | FAIL | `bin/amu` is still node + nbb (the image is not installed as bin/amu) |
| ENTRIES | PASS | check-cli and aarch64-cli objects in g3/o |
| STATIC | PASS | libSystem only; wires 3,34,35,37,38,39 |
| G1 | PASS | L1-L4 PASS; L2 Embench 19/19 BEHAVIOUR-SAME (in-repo ports), 114 export runs SAME |
| INTERPOSER | PASS | L3: 6 runs, 0 exec/spawn/system/popen |
| G2 | PASS | 391/391 in each of the three policy modes, NORM rows only, 0 traps |
| COMPILE_FULL | FAIL | 293 BOTH-ACCEPT SAME + 62 BOTH-REFUSE; the gate counts the named 1 CLASS-DIFF (w1-effect-named) + 16 HOST-ONLY (verifier strictness, owner: keep) |
| G3 | PASS | 181 cases (cases-args.txt incl. the 8 new + 35 policy files x 4), **0 DIFF** (section 9: 24 DIFF) |
| CHECK_FULL | FAIL | 0 STUB, 9 GAP: source-path-relative 1 (no cwd wire 40), policy-not-a-map 4 (p12: bin/amu internal error 70, image malformed policy 65), profile-phase 4 (p33: the snapshot's `:subset` 65 vs the current frontend's `:hir-validation` 70) |
| G5 | FAIL | `sudo -n dtruss` needs a password (fail closed) |
| REFACTOR_VERIFY | FAIL | declared stub (needs wire 20) |
| QUIET_BENCH | FAIL | load1 83.41 (> 4) |

**Open** (none of them is decided here):
1. The three CHECK_FULL GAP rows. p12 is a host internal error that the image answers better. Matching it would mean
   copying a host crash, which is an owner call. p33 goes away with a newer frontend farm. source-path-relative needs
   a cwd wire.
2. COMPILE_FULL's 17 named rows: verifier strictness (owner: keep) and w1-effect-named (kotoba-sema lines).
3. An existing file outside the baked scope is refused "input could not be read", where bin/amu reads it. That is
   the scope contract, and it is not measured as a case, because it depends on the machine.
4. The f64-literal question stays open (not touched).

## 11. Addendum 2026-10-11: compile-cli/run.sh builds its guest from source again (agent claude, branch claude/compile-cli-guest-build)

**Cause** (measured, seed r6m `8d3338e1` and r6n `b3f46d32`): `--entry`, not the objects or the order. Compiling
aarch64_cli.cljk against the image's own objects (`build/fp/g3/o`, which equal `front0/` file for file for these
modules), in scan order with only modules 1..109 present, and from the farm path all give E2104 with `--entry`. The same
command without `--entry`, as front.sh runs it, is OK (144,150 B with r6n, the image's object). An `--entry` module's
explicit exports must pass the loader's export codec (seed 21-check `ck-sig-export` / `ck-r6m-xty?`: :i64 :bool :string
:vector-i64, records, variants, fn values; no list). Section 8's `run [args [:list :string]]` fails that check. A
library's interface is the link table, so the image (root amu.main) admits it. The source is correct, so it is unchanged.

**Fix**: run.sh compiles nbb.aarch64-cli as a library, plus the new `seed/tests/compile-cli/guest.kotoba` (ns
`compile-cli.guest`, one export `main []` = `(product/main)`) as the `--entry` link root. Linked 8,210,649 B with r6m
(extract-native limit 8,388,608 B).

**Measured** (guest built by r6m against a copy of `build/fp/g3/o`, manifest `9d7a6966`; the 10 run.sh sources equal
the image's farm byte for byte):
- 372 corpus programs vs bin/amu: BOTH-ACCEPT 293 (seal, provenance and answer SAME on all; publication 290 SAME-SHAPE
  + 3 SIZE-DIFF), BOTH-REFUSE 62, CLASS-DIFF 1 (w1-effect-named), HOST-ONLY 16 (8 unsupported effect + 8 runtime KIR
  shape/operation), GUEST-ONLY 0. These are section 10's classes.
- 19 Embench ports: 19 BOTH-ACCEPT SAME (publication SAME-SHAPE).
- refusals.sh (host entry and guest columns): 34 cases. Equal exit 24, i.e. the 16 of the spike doc plus all 8
  section-10 cases (65 x 7, 0 for p20). The other 10 are the by-design rows (aarch64 / aarch64-linux / two packaged
  targets, `--artifact object`, `worker`, `extract-native`, `--module-lock`, `--package-lock`, `--fuel 5000`). The
  guest writes no artifact except p20, where both sides admit it.
