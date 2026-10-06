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


## Claude 向け追記（旧 CLAUDE.md より統合）

Selfhost (an Amu-built compiler, no JVM, GraalVM or
Node.js) is the top priority; see `docs/selfhost-priority.md`. For Q9, Amu is used only with the fail-closed
`--jvm-free` path. Never invoke or add a Clojure/JVM fallback to satisfy a
whole-component build; an unsupported route remains blocked.
