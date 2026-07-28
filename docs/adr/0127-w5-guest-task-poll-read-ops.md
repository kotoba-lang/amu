# ADR 0127: W5 deepen — guest poll/read ops (`task-ready?`, `bytes-task-byte-count`)

Status: accepted; intermediate dual-runtime evidence that a compiled guest
can poll and drain a `[:task [:stream :bytes]]` without host-side
`value/task-poll` / `value/stream-read!`; not multi-value stream handles as
guest returns and not Component v0.3 linear packaging of these ops

## Decision

### 1. Guest ops (reference KIR eval, kotoba-kir#17)

| op | arity | result | semantics |
|---|---|---|---|
| `task-ready?` | task | i64 | 1 if ready, 0 if pending; cancelled traps |
| `bytes-task-byte-count` | task | i64 | require ready; drain stream; return total bytes; pending/open-pending traps |

Both are pure guest-language forms evaluated by `kotoba.kir/execute` (not
host Clojure helpers after invoke).

### 2. Frontend admission (compiler)

- `task-ready?` admitted next to `bytes-task-byte-count` (arity 1, arg type
  `[:task [:stream :bytes]]` → `:i64`)
- Linear-resource ownership: either op may wrap a single direct
  `typed-cap-call` that returns a linear task (same exception as
  `bytes-task-byte-count` alone)

### 3. Dual-runtime evidence

Guest exports:

```text
(get-stream-ready request) → (task-ready? (typed-cap-call :…/get-stream …))
(get-stream-byte-count request) → (bytes-task-byte-count (typed-cap-call …))
```

Object (id 14) and http (id 13) on reference + nbb. Host invoke receives
only i64; no host `task-poll`/`stream-read!` in the vector.

### Evidence

- kotoba-kir#17 — eval + 3 execute tests (suite 47/221)
- compiler dual-runtime object/http + nbb guest cases
- Pin kotoba-kir → `d15a89eb3fd41b79fba9c591d5ca2ab66a7993fd`
- Provider pin unchanged (1275094)

## What this does NOT claim

- Guest return of stream handles / multi-value `{bytes, done?}` records
- Guest `stream-enqueue!` / progressive open-stream drain
- Live transport / Component v0.3 linear ABI packaging of poll/read

## Related

- ADR 0121–0126 — host-side task/stream path
- Migration plan: guest poll/read ops
