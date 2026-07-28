# ADR 0141: W5 deepen — guest object put→CAS→get product vertical

Status: accepted; dual-runtime guest single-export product path that puts a
block, compare-and-sets a ref, then measures get-stream body. Not conditional
skip on CAS lose and not production endpoint orchestration.

## Decision

### 1. Guest shape

```
(defn put-cas-then-count [put-req cas-req get-req] :i64
  (let [ok-put (typed-cap-call :object/put-block …)
        ok-cas (typed-cap-call :object/compare-and-set-ref …)
        task   (typed-cap-call :object/get-stream …)]
    (bytes-task-byte-count task)))
```

- Two non-linear companions (`:bool`) + one linear task binding
- Always runs get after put/CAS (no one-arm linear if); CAS lose still
  returns body length of the put payload when get key matches digest

### 2. Dual-runtime evidence

| check | expectation |
|---|---|
| typed HIR | effects `#{14 15 16}`, result `:i64` |
| CAS win round-trip | body length = payload |
| order | put → compare-and-set-ref → get-stream |
| CAS lose | get still measured (documented non-conditional) |

Extends ADR 0140 product vertical; example remains
`examples/w5-object-put-get-product.kotoba` (+ put-cas-then-count export).

### Evidence

- `object_product_vertical_test` put-cas cases
- nbb product-cas case
- Suite green (see PR)

## What this does NOT claim

- Conditional get only on CAS win (needs one-arm linear if)
- Production object/ref backend (ADR 0129)
- Component packaging of the three-op guest body

## Related

- ADR 0140 — put→get product vertical
- ADR 0132 — packaging put+get vertical
- ADR 0112 — put+CAS multi-step packaging
- Migration plan: deeper product paths / W6 inventory
