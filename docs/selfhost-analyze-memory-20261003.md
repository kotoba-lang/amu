# The native analyze pass: what fills memory, and the first fix (H-M3 / H-M4, agent MEM2, 2026-10-03)

Question: the native `analyze` guest (the whole linked frontend, `an/analyze`, compiled by the seed backend; FRONT,
docs/selfhost-front-native-20261003.md) costs ~865 vectors and ~49 KB of heap per source byte on test programs, so the
4 Mi vector table held ~5 KB of source per process. Which structures dominate, what is the cheapest fix, and how large a
module fits one process afterwards?

Labels: **M** measured here, **E** estimate. Host load 80-270 during every run: times below are indications only.
Guest: build/front/e2e.sd.bin (FRONT's, pre-ADR-0363 KIR lineage), unchanged; one loader process per input.

## 1. Inputs that are compiler-sized (M)

`scripts/selfhost-wall/analyze-memory-inputs.py` makes the seed's own MANIFEST prefixes (00-ns, +01-mem, ... +20-names)
into closed one-namespace programs (a `seed-main` stub; every module only calls earlier ones), with three
meaning-preserving rewrites so that this frontend analyses them to the end: `vector-assoc!` -> `vector-assoc`,
`-9223372036854775808` -> `(- -9223372036854775807 1)` (the guest's reader TRAPS on the i64-min literal), and
`(def NAME int)` constants inlined (symbolic `case` constants are refused). The first 6 prefixes analyse to a full HIR.
Correctness above the old ceiling: against the host's `kotoba.sema/analyze` (e2e-record.cljs), prefix 00-ns..01-mem
(5.37 M handles) is `form/eq` OK; ..02-io and ..10-lex equal the host modulo one guest difference (duplicate members in
`:named-operations`); the larger HIRs cannot be compared textually (the guest's printer does not escape quotes).

## 2. What dominates (M, `KEXE_ARENA_CENSUS`)

New loader diagnostic (off by default): every minted vector and pair handle records its first 8 guest frames
(frame-pointer walk); the supervisor prints a census and writes per-handle sites. Function starts were recovered
exactly by compiling the guest's KIR with a 12-byte exported marker before each of its 3,585 functions (offsets
checked against all 60 real exports), and module indices were named by their string literals.

Prefix 00-ns..02-io (39.6 KB), no hash-consing: 7.88 M vector handles, 18.1 M pairs.

| vector handles | share |
|---|---:|
| constant tables re-materialised per call: `validate_expr` check-form's `build-index` (64-bucket index, `idx-add` copies it by `replace-nth` per entry), `namespace_defs/reserved-function-names`, `forbidden-heads`, `frontend_tables` | **62.2%** (60.0% of all are superseded conj prefixes) |
| empty vectors (the empty kids list of every atom Form) | **35.0%** |
| everything else: the program's Forms, env copies, lists of records, reader | **2.7%** |

| pairs | share |
|---|---:|
| the same constant tables, incl. `frontend_tables` re-parsing its EDN strings with `form/edn-form` on every lookup | **78.6%** |
| everything else | 21.4% |

Whole-table census: 62% of handles are a conj-chain prefix of a later handle, 35% empty, 3% final; distinct contents
33% (vector hash-consing could save at most ~67%, but the volume is not duplication, it is recomputation); distinct
pairs 63%. At 217 KB with hash-consing on: 73% conj prefixes, 22% empty, 33.9 M handles, 45.2 M of 45.8 M pairs
distinct. So the cost per byte is a large per-definition/per-lookup constant, not Form nodes: H-M4 (flat Forms) would
shrink the 2.7% / 21% part.

## 3. Options and the one taken

| option | cost | effect (measured or E) | taken |
|---|---|---|---|
| raise the vector table 4 Mi -> 64 Mi (ADR 0364) | constant 15 + regenerated region; +2.2 GiB address space, RSS unchanged (26.07 vs 26.08 MB on a small case) | the wall moves from ~28 KB to the pair arena (M below) | **yes** |
| canonical empty vector (already in KEXE_HASHCONS) | none | -18 to -35% handles | on in the driver (AM_HC=16) |
| vector hash-consing | O(n) hash per conj | <= 67% (distinct contents 33%), quadratic risk on conj chains | no |
| arena release at a pass boundary | needs a copy-out of the live result; words are untyped (int vs handle) | - | no |
| flat Forms (H-M4) | frontend rewrite | acts on the 2.7% / 21% | not needed now |
| build the frontend's constant tables once per analyze run | kotoba-sema change (ADR63's files) | E: ~4-5x fewer pairs, ~3x fewer handles | filed (CONTRACT-REQUESTS) |

## 4. The ladder after ADR 0364 (M; `analyze-memory.sh`, KEXE_HASHCONS=16, budgets 64 Mi handles / 64 Mi pairs)

| input | bytes | outcome | handles | pairs | heap B | per source byte: handles / pairs / heap B |
|---|---:|---|---:|---:|---:|---|
| 19 Embench ports | 783-56,795 | 18 HIR, aha-mont64 SIGILL (known) | 0.25-1.56 M | | 10-61 MB | |
| 00-ns | 13,620 | HIR | 1.69 M | 3.69 M | 97 MB | 124 / 271 / 7,153 |
| ..01-mem | 28,691 | HIR (was a vector-table trap at 4 Mi) | 4.30 M | 6.17 M | 198 MB | 150 / 215 / 6,913 |
| ..02-io | 39,572 | HIR | 6.43 M | 8.32 M | 282 MB | 162 / 210 / 7,135 |
| ..10-lex | 63,961 | HIR | 11.05 M | 14.12 M | 481 MB | 173 / 221 / 7,528 |
| ..11-read | 72,389 | HIR | 12.87 M | 16.66 M | 564 MB | 178 / 230 / 7,785 |
| ..12-kirread | 180,558 | HIR | 27.37 M | 36.90 M | 1.22 GB | 152 / 204 / 6,759 |
| **..20-names** | **216,680** | **HIR (largest that fits)** | 33.85 M (50%) | 45.81 M (68%) | 1.51 GB | **156 / 211 / 6,985** |
| ..20-names + 45% of 21-check's forms / ..21-check | 291,371 / 465,688 | pair arena exhausted (64 Mi) | | 67.1 M | | |

Without hash-consing the pair arena is exhausted already at 180 KB (..12-kirread: 31 M handles at the trap) and the
rates are 170-220 handles, 456-633 pairs and 11.7-13.7 KB heap per source byte (00-ns .. 11-read, all HIR).

Verdicts: **H-M3** -- the analyze ceiling moves from ~5 KB (test programs) / ~28 KB (real code) to **~217 KB of real
source per process measured** (between 217 KB and 291 KB the 64 Mi pair arena is the next wall, E), at ~7 KB heap per
source byte; the seed's largest module (21-check, 263 KB) is at the edge, the 787 KB unity is not one process.
**H-M4 refuted as the next step**: Forms are a minority of the volume (2.7% of handles, 21% of pairs); recomputed
constant tables are the majority, and removing them (kotoba-sema, E 3-5x) comes before any data-layout change.

## 5. Reproduce

```
scripts/selfhost-wall/analyze-memory.sh build/am            # HC on; AM_HC=0 off; AM_CENSUS=1 prints the census
KEXE_ARENA_CENSUS=<path> <loader> ...                       # per-handle sites: <path> (vectors), <path>.pairs
```

## 6. Open risks

- The guest is FRONT's pre-ADR-0363 KIR; the current kotoba-sema frontend (ADR63's port) may allocate differently.
- Inputs are rewritten (section 1); the rewrites change a handful of nodes, not the per-byte rates' order.
- HIR equality above 4 Mi is checked on 3 programs (one strict, two modulo the set-duplicate finding).
- The pair arena (64 Mi) is now the wall; raising it is a separate ADR and was deliberately not taken.
