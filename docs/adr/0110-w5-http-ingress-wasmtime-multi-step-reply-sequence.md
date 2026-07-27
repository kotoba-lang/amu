# ADR 0110: W5 deepen — http-ingress multi-step Wasmtime reply true-sum

Status: accepted; intermediate multi-step execution evidence for
http-ingress-v1 **reply** path; not host inject and not `:wasm-aot`

## Decision

Deepen family-3 http-ingress wasm packaging with a **reply multi-step
Wasmtime driver** (counterpart to ADR 0109 accept):

1. Hand-authored application component imports `http-ingress.reply` only
2. Performs two replies with `status = 200`, empty headers/body
3. Synthetic dual-export provider always returns `true`
4. Returns `(ok1 + ok2)` as `s64`
5. Dual-export provider's primary `:capability` is remapped to
   `:http/reply` for `compose-closed` frequency matching (bytes still
   package both accept and reply)
6. Wasmtime execution yields **2**

Together with ADR 0109, both dual-export paths of http-ingress have
multi-step execution evidence. Bool results flatten to i32 (no retptr).

## Evidence

- kotoba-component#64 — driver in `http_ingress_provider_component_test`
- 5 tests / 21 assertions green (includes Wasmtime run)
- Pin advanced to `883503a5cb06a6768aecee20fb3f9fcc25a89acc`

## What this does NOT claim

- Host inject / multi-inflight real replies
- Lifecycle accept→reply coupling in one Wasmtime invoke
- `:wasm-aot :implemented`

## Related

- ADR 0098 — http-ingress wasm packaging
- ADR 0109 — accept multi-step
- ADR 0101–0108 — multi-step Wasmtime pattern
- Migration plan: Wasmtime multi-step drivers
