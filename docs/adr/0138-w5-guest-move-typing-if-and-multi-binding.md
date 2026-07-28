# ADR 0138: W5 deepen — guest move typing: multi-binding let + balanced `if`

Status: accepted; extends ADR 0137 affine let-move with non-linear companion
bindings, nested non-linear outer lets, and balanced `if` arms. Still not
match multi-arm, not linear parameters, not Component packaging of let-moved
forms.

## Decision

### 1. Multi-binding / nested lets

A `let` may include any number of **non-linear** bindings alongside **exactly
one** linear `typed-cap-call` binding. Non-linear initializers must not
reference the linear symbol or produce further linear calls.

Nested outer lets that bind only non-linear values may wrap an admitted
inner affine form.

### 2. Balanced `if`

Inside an affine let body:

```
(if test
  <exclusive-use of task>
  <exclusive-use of task>)
```

Both arms must exclusive-use the binding the **same way** (`:move` or
`:consume`). `test` must not mention the binding or produce linear calls.
Unbalanced arms (consume vs constant) remain rejected.

`bytes-task-byte-count` and `task-ready?` both count as `:consume`.

### 3. Still rejected

- linear ordinary parameters
- double use / unbalanced if
- two linear bindings in one let
- match multi-arm (deferred)

## Evidence

- `linear-let-move` ownership walk in `frontend.cljc`
- `linear_resource_test` multi-binding / nested / if-balanced / if-unbalanced
- Registered in `test_runner.clj`
- Suite **654 / 5702** green

## What this does NOT claim

- Multi-arm `match` / `cond` affine joins
- Linear values as function parameters
- Component Canonical lowering of let/`if`-wrapped linear bodies
- Host dual-runtime table changes

## Related

- ADR 0137 — single-binding let move/consume
- ADR 0127 / 0133 — guest poll/read + host table
- Migration plan: fuller product apps / match multi-arm / W6 inventory
