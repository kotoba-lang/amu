# ADR 0265: native-aot / jit stay pending — no C-free syscall path

Status: accepted

## Decision

Every application kit keeps `:native-aot :pending` and `:jit :pending`.
Backend-wide native stays `:pending` on
`backend-provider-qualification-v2.edn`.

The remaining gaps are still:

- `:typed-provider-syscall-abi`
- `:nested-request-result-host-codec`
- `:native-provider-semantic-vectors`
- `:c-free-aiueos-cpl3-syscall-substrate`

Hosted kexe C loader is a rejected surface (already fail-closed in
`backend-qualification-test`). Closing wasm-aot for http/llm (ADR 0263 /
0264) does not close those native gaps. There is no C-free typed-provider
syscall in this closure to implement against, so flipping a kit flag
would be theater.

Evidence that this decision is load-bearing:
`native-aot-qualification-test` asserts pending on every application kit
and that the four native gaps remain named.

ADR 0266 adds a hosted kexe clock-v1 **oracle** (nested codec + host
time) without flipping those flags. That oracle is not production
native-aot.

## What this does NOT claim

- A native clock, http, or llm provider
- JIT of kit-typed guests
- Any change to `:wasm-aot` (those flags live in ADRs 0258–0264)
