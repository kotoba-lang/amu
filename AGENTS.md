# Agent rules

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


## Claude 向け追記（旧 AGENTS.md より統合）

For Q9, Amu is used only with the fail-closed
`--jvm-free` path. Never invoke or add a Clojure/JVM fallback to satisfy a
whole-component build; an unsupported route remains blocked.
