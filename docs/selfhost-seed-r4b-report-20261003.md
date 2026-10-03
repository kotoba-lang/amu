# Seed R4B (values by reference): report, 2026-10-03

Extension rung R4B of the seed ladder: the KIR3 missing shapes other than `:document`
(docs/selfhost-seed-merge-20261003.md section 4). Tag `seed-r4b`, record `seed/rungs/r4b.record`. Timings were taken on a
loaded host (load average 40-75); rerun on a quiet host before quoting them.

## Result

| item | value |
|---|---|
| bridge | 9fd5111f8 (the features, sources in the R4 language) compiled by the R4 seed e9598b28 -> 49b7f7ca (502,303 B), its own fixed point |
| rung proof | f9bebf447 (unity 12,746 lines): 21-check and 30-lower rewritten with records by reference, a list of records and more than 5 parameters |
| fixed point | seed-1 == seed-2 568d6152 (502,759 B), built by the bridge seed |
| gates `--rung r4b` | BUILD ERR G1 G2 G3 G4 G5 GR all PASS (GR r1 52+5 / 40, r3 26+28 / 28, r4 33+4 / 27, r4b 26 = stage-0 + 2 = spec / 16 negatives refused) |
| other gates | gate-r5a READY (PREV r4, G3 refusal-r5a, part A 39/39, SPLIT fixed point 3eedeaea, SPLIT-G1/G2/G4, SEP 18/18); KIR gate 19/19 (code bytes and fuel equal to the source route); caps 6/6 equal to stage-0 |
| Embench compile, 19 ports | seed 518 ms in all vs stage-0 4,338 ms (record medians, load 42) |
| code bytes, 19 ports | 97,673 (unchanged: no port uses an R4B feature) |

## Language (seed/HEADS, seed/SIR, seed/CONTRACT-REQUESTS.md R4B lines)

- `[:ref :kw]` = the record registered under `:kw` by an ns `(:schemas {..})` clause, a defrecord's `:<ns>/Name` keyword or
  an inline `[:record :kw ..]` schema (the last one is the KIR shape; stage-0 refuses it in source). Recursive, mutually
  recursive and forward references resolve: defrecords are registered in two passes, inline schemas before the
  signatures. An undeclared ref is E2179. Records stay pair chains; a field of record, list, option or bytes type holds the
  value's handle.
- `:bytes` is a parameter, result, local, loop, record-field and list-item type (not an export, map-key or set-item
  type): `bytes-empty/count/at/concat/slice`, `string-from-utf8` (HD 142-147; the loader's ABI v11 `bytes_slice`,
  `bytes_concat`, `string_from_utf8`; count/at in line as on vectors).
- Capability calls on wires 3, 33, 34 and 41 (`:string :string`) and wire 35 `:string -> :bytes` (kind 9).
- Up to 16 parameters per clause (E2178). Arguments 7.. go to an outgoing area at the bottom of the caller's frame and are
  read at `[x29,#16+8k]`. Exports and variadic clauses stay at 5 (E2108).
- Vector literals of 65..128 integer literals (stage-0's limit) are pooled tables copied into a fresh vector (SIR OP-VECP).
- Loops take up to 20 bindings (KIR4 request).

## Proof (f9bebf447)

- A defrecord's fields are a `[:list [:ref :seed/ck-fld]]` of records, typed and stored in order. This replaces two
  packed-index functions.
- `ck-span3-eq` takes 9 parameters, so 2 are stack-passed in the self-compile. The defrecord keyword lookup that resolves
  `[:ref :seed/ck-fld]` runs through it.
- Ten checker functions take their operands as separate parameters instead of i64 packing.
- `lw-assoc-fields` takes `[:ref :seed/lw-asf]`.

## KIR per-function scan after R4B (seed/tests/kir/slice.py scan, the 10 big guests, every non-helper function's call closure)

Seed 4502396d (R4B plus integer wire ids in typed-cap-call, the KIR spelling, which stage-0 also admits in source). Load 46-54.

| guest | functions | KIR4 seed a7489ef4 | R4B seed 4502396d |
|---|---|---|---|
| ri | 89 | 72 | 89 |
| case | 14 | 12 | 14 |
| cc | 325 | 240 | 316 |
| codec | 200 | 84 | 181 |
| di | 412 | 226 | 397 |
| oa | 400 | 304 | 391 |
| oat | 304 | 233 | 304 |
| vc | 481 | 359 | 470 |
| vx | 394 | 75 | 341 |
| ds_guest_w | 1002 | 101 | 756 |
| **total** | **3,621** | **1,706 (47.1%)** | **3,259 (90.0%)** |

This counts compiles only. The flip condition (>= 95% compiling with EQUAL results) is not met: EQUAL is measured per guest
by merge.sh, not per function. The remaining frontier (slice.py frontier):

- a non-literal `document-keyword` inside `kotoba_module__0__83` and its kin (12-kirread, KIR4). It blocks most of the
  246 ds_guest_w and 53 vx refusals. The seed reports it as "E2104 ... expected :bool".
- `:f64` and `f64-to-f32-rounded`, 7 frontier functions (out of scope).
- the wire-35 WRITE_SEP compile SIGILL, 3 frontier functions with 27 in their closures (50-out).
- one `if` without an else (E2110) and one wire 23 cap.

## Open

- `scripts/seed/bootstrap.sh` only replays numeric rungs (`r<->.record`), so r4b is not replayed yet. The same is true of
  r5a (HOUSE2 request). The chain was reproduced by hand: the recorded R4 seed -> bridge 49b7f7ca -> 568d6152.
- 12-kirread drops the KIR `:schemas` map. Slices that only pass refs along are refused with E2179 until it emits the ns
  clause (request to KIR4).
- The compile SIGILL that KIR4 reported is the wire-35 write of a container that contains "WRITE_SEP" (request to the
  50-out owner).
- Narrower than stage-0, refused by name: more than 16 parameters, exports with more than 5, a 65+ item vector with a
  non-literal item, record captures in fn literals, fn types over `:bytes`, and loops of more than 20 bindings.
