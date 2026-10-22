# Agent rules

## Hosted compiler removal status

- The C/JVM/Node compiler implementations and build/launch routes are removed
  in this candidate. Public entrypoints currently refuse with exit 69; no
  independent native compiler is qualified yet. Do not reinstall NBB/KBB,
  restore a C loader, or infer success from the refusal wrappers.
- See `docs/native-compiler-retirement.md` and the hash/blob inventory under
  `docs/retirement/` for source recovery and pending native execution gates.

## Selfhost is the top priority

- Use canonical `.kotoba` source and an Amu-built native compiler for the
  compiler, CLI, build graph, packaging and operational tooling. This outranks
  features, new targets and benchmark publication. Details:
  `docs/selfhost-priority.md` (owner decision 2026-10-22).
- Remove CLJK/CLJC/CLJS, NBB, KBB, Clojure, Java/JVM, GraalVM, Node.js and
  C compiler/loader/runtime dependencies from that closure. CLJK is not a
  retained final syntax-sugar surface. C-loader pinning is not acceptance.
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

- Q9 callers use the qualified Amu selfhost-built entrypoint for `check`
  and `compile`. A Node/nbb `bin/amu` is not that entrypoint, and
  `--jvm-free` alone does not establish selfhost or exclude Node/NBB/C.
  An omitted `--target` selects the
  engine-neutral Kototama program target; `AMU_TARGET` or an explicit
  `--target` selects another backend. Browser / Worker / WASI builds name
  `wasm32-browser` / `wasm32-wasi` explicitly.
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


## Shared agent rule

These rules apply to every agent. Migrate and qualify whole components,
including their launch/build/packaging dependencies. Keep historical
measurements distinct from current qualification and preserve unrelated WIP.
