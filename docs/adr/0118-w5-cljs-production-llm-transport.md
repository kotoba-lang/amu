# ADR 0118: W5 deepen — production `:cljs`/nbb LLM transport via spawnSync hops

Status: accepted; production `:cljs` transport for `:llm/generate` on
Node/nbb; browser host and live-network CI default remain out of scope

## Decision

Close the ADR 0064 explicit `:cljs` gap for
`provider.llm-transport/production-transport`.

### Synchronous contract

Same design as ADR 0117 (HTTP): each network hop runs in a child `node`
process via `child_process.spawnSync`. Parent cljs blocks until the child
exits. Alias GET (`/infer/models/murakumo-main`) and messages POST
(`/v1/messages`) share one hop script.

### Parity with ADR 0064 `:clj`

- ① endpoint/model override (opts + env) → ② alias `:alias-for` only →
  ③ endpoint-only fallback with literal `murakumo-main`
- Wire endpoint always default gateway (or override), never alias entry
  `:endpoint`
- Anthropic Messages request/response mapping; empty text content → `\"\"`
- Non-2xx → typed `:error` with `:retryable` (429/5xx true; 401/403/404 false)
- Optional bearer `:api-key` / `MURAKUMO_API_KEY`
- `:on-call` audit hook (exceptions swallowed)
- Pure helpers (`request-body`, `extract-text`, `error-for-status`, …)
  shared across hosts

### Evidence

- provider#13 — `:cljs` implementation
- `test/nbb/llm-transport.cljs` — override resolve, success, empty text,
  429/401/500, bearer header
- Pin `provider` → `3f4a69be247037ea8e61e6ed45c4efa7cf38171e`

## What this does NOT claim

- Browser / non-Node cljs host
- Production cljs storage transport
- Default-CI live murakumo call (still `KOTOBA_LLM_INTEGRATION_TEST=1`)

## Related

- ADR 0064 — `:clj` production LLM transport
- ADR 0117 — cljs production HTTP transport (spawnSync pattern)
- Migration plan: production cljs transports
