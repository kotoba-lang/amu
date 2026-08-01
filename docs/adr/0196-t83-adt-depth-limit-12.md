# ADR 0196: T8.3/W4 parametric ADT depth 8 → 12 (match kir 0025)

- Status: Accepted
- Date: 2026-08-01
- Depends: kotoba-kir ADR 0025 (`ee62427a`)

## Decision

1. Pin kotoba-kir with `adt-depth-limit` 12.
2. Artifact limits `:parametric-adt-depth` **12**.
3. browser-host runtime `assertValue` depth budget **12** (descriptor metadata stays 8).

Enables structured kv pair spines for recursive EDN (provider 0248).

## Related

- T8.3 / W4; kir 0025; provider 0246–0248
