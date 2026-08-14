# ADR 0257: clock wasm32-kotoba-v1 is the i64 elaboration, not the kit variant

Status: accepted

## Decision

`clock-v1.edn` carries two surfaces. They are not the same ABI.

| Surface | Shape | Status |
| --- | --- | --- |
| `:reference` | kit `:request`/`:result` (variant + record) | `:implemented` (cljs/nbb provider) |
| `:wasm-aot` | that same kit schema on wasm component / WASI clocks | `:pending` (ADR 0084) |
| `:wasm32-kotoba-v1` | guest sugar `(clock/now seed)` → `(typed-cap-call 7 :i64 :i64 seed)` → import `kotoba:cap`/`call` | `:implemented` |

`:wasm-aot` stays pending. Flipping it would claim the variant kit schema
runs on wasm-aot, which it does not.

`:wasm32-kotoba-v1 :implemented` is the production host-time path:

- amu/kotoba-wasm emit `kotoba:cap`/`call (i64,i64)->i64` (not `kotoba:typed`)
- kototama.tender always links that import; id 7 requires `:clock-monotonic`
  and returns `System/currentTimeMillis`
- wasm-webcomponent `kotobaCapImports` is the browser/Node peer
- `kotoba compile --target wasm --run` is the public CLI

The other application kits keep `:wasm32-kotoba-v1 :pending`. Their guest
sugar can also lower to `typed-cap-call` with richer request types; the
i64 host has no kit semantics for those ids and fail-closes
(`grant/unknown-capability`). That is the gap, not a silent pass.

## What this does NOT claim

- kit variant/record marshalling on wasm or native
- `:wasm-aot :implemented` on any kit
- production WASI clocks (ADR 0084)

## Evidence

- kotoba-lang/kotoba `compile --run` clock test (host millis)
- kotoba-lang/kototama `amu-compiled-clock-now-links-kotoba-cap-call`
- kotoba-lang/wasm-webcomponent `test/verify-kotoba-cap.mjs`
- this repo: `clock-wasm32-kotoba-v1-qualification-is-the-i64-surface`
