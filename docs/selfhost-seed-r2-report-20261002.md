# Seed R2: performance rung (2026-10-02)

**Label: seed R2, a selfhost-built subset compiler. NOT an official Embench score.** No new language: the R1 front end,
SIR and lowering are unchanged; only the code generator `seed/41-a64gen.kotoba` (399 -> 932 lines) changed.

## What changed (41-a64gen)

| R2 item (design 1.4) | what was built |
| --- | --- |
| inline vector/pair ops through the ABI v9 pointers (288-328) | `vector-at`, `vector-assoc!`, `vector-count`, `pair-first`, `pair-second` (= `string-length`) are emitted in line: the C twin's handle check `(h-1) < *used` and index check, failure = `udf #0` (SIGILL, as `raise(SIGILL)` and stage-0's machine_ir inline sequence). Vector literals store their items straight into the fresh vector after `vector_alloc`. A string literal read only by `string-length` folds to a constant, and one read only by `string-code-point-at` (ASCII literal) becomes a bounds check + `ldrb` from the pool: no `pair_new`. |
| register allocation over SIR temporaries | not a classic linear scan: each temp carries a descriptor (REG / CONST / LOCAL slot / HOME), so constants and local reads cost nothing until used; live temps are materialized at labels and jumps only. Locals get registers: in a **leaf** (no guest call, no C call left) slot k <= 7 lives in x(k-1) (params stay where they arrive), the rest of the slots, ranked by use count weighted x8 per enclosing loop, get x19..x28 (saved in the prologue); a leaf with everything in registers has no frame. A result stored straight into a local is computed into its register. |
| constant folding | bin/cmp/un on constants, branches on constants (dead side not emitted), immediate forms: add/sub #imm12, shifts #n, and/orr/eor with a run of ones, mul by 2^k, quot by a constant (no trap checks unless 0 / -1), cmp #imm12. cmp (+ not) + brz/brnz fuse to b.cond; jumps thread through `br` and repeated `brz t`. |
| counted-loop fuel prepay | **replaced** by a fuel register: a leaf holds the counter in x8 (`subs x8,x8,#1 ; b.hs ; brk` per charge, stored back at ret). The number of charges is unchanged: fuel per port is identical to R1 (KIR gate: 1,932,797 total, 19/19 equal to the source route). Prepay would only remove `subs+b.hs` per iteration. |

## Gates (all measured on this host, load average 150-190 during the runs)

| gate | result |
| --- | --- |
| fixed point | R1 seed c0526b73 compiles the R2 unity -> seed-A 94d9cff3 (old code generator compiled, new one running) -> seed-B == seed-C, **269,456 bytes** (R1: 291,392). Self-compile 60 ms vs 74 ms with the R1 seed (same unity, one run each). |
| G1 / G2 / G3 / G4 / G5 / GR r1 | all PASS (`gates.sh --rung r1 --no-build` on build/seed-r2: G1 19/19 both compilers, G2 65/66 (060 refused as before), G3 196 programs 0 differ from refusal-r1, G4 84 containers identical seed-A vs seed-B, G5 clean, GR 52+5 / 35+5) |
| KIR gate | 19/19, 26 KIR tests pass, code bytes and fuel equal to the source route |
| a64gen fixtures | 131 fixtures, 756 loader runs pass (53 R0 fixtures + 78 new: inline ops and their traps, folding, immediates on MIN/MAX, fusion, callee-saved preservation, x8 fuel stored back, swap/protect) |
| units | all pass with the R2 seed except 11-read, whose golden is stale since R1 (n09-map; the R1 seed gives the same output) |
| Embench execute <= 1.5x stage-0 (same host) | **PASS**: max 1.40 (nettle-aes, 14 vs 10 µs single cold call), geometric mean **0.96** |
| code size not worse | **PASS**: 96,969 raw code bytes over the 19 ports (R1 seed 114,433; stage-0 152,476, defined as the prefix up to the export) |

## Embench table (runner `run_native_qualification.py`, unchanged; medians of 5; packaged seed-B)

Evidence: `bench/embench/evidence-seed-r2/` (seed) and `.../stage0-same-host/` (stage-0, same runner, same host, run
right after). Execute = one cold call per sample (calls 1, warmup 0), 1 µs resolution.

| port | compile ms seed / stage-0 | execute seed / stage-0 | ratio | raw code bytes seed / stage-0 |
| --- | ---: | ---: | ---: | ---: |
| aha-mont64 | 21.0 / 152.8 | 14 / 14 µs | 1.00 | 3,264 / 3,240 |
| crc32 | 20.3 / 557.0 | 21 / 42 µs | 0.50 | 3,304 / 17,796 |
| depthconv | 19.5 / 432.5 | 39 / 38 µs | 1.03 | 2,088 / 4,996 |
| edn | 19.5 / 123.3 | 44 / 59 µs | 0.75 | 1,072 / 1,940 |
| huffbench | 23.6 / 74.2 | 7 / 9 µs | 0.78 | 616 / 564 |
| matmult-int | 20.0 / 924.5 | 40 / 49 µs | 0.82 | 5,752 / 29,864 |
| md5sum | 20.7 / 229.1 | 30 / 26 µs | 1.15 | 4,488 / 8,604 |
| nettle-aes | 21.1 / 121.6 | 14 / 10 µs | 1.40 | 1,592 / 1,684 |
| nettle-sha256 | 20.2 / 260.4 | 17 / 18 µs | 0.94 | 5,868 / 9,948 |
| nsichneu | 24.4 / 80.8 | 14 / 16 µs | 0.88 | 468 / 524 |
| picojpeg | 19.4 / 80.7 | 8 / 7 µs | 1.14 | 664 / 652 |
| qrduino | 20.3 / 96.0 | 9 / 7 µs | 1.29 | 744 / 1,612 |
| sglib-combined | 19.6 / 87.9 | 23 / 20 µs | 1.15 | 1,360 / 1,600 |
| slre | 20.1 / 88.2 | 8 / 9 µs | 0.89 | 885 / 1,336 |
| statemate | 22.6 / 70.5 | 8 / 10 µs | 0.80 | 432 / 448 |
| tarfind | 20.7 / 116.3 | 32 / 30 µs | 1.07 | 1,436 / 1,800 |
| ud | 21.5 / 273.8 | 17 / 18 µs | 0.94 | 4,804 / 6,596 |
| wikisort | 22.0 / 173.9 | 815 / 774 µs | 1.05 | 2,680 / 3,312 |
| xgboost | 23.6 / 282.0 | 2.560 / 2.388 s | 1.07 | 55,452 / 55,960 |
| **sum / geomean** | 400 / 4,226 | | **0.96** | 96,969 / 152,476 |

The cold single call is dominated by first-touch effects for the µs ports. A warm measurement (same binaries,
kexe-benchmark with 200 calls, warmup 1, median of 5 interleaved rounds; `warm-r1-r2-vs-stage0.txt`) separates the
code generator: **R1 seed / stage-0 = 1.57 (geomean; nsichneu 2.81, matmult 2.12, sglib 1.99, wikisort 1.87, slre 7.06),
R2 seed / stage-0 = 0.91** (max sglib 1.12 and aha-mont64 1.12; crc32 0.65, edn 0.69, sha256 0.73).

The 2026-09-29 numbers come from another host (M4, not loaded); execution times across hosts are not comparable, so
the gate uses the same-host stage-0 columns, as in the R0 report.

## Open risks

- **Loaded host.** Every number above was taken at load 150-190 (`seed-provenance.json`); rerun `scripts/seed/embench.sh`
  on a quiet host before quoting times. The ratios were stable across runs: cold-call geomean 0.94, 0.92, 0.90 in three interleaved comparisons and 0.96 in the runner.
- **xgboost** (2.5 s, 99% of the suite's time) is bound by `string-code-point-at` on a `:string` parameter: each call
  of `byte-at` gets a fresh `pair_new` handle, so the C helper re-validates the 10.9 KB literal as UTF-8 on every call.
  Stage-0 has the same cost. A general in-line `string-code-point-at` fast path would remove it but needs a contract
  that every code-relative literal is valid UTF-8 (R3 owns non-ASCII strings); not done in R2.
- **Lineage records.** `scripts/seed/bootstrap.sh` checks `seed-1 == seed-2` per rung; for R2 the record sets
  `bridge_commit` = the R2 commit itself (the bridge is seed-A), see seed/rungs/r2.record.
- The R2 rung reuses the r1 gate set (no new language); `gates.sh --rung r2` has no refusal-r2 golden or r2 GR suite.
