# ADR 0142: W5 deepen — guest conditional get product path

Status: accepted; one-arm linear `if` ownership so product guests skip
get-stream when put/CAS fails, returning `0`. Not match-variant joins and not
Component packaging of conditional linear arms.

## Decision

### 1. Ownership: one-arm linear `if`

`linear-let-move` admits:

```
(if test
  <form that fully produce+consume one linear>
  <non-linear form with no linear calls>)
```

and the symmetric case with linear only in the else arm. The test must not
contain linear typed-cap-calls. When both arms contain linears, both must
reduce to the **same** producer form (rare; product paths use one-arm).

This is affine-sound: a linear created inside a branch is consumed inside
that branch; the other branch never observes it.

### 2. Product exports

| export | behavior |
|---|---|
| `put-then-count-if` | put; if true → get+count else `0` |
| `put-cas-then-count-if` | put+CAS; if CAS true → get+count else `0` |

Unconditional exports from ADR 0140/0141 remain.

### Evidence

- frontend one-arm if walk
- `linear_resource_test` one-arm admit + dual-producer reject
- `object_product_vertical_test` skip-get on fail / get on success
- Suite green (see PR)

## What this does NOT claim

- Producing a linear **result** from only one arm of an if (result type must
  still unify)
- match-variant multi-arm with partial linear arms
- Component packaging of conditional product bodies

## Related

- ADR 0140 / 0141 — unconditional put→get / put→CAS→get product verticals
- ADR 0138 / 0139 — balanced if / case multi-arm exclusive-use
- Migration plan: W6 inventory
