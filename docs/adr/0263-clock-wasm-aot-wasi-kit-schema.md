# ADR 0263: clock :wasm-aot is the WASI 0.3 kit schema

> **Status 2026-08-24 — proposed, not qualified.** `clock-v1.edn` keeps
> `:wasm-aot :pending` and the kit is not in
> `wasm32-kotoba-v1-qualification-test`'s proved sets. The suite written for
> this ADR was held back at merge because the composed component does not
> link:
>
> ```
> component imports instance `wasi:clocks/system-clock@0.3.0`, but a matching
> implementation was not found in the linker
>   instance export `now` has the wrong type
>   function implementation is missing
> ```
>
> Measured on wasmtime **43.0.2** and **45.0.3** — identical on both, so this
> is not the `:minimum-wasmtime-major 43` floor. The WIT that
> `kotoba.component.composition/package-clock-wasi-provider` emits disagrees
> with what wasmtime implements for that interface. Deciding which WASI 0.3
> revision the kit targets is this ADR's question; the suite can be restored
> from the PR branch once the shapes agree.


Status: proposed (see the note above -- the qualifying run does not link)

## Decision

`:wasm-aot` on `clock-v1.edn` would be `:implemented`. That flag names the kit
variant/record request/result schema running as a wasm component whose
time comes from `wasi:clocks/system-clock@0.3.0` and
`wasi:clocks/monotonic-clock@0.3.0`.

It does **not** name the i64 guest sugar `(clock/now seed)` →
`(typed-cap-call 7 :i64 :i64 seed)` → `kotoba:cap`/`call`. That remains
`:wasm32-kotoba-v1` (ADR 0257). The two surfaces stay distinct.

This supersedes ADR 0084 / 0101 / 0257 only on the clock wasm-aot row.
Those ADRs correctly refused to flip the flag when the only evidence was
synthetic `package-clock-provider` packaging or a multi-step observation
sequence. The missing piece was host time plus deny-when-ungranted.

## Evidence that is allowed to flip the flag

All four must hold in `clock-wasm-aot-qualification-test`:

1. `package-clock-wasi-provider` composed with `compose-with-declared-wasi`
2. wasmtime `run -S p3 --invoke run()` returns unix-millis within 1s of
   `System/currentTimeMillis`
3. wasmtime `run -S cli=n -S p3=n` fails in the linker on `wasi:clocks/`
   (guest never observes a fallback time)
4. wasmtime major ≥ the number pinned in
   `component-model-v1.edn` (`:minimum-wasmtime-major`); fail, do not skip

The driver is a wall-reading WAT (`run() -> s64` of unix-millis at
retptr+8), the same shape kotoba-component W6 already executed. Binding
it in this repo is what makes the kit flag a compiler claim rather than
a downstream anecdote.

## What this does NOT claim

- `:wasm-aot` on http / http-ingress / storage / llm
  (state and log: ADR 0264; ui: ADR 0265)
- `:wasm32-kotoba-v1` on those seven kits
- backend-wide wasmtime `:qualified` in
  `backend-provider-qualification-v2.edn` (other kits still synthetic;
  nested canonical ABI / production providers remain gaps)
- `:native-aot` / `:jit` on any kit (C-free aiueos typed-provider syscall
  is still the native gap)
- compiled `.kotoba` kit-typed source as the guest (compile-component of
  `(cap-call :clock/now 7)` still emits s64; the kit schema path is the
  WASI provider + kit-shaped driver)

## Related

- ADR 0257 — i64 wasm32-kotoba-v1 surface (unchanged)
- ADR 0084 — clock wasm packaging, synthetic, no flip
- ADR 0101 — wasmtime multi-step synthetic sequence, no flip
- kotoba-component `68774dc` — WASI 0.3 clock provider
