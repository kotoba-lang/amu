# ADR 0140: W5 deepen — guest object put→get product vertical

Status: accepted; dual-runtime guest **single-export** product path that
puts a content-addressed block then measures the get-stream body via affine
let-move. Not production HTTP endpoint orchestration and not Component
packaging of the mixed guest body.

## Decision

### 1. Guest shape

```
(defn put-then-count [put-req get-req] :i64
  (let [ok (typed-cap-call :object/put-block …)
        task (typed-cap-call :object/get-stream …)]
    (bytes-task-byte-count task)))
```

- `ok` is non-linear (`:bool`); `task` is the sole linear binding
- Consume via `bytes-task-byte-count` (ADR 0127 / 0133)
- Ownership admitted by multi-binding affine let (ADR 0137–0138)

This closes ADR 0132's deferred item: *Guest single-export put+get (linear
ownership still blocks mixed body)* — ownership no longer blocks after move
typing.

### 2. Dual-runtime evidence

In-memory transport: put stores `[binding digest] → bytes`; get loads by
`[binding key]` (same string for product round-trip).

| check | expectation |
|---|---|
| typed HIR | effects `#{[:cap/call 14] [:cap/call 15]}`, result `:i64` |
| round-trip | `put-then-count` returns payload byte length |
| order | transport sees `:put-block` then `:get-stream` |
| missing get | fail-closed |

Example: `examples/w5-object-put-get-product.kotoba`

### Evidence

- `object_product_vertical_test` (clj reference runtime)
- nbb product case in `test/nbb/object-provider.cljs`
- Suite green (see PR)

## What this does NOT claim

- Production object endpoint orchestration (ADR 0129 remains transport)
- Conditional skip of get when put fails (would need one-arm linear if)
- Component / Wasm packaging of the mixed put+get guest body
- CAS-in-the-middle product path

## Related

- ADR 0132 — packaging put+get product vertical (Wasmtime sum 3)
- ADR 0129 — production object-store transport
- ADR 0137–0139 — guest affine move typing
- Migration plan: product apps
