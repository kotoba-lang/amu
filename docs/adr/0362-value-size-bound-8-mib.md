# ADR 0362 — The string and bytes value bound: 64 KiB → 8 MiB

- Date: 2026-10-02
- Status: Accepted (owner decision 3 of 2026-10-02: "raise the native value-size limit (64 KiB string/bytes cap
  -> >= 8 MiB) by ADR now"; it is reversible, and reverting means restoring the numbers below).
- Amends: kotoba-lang `lang/limits.edn` `:language/value :string-value-bytes` (65 536 -> 8 388 608) and a new
  `:bytes-value-bytes` (8 388 608; the bytes bound was unlisted). It also amends `lang/guest-grammar.edn`
  `:bytes-value :limits` and its prose, with the copy vendored in kotoba-sema; osaho
  `kotoba.kir.value/string-value-byte-limit` and `bytes-value-byte-limit`, and the Kotoba-route interpreter's
  `str-limit` / `bytes-limit` twins; amu `tools/kexe_loader_decisions.kotoba` constants 18 and 19 and so
  `KEXE_STRING_VALUE_LIMIT` / `KEXE_BYTES_VALUE_LIMIT` (regenerated); `kotoba.compiler.limits/table` and the js
  manifest's `:string-value-bytes`.
- Related: ADR 0356 (source admission bound 8 MiB), 0358 / 0360 (the process followed here), 0359 (the module literal
  bound, 4 MiB, already split off the value bound), 0361 (growth regions).

## Context

`string-value-bytes` was 64 KiB: the most UTF-8 bytes one string value may hold, with the `:bytes` twin equal to it.
The compiler that builds itself reads each source file as one value (`:fs/app-data` wire 35 as `:string`, or as
`:bytes` and then `string-from-utf8`). The source admission bound is 8 MiB (ADR 0356), and `frontend/desugar.cljk`
alone is 10.6 k lines. So the self-built compiler would refuse its own sources, and it would do so by accident: the
value bound was never chosen for source text.

What was still 64 KiB on 2026-10-02 (after ADR 0359 had split off the module literal total):

| place | what it bounds | before | after |
|---|---|---|---|
| osaho `kotoba.kir.value/string-value-byte-limit` | one string value (reference interpreter, fold, `bounded-string!`) | 65 536 | **8 388 608** |
| osaho `bytes-value-byte-limit` | one `:bytes` value | 65 536 | **8 388 608** |
| osaho `kotoba.kir.interp` `str-limit` / `bytes-limit` | the same, Kotoba-route interpreter (frozen, constants only) | 65 536 | **8 388 608** |
| loader `KEXE_STRING_VALUE_LIMIT` (decisions 18) | `string-from-utf8` | 65 536 | **8 388 608** |
| loader `KEXE_BYTES_VALUE_LIMIT` (decisions 19) | `bytes-from-vector-i64`, `bytes-concat`, a file read or written as `:bytes` | 65 536 | **8 388 608** |
| osaho `string-literal-byte-limit` | one string LITERAL | 65 536 (was defined as the value bound) | 65 536, now its own constant |
| loader `KEXE_BOUNDARY_STRING_BYTES` / `_BYTES_ITEMS` | one leaf of a native export ARGUMENT (argv) | 65 536 (listed as a copy of the value bound) | 65 536, now `:profile/native :structural :export-argument-*` |
| loader `KEXE_NET_REQUEST_MAX` | one native TCP request frame | value bound + 1 | 65 537, its own number |
| kotoba-script `max-string-value-bytes` | the ESM runtime | 65 536 | 65 536, now `:profile/esm :string-value-bytes` |
| `:language/boundary :traversal-bytes` | payload bytes per boundary walk | 1 MiB | 1 MiB (unchanged) |

Native code never checked string length inline. `string-concat` and a file read as `:string` were already unbounded
except by the pool budget, so on native the cap applied only where a value crosses between `:bytes` and `:string`.
Measured with `scripts/selfhost-wall/guests/value_cap.cljk` (a round trip through `string-to-utf8`, `bytes-concat`
and `string-from-utf8`): before, 65 537 bytes trapped SIGILL; after, 65 537, 1 MiB and 8 MiB answer `ok`, and
8 MiB + 1 traps.

## Decision

The value bound for `:string` and `:bytes` is 8 MiB (8 388 608), the source admission bound. The table's authority
lists every copy, and `value_bounds_agreement_test`'s rule applies: 76 copies compared, 0 mismatches. That was
checked on 2026-10-02 with the nbb twin of the test, because the JVM route is gone (ADR 0347).

Three numbers that used to be copies of the value bound are split off. They stay 64 KiB, because each bounds a
different resource:

- a string LITERAL (code size, rodata, bounded as a module total by ADR 0359);
- a leaf of a native export argument (argv);
- the ESM profile's runtime. Its target is deferred from the first self-build (owner decision 1), so it keeps
  the bound it enforces, and its artifact manifests keep saying `:string-value-bytes 65536`. Rule 5 holds:
  the deferred target refuses by the same trap name, `:string/too-large`, rather than claiming the new bound.

The boundary walk's budget is not changed. On the reference route a capability result is walked, so a source file
over 1 MiB returned by a capability needs a caller-named `:boundary-budget` (osaho `execute`). The native loader does
not walk capability results.

## Consequences

- Programs refused only because a value passed 64 KiB are now admitted. Nothing admitted before is refused.
- A `vector-alloc` / `bytes-from-vector-i64` of 8 Mi items on the reference interpreter is a large host allocation
  (the osaho test now does exactly that, once).
- osaho tests: `kir_string_from_utf8_test` and `kir_string_upper_test` derive or name the new bound.
  `kir_string_literal_bound_test` now pins literal < value. `value_test` keeps the 16 x 64 KiB = 1 MiB boundary
  relation with an explicit 64 KiB leaf.
- Wasm (`kotoba-wasm`) and the cljs backend are deferred (owner decision 1) and were not touched. They enforce their
  own bounds and are not copies listed in the table.
