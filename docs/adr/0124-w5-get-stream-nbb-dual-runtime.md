# ADR 0124: W5 deepen — get-stream dual-runtime on nbb (`:cljs`)

Status: accepted; intermediate dual-runtime evidence for object + http
get-stream (ready / pending→fulfill / multi-chunk) on nbb; not guest
poll/read ops and not linear Component v0.3 handles

## Decision

### 1. nbb dual-runtime vectors

Extend `test/nbb/object-provider.cljs` and `test/nbb/http-provider.cljs` so
the `:cljs` path mirrors the reference-path oracle (ADR 0121–0123):

| case | transport reply | host ops |
|---|---|---|
| ready-task | `{:bytes ...}` | `task-poll` → `stream-read!` |
| pending→fulfill | `{:pending true}` | `task-fulfill!` → read |
| multi-chunk | `{:chunks [...]}` | join → ready stream |

### 2. Kit resource sync

Compiler-local `stream-object-v1.edn` `:http/get-stream` request was still
bare `:i64`. Synced to provider kit record shape
(`url` + `headers` set) from ADR 0122.

### Evidence

- nbb object-provider: 8 cases (write path 5 + get-stream 3)
- nbb http-provider: 8 cases (POST 5 + get-stream 3)
- Pins unchanged from ADR 0123 (kir `314d65e…`, provider `90938d5…`)

## What this does NOT claim

- Guest-language poll/read/fulfill ops
- True async multi-chunk producers
- Live HTTPS / object-store stream transport
- Linear Component v0.3 handle ABI / `:wasm-aot`

## Related

- ADR 0121–0123 — reference-path get-stream ready / pending / multi-chunk
- ADR 0095 — stream-object write dual-runtime first slice
- ADR 0086 — http POST dual-runtime first slice
