# ADR 0119: W5 deepen — production `:cljs`/nbb storage transport via spawnSync hops

Status: accepted; production `:cljs` transport for `:storage/transact` on
Node/nbb; no ambient filesystem backend and no browser host

## Decision

Close the ADR 0071 explicit `:cljs` gap for
`provider.storage-transport/production-transport`.

### Synchronous contract

Same design as ADR 0117 (HTTP) and ADR 0118 (LLM): each
`/storage/v1/transact` POST runs in a child `node` process via
`child_process.spawnSync`. Parent cljs blocks until the child exits.

### Parity with ADR 0071 `:clj`

- Required host-configured `:endpoint` (or `KOTOBA_STORAGE_ENDPOINT`);
  no baked default (no ambient filesystem authority)
- Fixed path (default `/storage/v1/transact`); operation/key/namespace in
  JSON body only
- Wire tags: found/missing/written/deleted/conflict/error with fail-closed
  value/version sanitization
- Non-2xx → typed `:error` with `:retryable` (429/5xx true)
- Optional bearer `:api-key` / `KOTOBA_STORAGE_API_KEY`
- `:on-call` audit hook (exceptions swallowed)

### Evidence

- provider#14 — `:cljs` implementation
- `test/nbb/storage-transport.cljs` — resolve-endpoint, put/get, missing,
  conflict, delete, 429/500
- Pin `provider` → `69029568a450dcfa4baf8ba21ad53186a2952c5d`

## What this does NOT claim

- Browser / non-Node cljs host
- Ambient local-filesystem storage backend
- A repo-wide well-known live storage endpoint for CI

## Related

- ADR 0071 — `:clj` production storage transport
- ADR 0117 / 0118 — cljs HTTP / LLM spawnSync pattern
- Migration plan: production cljs transports
