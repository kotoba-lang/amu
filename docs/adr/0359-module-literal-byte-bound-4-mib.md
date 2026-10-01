# ADR 0359 — The module literal-byte admission bound: 64 KiB → 4 MiB

- Date: 2026-10-01
- Status: Accepted (owner direction: the 100% definition is a native compiler
  that builds itself).
- Amends: `kotoba.compiler.frontend.infer/check-value-types!` (a new constant,
  `max-module-literal-bytes`, replaces the reuse of `value/string-value-byte-limit`).
- Related: ADR 0354 (limits are kept only when they bound a resource), 0356
  (source admission bound), 0358 (function-count bound, the process followed here).

## Context

`check-value-types!` refuses a module whose string literals, or whose keyword
literals, total more than `value/string-value-byte-limit` (65 536) bytes, each
occurrence counted after desugaring. That number is the cap on ONE runtime
string value; it was borrowed as the cap on the module's literal total because it
was at hand. Two different resources, one number.

The desugar differential's guest (`scripts/selfhost-wall/ds-gen.sh`, 976
functions: the `:kotoba` view of kotoba-sema's desugar half and the helpers it
calls, a fraction of the frontend) measures, in `check-value-types!`, 65 504
keyword bytes and 58 325 string bytes (instrumented, 2026-10-01): 32 bytes under
the bound for keywords. The next port (callable contracts, structured-result
dispatcher names) pushed it over: `module keyword literals exceed UTF-8 byte
limit` is the first refusal of the guest, before any Kotoba-route gap. The whole
frontend closure is several times larger (type descriptors such as
`[:ref :form/r]` expand per use into the record they name, so keyword bytes grow
with the number of typed operations, not with source size). No arrangement of
modules lowers the whole-program total, as for ADR 0358: the linker produces one
unit.

## Decision

The module-total bound is its own constant, `max-module-literal-bytes` = 4 MiB
(4 194 304), for both totals. It bounds the module's read-only data, which is
bounded in turn by the 8 MiB source admission bound (ADR 0356) for strings and by
the same order for keywords. The per-value caps are unchanged: one string
literal still may not exceed 4096 bytes, one runtime string 64 KiB
(`string-value-byte-limit`).

## Consequences

- `frontend_extensions_test`: the pinned refusal now takes 1025 literals of 4096
  bytes (one over the new bound) instead of 17.
- Programs that were refused for a literal total between 64 KiB and 4 MiB are now
  admitted; nothing previously admitted is refused.
- The wall of the desugar guest moves from the literal bound to the next
  Kotoba-route gap.
