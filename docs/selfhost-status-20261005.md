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
| seed compiles the compiler from source (selfbuild `--no-link`, 138 modules) | **138 / 138** on r6m with the refactor modules through their kotoba-lang twins (2026-10-10: 143/143 with the closure's 5 extra modules incl. rule g's twin rules.fnlit; kotoba-lang `claude/refactor-twins-parity` 1c7260f, amu c78b96f3f, osaho d2cc281 interp/target). In place (amu's own refactor `.cljk`): 122 / 138 (124/141). Before: 122 / 138 (2026-10-09), 120 (WALL2), 113 (FRONTSRC), 111 (FOLD) | `docs/selfhost-selfbuild-20261004.md` section 8; `scripts/seed/selfbuild-inputs.sh` + `selfbuild.sh --no-link`; walls left: none in the twins view; in place 5 refused (refactor.cst `declare`, edit/diff/verify `#`, prelude exports nothing) + 12 blocked incl. rules.fnlit (owner decision: twins vs in-place readings) |
| frontend from source | 33 modules / 64,457 lines compiled by the seed, no kir-dump; amu-one-src rebuilds itself byte-identically for 3 generations on r6l | REBUILD `cf201da75`, `scripts/seed/launcher/rebuild-r6l.record` |
| native `amu` (one Mach-O, C loader + seed-built code, libSystem only, wires 3,34,35,37,38,39, never 20) | unified image = launcher + check + compile + refactor; REBUILD's `fc691d84` rebuilds itself 3 generations; CHECKFULL's `994fb5ed` (6,043,128 B) adds check's policy/project route | `launcher/test.sh` on `994fb5ed`: L1 34 SAME + 3 DECLARED, L2 Embench 19/19 (114 export runs, 19 kexe/v1 seals), L3 0 exec/spawn/system/popen in 6 runs, L4 PASS |
| `check` | **391/391** corpus programs = stage-0 (verdict, line, exit) without a policy and with two policies (grants 35,37,38,39; all 42 catalog names); `--policy`/`--profile` 150 SAME + 9 SAME-NORM + 5 DECLARED + 9 STUB, 0 DIFF; `--source-path`: WALL2's 17 trees x 2 = **34/34 byte-identical**, CHECKFULL's 9 trees x 2 = 14/18 | `seed/amu-main/CHECK.md`, `seed/tests/checkfull/*.sh` |
| `compile` (aarch64-macos) | 264 of 315 stage-0-compilable programs behaviour-same, 646 export runs SAME, 0 DIFF (launcher on r6l); r6m compiles 35 of the 47 refusals seed-direct (33 behaviour-same), **not yet in an image** | REBUILD record; SEEDLANG `1f1e69a62` |
| `refactor` | every sub-command real on the Kotoba route except `verify`'s process runs (needs wire 20, never granted); 0 differ in 10 suites vs bin/amu (args 31, graph 20, plan 18, partition 19, dynvars 44, graph-src 109, plan-src 128, apply 40, split 10, verify twin 5); content holding `WRITE_SEP` now applies (6/6 SAME; was SIGILL) | `scripts/seed/refactor/all.sh` on CHECKFULL's code; `seed/tests/checkfull/refactor-writesep.sh` |
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
