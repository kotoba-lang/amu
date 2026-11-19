# Agent rules

## Product introduction and performance evidence

Describe Amu as the native compiler for Kotoba's Lisp machine in development.
Lisp's programs-as-data and composable forms motivate the work; do not describe
interactive machine capabilities as shipped without their own evidence.

The 2026-10-15 M4 observation measured translated Kotoba ports at 0.80× C
execution time across 19 Embench workloads for a specific compiler snapshot,
with one sample per workload and audited algorithm substitutions. This is not
an official score, a measurement of the current released compiler or a
universal speed ranking. Keep the boundary and audit with the number:
https://kotoba-lang.org/blog/embench-c-parity-20261015/.

## Selfhost is the top priority

- Use canonical `.kotoba` source and an Amu-built native compiler for the
  compiler, CLI, build graph, packaging and operational tooling. This outranks
  features, new targets and benchmark publication. Details:
  `docs/selfhost-priority.md` (owner decision 2026-10-22).
- Remove CLJK/CLJC/CLJS, NBB, KBB, Clojure, Java/JVM, GraalVM, Node.js and
  C compiler/loader/runtime dependencies from that implementation closure.
  C-loader pinning is not acceptance.
- CLJK and EDN remain accepted as permanent INPUT reader sugar (owner
  decision 2026-10-29, JUN-579; supersedes the 2026-10-22 "CLJK is not
  retained" wording). The reader is implemented in Kotoba, and each sugar
  spelling must desugar to the same canonical Kotoba form and mint the same
  Definition CID as pure `.kotoba`
  (`kotoba-lang/lang/surface-equivalence-corpus.edn`). The compiler's own
  closure stays free of them. Native entry so far (owner decision 2026-11-06):
  a lone `check FILE.cljk` and `definition-cids FILE.cljk`, through the same
  frontend; compile, run, lock and project routes are `.kotoba` only, and
  `.edn` has no native entry yet.
- CLJC/CLJS/CLJ are refused as native input. They may remain only as a local
  reference oracle under a project-root `oracle/` holding an `ORACLE.edn`
  (owner decision 2026-11-06, JUN-579; see the local reference oracle rules).
- CLJK stays as a reference oracle source and is treated as CLJC-equivalent
  for oracle runs (owner decision 2026-11-07, JUN-579): `#?(:kotoba …)`
  selects the Kotoba branch, `#?@` is not read, and an oracle is handed the
  source as `.cljc`. The route stays `.kotoba`: the native entries above are
  unchanged and are not extended, and native acceptance of `.cljc` is not
  pursued. This replaces the earlier 2026-11-07 wording that made native
  `.cljc` acceptance the target. Where the code and this text disagree, the
  code is the state and the disagreement is reported.
- Kotoba and AIUEOS stay a Kotoba / Amu selfhost-only Lisp machine, language and
  compiler (owner decision 2026-11-07, AWAI-160). Apps and OS features are built
  first in `.cljc` as Otehon, which may use NixOS and other stacks, and are used
  later as an oracle for the selfhost implementation under the oracle rules. See
  network-awai-apex ADR 0026 D18. Otehon never enters a native route.
- Only a compiler built and rebuilt by Amu selfhost qualifies. Historical
  hosted builds and C-loader receipts remain labelled historical evidence;
  they do not qualify the replacement route.
- Do not add a legacy host, C loader or hosted packaging fallback.
  Unreachable files stay on the scoreboard as refused, with the reason.
- Compiler benchmarks (Embench etc.) are published as selfhost results only
  when taken with a selfhost-built compiler on a quiet host.

## The measured Embench compiler is the compiler core

- Extend the adopted `seed/MANIFEST` compiler lineage for Amu selfhost and
  the public `amu` / `kotoba` compiler. Preserve its frontend, lowering,
  optimization and backend behavior while growing the complete command and
  build closure. Do not replace it with an independently implemented core
  or make it an optional benchmark-only backend.
- `seed/compiler-core.json` pins the measured M104 baseline and the adopted
  M105 source lineage. ADR 0370 defines the integration and review order.
  Review and merge this lineage before unrelated feature work.
- Preserve the full 19-workload corpus, exact result/fuel/arena/refusal
  behavior and source/artifact provenance. A successor needs complete
  self-rebuild and conformance evidence before replacing the admitted core;
  a new score needs fresh measurements of that exact compiler.
- Historical C-loader results remain historical. This core decision does
  not relax the native-only build/execution contract above or qualify the
  public CLI, a new runtime, or CDCI through source inspection alone.

## Q9 compiler routes must use Kotoba / Amu selfhost only

- Owner decision 2026-10-29 (KOTOBA-171, superseding the KOTOBA-170
  public FD3 requirement): `bin/amu`, `bin/kotoba` and `bin/kotoba-compiler`
  resolve to the Amu-built native Mac ARM64 host CLI in
  `seed/bootstrap/aarch64-macos/cli.json`. Ordinary check/compile/run require
  no manual FD3, target, lock, packaging or signing. This bounded host CLI
  explicitly chooses `aarch64-macos` and retains the adopted frontend/checker
  and pinned full compiler. Generated guests never receive host filesystem
  or process grants. Full Mac runtime and independent-user release remain
  unqualified. See `docs/native-public-entry.md`.
- The low-level compiler pinned by `seed/bootstrap/aarch64-macos/root.json`
  retains its explicit directory FD3 and basename output/lock interface.
  Its engine-neutral omitted target still refuses `E2`; the Mac host default
  is not a new language default. Browser/Worker/WASI support still requires
  its own qualification. Unsupported public flags must refuse, never discard
  source paths or locks. Linux x86 callers/CDCI retain
  `bin/amu-linux-x86_64` and the two Linux aliases in `native-product.json`.
- The build and execution closure must not invoke NBB, KBB, Node, Java,
  Clojure/JVM, GraalVM, a C compiler or C loader, including through wrappers,
  `resolveWithJvm`, compatibility adapters or packaging helpers.
- Missing/stale dependency locks, unsupported commands/targets and project
  linker gaps fail closed. Do not silently remove `--source-path`, ignore a
  module lock or fall back to a legacy host to make a component compile.
- New Q9 compiler/test routes are authored in Kotoba, built by Amu selfhost,
  and executed as qualified native artifacts or selfhost-produced Wasm in
  the declared host. JavaScript/Wasm output does not authorize a Node/NBB
  compiler host. CDCI is limited to Amu selfhost and Kotoba native as
  loaderless `x86_64-linux-static` ELF artifacts.
- Preserve the positive/refusal and lock-failure corpus while migrating it
  to the native route. Record forbidden-process traces, compiler generations,
  source/lock pins, artifact hashes and actual execution results. Missing
  native functionality stays blocked; source admission alone is not a pass.

## Native CDCI and retired public entry

The integrated FULL47 source retains native CLI/CID/FS2, the native i64
receipt profile, all live/desktop modules and all18 normal adopted core
modules. Root and public images are rebuilt from this exact graph with
native ARM F1=F2, core generations, runtime cases and admission/refusal
proofs. The controller and both gate identities are preserved from the
qualified45 source. Current47 acceptance requires terminal exact-head
native ARM/x86, receipt-profile, controller/public and locked consumer CI.
Historical ARM/QEMU receipts remain bound to their own sources.
The closed v5 project reserves low20KiB for non-live context/catalog. The
v6 PCI candidate has128KiB RW storage and a64KiB private floor; its copied
BAR catalog starts at context20480. The v2 live ABI and v3 private user/desktop context provide separately
versioned queue/arena/capability/domain regions, with native admission and
actual guest receipts; full scheduling and shared Browser remain separate.

- The complete candidate uses `seed/FULL-MANIFEST` (48 modules), retaining
  every adopted core module. Static OUT is 12MiB because the complete
  TCP/spawn image exceeded the old 8MiB bound. The complete static profile
  also uses LitB1MiB, TOK1048576, NODE786432, SIR589824 and MM-WORDS32,505,856 (<2^25).
  TOK is not fixed: it was raised from 786432 by owner decision (2026-11-01, JUN-737), and
  `scripts/seed/check-token-headroom-native.py` (native-definition-graph `headroom` job) reports
  the TOK/NODE/FN table headroom of the largest static builds and fails below its floors. Change any capacity through the `seed/MEMORY-MAP` static
  overrides and `seed/gen-static-ns.kotoba`, never by hand. Heap size, expected results,
  all19 workloads and all24 runtime fixtures remain unchanged.
- `seed/cdci` owns the Kotoba-native controller and gate. Its two mandatory
  roles are Amu selfhost and Kotoba native; legacy fleet/authoring labels
  are not extra gates. Privileged role sources, images and inputs are
  pinned; changed source needs matching newly built artifacts and proof.
- GitHub Actions/Python can stage bytes, launch test processes and transport
  artifacts. They do not replace the native controller's ordered verdict
  or turn source admission, cached historical receipts or pending execution
  into a successful native gate. Keep artifact qualification, terminal CI
  status and live service deployment distinct.
- Old Node/NBB/KBB launchers, package manifests, JVM deps and former README
  are complete non-executable historical text under
  `docs/retired/legacy-public-entry-20261023`. They are not fallback tools,
  installation inputs, current Q9 instructions or acceptance blockers.
  Preserve their corpus while porting genuinely missing public behavior.


## Local reference oracle (owner decision 2026-10-29, JUN-579 / JUN-588; C and Python added 2026-11-06)

The legacy cljk / JVM / nbb reference route (kotoba-sema, osaho, the nbb
`definition-cids`, `.cljk` test suites) may be run on a developer machine as a
one-off **measurement oracle**, to obtain reference values (KIR, Definition
CIDs, outputs) when porting a construct or checking cljk/edn-sugar vs pure
`.kotoba` equivalence.

- Record the exact command, tool versions, inputs and outputs as data
  (evidence, with the date); keep downloads minimal and say what was fetched.
- It never appears in CI, a gate script, a workflow, a build, packaging or a
  runtime path, and is never a fallback or a required comparison route. The
  CDCI ban on JVM/nbb is unchanged; a native result must not silently fall
  back to it.
- A reference value is evidence of the reference's behavior. It is not proof
  that a native implementation is correct, and a mismatch is reported, not
  forced to agree.
- The oracle languages are nbb, JVM, C, Python, Basilisp, jank and Fennel (owner decision
  2026-11-06; Hy replaced by Basilisp 2026-11-07): reference implementations and prototypes in those
  languages. The same rules apply
  to every use, including a Workflow subagent running one on a developer machine: one-off,
  dated evidence, never in CI, gates, builds or runtime paths.
- Every language that supports `.cljc` is also an oracle language (owner decision 2026-11-07), for
  example Clojure, ClojureScript, ClojureCLR, Babashka, Squint, Cherry, ClojureDart, jank, Clojerl, Lokke
  and Phel. The unverified candidate table is `docs/oracle-cljc-dialects-20261107.md` in
  kotoba-lang/kotoba-lang; confirm the tool version, feature key and `.cljc` handling at first use and
  record it.
- CI exception (owner decision 2026-11-07; relaxes the "never in CI" and CDCI JVM/nbb wording above for
  oracle use only): JVM, nbb, Babashka and every other `.cljc` language above may run in CI as oracle jobs. Keep each in its own job, named
  and reported as an oracle. Native build, gates, packaging and runtime must not depend on it, and a
  native result must not silently fall back to it. Making an oracle job a required check is a separate
  owner decision; until then it is not required. The ban on JVM, nbb, Babashka and GraalVM in CI for any
  other purpose (JUN-290) was withdrawn by owner decision 2026-11-17 (see
  `com-junkawasaki/root/AGENTS.md`, CDCI section); the native-closure and no-silent-fallback conditions
  above still apply to those tools.
- Hosted CI tooling (owner decision 2026-11-19, JUN-974; canonical text: the language-by-context table in
  `com-junkawasaki/root/AGENTS.md`): Basilisp, the JVM family and every other `.cljc`-capable tool (nbb, JVM,
  Babashka, Clojure, GraalVM, jank and others), C, Python and Fennel may run as hosted CI tooling in any job,
  including the check, gate-support and diagnostic scripts of the native workflows. Such a script may orchestrate
  or inspect but must not replace a native check: artifacts and gate verdicts are still produced and verified by
  Kotoba / Amu native tools. These tools are not part of the native compile, build, packaging or runtime closure,
  and a native result must not silently fall back to them. Hosted-tooling jobs are not required checks; making one
  required is a separate owner decision. New Rust, shell or raw JS tooling in the selfhost scope is still not added.
- Policy and plan: ADR `adr-2611071200-cljk-oracle-cljc-standard` (com-junkawasaki/root `90-docs/adr/`), tracked in
  Linear JUN-579 and JUN-967 to JUN-973. cljk sources follow standard cljc; cljc itself is not customised. Moving
  the `:kotoba/*` namespace attribute-map keys to a quoted spelling (JUN-967 to JUN-969) is a plan, not yet
  implemented; until then a JVM run stops on `{:kotoba/export [...]}`.
- Before a selfhost refactor of a cljk component, take its reference values first from the JVM and
  node (nbb) oracles (owner decision 2026-11-07). Hand an oracle the source as `.cljc`; Basilisp reads
  `.cljc` with the `:lpy` feature key and does not read the `.cljk` extension. Record versions,
  inputs and outputs with the date.

## S5 Rust target-qualification tier (non-required, local-only, KOTOBA-365)

SIR-to-Rust emission (`src/kotoba/compiler/backend/rust.cljk`, pure-i64 then
pure-f64 slices, checked KIR only, fail-closed) is a separate
target-qualification tier, not a compiler target: it adds no `--target`, is
not registered in `target-names` or `backend-qualification`, and NEVER enters
the compiler, build, mandatory gates, CI, workflows, packaging, or any
fallback or required route. It does not relax the JVM/nbb CI ban or the
native-only build closure above. Verification runs on a developer machine
only, gated on a locally installed rustc; measured 2026-11-12 (rustc 1.99.1,
kbb suite green, pilot corpus funnel match 3 / emit-refused 58 /
analyze-refused 2, rustc execution 7/7 warning-clean). Keep evidence,
coverage and blockers in Linear KOTOBA-365, never in CI. Creating a required
tier out of this slice is a separate owner decision; updating
`com-junkawasaki/root/AGENTS.md` for it is proposed in KOTOBA-365, not done here.

## Shared agent rule

These rules apply to every agent. Migrate and qualify whole components,
including their launch/build/packaging dependencies. Keep historical
measurements distinct from current qualification and preserve unrelated WIP.

The native-only entry refuses `--format platform-linked` with E2. The
optional provider backend source and corpus are retained, but libc/dynamic-
loader execution is excluded from mandatory native CDCI. The static
launcher, complete core, all24 native cases and hardening remain required.

The linked GPU-provider fake-device/Vulkan/libc qualifications are also
excluded from mandatory native CDCI: they require the refused C-linked
format. Their source and corpus remain preserved, and provider qualification
is blocked until an Amu/Kotoba-native route exists. Do not mark those
excluded checks passed through the two bounded native compiler roles.

The public-product native check must receive the current complete compiler
receipt (`--complete`) and match the actual entry to all3 current native F
images/current FULL-MANIFEST bytes. An older self-consistent descriptor is
insufficient. Runtime/target changes must regenerate affected role/source,
root and product pins and re-run native positive/refusal/resource checks.

## Derived seed pins are regenerated, never merged (JUN-631, ADR 0388)

Compiler images, `native-product.json`, `seed/bootstrap/*`, `bin/amu-linux-x86_64`,
the public Mac CLI and foundation-starter descriptors are build outputs of the
whole seed tree. When a seed PR conflicts with main in them:

- merge main (never rebase or force-push), then run
  `python3 scripts/seed/repin-derived-pins.py --take-pins-from FETCH_HEAD` on Mac
  arm64. It restores main's pin files and rebuilds every pin on the merged
  source with the two-phase writer and the public CLI repin. Do not pick
  either side of a pin conflict by hand.
- leave `sourceRevision` `null` after regeneration: it means the descriptor's
  own commit and the source-revision audit checks that commit. Do not open a
  follow-up PR to name a squash commit.
- The post-merge bot repin (ADR 0406) was withdrawn by the owner (2026-11-06): no bot token/App. Pins stay in the PR.
  Do not add a bot or relax PR pin checks; latency work is bot-free (see ADR 0406 "Withdrawn").

## Component contracts (moved to `docs/agents/component-contracts.md`)

These per-ticket contracts moved verbatim to [`docs/agents/component-contracts.md`](docs/agents/component-contracts.md) (JUN-974). **Before you change one of these components, read its section there; the rules still apply.**

- Bounded canonical Kototama native frontend (JUN-369)
- Scoped flock candidate (AWAI-81)
- Bounded native receipt profile (JUN-370)
- Budget-independent local cache (JUN-371)
- Locked shared components (JUN-93)
- Native iteration scheduling and observations (JUN-332)
- Immutable SIR label proofs (JUN-332)
- Explicit selfhost parameter types (JUN-27 / JUN-332)
- Native incremental identity foundation (JUN-332 / JUN-358)
- Native vector zero highwater contract (JUN-27 / JUN-332)
- Closed native benchmark measurement host candidate (KOTOBA-145)
- Native instruction-class filter qualification
- Native checked identity / SCC prototype
- Native definition-object build prototype

## Native CI derivation and independent ISA qualification

Fresh ARM bootstrap/one-compiler transport precedes separate ARM and x86
qualification jobs. Transport alone is never qualification: all six native
job executions (including both shared-module matrix entries) must succeed.
Every previous ARM/x86 gate, uncached main/full tier and fresh controller
verdict remains required. The ARM artifact includes root and final generations
for unchanged native producer pin checks after transport. No compiler/image
bytes, limits, case expectations or native gate commands change in this split.

## CI input-hash gate (JUN-759)

Every job of `selfhost-native` and of the other native workflows starts with `./.github/actions/ci-gate`
(`scripts/ci/ci_gate.cljc`) and guards its later steps; required check names are never changed or made conditional.
- A step added after the gate needs `if: steps.gate.outputs.skip != 'true'`, or it runs without the job's earlier
  steps when the gate skips. `scripts/ci/test_ci_gate.cljc` fails on a missing guard; the one step meant to run on a skip
  is named in its `MAY_RUN_WHEN_SKIPPED`.
- Docs-only (pull_request / merge_group whose changed files are only inert) skips the heavy steps. Inert, per `INERT` in
  `scripts/ci/ci_gate.cljc`: top-level `*.md`, `docs/**/*.md` outside `docs/evidence/`, `LICENSE`, `.DS_Store`,
  `.github/dependabot.yml`, and the tooling no native job reads (JUN-818), named one by one:
  `scripts/ci/{pr_batch,test_pr_batch}.py`. Everything else runs, including every other workflow, action and script,
  all of `seed/**` and `examples/**` (their `*.md` too) and `docs/evidence/**`.
- Marker jobs skip when the same tree already passed that job (cache key = tree hash + runner arch + tier). Derivation
  jobs (`bootstrap-arm64-root`, `one-compiler-arm64`, `x86-native-qualification`, `x86-complete`) restore the exact
  derived compiler files when their inputs (tree minus gate-only `check-*`/`test_*` scripts they do not reference)
  are unchanged. Markers/caches are saved only after a job passed.
- push to main, the schedule and workflow_dispatch never skip and never restore: they run the full suite and only save.
- A new gate-only script that a derivation starts to call must be reachable by name from the derivation's roots in
  the workflow (`roots:`), or its edits will not bust that derivation's key.

## All derived pins in one command (JUN-759)

`scripts/seed/repin-derived-pins.py` covers the bootstrap roots, Linux images, product descriptors and Mac CLI.
`scripts/seed/repin-all-pins.py` (Mac arm64, native only) adds the two pin kinds that PRs used to hand-edit:

- **Core adoption**: when the `seed/MANIFEST` modules change, it rebuilds the Mac G1/G2/G3 core generations with the
  Mac fixed point (the same procedure as `check-macos-core-adoption.py`) and rewrites the sources, source unity,
  native image, container and generations of the receipt named by `seed/compiler-core.json` `adoptionReceipt`,
  plus the sources and unity of `seed/compiler-core.json`.
- **Native CDCI**: `seed/cdci/policy.json` (core source/container, amu-selfhost gate, kotoba-native gate, gate source),
  the five pin rows of `seed/cdci/controller.kotoba`, the 24 case image rows of `seed/cdci/kotoba-gate.kotoba` and the
  two role source hashes in `seed/79-native-cdci.kotoba`, all from the Mac fixed point
  (`compile --target x86_64-linux --format static`, `cdci-build`). The compiler embeds `seed/79`, so the command
  repeats repin + sync until the pins reach a fixed point (normally 3 rounds, about 8 minutes).

```
scripts/seed/repin-all-pins.py --merge origin/main   # merge, resolve mechanically, regenerate; then review + commit
scripts/seed/repin-all-pins.py --check               # never writes; exit 10 CDCI stale, 11 core adoption stale
scripts/seed/test-repin-all-pins.py                  # negative controls: each stale pin must fail --check
```

`--merge` resolves conflicts only in pin files, `seed/cdci/{policy.json,controller.kotoba,kotoba-gate.kotoba}`,
`seed/compiler-core.json`, `seed/adoption-*.json` (main's side, then regenerated) and the role-hash lines of
`seed/79-native-cdci.kotoba` (three-way merge ignoring them). Anything else exits 12 with the file list.

What it does not cover (exit 12 `OWNER_AUTHORED_CONTENT_NEEDED`, or documented here):
- semantic edits to `seed/79`, `seed/cdci/{entry,runtime}.kotoba`, new `static-cases.json` cases (new gate vectors) or
  a changed case count; the entry/runtime hashes embedded in `seed/79` are not recomputed;
- a core change whose G1/G2/G3 do not self-reproduce (fix the source);
- a PR that creates a new `seed/adoption-*.json` and repoints `compiler-core.json`: main's pointer wins and the
  PR's new file stays as a record; repointing is an owner decision;
- `docs/evidence` and `docs/*.json` receipts are historical records bound to their own sources, are not read by any
  CI check against current sources, and are not regenerated (`--report-receipts` lists drifted pins, informational);
- native Linux execution of the controller/gate: CI remains the verdict; this command only reproduces the pinned bytes.
