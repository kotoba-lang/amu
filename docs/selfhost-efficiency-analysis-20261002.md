# Selfhost: the most efficient way to finish (analysis, 2026-10-02)

Goal (owner, rule 11 of `docs/selfhost-priority.md`): an `amu` built by `amu` that runs `check`, `refactor` and
`compile` on its own sources with zero node/JVM/nbb processes. Stubs and refusal twins do not count. This page
does not port anything. It reads the evidence (docs, scans, git history, workflow journals) and says what to cut,
what to reorder and how to run the agents. Every number has its source in the appendix. Where a number is an
estimate, it says so.

## 0. Summary

1. **Prune the target.** A first self-build needs one target (aarch64-macos), one entry (check + compile +
   refactor) and **122 modules (about 123k lines with both readings), not 177.** The other 55 modules
   (wasm, component, script, x86-64, linux-static, uefi, pe32/elf, cljs/evm/js backends, test/trust/run CLIs)
   hold about 27k lines of host code with no Kotoba reading. None of them is on the path.
2. **Stop work on the KIR interpreter beyond what constant folding needs.** It took 15% of agent time. The
   self-built compiler needs `kir/lower` and an evaluator only for `fold-def-value!`. Oracle sealing applies
   only to pure i64/bool entries, so it never runs for `amu` itself. As a test harness the interpreter is
   now about 1000x slower than compiled native guests.
3. **The critical path is now three parallel tracks that meet in integration:**
   (A) the rest of the frontend plus a linked end-to-end differential;
   (B) the native code generator (`machine_ir` + `aarch64`, about 11.4k host lines, almost nothing ported);
   (C) native runtime capacity (value-size limits, a list builder, heap high-water, abort across modules).
   The driver (`project`, `nbb/cli`), `refactor` and the launcher come after these and are small.
4. **Representation.** Keep the Form rewrite for the frontend: it is about 75% done, so switching now
   would waste that work. For the host-map-heavy modules still to do (`machine_ir`, `aarch64`, `project`,
   `kir` lower, `refactor`), run a one-day decision test first: make the core collection ops polymorphic
   over `:form/r`, so code can be ported nearly verbatim. A full dynamic runtime (option b) is rejected:
   it costs months and contradicts the language's bounded, typed design.
5. **Measure REAL, differential-covered definitions on the pruned set, not files OK.** Do not run per-file
   sweep waves again: 321 agents produced 12 admissions.
6. **ETA (estimates, assumptions in section 3).** Current method: 16-28 days to rule-11 100%. Recommended
   method: 9-15 days. The main risk tail is native memory with no reclamation, about +5 days.

## 1. Critical path

### 1.1 Where things stand (measured)

| item | state | evidence |
|---|---|---|
| reach list | 119 / 162 OK on the native checker (`wall-scan-native4.tsv`, 2026-10-01 23:53), nbb peak 96 | scans |
| REAL among OK | 70 / 94 REAL, 14 PARTIAL, 10 HOLLOW (632 public defns, 448 with a Kotoba body) | real-vs-hollow audit |
| frontend | 20.0k lines -> 43.4k lines (both readings); 0 -> 2727 `#?(:kotoba` arms in 48 h; desugar, infer, validate, expand, base, closure-types, kernel-region, namespace-defs carry Kotoba bodies | git, section 2.3 |
| frontend not ported | `analyze` (2836 lines, 63 defns, 23 arms), `record_projection` (1426 / 14 / 10), `row` (562 / 18 / 1), `state_ability` (640 / 9 / 4) | grep |
| frontend blocker | 12 reach files stop at `document-of-constructor! is not exported by ...infer` | native4 |
| differentials | vx 1543/1543 (interp), 905/905 (native); ds 1241/1245 (native); abort 730/731; mir differential; probes for 6 leaf modules | docs |
| native backend | aggregate lists, bytes fields, options of handles, document ops: closed. All 9 guests compile and run natively | native-gaps |
| `kotoba.kir` (6133 lines, 134 defns) | 0 arms; twin `kir.kotoba` (253) + `kir/interp` (1631) + `kir/lowering` (422) cover a subset | grep |
| `kotoba.verifier` (3450) | 7 arms; Kotoba twins of about 3.2k lines (`verifier`, `/kir`, `/program`, `/ops`, `/fx`, `/signing`) | wt-K |
| `mir` (7716), `gmir` (2492), `codegen` | OK on the Kotoba route (mir has a differential) | scans |
| `native/machine_ir` (9774, 295 defns), `aarch64` (1672, 73 defns) | 6 + 3 arms; refused at `constant must contain exactly one literal value` | grep, native4 |
| `project.cljk` (1917, 69 defns), `core.cljk`, `nbb/cli` (768), `wasm_cli` `check!` | 0 arms | grep |
| refactor library (`refactor/*`, 2848 lines) | about 16 arms, essentially host-only; **not in the reach list at all** | grep |
| launchers | `bin/amu` 631 lines of Node, `bin/kotoba` 310 lines of nbb | bootstrap-boundary |

### 1.2 Dependency DAG (to rule-11 100%)

```
 C1 list builder (typed-list-conj copies)   C2 value-size ABI (64 KiB -> >= 8 MiB)
 C3 heap high-water / arena reclamation     C4 abort across module boundary (sema)
 C5 project bounds (16384 fns, 1024 exports) measured on the linked compiler
        |                    |                        |
        v                    v                        v
 A1 frontend remainder ---> A2 linked frontend e2e differential (canonical HIR, corpus)
   (analyze driver, record-projection, row, state-ability, fold-def-value!)
        |                                             |
 K1 kir/lower REAL (HIR->KIR, validation) ---+        |
 K2 fold evaluator = KIR eval SUBSET --------+        |
        |                                    |        |
 B1 machine_ir + aarch64 Kotoba route ---> B2 native-package (kexe) w/o linux-static/pe32 edges
        |                                             |
 D1 driver: project linker, project_files, compile-native!, check! moved out of wasm_cli,
    cli_support/project_source/module_lock REAL, host seams (clock/env/entry) as capabilities
        |
 S5 stage0 (host route) builds stage1 amu.kexe -> stage1 builds stage2 -> stage2 == stage3 bytes
        |
 R1 refactor library + refactor_cli (parallel from now) ----+
 L1 native launcher (argv, --source-path/lock resolution) --+--> S6 no-host-processes.sh on
 V1 verifier on the Kotoba route (parallel, off path) ------+    check/refactor/compile of own sources
```

Gating facts:
- **C1-C3 gate every natively run differential at compiler scale, and gate S5.** Today the ds guest needs 4M
  vector-table entries and 128M item words because `typed-list-conj` copies. A string or bytes value is capped
  at 64 KiB, but a source file may be 8 MiB (ADR 0356) and `desugar.cljk` alone is 10.6k lines. The runtime
  has bounded arenas and no reclamation. None of this blocks porting. It blocks S5, so it must start now,
  owned by one strong agent.
- **C4 gates A2.** An aborting imported function does not propagate its abort, so modules carry local copies
  (`type-valid!`, `ae-let-body`, ...). The linked frontend cannot be trusted until sema carries `E` and
  `:abort` across the import interface.
- **A1 -> A2 gates D1 and S5.** Everything after the frontend consumes HIR.
- **K1 gates B1's input and S5. K2 gates only `fold-def-value!`** (`frontend/analyze.cljk:1729`).
- **B1 is the largest unported block on the path** and was not on anyone's list. It can start today in
  parallel with A1, because MIR is already Kotoba-route and differential-tested.
- **R1 and L1 gate only the final S6 claim,** so they run in parallel. V1 runs in parallel too (section 5,
  decision 4).

### 1.3 What can be cut or deferred

| item | why it is not needed for the first self-build | saving |
|---|---|---|
| KIR interpreter beyond the fold subset (`eval-expr` 1800 lines, wave 9/10 families) | the oracle seals only an entry with zero arguments, an i64/bool result and pure/state/abort effects (`kir.cljk` `lower`); `amu`'s entry is effectful, so its build never seals one. Check-time evaluation is `fold-def-value!` only. Native guests replaced it as the harness (ds: 288 s interp vs 4.1 s native for 100 cases) | 15% of agent time so far |
| wasm backend + `wasm_cli` + component (`component/core` 14.3k, `wasm/core` 4.1k, `wasm/tools`, `canonical_abi`, `typed`) | one target suffices; move `check!` out of `wasm_cli` into the native entry | about 20k lines |
| x86-64, linux-static, uefi, pe32plus, elf64, `packaging`, `linux_static_handlers` | aarch64-macos only; cut 5 require edges (below) | about 9k lines |
| `backend/cljs`, `backend/evm`, `js_cli`, `evm_cli`, `script` (3.3k), `ios_aot` | not check/compile/refactor of amu | about 4k lines |
| `test_cli`, `trust_cli`, `run_cli`, `test_profile`, `lang_conformance`, `reference_runtime`, output-admission/attestation, release, receipt | not in rule 11's three commands | about 4k lines |
| definition CIDs (`check --json :definitions`) | 89% of check time; already REAL; keep but put last | n/a |
| nbb/JVM parity fixes (`nbb` leniency, JVM-route staging defects) | bootstrap only | n/a |

Edges to cut so the pruned closure holds (one-line target-dispatch or reader-conditional changes):
`nbb/cli -> uefi-operations`; `nbb/native-package -> native.linux-static, verifier.linux-static,
packaging.pe32plus, linux-static-handlers`; `verifier -> native.x86-64`; `check!` out of `nbb/wasm_cli`.

### 1.4 Pruned minimal reach set (computed from the `ns` requires of the 162 reach files plus the 15 split
frontend modules; roots `nbb/aarch64-cli`, `nbb/cli`, `nbb/refactor-cli`, `sema`, `native/aarch64`)

| set | modules | lines (both readings) | OK on native checker | not OK |
|---|---|---|---|---|
| everything reachable from every `*_cli` | 177 | 171.6k | 119 of 162 listed | - |
| **minimal: check + compile(aarch64) + refactor** | **122** | **122.7k** | 86 of 107 listed (+15 frontend modules) | 36 modules, 71k lines (includes frontend, kir, verifier, machine_ir, project) |
| deferred | 55 | 48.9k | 34 | 21 (about 27k lines of host-only code) |
| plus, not in the reach list | refactor library | 2.8k | - | host-only |

The not-OK modules in the minimal set, in work units: frontend (facade + 12 pass modules + `kotoba_reader`),
`kir` (lower + fold subset), `verifier`, `native/machine_ir`, `native/aarch64`, `project`, `project_files`,
`core`, `effect_row`, `effect_classification`, `capability_names`, `nbb/cli`, `nbb/aarch64_cli`,
`nbb/native_package`, `nbb/host/{clock,env,entry}`, `lang/{coll,text,io/file}`. Most of the "if branches must have the same
value type" rows (`core`, `effect_row`, `interface`, `capability_names`, `effect_classification`) are the
frontend dependency showing through and need no separate work until A2.

**Remaining host code on the minimal path (estimate):** frontend 5.5k + kir lower/fold 2-3k + machine_ir/aarch64
11.4k + driver/project/cli 3.5k + refactor 2.8k + leaves 2k = **about 27-28k host lines**, plus C1-C5 and the
launcher. Under the current scope the same count is about 55k: the deferred 27k, plus finishing the
interpreter.

## 2. Representation strategy

Facts that decide it:
- The Form rewrite works and has momentum. From 09-30 12:00 to 10-02 12:00 the frontend went from 0 to 2727
  Kotoba arms. About 15k host lines of passes are rewritten, and the differentials agree, with harness
  artifacts accounting for the mismatches.
- Rewrites inflate. Kotoba readings are 1.5-2x the host lines (frontend 20k -> 43k with both readings kept),
  and in the audit's token counts up to 4-9x for low-level modules.
- What is left is a different shape. `machine_ir`, `aarch64`, `project`, `kir` lower and `refactor` are
  host-keyword-map code (`{:mc/op .. :mc/target ..}`, `{:mir/keys [...]}` destructuring), the same shape as
  `mir`. `mir` took one agent 576 minutes for 7.7k lines.
- The language already has two dynamic value types. `:form/r` is recursive and native since the
  aggregate-list fix. `:document` is native only as canonical EDN text: 32 items per container, depth 8,
  4096 nodes, every operation O(n). That makes `:document` unusable for compiler data.

| option | what it costs | what it buys | verdict |
|---|---|---|---|
| (a) continue Form rewrite + codemods a-f | about 28k host lines at about 6-8k/day with 5-6 agents (section 3) | proven path; differential per pass | **keep for the frontend; default elsewhere** |
| (a') Form-polymorphic core ops: `get`/`assoc`/`dissoc`/`keys`/`vals`/`count`/`first`/`rest`/`nth`/`conj`/`map`/`filter`/`reduce`/`{:keys}` destructuring lowered to `kotoba.form` calls when the operand is `[:ref :form/r]` | about 1-2 days. The 25 `:document` heads took one morning on 09-30. It must be added on the host frontend and its Kotoba twin (desugar arms) | ports host-map code nearly verbatim: keyword maps become Form maps. Cost: O(n) map lookup, fine for 5-15-key instruction maps and bad for large symbol tables, which stay typed | **run the decision test, then adopt for B1/D1/K1/R1 if it passes** |
| (b) full dynamic runtime: persistent maps/vectors/sets, seqs, atoms, symbols, closures-as-values, exceptions, dynamic vars, regex, `pr-str` | native heap + GC (or refcounting) on 2 ISAs, verifier twin, loader, frontend untyped-value typing, about 150 clojure.core functions, a Clojure-identical printer. Estimate 4-10 weeks | ports nearly verbatim | **reject**: it costs more than the remaining rewrite (about 2 weeks), it reverses the bounded/typed design (ADR 0355-0360), and 75% of the frontend no longer needs it |
| (c) new subset compiler written from specs and tests | rewrite 757 `reject!` sites, ADR behaviours and the codegen from scratch | smaller | **reject**: the host route already is a stage-0 compiler for the Kotoba reading (guest-run compiles Form guests natively today). A subset compiler adds a third semantics to keep identical |
| (d) JVM native-image as stage-0 | about 7-12 min per build, peak RSS 4.5 GB, one at a time; already exists | 20-40x faster check/compile than nbb for builds and differentials | **adopt as BOOTSTRAP tooling**, not as a strategy. It stops being bootstrap at S5: stage1 (built by stage-0) builds stage2, stage2 builds stage3, and stage2 == stage3 bytes. From then on stage-0 is only a regression reference |

**Decision test for (a'), about one day, one strong agent, in its own worktree.** Take 3 `machine_ir`
functions of different shapes: `lower-mc-instructions` (map rewrite), one register/frame helper, one encoder
table walk. Port each twice: (1) Form rewrite under the current rules, (2) the (a') prototype, with ops added
to desugar on both readings. For each port, measure the agent minutes, the Kotoba lines against the host
lines, native differential agreement on recorded host inputs, and native run time.
**Adopt (a') if** its ports take at most 1/3 of the time, agree 100%, and run at most 2x slower. Otherwise
continue with (a) and split `machine_ir` into 4-5 modules with `amu refactor split` for parallel ports.

**Decision test for the interpreter cut, about 2 hours.** Wrap `kir/execute` inside `fold-def-value!` on the
host. Run `check` over the 122 minimal modules and log the distinct `eval-expr` heads used. If
`kir/interp.cljk` covers them, freeze interpreter work. If not, port exactly the missing heads.

**Decision test for memory (C3), about 2 hours.** Run the native ds guest on its largest corpus batch and on
a synthetic module the size of `desugar.cljk`. Record loader high-water marks (pairs, vector table, items,
string pool) and extrapolate to the 122-module self-compile. If the extrapolation exceeds about 8 GB, add
per-function or per-module arena reset before S5.

## 3. Throughput

### 3.1 Measured rates (2026-09-29 22:00 to 2026-10-02 10:30, about 2.5 days)

| metric | value |
|---|---|
| workflow waves / agents / agent-hours | 22 waves, 479 agents, 101 agent-hours (all `claude-sonnet-5-5`) |
| tokens | 8.9M output, 4.0B input (mostly cache reads) |
| commits since 09-29 | amu 139, kotoba-sema 66, osaho 27, kotoba-lang 30, verifier 15, native 19, mir 5, wasm 5, codegen 3 |
| files OK (nbb) | 58 (09-30 13:11) -> 96 (10-01 21:13): about 28/day, mostly leaves; native4 119 |
| REAL (audit) | 68 -> 70 of 94 in one day of re-measurement |
| frontend Kotoba arms | 0 -> 2727 in 48 h; about 15k host lines rewritten in about 37 agent-hours (about 400 host lines per agent-hour, about 7.5k per day at 5 parallel agents) |
| differential cases agreed | vx 1543 + 905 native, ds 1241, abort 730, infer (in progress); about 4-5k agreed cases in total. Coverage, not time, is the right denominator |

### 3.2 Where agent time went (agent-minutes from the journals)

| area | agents | agent-min | share | comment |
|---|---|---|---|---|
| frontend port | 23 | 2200 | 36% | the real progress |
| KIR lower/interpreter | 5 | 898 | 15% | mostly off the critical path (section 1.3) |
| leaf walls / limits | 33 | 884 | 15% | half useful (ADR 0355-0360, io/edn leaves); half re-walls |
| mir/wasm port | 4 | 605 | 10% | mir needed (576 min); wasm not |
| per-file sweep (3 waves) | 321 | 409 | 7% | **12 ADMITTED, 29 ALREADY_OK, 265 BLOCKED**: 3.7% yield; 342M input tokens re-discovering that the code is host-data-shaped |
| verify agents | 75 | 347 | 6% | 1-3 minute confirmations; a script does this |
| verifier + signing | 2 | 331 | 5% | twin exists; off path for S5 |
| native backend / checker | 6 | 217 | 4% | very high value per minute (aggregate lists, fast checker) |
| docs / repo meta | 10 | 186 | 3% | |

Waste, measured or named in agent reports:
- **Same-file contention.** 33 agent results report another agent's edits or a half-saved file. One example:
  `Feature should be a keyword` from a half-written `kotoba-sema` file was misread as a native-backend
  failure (native-gaps, update 2). The 12 frontend modules all declare the `:fe/env` schema, so a field
  change touches 12 files.
- **Stale classpaths and paths.** About 33 results mention it. `wall-cp-5` .. `wall-cp-11`;
  `check-native` remaps stale gitlib and old-worktree paths; `bin/amu`'s pinned classpath re-verified with
  the old verifier; `wall-scan-21` had 24 stale rows.
- **Slow oracles.** Before the native guests, linking the 1000-function desugar guest on nbb took about
  5 minutes and each 100-case batch several more. One attestation probe used about an hour of interpreter
  time.
- **Keeping the JVM reference alive** cost repairs to six JVM-route defects (fast-checker section 5).
- **Metric drift.** Files OK rose while REAL barely moved. 94 OK files included 26 PARTIAL/HOLLOW, and the
  frontend's own scan line hides about 104 unported definitions behind one refusal.

### 3.3 ETA (estimates)

Assumptions: 5-6 concurrent porting agents plus one integrator. 6-8k host lines ported per day (the frontend
rate, discounted for integration). Integration bugs found by the end-to-end differential and the stage build
take 40-60% of the porting time, as the frontend's linked-module walls did (sections 8-10 of the typemodel
doc). C1-C3 do not need a redesign of the value ABI beyond raising limits and adding a builder.

| method | host lines left | porting | integration + S5 | S6 (launcher, refactor, no-host trace) | total |
|---|---|---|---|---|---|
| current: unpruned, file-OK metric, interpreter/wasm/verifier continuing, sweeps | about 55k | 7-10 days | 5-10 days | 3-5 days | **16-28 days** |
| recommended: pruned set, (a) or (a'), stage-0 native-image, scripted gates | about 28k | 4-5 days (3-4 with (a')) | 3-6 days | 2-4 days, overlapped | **9-15 days** |
| risk tail | memory reclamation (C3), the 16384-function bound, kexe KIR-as-EDN load time for a 40+ MB program | | | | +3-7 days |

## 4. Orchestration

**Partition by module, with one owner per file per wave.** Each owner works in its own worktree on its own
branch. The integrator alone merges and rebuilds the classpath snapshot.

| track | owner (model) | files | gate to merge |
|---|---|---|---|
| C runtime capacity | strong (Opus) | osaho value ABI, kotoba-native list builder, loader budgets, sema abort-across-modules | ADR + loader decision tests + `native-gaps.sh` 0 + memory extrapolation |
| A1a analyze driver + `fold-def-value!` | strong | `frontend/analyze.cljk` | native check OK + pass-level differential (tap after each driver binding) |
| A1b record-projection + row | mid (Sonnet) | `frontend/record_projection.cljk`, `frontend/row.cljk` | pass differential |
| A1c state-ability + `infer` export fix (`document-of-constructor!`) | mid | `frontend/state_ability.cljk`, `infer.cljk` export line only | 12 reach files move past the export refusal |
| B1 machine_ir (split first into about 5 modules with `amu refactor split`) | 1 strong + 3-4 mid, one per split module | `native/machine_ir/*` | per-module native differential against recorded host inputs |
| B1' aarch64 + native-package (with edges cut) | mid | `native/aarch64.cljk`, `nbb/native_package.cljk` | byte-identical emission on the guest corpus |
| K1 kir lower + fold subset | mid | osaho `kir/lowering`, `kir/interp` (subset only) | KIR equal to host on the frontend corpus |
| D1 driver | mid, after A2 | `project.cljk`, `project_files`, `nbb/cli`, `cli_support`, `project_source`, `module_lock` | e2e `check` outcomes equal on the 122 modules |
| R1 refactor | mid | `refactor/*`, `refactor_cli` | `refactor plan/apply/verify` outcomes equal on the frontend |
| leaves | cheap (Haiku/Sonnet) | `lang/coll`, `lang/text`, `io/file`, `nbb/host/{clock,env,entry}` | native check + probe |
| integrator | strong | none of the above; owns the classpath snapshot, merges, scans | full gate set |

Rules that remove the measured waste:
1. **One writer per file per wave,** enforced by a lock file (`.owner` with the agent id) checked by the wave
   script. Shared headers (the `:fe/env` schema in 12 modules, `frontend_tables`, ns `:refer` lists) belong to
   the integrator. Agents send schema changes as requests.
2. **Immutable snapshots for measurement.** At wave start, write `wall-cp-<sha>.txt` from a manifest of
   `repo@sha`, and `cp -R` each repo under test to `/tmp/snap-<sha>`. Agents measure against the snapshot and
   edit only their worktree. No agent measures a tree another agent is writing.
3. **Concurrency on this Mac:** 6 porting agents + 1 integrator. Rebuild the native-image checker centrally
   (7-12 min, 4.5 GB RSS, under a `flock`) at most every 2-3 hours, not per agent. Run full minimal-set scans
   under the same lock: about 1.5 min for 122 files with 3 processes. Per-agent checks are single-file
   `check-native.sh` runs (0.3-7 s). Native guest compiles are 15-20 s on nbb and seconds on stage-0
   native-image; at most 2 at a time.
4. **Gates per commit (scripted, no verify agents):** (i) `check-native.sh` on the touched module and its
   dependents in the minimal set; (ii) the native-compiled differential for every ported definition, zero
   disagreements, and new unported cases named; (iii) `hostview.py` byte-identical host reading; (iv) the
   ledger update below. Run the host suite (`run-tests.cljk`, before and after outcome sets) once per wave by
   the integrator, not per commit.
5. **The progress metric is a ledger, not a scan.** `selfhost-ledger.tsv` has one row per host definition in
   the 122-module set: `module, name, host-lines, kotoba-body?, differential-cases, disagreements`. Report
   `REAL+covered definitions / total` and `REAL+covered host lines / total`. Files OK is a diagnostic only.
   A 50-line script over the `:default` and `:kotoba` views (the audit's resolver) and the differential
   recordings produces it.
6. **No sweep waves.** A wall shared by many files (an export, a language construct) gets one owner and one
   fix. Per-file agents only for leaves with a known, distinct refusal.
7. **Models.** Strong models for representation, driver, runtime ABI, integration and the S5 fixed point.
   Mid models for pass ports with a differential already in place. Cheap models for leaves, table-shaped
   arms (116 of 151 infer arms were generated by a parser: do that again), corpus generation and ledger and
   doc refreshes. Every agent in the journals ran as `claude-sonnet-5-5`, including the hardest integration
   tasks (`infer-closure-loops` 588 min, `desugar-state` 410 min).

## 5. Decisions for the owner (the five that most change the outcome)

| # | decision | recommendation | why |
|---|---|---|---|
| 1 | Scope of the first rule-11 100%: aarch64-macos only, with wasm/js/evm/cljs/x86-64/linux-static/uefi/component/script and the test/trust/run commands deferred (refused by name in the self-built binary until ported)? | **Yes.** Rule 11 names `check`, `refactor`, `compile` on its own sources; one native target satisfies it | removes 55 modules and about 27k host lines from the path |
| 2 | Is a `.kexe` run by `tools/kexe_loader.c` (12.5k lines of C, built by cc) an acceptable "amu binary", or must amu emit a standalone Mach-O? | **Accept the loader for milestone 1** (it is not node/JVM/nbb and is already the product runtime). Standalone image as milestone 2 | a standalone image adds the object writers and runtime linkage to the critical path |
| 3 | Raise the Product Value ABI string/bytes cap (64 KiB) to at least 8 MiB (the ADR 0356 source bound) for the compiler profile, and add a capacity list builder? | **Yes, as one ADR now** (osaho, loader, verifier, limits.edn; wasm refuses by name per rule 5) | without it the self-built compiler cannot read its own larger sources; the builder decides whether self-compile fits in memory |
| 4 | What counts inside `compile` for 100%: KIR interpreter, oracle sealing, native verifier re-execution? | **Interpreter: fold subset only (freeze the rest). Oracle: unchanged semantics; it does not fire for `amu`. Verifier: in scope, but scheduled after S5** as its own track (twins of about 3.2k lines exist) | takes about 15% of effort off the path without changing any output byte of the self-build |
| 5 | Use the JVM native-image as the stage-0 compiler (BOOTSTRAP-labelled) for builds and differentials, and approve the one-day Form-polymorphic-ops test for the remaining host-map modules? | **Yes to both.** Stage-0 stops counting at stage2 == stage3. Adopt (a') only if the test meets its bar | 20-40x faster feedback; potentially 3x faster ports for the 11.4k-line code generator |

Also needed, but lower leverage: switch the progress metric to the ledger (section 4, rule 5), and move the
`:fe/env` schema into one module once C4 lands.

## Appendix: sources and commands

- Scans: `/private/tmp/wall-scan-{13..22}.tsv` (nbb), `wall-scan-native{1..4}.tsv`, `wall-scan-native-0360.tsv`.
  OK counts: 58, 59, 66, 81, 46, 85, 86, 94, 96, 96; native 92, 99, 100, 119; 0360 100. native4 swaps
  gitlibs for the `wt-F`/`wt-G` worktrees, which is why it is higher.
- Minimal closure: a script (scratch, not committed) parses each file's `ns` requires (all reader branches),
  adds the 15 split frontend modules, takes the closure from the 5 roots in section 1.4, and excludes the
  prefixes in section 1.3.
  Result: 122 modules / 122,695 lines / 7,749 `(defn` tokens (both readings); deferred 55 / 48,938.
- Frontend history: `git rev-list -1 --before=<t>` on kotoba-sema, counting `#?(:kotoba` and lines in
  `frontend*`, `validate_expr`, `value_type`: 09-30 12:00 0 / 20.6k; 09-30 24:00 225 / 23.4k;
  10-01 13:00 492 / 25.9k; 10-01 20:00 1209 / 31.0k; 10-02 00:00 2171 / 38.5k; 10-02 12:00 2727 / 43.4k.
- Journals: `~/.claude/projects/-Users-junkawasaki-github/45370866-.../subagents/workflows/*/journal.jsonl`
  plus per-agent transcripts (timestamps, usage). Status counts come from the structured results of the
  three sweep waves (`wf_ae6aa29f`, `wf_b21d989f`, `wf_354aa22d`). Conflict and stale counts come from keyword
  matches on result text (approximate).
- Oracle condition: osaho `src/kotoba/kir.cljk` `lower` (`(:entry hir)`, `#{:i64 :bool}` result, effects within
  `#{:state :abort}`). Fold: kotoba-sema `frontend/analyze.cljk:1729`. Verifier re-execution:
  `kotoba-verifier/src/kotoba/verifier.cljk:3397`.
