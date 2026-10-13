# Agent rules

## Kototama is the default execution contract

- `amu compile` without `--target` emits the canonical Kototama VM program.
  Keep Kototama as the portable, engine-neutral program contract across OSes.
- Native and Wasm are explicit deployment backends. Do not make either the
  default artifact, the acceptance path, or a prerequisite for running a
  Kototama program. New runtime examples and integration work start from the
  Kototama artifact and host VM.
- Selfhost remains a compiler milestone, not a reason to defer the portable
  VM contract or to restore native/Wasm-first application execution. Details:
  `docs/selfhost-priority.md`.

- The Amu compiler should become a native executable produced by Amu, with no
  JVM, GraalVM or Node.js needed to build it. This compiler-build goal is
  separate from the Kototama application execution contract.
- Only a selfhost-built compiler is selfhost evidence. GraalVM Native Image,
  JVM and Node/nbb builds are bootstrap references; label their numbers so.
- Do not add a JVM, GraalVM or Node fallback to make a selfhost stage pass.
  Unreachable files stay on the scoreboard as refused, with the reason.
- Compiler benchmarks (Embench etc.) are published as selfhost results only
  when taken with a selfhost-built compiler on a quiet host.

## Q9 compiler routes must be JVM-free

- Q9 callers use `bin/amu check ... --jvm-free` and
  `bin/amu compile ... --jvm-free`. An omitted compile `--target` selects the
  Kototama VM program; direct and worker compile requests share this default.
  Choose native or Wasm explicitly for deployment. The worker process itself
  runs on its host runtime.
- `--jvm-free` must never invoke `java`, `javac`, `clojure`, `clj`,
  `resolveWithJvm`, a Clojure main namespace or another JVM launcher.
- Missing/stale dependency locks, unsupported commands/targets and project
  linker gaps fail closed. Do not silently remove `--source-path`, ignore a
  module lock or fall back to the JVM to make a component compile.
- New Q9 compiler/test routes exercise the Kototama artifact and VM first.
  Native/Wasm tests cover explicit deployment profiles. Existing JVM suites are
  compatibility diagnostics and are not Q9 acceptance evidence.
- Preserve tests that shadow forbidden JVM executables and verify that no
  marker was written on both unsupported-route and lock-failure paths.


## Claude 向け追記（旧 CLAUDE.md より統合）

Kototama is the default program and runtime contract; native and Wasm are
explicit deployment backends. Amu selfhost (an Amu-built compiler, no JVM,
GraalVM or Node.js) remains a separate compiler milestone; see
`docs/selfhost-priority.md`. For Q9, Amu is used only with the fail-closed
`--jvm-free` path. Never invoke or add a Clojure/JVM fallback to satisfy a
whole-component build; an unsupported route remains blocked.
