# Process-per-pass driver with hash-consing: measured (H-M3, 2026-10-03)

Hypothesis H-M3 (docs/selfhost-coscientist.md): running each compiler pass as its own loader process, with the Form state
passed as serialized text, keeps every pass under the loader's arena limits when pair hash-consing (H-M2) is on.

Labels: **M** = measured in this run (host M1 Max, 32 GB; load average 30-170 during the runs, so CPU seconds are upper bounds
and are quoted only as A/B pairs run back to back). **E** = estimate.

**Verdict: confirmed for the desugar-class passes that run natively today, conditional on hash-consing; the binding limit is
the vector table (4,194,304 entries), not the pair arena.** The full frontend (`analyze`, `infer`) does not compile natively
yet, so the verdict does not cover its passes (section 5).

## 1. Falsification: desugar at 1x, 8x, 32x of a real corpus (M)

Workload: the native desugar guest (`ds_guest_w` of 2026-10-02, 976 functions, the Kotoba view of kotoba-sema's desugar half)
run by the C loader. Input: 2,183 `defn`/`defn-` forms from kotoba-sema `frontend.cljk` and `frontend/*.cljk`
(`hc-corpus-gen.py`); of them 527 (129 KB) are forms the guest desugars to a result (the rest refuse on `form/*` operations
and cost little), kept as the 1x corpus. 8x and 32x repeat it with the bound names renamed per copy (`hc-corpus-scale.py`),
so that copies do not share leaves for free (repeating verbatim gave the same marks within 1%). Loader budgets at their
maxima: 64 Mi pairs, 4 Mi vectors, 128 Mi vector items, 1 GiB string pool. Marks from `KEXE_ARENA_USE=1`.

| input | hash-consing | pairs (of 64 Mi) | vectors (of 4 Mi) | heap | peak RSS | result |
|---|---|---:|---:|---:|---:|---|
| 1x, 130 KB | off | 2.97 M | 401 k | 60 MB | 87 MB | ok |
| 1x | on (2^22, spike) | 0.40 M | 101 k | 14 MB | 54 MB | ok, output identical |
| 8x, 1.1 MB | off | 23.8 M (35%) | 3.21 M (76%) | 485 MB | 545 MB | ok |
| 8x | on | 3.14 M (4.7%) | 0.81 M (19%) | 116 MB | 162 MB | ok, output identical |
| 32x, 4.6 MB | off | 31.1 M (trap) | 4.19 M (trap) | 636 MB | 708 MB | **trap: vector table exhausted** |
| 32x | on | 12.5 M (19%) | 3.23 M (77%) | 468 MB | 367 MB | ok |

Hash-consing cuts the heap per source byte from about 438 B (8x, off) to about 100 B (32x, on). The H-M3 projection (0.5 GB,
14.5 M pairs per pass) holds: one pass over 1.4x the reach set's 3.3 MB of Kotoba code needs 0.42-0.48 GB and 12.5-14.6 M pairs.

## 2. The driver (M)

`scripts/selfhost-wall/pass-driver.sh [-w dir] [-l loader] <pass.bin> <input> <pass>...` runs each pass as a loader process
(`KEXE_HASHCONS` on by default at 2^16, `KEXE_ARENA_USE=1`). The input of a pass is `!<pass>` then the previous pass's output
file: one serialized Form per line (compact EDN text), so a process exit reclaims every arena. Refused forms
(`ERR`/`UNPORTED` lines) are counted and not passed on. It prints, per pass, bytes in and out, pairs, vectors, heap, peak RSS,
user CPU and the share of the pair and vector limits, and stops at the first trap.

`scripts/selfhost-wall/ds-pass-build.sh <dir>` builds the pass image (BOOTSTRAP-REFERENCE: stage-0 compile, 31 s CPU; the image
is 911,487 bytes, reproducible byte for byte). Passes in `ds-pass-tail.cljk`: `!read` (parse and print), `!desugar` (the
`desugar-expr` of a ds-diff case, one form per line), `!count` (node count), `!all` (read, desugar, desugar, count in ONE
process: the single-process baseline). The chain used below: read, desugar, desugar (a second pass over the first's output,
which is a distinct heavy workload), count.

Per-pass peaks, hash-consing on (2^16), 8x and 32x corpus, one process per pass (M):

| pass | 8x: in KB | pairs | vectors | heap MB | RSS MB | 32x: in KB | pairs | vectors | heap MB | RSS MB |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| read | 905 | 1.24 M | 142 k | 40 | 63 | 3,762 | 4.93 M | 567 k | 161 | 189 |
| desugar | 907 | 3.14 M | 807 k | 105 | 134 | 3,771 | 12.57 M | 3.23 M | 423 | 472 |
| desugar (2nd) | 1,509 | 3.64 M | 857 k | 118 | 147 | 6,171 | 14.56 M | 3.43 M | 478 | 531 |
| count | 1,507 | 1.35 M | 214 k | 28 | 52 | 6,170 | 5.38 M | 855 k | 114 | 146 |
| **all four, one process** | 905 | 9.36 M | 2.02 M | 287 | 328 | 3,762 | **trap: vector table** | | | |

At 32x the single process traps and the four processes each fit: the largest pass uses 82% of the vector table, 22% of the
pairs, 0.48 GB of heap. With hash-consing off the 32x chain already traps in its second process (`desugar`). So process-per-pass
and hash-consing are both needed; neither alone reaches 32x. The chain's final output is byte-identical with hash-consing on
and off (8x and 1x). The single-process baseline is not byte-compared: it feeds `ERR` lines to the next pass, which the driver
drops.

## 3. Hardening the hash-consing in `tools/kexe_loader.c` (M)

Audit (the spike's claims, re-checked in the source):

- **Collision safety.** A table entry is used only when the pair it names holds exactly the same two words (a full compare, not
  a hash compare), and its handle is within `pair_used`. A hash, tag or index collision therefore costs a missed share, never a
  wrong pair. Stale entries from an arena-scope release are rejected by the same two tests (a released index is either above
  `pair_used`, or reallocated, in which case equal words denote the same value).
- **Immutability.** Every store into `pairs[]` is an allocation (4 sites: `checked_pair_new`, the host-pair, string-import and
  record-import helpers); nothing mutates an existing pair.
- **Sensitivity.** `guests/hashcons_scope.kotoba` builds strings in 50,000 `arena-scope`s that reuse the same pair indexes and
  string-pool offsets. It answers the same checksum with sharing off and at 2^12, 2^16, 2^22, 2^28, and under ASan+UBSan. With
  the pair compare and the `pair_used` test removed from the loader the same probe traps (`SIGILL`), so the test sees the bug.
- **Silent off.** A table that could not be mapped used to leave sharing silently off; it is now a fatal error.

CPU cost, 8x desugar, one pass, same host back to back, user seconds (M, min of 3; off = 0.33-0.34):

| table | pairs | user s | vs off |
|---|---:|---:|---:|
| off | 23.47 M | 0.34 | |
| spike: direct-mapped 2^22 x 4 B (16 MiB) | 3.04 M | 0.58-0.61 | **+75%** |
| direct-mapped 2^16 | 3.23 M | 0.45 | +32% |
| **4-way set-associative with 32-bit tags, 2^16 entries x 8 B (512 KiB), cheaper hash** (new default) | 3.14 M | 0.44-0.47 | **+32%** |
| same, 2^12 entries | 3.81 M | 0.44-0.47 | +32% |
| same, 2^22 entries | 3.02 M | 0.55-0.57 | +65% |

At 32x desugar: 2^22 spike loader 12.12 M pairs, 2.56 s; new default 12.55 M pairs (+3.6%), 1.76 s (-31% CPU). The cost is the
cache footprint of the table, not the hash: reuse is local (the pairs that hit are recent), so a table that fits in L2 finds
all but 4% of what a 16 MiB table finds. The floor of about +30% is the hash, the probe and the exact compare per `pair_new`.
Not tried: skipping sharing for string-view pairs, which would need a type hint at the call.

Loader/seed gates with the hardened loader and `KEXE_HASHCONS=16` in the environment (private copy of the seed bins, R3 seeds
e1b2ecd5 and 495d6652): G1 19/19 for both seeds, G5 PASS. The R3 seed compiling its own unity under the hash-consing loader
gives the identical container (sha256 7ab691e4...) with half the pairs (1.34 M to 0.67 M).

## 4. Where it stops (ceilings)

- **Vector table.** The binding limit at 32x is `KEXE_VECTOR_MAX` = 4 Mi entries: the desugar pass uses 0.86 vector per input
  byte, so one pass tops out near 4.9 MB of input, 1.5x the reach set's 3.3 MB. That is too thin for infer-class passes whose
  per-byte cost is unknown. Two ways out, neither done: raise `KEXE_VECTOR_MAX` (address space only, 16 B per entry, a decision
  in `tools/kexe_loader_decisions.kotoba`), or run per (module, pass) (memory plan row 5), which divides it by the module count.
- **Time.** About 0.5 us per input byte per desugar pass on a quiet host (E from 0.46 s at 0.9 MB): 4.6 MB takes 2 s per pass.

## 5. What is not covered

- `analyze`, `infer`, `expand`, `validate` are not passes of a native chain yet: compiling the e2e guest
  (`guests/e2e.cljk`, whole `analyze`) with the stable stage-0 stops with `E subset: expression type mismatch ... in
  expand.cljk line 149` after 10 s, so its memory is unmeasured. `analyze` also runs the passes interleaved per definition
  over one environment, so a per-pass split of it needs the state (`:fe/env`, `:ie/ctx`) to be serialized too. The `!read` and
  `!desugar` passes here carry forms, not that environment.
- The serialization is the guest's `ds-print` (strings are not escaped), enough for the desugar workload but not a general Form
  codec; a faithful one is a pre-condition for chaining `infer`.
- The corpus is the desugar-able 24% of the frontend's own defns; its shape is real but it is not the whole reach set.

## Reproduce

```sh
scripts/selfhost-wall/ds-pass-build.sh build/hc                        # stage-0 compile -> ds_pass.{bin,offset}
python3 scripts/selfhost-wall/hc-corpus-gen.py 100000 <frontend files> > real.txt   # then keep the lines the guest answers DIFF to
python3 scripts/selfhost-wall/hc-corpus-scale.py 32 ok.txt | sed -E 's/^\[\{f #\{1 2\}\} false (.*) nil \[\] \{\} \[\] #\{\} false false\]$/\1/' > forms32.txt
scripts/selfhost-wall/pass-driver.sh build/hc/ds_pass.bin forms32.txt read desugar desugar count
KEXE_HASHCONS=0 scripts/selfhost-wall/pass-driver.sh ...               # the same without sharing
scripts/selfhost-wall/hashcons-test.sh build/hc/ds_pass.bin forms.txt desugar   # loader tests
```
