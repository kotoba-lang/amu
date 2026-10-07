# Typed guest closures with opaque JS values (bootstrap qualification)

The locked normal compiler consumes Sema PR97 (`621e89b7c45e6aaad4943e72977160bedf5826c0`)
and Osaho PR102 (`9d033b3e07fe32195e2c3ec93aa6d4a0645a848e`). Script remains
`6f7243022a01265916f89bfee46e1941e3e736a6`. Sema permits checked guest closure
parameters and results containing `:js-value`, including bounded record fields.
Osaho distinguishes internal tail-call controls by weak allocation identity;
opaque results are not probed for map/protocol properties or control tags.

## Source and target contract

```clojure
(ns host.closures (:export [keep]))
(defn applyOpaque [f [:fn [[:js-value] :js-value]] v :js-value] :js-value (f v))
(defn keep [v :js-value] :js-value (applyOpaque (fn [x] x) v))
```

Both explicit `--target js --jvm-free` and `--target js-browser --jvm-free`
compile this source through the ordinary dependency lock. Non-JS targets
reject opaque JS types before KIR lowering, even when only an internal
closure returns one and the public function returns `:i64`.

## Qualification on 2026-10-08

* The maintained portable suite passed 76 tests / 526 assertions on the pinned
  Node/nbb bootstrap engine, including two new tests / 21 assertions.
* Actual normal JS and JS-browser artifacts executed in a pinned offline Node
  container: 15 opaque values / 45 identity comparisons per artifact, including
  revoked and throwing proxies, zero observed property reads. The exercised
  forms were a typed guest lambda, typed function reference, and stored
  zero-argument guest closure returning native undefined.
* Normal cljs, wasm32-browser, and x86_64 requests exited 65 without artifacts.
  Shadowed forbidden JVM launchers wrote no marker. The final matching lock
  produced the identical qualified JS artifact.

These are JVM-free bootstrap and offline Node results. They do not establish
native selfhost or browser-host execution. Opaque JS captures and calling raw
host callbacks remain refused; the existing bounded i64 closure handle/capture
representation and restricted execution budgets remain unchanged. Host callback
adaptation and authorized property operations remain separate prerequisites for
CosmoKit mapValues and the full Mithril Harness migration.

This change is operator-authored. The public System One status endpoint returned
HTTP 503 during this work, so no model execution or performance result is claimed.
