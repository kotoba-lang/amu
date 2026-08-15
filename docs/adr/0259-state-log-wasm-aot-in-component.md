# ADR 0259: state and log :wasm-aot are the in-component store and ring

Status: accepted

## Decision

`:wasm-aot` on `state-v1.edn` and `log-v1.edn` is `:implemented`.

Unlike clock (ADR 0258), these kits have no host clock/network to import.
The production source of truth is the provider instance itself — the same
reason the CLJ reference was never a transport fixture (ADR 0067 / 0072).
The wasm component store/ring is that instance.

Clock needed WASI because a synthetic epoch is not a clock. A synthetic
HTTP 200 is not HTTP. An in-component key/value table **is** `state`; an
in-component ring **is** `log`.

## Evidence that is allowed to flip the flags

### state

`state-wasm-aot-qualification-test` must:

1. Compose the ADR 0060 14-step driver with `package-state-provider`
   (capacity 4, matching that vector)
2. wasmtime `run --invoke run()` returns bitmask `16383` (every step)
3. The same harness with step 2's expected version corrupted to `999`
   returns `16379` (bit 2 cleared). A vacuously-all-ones driver cannot
   pass this.

### log

`log-wasm-aot-qualification-test` must:

1. Two appends → `(seq2 - seq1) = 1`
2. Capacity-2 ring, three appends, read oldest-sequence → `2` (seq 1
   dropped). A canned append result cannot drop the oldest entry.

## What this does NOT claim

- `:wasm-aot` on http / http-ingress / storage / llm / ui
  - http / llm: synthetic ok body, no network/model
  - storage: always `:missing`, no durable backend
  - ui: `next-event` is always none (no host event queue)
  - http-ingress: `accept` is always none (no incoming queue)
- `:wasm32-kotoba-v1` on state or log (still i64-only on clock)
- backend-wide wasmtime `:qualified`
- `:native-aot` / `:jit`
- compiled `.kotoba` guests as the driver (WAT drivers, same honesty as
  clock ADR 0258)

HTTP remains blocked on WASI 0.3 `async func` (`:bounded-wasi-0.3-async`
and `wasi:http/client@0.3.0`). Do not spell 0.2 `outgoing-handler` as 0.3.

## Related

- ADR 0258 — clock WASI kit schema
- ADR 0060 / 0061 — state real provider + 256 capacity
- ADR 0085 / 0102 / 0115 — log provider + wasmtime sequences
