# ADR 0122: W5 deepen — http/get-stream dual-runtime ready-task

Status: accepted; intermediate dual-runtime evidence for `:http/get-stream`
on the reference path; not production stream transport and not linear v0.3 handles

## Decision

### Kit request shape

`stream-object-v1` `:http/get-stream` request was bare `:i64` (underspecified
vs WIT `http-get-stream-request`). Dual-runtime uses:

```
[:record :kotoba.http/get-stream-request
 [[:url :string] [:headers header-set]]]
```

### Provider

`provider.http/get-stream-provider` (id 13):

1. Exact-origin allowlist (same as POST)
2. Header bounds
3. Transport `{:operation :get-stream :url :headers}` → host `:bytes`
4. Wrap as **ready** `[:task [:stream :bytes]]`

### Evidence

- provider#17 — provider + kit
- compiler http-provider-test: get-stream poll/read + origin denial + redaction + missing grant
- Pin provider → `c465893e0cea3ecf32dce438943ef939b6f0890e`
- Suite: 621 tests / 5610 assertions green

## What this does NOT claim

- Live HTTPS stream transport (mock only in this slice)
- Guest-language poll/read ops
- Pending→ready scheduling / multi-chunk
- Component v0.3 linear handle ABI

## Related

- ADR 0121 — object get-stream dual-runtime
- ADR 0120 — runtime `:bytes`
- http-v1 POST (id 4)
