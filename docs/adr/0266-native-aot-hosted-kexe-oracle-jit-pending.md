# ADR 0266: native-aot hosted kexe clock oracle; production and jit stay pending

Status: accepted

Supersedes the “no executable path” sentence of ADR 0265. Kit flags and
backend-wide native status from ADR 0265 are unchanged.

## Decision

Production `:native-aot` is still `:aiueos-c-free-bare-metal-v1`. Hosted
kexe C is a rejected production surface (`backend-qualification-test`
fail-closes `:hosted-kexe-c-loader`). This ADR does **not** flip any kit
`:native-aot` or `:jit`, and does **not** close the four native backend
gaps.

What this slice *does* ship is a **hosted oracle** for the clock-v1 nested
codec, so later C-free work has a known-good pair layout and semantic
vectors rather than an identity provider that would accept `"ok"` theater:

- Guest `typed-cap-call 7` with the kit request/result schemas
- Host decodes `pair(ordinal, bool)`, reads `CLOCK_REALTIME` /
  `CLOCK_MONOTONIC` (Windows: `GetSystemTimeAsFileTime` /
  `QueryPerformanceCounter`), encodes wall/monotonic records with a
  provider-local observation sequence
- Identity echo of the request pair cannot satisfy unix-millis
- Withholding cap 7 is `SIGILL`

`:jit` remains a future KIR→native runtime compiler. It is not wasmtime
Cranelift. iOS/iPadOS must not JIT (ADR 0001). There is no JIT backend in
this closure.

## Production order (unchanged)

ADR 0240: boot-map → allocator → paging → TSS/#DF → timer → CPL3 →
typed-provider syscall → clock kit. A later phase cannot substitute for
an earlier one. C-free kernel work lives in aiueos, not this hosted
loader.

## Evidence

`clock-native-kexe-oracle-test` must:

1. Compile the kit-shaped guest on both native ISAs
2. Execute wall `unix-millis` in `[before, after]` of `currentTimeMillis`,
   and greater than `10^12` (not 0/1 identity)
3. Two wall observations in one process return observation-sequence `2`
4. Execute without the cap 7 grant is denied at admission (before the
   hosted provider can run). The loader bitmap remains a second SIGILL
   check.
5. `clock-v1.edn` still has `:native-aot :pending` and `:jit :pending`

Verifier independently admits `variant-match` on the sealed clock-v1
`typed-cap-call` result (not a widening of local SROA).

## What this does NOT claim

- C-free aiueos typed-provider syscall
- Kit `:native-aot :implemented` or backend-wide native `:qualified`
- JIT of kit-typed guests
- HTTP/LLM/state native providers
- Closing `:typed-provider-syscall-abi` or
  `:c-free-aiueos-cpl3-syscall-substrate`
