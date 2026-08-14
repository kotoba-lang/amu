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
- Public CLI is the JVM launcher (`kbb` does not exist). The hosted
  i64 surfaces are:
  - `kotoba compile --target wasm --run` via kototama.tender
  - `kotoba compile --target web --run` via Node `instantiateKotoba`
    (js-kotoba-v1). The hosted grant is capability 7
    (`:clock-monotonic`) only; other kit ids in `--policy :allow` are
    refused (`:compile/run-unsupported-capability`). Host-free i64
    `main` runs with empty grants.
  - `kotoba wasm run <file.wasm>` of a guest that imports `kotoba:cap`
    uses tender. Source `.kotoba` `wasm run` stays `kotoba.wasm-exec`
    (admission-gated). Non-cap wasm is refused
    (`:wasm/run-requires-kotoba-cap`).
- kotoba-script hosts i64 `(typed-cap-call 7 :i64 :i64 seed)` as
  `callCapability(7, …)`. Non-i64 request/result still refused.

The other application kits keep `:wasm32-kotoba-v1 :pending`. Their guest
sugar can also lower to `typed-cap-call` with richer request types; the
i64 host has no kit semantics for those ids and fail-closes
(`grant/unknown-capability`). That is the gap, not a silent pass.

## What this does NOT claim

- kit variant/record marshalling on wasm or native
- `:wasm-aot :implemented` on any kit
- `:wasm32-kotoba-v1 :implemented` on the other seven application kits
- production WASI clocks (ADR 0084)
- a public CLI off the JVM (`kbb`)

## Evidence

- kotoba-lang/kotoba `compile-run-host-free-i64-main-on-js-kotoba-v1`,
  `compile-run-clock-now-web-returns-host-millis`,
  `compile-run-refuses-unsupported-capability`,
  `wasm-run-kotoba-cap-artifact-on-tender`,
  `wasm-run-non-cap-wasm-is-refused` (launcher-test 90 tests, 2026-08-14)
- kotoba-lang/kotoba-script `typed-cap-call-i64-hosts-as-call-capability`
  (landed `d4b34e79`)
- kotoba-lang/kotoba merge `793808c5` (web `--run` + `wasm run` of
  `kotoba:cap` artifacts)
- kotoba-lang/kototama `amu-compiled-clock-now-links-kotoba-cap-call`
- kotoba-lang/wasm-webcomponent `test/verify-kotoba-cap.mjs`
- this repo: `clock-wasm32-kotoba-v1-qualification-is-the-i64-surface`
