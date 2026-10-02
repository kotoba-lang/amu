# Memory plan for the self-build on the Kotoba route: five ideas, measured (2026-10-02)

The owner proposed five ways to cut the memory of the big compiler's Kotoba route (the Form-based port):

1. hash-consing (shared immutable Forms);
2. a flat representation;
3. persistent structures for large records;
4. definition CIDs for dedup;
5. per-pass region release (process per pass).

The starting point:

- ADR 0089 (kotoba-native): 28 KB of KIR as Forms takes 3.4M vectors and 16M pairs.
- `docs/selfhost-native-memory-20261002.md` (the memory study): desugar keeps 616 B of heap per source byte. That
  extrapolates to 16-30 GB for a self-build in one process, over `KEXE_PAIR_MAX`.
- `docs/selfhost-seed-kirread-20261002.md`: the seed's flat arena uses 27.6 B per KIR byte for its whole pipeline.

This document measures each idea on real data, projects the self-build peak under each combination and gives an
order of work. It also reports the spike for the cheapest high-yield idea. That idea turned out to be loader-level
pair hash-consing, not a kotoba.form intern table.

**Short answer.** About 86% of desugar's pair allocations are byte-identical to a pair that already exists. Hash-
consing pairs in the loader (`KEXE_HASHCONS`, 76 lines of C, off by default) plus one shared empty vector has these
effects on the desugar guest:

- desugar's slope drops from 616 to **148 B of heap per source byte** (-76%);
- pairs per byte drop from 30.6 to **4.4** (-86%);
- the guest's output is byte-identical;
- the guest takes about 1.75x the CPU.

Combined with process-per-pass (idea 5), one pass of the whole compiler needs about **0.5 GB and 14.5M pairs**,
inside today's `KEXE_PAIR_MAX`. Today it needs 2.0 GB and 100M pairs. Recommended order:

1. hash-consing (done as a spike; make it the self-build default);
2. process-per-pass (2-4 days);
3. the seed backend through compile-kir (design 5.2), which removes the ADR 0089 KIR-as-Forms cost;
4. a cheap record-assoc lowering fix;
5. CIDs, for incremental builds only;
6. a flat representation, last and only if a measured pass needs it.

Labels used below: **M** = measured in this run on this host (M1 Max, 32 GB, load average 40-150). **E** = estimated
(the basis is given). **S** = from the cited study.

## 1. Hash-consing: how much of a Form tree is repeated

### 1a. Census of the real trees (M)

`scripts/selfhost-wall/form-census.py` reads each file of the minimal self-build reach set the way the Kotoba route
sees it: reader conditionals take the `:kotoba` branch, metadata is dropped and reader macros become lists. It builds
kotoba.form-shaped trees. As a cross-check, the native guest `guests/form_count.cljk` reads the same trees with
`form/edn-form` and counts exactly the same **467,058** nodes.

| reach set (`/private/tmp/reach-minimal.txt`, 126 files, 7.11 MB of text) | Kotoba view | host view (`:default`) |
|---|---:|---:|
| nodes | **467,058** | 321,046 |
| leaves (symbols, keywords, ints, strings, nil, bools) | 321,136 (68.8%) | 219,257 (68.3%) |
| interior nodes / kid edges | 145,922 / 457,092 | 101,789 / 313,839 |
| distinct leaves, summed per module / whole set | 40,661 / **19,737** | 40,421 / 18,632 |
| nodes with leaves shared, per module / whole set | 186,583 (40.0%) / 165,659 (35.5%) | 142,210 / 120,421 |
| nodes with full hash-consing (distinct subtrees), per module / whole set | 132,726 (28.4%) / **98,255 (21.0%)** | 115,361 / 85,469 |
| top-level `def`/`defn`, of them byte-identical to another one | 8,688 / 910 (10.5%) | 4,494 / 66 |

The largest modules:

| module | text | nodes | nodes, leaves shared | nodes, hash-consed |
|---|---:|---:|---:|---:|
| `frontend/desugar` | 601 KB | 40,341 | 14,380 (35.6%) | 8,731 (21.6%) |
| `native/machine_ir` | 804 KB | 40,260 | 15,060 | 10,184 |
| `frontend/infer` | 432 KB | 33,993 | 11,483 | 6,912 |

The text averages 15.2 bytes per node (docstrings, comments and long names). **A source tree shrinks 2.5x with leaf
sharing and 3.5-4.8x with full hash-consing.**

The input tree is not where the heap goes, though. At about 170 B per node (section 2), the whole reach set's trees
take 79 MB (E). Desugar alone keeps 616 B per source byte (S), that is about 9 KB per input node: **pass state and
rebuilt output, not the input tree, dominate.** Section 1b measures sharing on all of it.

### 1b. The spike: pair hash-consing in the loader (M)

**Where the sharing can be done.**

- **In kotoba.form (owner's guess).** A shared `nil-form` / `symbol-form` instance needs a value that lives across
  calls. Kotoba has no mutable global, and top-level `def`s are folded at analysis time (core-rewrite plan, "quoted
  data tables"). An intern table would have to be threaded through every constructor call in every port.
- **In the loader (chosen).** A Form is a 7-field record, and a record is a declaration-order **pair chain**:
  `record-new` lowers to `(pair f0 (pair f1 ... (pair f6 0)))` in `kotoba-native` `normalize-scalar-record-boundary`.
  Pairs are immutable: no context slot writes one. Their identity is not observable apart from the two words. So
  `pair_new(a, b)` may answer an existing handle holding exactly (a, b).

The change, in `tools/kexe_loader.c`:

- `KEXE_HASHCONS=1` turns on a lossy direct-mapped table: 2^22 slots, 16 MiB, or 2^N with `KEXE_HASHCONS=N`. A slot
  is believed only if the pair it names is below `pair_used` and holds the same words, so arena-scope releases need
  no invalidation.
- `vector_new_empty` answers one empty vector made before the guest starts. Every leaf's kids list and every
  `bytes-empty` was a new 16 B table entry.
- The first conj onto any empty slice appends at the arena top.

The effects:

- identical leaves share their whole chain;
- records that agree on trailing fields share that suffix;
- `record-assoc` re-shares every field after the changed one (idea 3, for free);
- equal string views (`""` literals) share one pair.

**Correctness (M).** Every A/B run produced byte-identical guest output (`scripts/selfhost-wall/hashcons-ab.sh`):

- the desugar guest `ds_guest_w` (976 functions) on 720 test cases, 720x8, and 55 real defn bodies (the outputs
  include the full printed desugared forms);
- the form_count guest on the 3.0 MB reach-set EDN;
- the seed compiling its own unity under the hash-consing loader gives the published seed-2 container (sha256
  `b1596f6f...`), with half the pairs;
- seed gate G1 passes 19/19 (Embench ports compiled by the seed and run under the hash-consing loader).

Unset, the loader behaves exactly as before. The existing differentials (ds-diff, the seed gates) are unaffected by
construction.

**Arena high-water marks, off -> on (M, `KEXE_ARENA_USE=1`):**

| workload | pairs | vectors | heap | peak RSS | user CPU |
|---|---|---|---|---|---|
| desugar, real code: slope per source byte (55 single-case runs, least squares, as in the study) | 30.6 -> **4.4** | 4.04 -> 1.02 | **616 -> 148 B** | | |
| desugar, real code: fixed cost per run | 15.5 k -> 6.0 k | 3.2 k -> 1.0 k | 317 -> 129 KB | | |
| desugar, 720 test cases (1x, 235 KB) | 3.51 M -> 0.47 M | 496 k -> 118 k | 65.9 -> 11.3 MB | 88 -> 46 MB | 0.05 -> 0.08 s |
| desugar, 720 cases x8 (1.88 MB) | 27.9 M -> 3.66 M | 3.95 M -> 0.93 M | **526 -> 88 MB (-83%)** | 594 -> 136 MB | 0.38 -> 0.67 s |
| reader only: `form/edn-form` over the reach set (467 k nodes) | 7.31 M -> 2.62 M | 1.50 M -> 0.46 M | 151 -> 59 MB (-61%) | 170 -> 86 MB | 0.09 -> 0.23 s |

Notes on the table:

- **Table size.** Of 28 M `pair_new` calls in the x8 run, 24.3 M hit. A 2^20-slot table gives 3.71 M pairs, 2^26
  gives 3.62 M: the reuse is local, so the table size hardly matters.
- **Vector table.** The x8 baseline used 3.95 M of the 4,194,304 entries of `KEXE_VECTOR_MAX`, so at about 9x it
  would trap on the vector table before the pair arena. Hash-consing moves that wall 4x out.
- **What remains of the 148 B/B (M).** Pairs 70 B, vector entries 16 B, vector items 11 B, string pool 51 B. Part of
  the string pool is the harness printing every result.
- **Cost.** About 10 ns per `pair_new` (a table probe and one random pair read), which is +75% CPU on this
  pair-bound guest. That is about +1 s per desugar pass of the whole compiler (100 M calls), against the GBs it
  saves.

## 2. Flat representation: bytes per node

Words per Form node in the loader's arenas today (from the lowering, checked against the census run):

- **Record and leaf.** A record is 7 pairs of 16 B, plus a 1-byte UTF-8 flag per pair. A leaf adds its `s` pair (a
  substring view, or the `""` literal re-made at each evaluation) and two empty vectors (`no-forms`, `bytes-empty`).
- **Kids list.** An interior node adds a list handle and 8 B per kid. Building it adds one dead 16 B handle per
  `typed-list-conj`.

| layout | bytes per node | basis |
|---|---:|---|
| today, the tree as kept (leaf 8 pairs + 2 vector entries = 160 B; interior the same + 8 B per kid) | **about 170** (+16 dead per kid while building) | E (lowering) |
| today, `edn-form` reading the reach set (15.7 pairs, 3.2 vector entries, 1.6 items per node; includes the reader's `:form/rd` results and tokens) | **323** | M |
| pair hash-consing, the same read | **126** | M |
| flat record (one vector entry + 7 words; the study's "record as a flat vector", an ABI bump) | about 120 | E |
| struct of arrays: tag/value, kids offset, kids count, span = 4 words, plus 8 B per edge | **40** | E |
| struct of arrays with leaves as immediate edge words (symbol/keyword ids, small ints) | **17.8** | E, from the census counts |

Flat saves 4-9x on the tree, and the seed proves the style: 27.6 B per KIR byte for its whole pipeline. But kotoba.form
is not an opaque API. `kids-of` returns a `[:list [:ref :form/r]]` that ports index with `typed-list-nth` directly
(the desugar guest alone has 33 `kids-of` and 81 `typed-list-nth` sites). So a flat Form means touching every port, not one module
(section 6). Hash-consing already gets the input-tree part, and the pass churn is what a flat tree does not remove.

## 3. Persistent structures: what a record update copies

A `record-assoc` on a pair chain rebuilds all k pairs today. The lowering rebuilds the whole chain, reading every
other field back. Path copying shares the chain after the changed field, so it copies index+1 pairs. Static sites in
the two large pass states (M, from the sources; field order as declared):

| record | fields | full copy per update | prefix copy, mean over `record-assoc` sites | hottest fields (index: sites) |
|---|---:|---:|---:|---|
| `:fe/env` (desugar guest) | 24 | 384 B | 182 B | types (5): 3; counter (0): 2; contracts (23): 2; 15 more, 1 site each |
| `:ie/ctx` (infer) | 14 | 224 B | 85 B | known (10): 4; recorded (7): 2; final, tail, names, throws: 1 each |

Path copying for the suffix falls out of section 1b's hash-consing: the rebuilt suffix pairs are hits. Two cheap
additions remain. Both are E.

- **Lowering.** Lower `record-assoc` to rebuild only the prefix, with the tail taken as `pair-second^(i+1)`. That is
  `kotoba-native` `normalize-scalar-record-boundary`, both arms. It saves the hash probes and works with hash-consing
  off.
- **Field order.** Put the hot fields first. Because record types compare structurally, every module that declares
  `:fe/env` must change its order together.

Form maps inside the env (`:lexical`, `:types`, `:helpers`) are rebuilt whole by `assoc-form`, O(entries) per
update. A persistent map behind `assoc-form` / `form-get` would fix that. But in desugar, vector entries and items
together are only 27 of the remaining 148 B/B (M), so a persistent map has a low measured yield there. Infer's
substitution maps are unmeasured, because infer does not run natively yet.

## 4. Definition CIDs: how much is unchanged

ADR 0300 CIDs are computed over normalized KIR. That is after reader, expand, desugar, infer and lower, so a CID
cannot by itself stop a definition from being re-expanded. To skip the frontend, a definition needs a source-level
pre-key (its read form plus the CIDs and signatures it depends on) that maps to the cached CID and KIR.

What such a cache could reuse (M, `scripts/selfhost-wall/def-churn.py`; kotoba-sema `frontend.cljk` +
`frontend/*.cljk`, the last 60 commits, 2026-09-30 to 10-02, about 2,900-3,600 top-level definitions):

- between consecutive commits, the read form is unchanged for a median **99.2%** of definitions (p10 87%, mean 94.9%);
- across all 59 commits, 0% of definitions are unchanged, because of one wholesale rewrite commit;
- byte-identical definitions across modules: **10.5%** of the reach set's top-level forms (910 of 8,688, Kotoba view).

What it means for memory: none of this lowers the peak of a cold self-build.

- With process-per-module, the peak is the largest changed module.
- A bootstrap stage N -> N+1 must recompile everything, or it does not prove the fixed point.
- CIDs cut the total work of incremental builds (about 99% reuse per commit) and dedup about 10% across modules.

They belong to the build cache (S4/S5), not to milestone 1's memory budget.

## 5. Per-pass release: per-pass peak against the total

Peak inputs (S unless marked):

- the reach set's Kotoba view is about 3.3 MB of code;
- the largest module is 507 KB of code (`machine_ir`); desugar is 417 KB;
- the pipeline is 8-15 desugar-equivalent passes;
- desugar costs 616 B/B (M: reproduced exactly in this run), or 148 B/B with hash-consing (M);
- by the census, the largest module is 8.6% of the nodes (M), or 15% of the code bytes (S).

The arenas only grow, so one process keeps the sum of its passes. A process per pass keeps one pass. A process per
(module, pass) keeps one module's pass. That is the whole of idea 5. Its cost is the text round trips between passes:
the study gives 2-4 days for the driver, with the MIR and machine-IR text formats as the risk.

## 6. Projected peak of a self-build of the big compiler

All rows are E built from the measured slopes above. "Hash-consing" applies desugar's 0.24 ratio to every pass. The
reader alone gives 0.39, so the hash-consing figures can be up to 1.6x higher for passes shaped like the reader.

| combination | peak heap | pairs in the peak | fits? |
|---|---:|---:|---|
| today: one process, all passes | 16-30 GB | 0.8-1.5 G | no (S) |
| + hash-consing, one process | 3.9-7.3 GB | 116-218 M | heap yes; pairs over `KEXE_PAIR_MAX` 64 M; no margin |
| process per pass | 2.0 GB | 100 M | only with `KEXE_PAIR_MAX` raised |
| **process per pass + hash-consing** | **0.49 GB** (up to 0.8) | **14.5 M** | **yes, with today's maxima** |
| process per (module, pass) | 312 MB | 15.5 M | yes |
| process per (module, pass) + hash-consing | **75 MB** | 2.2 M | yes |
| process per pass + hash-consing + seed backend (design 5.2: big frontend -> KIR text -> `compile-kir`) | 0.38 GB per frontend pass; the backend at 27.6 B per KIR byte (M, kirread doc) | 11 M | yes; machine_ir, mir, gmir and codegen (23% of the reach set's nodes, M) leave the self-build |
| flat Forms (all passes rewritten seed-style, about 20-60 B/B per pass) | about 0.1-0.2 GB per pass | none (arenas) | yes; weeks of work |

The compile-kir route and the machine_ir/mir question:

- **Backend: yes, moot.** The seed backend reads stage-0's KIR text and compiles all 19 Embench ports at 27.6 B per
  KIR byte (kirread doc). So the backend half of the problem goes away: ADR 0089's 16M pairs per 28 KB of KIR are
  machine_ir/mir state on Forms. Those modules also leave the self-build's own reach set, about 23% of its nodes,
  with the largest single module (`machine_ir`).
- **What remains.** The frontend: reader, expand, desugar, validate, infer, analyze/HIR, and KIR lower plus a KIR
  printer. That is about 5-8 desugar-equivalent passes, and their state: `:fe/env`, `:ie/ctx`, the lexical, type and
  substitution maps, and rebuilt output trees.
- **What that costs.** With hash-consing and a process per pass this is about 0.4 GB per pass (E). The measured
  numbers say no flat rewrite is needed for milestone 1. Infer and analyze must be re-measured once they run
  natively: their per-byte cost is the main unknown in every row above.

## 7. Recommendation and effort

| # | step | where | effort | yield |
|---|---|---|---|---|
| 1 | **Pair hash-consing + canonical empty vector** (spike landed, off by default). Turn it on in the self-build driver's processes, add a loader unit test, and record the ABI-neutral decision in an ADR | `tools/kexe_loader.c` (done); `tools/kexe_loader_decisions.kotoba` untouched (no decision changes) | 0.5-1 day left | -76% heap / -86% pairs on desugar (M) |
| 2 | **Process per pass**, text at the boundaries (the memory study's option B), `KEXE_PAIR_MAX` raised for margin | driver + round trips (amu `src`, `:process/spawn`) | 2-4 days (S) | peak = one pass: 0.5 GB with step 1 (E) |
| 3 | **Seed backend via compile-kir** for the self-built compiler (design 5.2 step 2): the big frontend prints KIR, `compile-kir` compiles it | `seed/12-kirread` (exists) + a KIR printer in the frontend | already the plan; the reader exists | removes the KIR-as-Forms backend cost (ADR 0089) and 23% of the reach set |
| 4 | `record-assoc` rebuilds only the prefix; hot fields first in `:fe/env` / `:ie/ctx` | `kotoba-native` machine_ir (both arms); the port headers together | 0.5 day + 0.5 day | saves the probes step 1 spends; 2x (prefix only) to about 6x (hot fields first) fewer pairs per env update (E) |
| 5 | Process per (module, pass), only if a single pass over the whole program exceeds about 2 GB once infer runs natively | driver | 1-2 days on top of 2 | peak = largest module's pass (75 MB, E) |
| 6 | Source-level definition key -> CID -> cached KIR | `kir/definition_identity` + the compile cache (ADR 0300) | 1-2 weeks | incremental builds reuse about 99% per commit; nothing for the cold peak |
| 7 | Flat Forms (struct of arrays, immediate leaves) | `kotoba-hir` `form.cljk` plus every port that indexes `kids-of` | 2-4 weeks | 4-9x on trees (E); do it only if a measured pass needs it after 1-5 |

Not recommended now: a kotoba.form intern table (no global state in Kotoba, and step 1 does it underneath with no
port change), a collector (the study's 4-10 weeks), and persistent Form maps (low measured yield in desugar).

## Reproduce

```sh
# the census (Kotoba view; PREFER=:default,:clj,:cljs for the host view), and the EDN the guest re-reads
python3 scripts/selfhost-wall/form-census.py --edn reach.edn @/private/tmp/reach-minimal.txt > reach.json
# A/B of the loader change on any native guest: arena marks off/on and output identity
scripts/selfhost-wall/hashcons-ab.sh <cache>/<key>-ds_guest_w.native.bin cases.txt
scripts/selfhost-wall/guest-run.sh --native-only scripts/selfhost-wall/guests/form_count.cljk fc-run < reach.edn
# definition churn between commits
python3 scripts/selfhost-wall/def-churn.py <kotoba-sema> src/kotoba/compiler/frontend.cljk,... 60
```

Inputs used here:

- the 720 test cases and 55 real-code cases captured from the memory study's runs (the ds_guest_w build of
  2026-10-02 01:25);
- `WALL_CP=/private/tmp/wall-cp-14.txt`. The main kotoba-sema checkout did not load under nbb during this run
  (`Unable to resolve symbol: definition-heads`), so ds-diff's host side could not be re-run. The A/B therefore
  compares the guest's own outputs off and on, which for a loader change is the stronger check.
