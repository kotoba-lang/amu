# ADR 0139: W5 deepen — guest move typing through `case` / `cond` multi-arm

Status: accepted; multi-arm affine exclusive-use for linear task/stream via
desugared nested `if` chains, including `case` / `condp` dispatch `let`
wrappers. Not match-variant, not linear parameters, not Component packaging.

## Decision

### 1. Background

ADR 0138 admitted balanced binary `if` exclusive-use of a let-bound linear.
Portable multi-arm forms desugar as follows:

| surface | desugar |
|---|---|
| `cond` | nested `if` |
| `case` | `(let [tmp dispatch] nested if)` |
| `condp` | `(let [tmp dispatch] nested if)` |

`cond` already worked under 0138. `case` / `condp` failed because
`exclusive-use-of-linear` stopped at the dispatch `let`.

### 2. Extension

`exclusive-use-of-linear` walks **pure non-linear** nested `let` wrappers
(bindings do not mention the linear symbol, do not produce linear calls)
and continues into the body. Nested balanced `if` then joins all arms.

Admitted examples:

```
(let [task (typed-cap-call …)]
  (case k
    0 (bytes-task-byte-count task)
    1 (task-ready? task)
    (bytes-task-byte-count task)))

(let [task (typed-cap-call …)]
  (cond a (bytes-task-byte-count task)
        b (task-ready? task)
        :else (bytes-task-byte-count task)))
```

Every arm must exclusive-use the binding the **same kind** (`:move` or
`:consume`). Unbalanced arms remain rejected.

### Evidence

- `exclusive-use-of-linear` non-linear let walk
- `linear_resource_test` cond / case / condp multi-arm + unbalanced reject
- Suite **659 / 5708** green

## What this does NOT claim

- `match-variant` / structural multi-arm joins
- Linear function parameters
- Component Canonical lowering of case/cond-wrapped linear bodies
- Host dual-runtime table changes

## Related

- ADR 0137 — single-binding let move/consume
- ADR 0138 — multi-binding companions + balanced if
- Migration plan: fuller product apps / W6 inventory
