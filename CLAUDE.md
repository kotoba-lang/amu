# Claude project rules

Follow `AGENTS.md`. wasm32 is one build target, not the language: never
narrow or defer a feature for wasm32 (ADR 0354). Selfhost (an Amu-built compiler, no JVM, GraalVM or
Node.js) is the top priority; see `docs/selfhost-priority.md`. For Q9, Amu is used only with the fail-closed
`--jvm-free` path. Never invoke or add a Clojure/JVM fallback to satisfy a
whole-component build; an unsupported route remains blocked.
