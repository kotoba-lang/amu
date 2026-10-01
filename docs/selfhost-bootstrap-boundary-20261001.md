# Selfhost bootstrap boundary: what still needs nbb, Node or the JVM (2026-10-01)

Decision (owner, 2026-10-01): the product must not depend on nbb either. The product is
self-hosted: a native compiler built by Amu itself that runs `amu check`, `amu refactor` and
`kotoba ...` with no nbb, Node or JVM process at runtime. nbb, Node, the JVM and GraalVM are
**bootstrap references** only, usable to build and measure until the self-built compiler exists.
This report is the inventory of what is still on the wrong side of that line. Rules:
`AGENTS.md` and `docs/selfhost-priority.md` (rules 8-11). Removal plan: stage S6 of
`docs/selfhost-core-rewrite-plan-20260930.md`.

Produced by `scripts/selfhost-wall/bootstrap-boundary.sh --markdown` (bash, grep and awk only; it
needs no nbb and no Python). Re-run it; this file is a snapshot at the commit that added it.
The scan is static: it reads reader-conditionals with a small S-expression scanner, so a file
counted here is a lead to verify with `amu check`, not a proof. The hollow/partial classification of
the 94 files that print OK comes from `docs/selfhost-real-vs-hollow-20261001.md`.

## Classes

- **PRODUCT**: reachable when a user runs `amu` or `kotoba`. Every PRODUCT entry below must be
  replaced by Kotoba (`.cljk`/`.kotoba` with a `:kotoba` reading that passes `amu check`) and
  compiled by Amu for the project to count as 100% selfhost.
- **BOOTSTRAP-TOOL**: scaffolding that builds, measures or tests the product (wall harness,
  differential scripts, tests, benchmarks, native-image build). It may stay nbb/Node/Python until the
  self-built compiler exists; afterwards each piece is ported or retired by choice, not by rule. A
  source file opts in with `;; bootstrap-tooling` in its first five lines.

The two lists are not symmetric: PRODUCT counts files that must change; BOOTSTRAP-TOOL counts files
that merely exist.

## Reading the numbers

- The 54 of 105 `src` files that carry a `:kotoba` arm is not "54 done". Within them 132
  `#?(:kotoba nil ...)` forms drop host behaviour from the Kotoba reading (section 3b), and the
  audit calls 16 files in this repo HOLLOW or PARTIAL (section 3a).
- A file in section 3b with `no-:kotoba-arm-with-host-refs` has no Kotoba reading at all: the
  Kotoba route reads its host code or its guarded `:cljs` arm as absent.
- The launchers are the largest single item: `bin/amu` (631 lines) is a Node script that spawns
  nbb with a computed classpath, and `bin/kotoba` (310 lines) is an nbb script. Neither can exist
  in the end state; both are replaced by the native launcher (S6).
- The seven nbb entry points with no `:kotoba` arm (`aarch64_cli`, `cli`, `js_cli`,
  `output_set_cli`, `run_cli`, `wasm_cli`, `x86_64_cli`) are the commands that cannot run from a
  self-built binary today. `refactor_cli`, `evm_cli`, `test_cli` and `trust_cli` have an arm that is
  nil or a named refusal (exit 64).

## Counts

scanned root: /private/tmp/wt-A-amu-measure
src files scanned (.cljk/.kotoba/.cljc/.cljs): 105

| area | PRODUCT | BOOTSTRAP-TOOL |
|---|---|---|
| launchers (bin/*) | 4 | 2 |
| nbb-only entry points (*_cli.cljk) | 15 (7 with no :kotoba arm) | 0 |
| modules with a nil/refusal Kotoba reading, from the audit doc (docs/selfhost-real-vs-hollow-20261001.md, HOLLOW+PARTIAL rows of this repo) | 16 | 0 |
| modules with `#?(:kotoba nil ...)` forms or no :kotoba arm, computed from source | 48 | 0 |
| src files with unguarded host tokens (node:*, js/*, java.*, :import, host requires) | 13 (36 tokens; 185 more are guarded) | 0 |
| src files with at least one :kotoba arm | 54 of 105 | |
| `#?(:kotoba nil ...)` forms in src | 132 | |
| distinct PRODUCT src files in any list above (the union) | 56 | |
| scripts/test/bench/tools files (bootstrap scaffolding) | | 730 |
| of which scripts/selfhost-wall (wall harness; 12 .cljs, 3 .py, 9 .sh) | | 33 |

## 1. Launchers (bin/*)

- `bin/amu` | PRODUCT | node(shebang)+host-calls | 631 lines
- `bin/amu.cmd` | PRODUCT | (delegates) | 2 lines
- `bin/build-native-image` | BOOTSTRAP-TOOL | python/graal | 14 lines
- `bin/kbb` | BOOTSTRAP-TOOL | node(shebang)+host-calls | 51 lines
- `bin/kotoba` | PRODUCT | nbb(shebang)+host-calls | 310 lines
- `bin/kotoba-compiler` | PRODUCT | (delegates) | 4 lines

## 2. nbb-only entry points

- `src/kotoba/compiler/nbb/aarch64_cli.cljk` | PRODUCT | nbb entry (nbb/*_cli) | NO-:kotoba-arm
- `src/kotoba/compiler/nbb/cli.cljk` | PRODUCT | nbb entry (nbb/*_cli) | NO-:kotoba-arm
- `src/kotoba/compiler/nbb/evm_cli.cljk` | PRODUCT | nbb entry (nbb/*_cli) | has-:kotoba-arm
- `src/kotoba/compiler/nbb/js_cli.cljk` | PRODUCT | nbb entry (nbb/*_cli) | NO-:kotoba-arm
- `src/kotoba/compiler/nbb/output_set_cli.cljk` | PRODUCT | nbb entry (nbb/*_cli) | NO-:kotoba-arm
- `src/kotoba/compiler/nbb/refactor_cli.cljk` | PRODUCT | nbb entry (nbb/*_cli) | has-:kotoba-arm
- `src/kotoba/compiler/nbb/run_cli.cljk` | PRODUCT | nbb entry (nbb/*_cli) | NO-:kotoba-arm
- `src/kotoba/compiler/nbb/test_cli.cljk` | PRODUCT | nbb entry (nbb/*_cli) | has-:kotoba-arm
- `src/kotoba/compiler/nbb/trust_cli.cljk` | PRODUCT | nbb entry (nbb/*_cli) | has-:kotoba-arm
- `src/kotoba/compiler/nbb/wasm_cli.cljk` | PRODUCT | nbb entry (nbb/*_cli) | NO-:kotoba-arm
- `src/kotoba/compiler/nbb/x86_64_cli.cljk` | PRODUCT | nbb entry (nbb/*_cli) | NO-:kotoba-arm
- `src/kotoba/compiler/refactor_cli.cljk` | PRODUCT | cli entry (non-nbb twin or shared) | has-:kotoba-arm
- `src/kotoba/compiler/run_cli.cljk` | PRODUCT | cli entry (non-nbb twin or shared) | has-:kotoba-arm
- `src/kotoba/compiler/test_cli.cljk` | PRODUCT | cli entry (non-nbb twin or shared) | has-:kotoba-arm
- `src/kotoba/compiler/trust_cli.cljk` | PRODUCT | cli entry (non-nbb twin or shared) | has-:kotoba-arm

## 3. Modules whose Kotoba reading is nil or refusal

### 3a. From docs/selfhost-real-vs-hollow-20261001.md (HOLLOW / PARTIAL, this repo)

- `src/kotoba/compiler/backend/cljs.cljk` | PRODUCT | audit:HOLLOW | 
- `src/kotoba/compiler/module_lock.cljk` | PRODUCT | audit:HOLLOW | 
- `src/kotoba/compiler/nbb/compile_cache.cljk` | PRODUCT | audit:PARTIAL | 
- `src/kotoba/compiler/nbb/evm_cli.cljk` | PRODUCT | audit:HOLLOW | 
- `src/kotoba/compiler/nbb/test_cli.cljk` | PRODUCT | audit:HOLLOW | 
- `src/kotoba/compiler/nbb/trust_cli.cljk` | PRODUCT | audit:HOLLOW | 
- `src/kotoba/compiler/reference_runtime.cljk` | PRODUCT | audit:HOLLOW | 
- `src/kotoba/compiler/run_cli.cljk` | PRODUCT | audit:HOLLOW | 
- `src/kotoba/compiler/test_cli.cljk` | PRODUCT | audit:HOLLOW | 
- `src/kotoba/compiler/trust_cli.cljk` | PRODUCT | audit:HOLLOW | 
- `src/kotoba/compiler/atomic_output.cljk` | PRODUCT | audit:PARTIAL | 
- `src/kotoba/compiler/nbb/cli_support.cljk` | PRODUCT | audit:PARTIAL | 
- `src/kotoba/compiler/nbb/host/sys.cljk` | PRODUCT | audit:PARTIAL | 
- `src/kotoba/compiler/nbb/output_admission.cljk` | PRODUCT | audit:PARTIAL | 
- `src/kotoba/compiler/nbb/project_source.cljk` | PRODUCT | audit:PARTIAL | 
- `src/kotoba/compiler/nbb/verdict_cache.cljk` | PRODUCT | audit:PARTIAL | 

### 3b. Computed from source (#?(:kotoba nil ...) or no :kotoba arm with host tokens)

- `src/kotoba/compiler/atomic_output.cljk` | PRODUCT | kotoba-nil-forms=2 | 
- `src/kotoba/compiler/backend/cljs.cljk` | PRODUCT | kotoba-nil-forms=1 | 
- `src/kotoba/compiler/backend/evm.cljk` | PRODUCT | kotoba-nil-forms=16 | 
- `src/kotoba/compiler/bounded_edn.cljk` | PRODUCT | kotoba-nil-forms=2 | 
- `src/kotoba/compiler/cache.cljk` | PRODUCT | kotoba-nil-forms=10 | 
- `src/kotoba/compiler/capability_names.cljk` | PRODUCT | no-:kotoba-arm-with-host-refs | 
- `src/kotoba/compiler/cli.cljk` | PRODUCT | no-:kotoba-arm-with-host-refs | 
- `src/kotoba/compiler/core.cljk` | PRODUCT | no-:kotoba-arm-with-host-refs | 
- `src/kotoba/compiler/coverage_evidence.cljk` | PRODUCT | kotoba-nil-forms=10 | 
- `src/kotoba/compiler/definition_identity.cljk` | PRODUCT | kotoba-nil-forms=37 | 
- `src/kotoba/compiler/fuel_estimate.cljk` | PRODUCT | no-:kotoba-arm-with-host-refs | 
- `src/kotoba/compiler/host_integer.cljk` | PRODUCT | no-:kotoba-arm-with-host-refs | 
- `src/kotoba/compiler/host_profile.cljk` | PRODUCT | no-:kotoba-arm-with-host-refs | 
- `src/kotoba/compiler/ios_aot.cljk` | PRODUCT | kotoba-nil-forms=6 | 
- `src/kotoba/compiler/ipld_adl.cljk` | PRODUCT | no-:kotoba-arm-with-host-refs | 
- `src/kotoba/compiler/ipld_adl_source.cljk` | PRODUCT | no-:kotoba-arm-with-host-refs | 
- `src/kotoba/compiler/lang_conformance.cljk` | PRODUCT | no-:kotoba-arm-with-host-refs | 
- `src/kotoba/compiler/lang_native_conformance.cljk` | PRODUCT | no-:kotoba-arm-with-host-refs | 
- `src/kotoba/compiler/module_lock.cljk` | PRODUCT | kotoba-nil-forms=1 | 
- `src/kotoba/compiler/nbb/cli_support.cljk` | PRODUCT | kotoba-nil-forms=2 | 
- `src/kotoba/compiler/nbb/compile_cache.cljk` | PRODUCT | kotoba-nil-forms=2 | 
- `src/kotoba/compiler/nbb/evm_cli.cljk` | PRODUCT | kotoba-nil-forms=1 | 
- `src/kotoba/compiler/nbb/host/clock.cljk` | PRODUCT | no-:kotoba-arm-with-host-refs | 
- `src/kotoba/compiler/nbb/host/entry.cljk` | PRODUCT | no-:kotoba-arm-with-host-refs | 
- `src/kotoba/compiler/nbb/host/env.cljk` | PRODUCT | no-:kotoba-arm-with-host-refs | 
- `src/kotoba/compiler/nbb/js_cli.cljk` | PRODUCT | no-:kotoba-arm-with-host-refs | 
- `src/kotoba/compiler/nbb/native_package.cljk` | PRODUCT | no-:kotoba-arm-with-host-refs | 
- `src/kotoba/compiler/nbb/output_admission.cljk` | PRODUCT | kotoba-nil-forms=1 | 
- `src/kotoba/compiler/nbb/output_attestation.cljk` | PRODUCT | kotoba-nil-forms=1 | 
- `src/kotoba/compiler/nbb/output_set.cljk` | PRODUCT | kotoba-nil-forms=8 | 
- `src/kotoba/compiler/nbb/package_authoring.cljk` | PRODUCT | kotoba-nil-forms=1 | 
- `src/kotoba/compiler/nbb/package_lock.cljk` | PRODUCT | kotoba-nil-forms=1 | 
- `src/kotoba/compiler/nbb/project_source.cljk` | PRODUCT | kotoba-nil-forms=1 | 
- `src/kotoba/compiler/nbb/refactor_cli.cljk` | PRODUCT | kotoba-nil-forms=1 | 
- `src/kotoba/compiler/nbb/test_cli.cljk` | PRODUCT | kotoba-nil-forms=1 | 
- `src/kotoba/compiler/nbb/verdict_cache.cljk` | PRODUCT | kotoba-nil-forms=1 | 
- `src/kotoba/compiler/nbb/wasm_cli.cljk` | PRODUCT | no-:kotoba-arm-with-host-refs | 
- `src/kotoba/compiler/project.cljk` | PRODUCT | no-:kotoba-arm-with-host-refs | 
- `src/kotoba/compiler/project_files.cljk` | PRODUCT | no-:kotoba-arm-with-host-refs | 
- `src/kotoba/compiler/provenance.cljk` | PRODUCT | kotoba-nil-forms=6 | 
- `src/kotoba/compiler/refactor_cli.cljk` | PRODUCT | kotoba-nil-forms=1 | 
- `src/kotoba/compiler/reference_runtime.cljk` | PRODUCT | kotoba-nil-forms=1 | 
- `src/kotoba/compiler/release.cljk` | PRODUCT | kotoba-nil-forms=14 | 
- `src/kotoba/compiler/run_cli.cljk` | PRODUCT | kotoba-nil-forms=1 | 
- `src/kotoba/compiler/test_cli.cljk` | PRODUCT | kotoba-nil-forms=1 | 
- `src/kotoba/compiler/test_profile.cljk` | PRODUCT | no-:kotoba-arm-with-host-refs | 
- `src/kotoba/compiler/trust_cli.cljk` | PRODUCT | kotoba-nil-forms=1 | 
- `src/kotoba/compiler/value_codec.cljk` | PRODUCT | kotoba-nil-forms=1 | 

## 4. Host-only tokens not guarded by #?(:cljs / :clj / :default)

- `src/kotoba/compiler/cli.cljk` | PRODUCT | unguarded-host-tokens=1 guarded=0 | 
- `src/kotoba/compiler/host_profile.cljk` | PRODUCT | unguarded-host-tokens=1 guarded=0 | 
- `src/kotoba/compiler/ipld_adl.cljk` | PRODUCT | unguarded-host-tokens=10 guarded=0 | 
- `src/kotoba/compiler/lang_conformance.cljk` | PRODUCT | unguarded-host-tokens=4 guarded=0 | 
- `src/kotoba/compiler/lang_native_conformance.cljk` | PRODUCT | unguarded-host-tokens=1 guarded=0 | 
- `src/kotoba/compiler/nbb/host/clock.cljk` | PRODUCT | unguarded-host-tokens=2 guarded=0 | 
- `src/kotoba/compiler/nbb/host/entry.cljk` | PRODUCT | unguarded-host-tokens=6 guarded=0 | 
- `src/kotoba/compiler/nbb/host/env.cljk` | PRODUCT | unguarded-host-tokens=1 guarded=0 | 
- `src/kotoba/compiler/nbb/js_cli.cljk` | PRODUCT | unguarded-host-tokens=3 guarded=0 | 
- `src/kotoba/compiler/nbb/native_package.cljk` | PRODUCT | unguarded-host-tokens=2 guarded=0 | 
- `src/kotoba/compiler/nbb/wasm_cli.cljk` | PRODUCT | unguarded-host-tokens=1 guarded=0 | 
- `src/kotoba/compiler/posix_path.cljk` | PRODUCT | unguarded-host-tokens=3 guarded=0 | 
- `src/kotoba/compiler/project.cljk` | PRODUCT | unguarded-host-tokens=1 guarded=0 | 

## 5. Packaging and dependency manifests

- `package.json` | BOOTSTRAP-TOOL | node package manifest (nbb pin, playwright; npm scripts run node/nbb) | 
- `nbb.edn` | BOOTSTRAP-TOOL | nbb classpath config (read only by nbb) | 
- `deps.edn` | BOOTSTRAP-TOOL | Clojure CLI (JVM) deps; JVM compatibility route only | 
- `node_modules/` | BOOTSTRAP-TOOL | installed nbb + playwright (not shipped) | 
- `bin/amu -> node + nbb` | PRODUCT | launcher resolves classpath and spawns nbb on src/kotoba/compiler/nbb/*_cli.cljk | 

## 6. Bootstrap tooling (may stay until the self-built compiler exists)

- `scripts/` | BOOTSTRAP-TOOL | files=206 py=21 mjs/js=26 clj*=128 sh=16 | 
- `test/` | BOOTSTRAP-TOOL | files=388 py=0 mjs/js=7 clj*=244 sh=0 | 
- `tests/` | BOOTSTRAP-TOOL | files=9 py=0 mjs/js=5 clj*=0 sh=0 | 
- `bench/` | BOOTSTRAP-TOOL | files=98 py=10 mjs/js=1 clj*=8 sh=0 | 
- `tools/` | BOOTSTRAP-TOOL | files=9 py=0 mjs/js=0 clj*=0 sh=0 | 
- `fuzz/` | BOOTSTRAP-TOOL | files=20 py=0 mjs/js=0 clj*=0 sh=0 | 

## What must exist before each PRODUCT group can go

| group | needs first | stage |
|---|---|---|
| bin/amu, bin/kotoba, bin/kotoba-compiler | a native launcher produced by Amu: argv, env, `fs`, `process/spawn`, exit codes, in-process dispatch to compiled entry points | S6 |
| nbb/*_cli entry points (7 no-arm, 4 nil-arm) | each `main` reads on the Kotoba route and compiles to the native target; `cli/args`, `io`, `fs` abilities in the native runtime | S6, after S3-S5 |
| `refactor_cli` and `refactor/*` | `amu check` passes the whole refactor library on the project route; reader and printer lossless in Kotoba (`kotoba.reader`) | S6 |
| frontend/KIR/verifier core | S2-S5 of the core rewrite plan (they are the compiler) | S2-S5 |
| host-only requires in section 4 | per-module Kotoba readings or native abilities (`clock`, `env`, `entry`, `sys`) | S6 |
| `run_cli`, `test_cli`, `trust_cli`, `evm_cli` | the refusal becomes an implementation: KIR interpreter + native runtime for `run`/`test`; trust plane over the pure Ed25519 already on the route | S6 |

## Acceptance

100% is measured by process, not by file counts: the `amu` binary built by `amu`, run on its own
sources (`check`, `refactor plan/apply/verify`, `compile`), under
`scripts/selfhost-wall/no-host-processes.sh`, executes no `node`, `nbb`, `java`, `clojure` or
`python` process. Exit 0 from that script plus a clean section 1-4 of this report (PRODUCT = 0)
is the definition. Fail closed: no tracer, no pass.
