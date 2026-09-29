# Agent rules

## Selfhost is the top priority

- The Amu compiler must become a native executable produced by Amu, with no
  JVM, GraalVM or Node.js needed to build it. This outranks features, new
  targets and benchmark publication. Details: `docs/selfhost-priority.md`.
- Only a selfhost-built compiler is selfhost evidence. GraalVM Native Image,
  JVM and Node/nbb builds are bootstrap references; label their numbers so.
- Do not add a JVM, GraalVM or Node fallback to make a selfhost stage pass.
  Unreachable files stay on the scoreboard as refused, with the reason.
- Compiler benchmarks (Embench etc.) are published as selfhost results only
  when taken with a selfhost-built compiler on a quiet host.

## Language semantics are target-independent

- wasm32 is one build target of the Amu native compiler, not the definition of
  the language. Do not cap, narrow or defer a language or stdlib feature
  because wasm32 cannot lower it yet. Specify the semantics, check them
  against the KIR interpreter, and let each target either lower the feature or
  refuse it by name (exit 65, recorded in `lang/surface-status.edn`).
- A limit is kept only if it bounds a resource or protects an invariant. Remove
  a limit that only records what one backend could do. Details:
  `docs/adr/0354-language-semantics-are-target-independent.md`.
- This never relaxes the shared safety pipeline, fail-closed behaviour, or the
  no-JVM/GraalVM/Node-fallback rules.

## Q9 compiler routes must be JVM-free

- Q9 callers use `bin/amu check ... --jvm-free` and
  `bin/amu compile ... --target <target> --jvm-free`. Write the target: an
  omitted `--target` means the host's native target (ADR 0351), so a
  browser / Worker / WASI build names `wasm32-browser` / `wasm32-wasi`.
- `--jvm-free` must never invoke `java`, `javac`, `clojure`, `clj`,
  `resolveWithJvm`, a Clojure main namespace or another JVM launcher.
- Missing/stale dependency locks, unsupported commands/targets and project
  linker gaps fail closed. Do not silently remove `--source-path`, ignore a
  module lock or fall back to the JVM to make a component compile.
- New Q9 compiler/test routes use nbb/CLJS, Node, native or Wasm. Existing JVM
  suites are compatibility diagnostics and are not Q9 acceptance evidence.
- Preserve tests that shadow forbidden JVM executables and verify that no
  marker was written on both unsupported-route and lock-failure paths.
