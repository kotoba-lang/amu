# ADR 0102: W5 deepen — log multi-step Wasmtime append sequence driver

Status: accepted; intermediate multi-step execution evidence for log-v1 wasm
packaging; closes ADR 0085 multi-step deferral for log; not `:wasm-aot` flip

## Decision

Deepen family-1 log wasm packaging with a **multi-step Wasmtime driver**:

1. Hand-authored application component imports `log.append` only
2. Performs two appends (empty field sets; fixed level/event/message literals)
3. Returns `(seq2 - seq1)` as `s64`
4. Composed closed with real dual-export `package-log-provider`
5. Wasmtime execution yields **1** (ring buffer sequence advances once per
   successful append)

This is the log counterpart to ADR 0101 (clock wall→mono) and the state
stateful-sequence drivers (ADR 0060/0061). ADR 0085's deferred "Wasmtime
multi-step driver bitmask" for log is now partially closed for the append
path; full append+read multi-step remains optional follow-up.

## Evidence

- kotoba-component#57 — driver in `log_provider_component_test`
- 4 tests / 16 assertions green (includes Wasmtime run)
- Pin advanced to `45b4b75238fbbaafa0e6a1d872a78cd1451a4c0a`

## What this does NOT claim

- Multi-step append+read ring-buffer walk in one Wasmtime invoke
- Production host log transport
- `:wasm-aot :implemented`

## Related

- ADR 0085 — log wasm packaging (multi-step deferred)
- ADR 0101 — clock multi-step pattern
- Migration plan: Wasmtime multi-step drivers
