# ADR 0137: W5 deepen — guest affine let move for linear task/stream

Status: accepted; guest source may bind one linear task/stream in a single
`let` and move or consume it exactly once. Not multi-binding lets, not
parameter-passing of linear types, not full move typing across arbitrary
control flow.

## Decision

### 1. Admitted shapes (in addition to direct call / direct consume)

| shape | meaning |
|---|---|
| `(let [task (typed-cap-call … linear)] task)` | affine rename / move out |
| `(let [task (typed-cap-call … linear)] (bytes-task-byte-count task))` | consume once |
| `(let [task (typed-cap-call … linear)] (task-ready? task))` | poll once |

Exactly one binding pair; the initializer is the sole linear typed-cap-call;
the body uses the symbol exactly once as above.

### 2. Still rejected

- linear types as ordinary parameters (move-aware parameters)
- double use of the same binding
- multi-binding `let` that includes a linear resource
- control flow that aliases or copies the handle

### 3. Evidence

- `test/kotoba/compiler/linear_resource_test.clj` — move / consume admit +
  double-use / multi-binding reject
- Prior direct-call and component packaging paths unchanged

## What this does NOT claim

- Full affine typing across nested `if` / multi-arm match
- Component Canonical lowering of let-wrapped forms (packaging still prefers
  direct bodies; free-function / CM resource multi-step is ADR 0134–0136)
- Host dual-runtime table changes (ADR 0133)

## Related

- ADR 0077 — linear capability resources (issue/execute mode)
- ADR 0127 — guest poll/read ops
- ADR 0133 — host linear resource table
- Migration plan: guest move typing / product apps
