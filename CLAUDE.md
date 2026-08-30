# Claude project rules

Follow `AGENTS.md`. For Q9, Amu is used only with the fail-closed
`--jvm-free` path. Never invoke or add a Clojure/JVM fallback to satisfy a
whole-component build; an unsupported route remains blocked.
