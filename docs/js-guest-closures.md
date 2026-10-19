# Typed guest closures and opaque captures (bootstrap qualification)

The normal locked compiler consumes published Sema PR98/99
(`60a1b0e67bbeb230a5eff398721b8bff4ada59d7`), Osaho PR103
(`d1c27ed446745f9db7d4b20c6531e108e6949a9c`) and Script PR111
(`ed36af5f71be11c2e688098653df516e684b1150`).
Typed guest closure parameters/results may contain opaque `:js-value` leaves.
Leaf captures use typed arena cells; mixed integer captures preserve the word
ABI. Proven lexical initializers and aliases retain their type during lifting;
rebinding and lambda parameters shadow an outer opaque type.

## Source and target contract

```clojure
(ns host.captures (:export [keep]))
(defn create [v :js-value] [:fn [[] :js-value]] (fn [] v))
(defn keep [v :js-value] :js-value (let [f (create v)] (f)))
```

Explicit `--target js --jvm-free` and `--target js-browser --jvm-free` compile
through the ordinary dependency lock. Non-JS targets reject JS types before
KIR lowering, including a hidden opaque capture whose enclosing public function
returns `:i64`. Stored values retain identity without inspecting host proxies.
Opaque cells share the existing bounded pair arena and constructor fuel/cells;
the five-capture bound and restricted execution budgets remain in place.

## Qualification on 2026-10-08

* Maintained portable suite: 78 tests / 547 assertions, zero failures/errors.
  The hidden lexical capture regression previously failed twelve target/phase
  assertions; those unchanged assertions now pass through the published pins.
* Actual normal JS and JS-browser artifacts each ran in pinned offline Node:
  14 opaque values / 98 identity comparisons across seven capture functions,
  two additional lexical scalar checks, zero observed property reads, three
  budget checks and 2,000 repeated calls. Cases include mixed capture slots,
  typed guest arguments, nested captures, captured guest functions, five
  opaque captures, aliases, native undefined, revoked and throwing proxies.
* Normal cljs, wasm32-browser and x86_64 requests exited 65 without artifacts.
  Forbidden JVM launchers were shadowed and no invocation marker was written.
* Sema's three integer capture fixtures retain byte-identical complete HIR.

These are JVM-free Node/nbb bootstrap and offline Node results. Native selfhost
and browser-host execution require their own evidence. Captures containing
records with JS leaves, raw host callbacks, authorized property operations and
persistent/escaping host callable adaptation remain separate prerequisites for
CosmoKit mapValues and the full Mithril Harness migration. Public typed guest
parameter/result support does not establish those capture/host contracts.

The changes are operator-authored. System One's public status returned HTTP 503
during this work; no model execution or performance result is attributed to it.
