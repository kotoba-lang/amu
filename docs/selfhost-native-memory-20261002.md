# Native heap for a self-build: measured high-water marks and the reclamation question (2026-10-02)

Item C3 of `docs/selfhost-efficiency-analysis-20261002.md`. The question: can the self-built compiler (a `.kexe` run
by `tools/kexe_loader.c`, aarch64-macos) compile its own sources with the loader's append-only arenas, that is with
no reclamation? The analysis estimated reclamation might add 3-7 days to the critical path.

**Short answer: not in one process.** On real code the desugar pass alone keeps about 0.6 KB of heap per byte of
source. Scaled to the compiler's own code, that is about 2 GB and about 100 M pairs for one pass, over the pair
arena's 64 M address-space maximum. The whole pipeline is an estimated 16-30 GB, against a 32 GB host. The cheap
way out is to bound each process rather than collect garbage: run each pass (or each module) in its own loader
process, with its input and output as text, and let the process exit be the reclamation. That is about 2-4 days,
below the analysis's 3-7. A collector is not needed for milestone 1.

## How it was measured

- Instrument: `KEXE_ARENA_USE=1` (ADR 0361) makes the loader's supervisor print the high-water mark of each arena
  after the guest exits: pairs (16 B each), string pool bytes, vector table entries (16 B), vector item words (8 B),
  and their sum (`:heap-bytes`). Peak RSS comes from `/usr/bin/time -l`.
- Workload: the desugar differential's guest `ds_guest_w` (976 functions, the Kotoba view of kotoba-sema's desugar
  half), compiled to aarch64 by amu and run natively. It agrees with the host on 720/720 cases (ds-diff, this run).
  The aggregate-list work had landed (the guest runs natively), so this is the representative compile step that
  can be run today.
- Inputs, all through `scripts/selfhost-wall/guest-run.sh` native mode with a capturing loader wrapper:
  (1) the differential corpus, 720 forms from kotoba-sema's tests (235 KB of case lines, 22.4 KB of forms);
  (2) **real code**: the 55 `defn` bodies of kotoba-lang `lang/compat/kotoba/{string,edn,walk}.kotoba` (8.2 KB of
  code), one case per run, so the per-byte slope is fitted, not assumed.
- Host: 32 GB, 10 cores, load average 120-130 during the runs (times are upper bounds).

## Results

### The desugar pass, per byte of source

| input | fixed cost per run | slope (least squares over single-case runs) |
|---|---|---|
| real code (55 bodies, median 136 B, max 609 B) | 15.5 k pairs, 317 KB heap | **30.6 pairs and 616 B of heap per source byte** |
| test corpus (720 forms, median 22 B) | 12.9 k pairs, 262 KB heap | 148 pairs, 3.35 KB per byte (the test forms are expansion-heavy: `doseq` over literals unrolls) |

The pair heap is 75-85% of the heap: a Form record of k fields is k pairs. The vector table is the next 10%.
The 15 k-pair fixed cost is the per-run environment (contract tables, name maps).

### Scaling and the builders (ADR 0361)

The same 720-case corpus concatenated 1/2/4/8 times (0.23-1.88 MB of input, one run):

| x | pairs | string pool without regions -> with | heap (with) | peak RSS (with) | time |
|---|---|---|---|---|---|
| 1 | 3.5 M | 3.3 MB -> 0.58 MB | 66 MB | 88 MB | 0.11 s |
| 2 | 7.0 M | 10.9 MB -> 1.15 MB | 132 MB | 163 MB | 0.25 s |
| 4 | 14.0 M | 39.2 MB -> 2.30 MB | 263 MB | 308 MB | 0.66 s |
| 8 | 27.9 M | 148.3 MB -> 4.60 MB | 526 MB | 594 MB | 1.37 s |

Pairs and vectors are linear in input. The string pool was quadratic (the output accumulator was re-copied on every
append once anything was interned in between) and is linear with growth regions. Before regions, the string pool
alone would pass the pair heap at about 30x this input.

### Extrapolation to the self-build

- The minimal reach set (`/private/tmp/reach-minimal.txt`, 126 files) is 7.09 MB of text, or 4.87 MB with comments
  stripped and whitespace collapsed. That count includes host arms; the Kotoba view the self-built compiler reads is
  taken as 3-3.5 MB. Largest single modules (code bytes): `native/machine_ir` 507 KB, `frontend/desugar` 417 KB,
  `frontend/infer` 331 KB.
- Desugar alone: 3.3 MB x 616 B/B = **about 2.0 GB** of heap, 3.3 MB x 30.6 = **about 100 M pairs**. That is over
  `KEXE_PAIR_MAX` (64 M pairs, 1 GiB of address space). The per-run `KEXE_PAIRS` budget is also far below it.
- Pipeline: reader, expand, desugar, validate, infer, analyze/HIR, KIR lower, MIR, machine IR, aarch64 encoding,
  package. Most passes rebuild their input, and ADR 0360 measured 1-5 lowered nodes per expression node, so the
  later IRs are larger than the source. Counting 8-15 desugar-equivalents gives **16-30 GB with no reclamation**,
  all of it live to the end of the process, because the arenas only grow.
- Not covered: the passes that do not run natively yet (infer, analyze, KIR, MIR, machine IR on the Kotoba route).
  Their per-byte cost is assumed to be of desugar's order. Desugar was measured on small bodies (under 610 B); a
  pass that is superlinear in a function's size would make this worse.

## Feasibility

| option | peak memory | work | verdict |
|---|---|---|---|
| A. one process, no reclamation (today) | 16-30 GB, more than 64 M pairs per pass | raise `KEXE_PAIR_MAX` / `KEXE_VECTOR_MAX` (address space) | **not feasible** on a 32 GB host; a 10-20% error in the estimate decides it |
| B. one loader process per pass (or per module), each pass reads the previous pass's output as text from a file and writes its own; process exit reclaims | about 2-4 GB per pass (the largest pass), about 0.5 GB per module for the largest module | serialized forms exist for source (linked text), HIR (EDN), KIR (the kexe's KIR-as-EDN). Missing: MIR/machine-IR text round trips, a driver that sequences processes (`:process/spawn` wire 20 exists), raising `KEXE_PAIR_MAX` to 256 M (address space) | **feasible; about 2-4 days.** The driver is small. The round trips are the risk, and they are testable as differentials |
| C. `arena-scope` (ABI v6) inside one process | per definition | the body's result must be a scalar, so per-definition results must leave through a capability (a file append) and be read back. That is B at a finer grain, inside the process | useful later, inside B's passes (per definition of the largest module); not a substitute |
| D. a collector (mark-compact over pairs/vectors) | live set only | 4-10 weeks with a verifier twin (the analysis's estimate for a dynamic runtime) | **reject for milestone 1** |

Cheap multipliers that help any option:

- A record as a flat vector (one table entry plus k words, 16 + 8k B) instead of a pair chain (16k B) roughly halves
  the pair heap of Form-heavy passes. That is a native-lowering change (`record-new` / `record-get` in
  `kotoba.native.machine-ir`) with an ABI version bump.
- `pair_validated` (the UTF-8 validity flag of a string pair) costs 1 B for every pair on top of the 16 B.

## Recommendation

Plan the self-build driver as a sequence of loader processes from the start (option B). Put the pass boundary where
a text format already exists (linked source, then HIR, then KIR). Raise the pair and vector maxima, which are address
space and not memory, in the same change. Re-measure with `KEXE_ARENA_USE` on the first pass that runs on the whole
linked compiler, and refit the 616 B/B slope on the largest module (`machine_ir`) once it runs natively.

## Reproduce

```sh
# arena high-water marks of any native guest run
KEXE_ARENA_USE=1 scripts/selfhost-wall/guest-run.sh --native-only <guest.cljk> <entry> < input
# A/B of the growth regions
KEXE_NO_GROWTH_REGIONS=1 KEXE_ARENA_USE=1 scripts/selfhost-wall/guest-run.sh ...
# the builder benchmarks (ADR 0361)
head -c 1000000 /dev/zero | tr '\0' a | scripts/selfhost-wall/guest-run.sh --native-only scripts/selfhost-wall/guests/list_builder.cljk run
```
