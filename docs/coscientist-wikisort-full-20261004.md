# Selfhost WikiSort: original 400-item, nine-input profile

`bench/embench/wikisort-full.kotoba` implements the original Embench body,
not the historical insertion-sort substitute: 400 stable value/index pairs,
all nine generators with the original continuous RNG sequence, 16 initial
runs, four merge levels, reversed-range rotation, cached merging and ordered
range skips. Native selfhost check/compile pass. All 14,490 staged and 3,220
repeated-body observations match the unchanged C implementation. The full
800-field original verifier and native bounds/fuel pass. Only picojpeg still
needs a complete alternative. No performance or official-score claim follows;
asher remains offline and C-or-better remains unachieved.

Upstream commit is `09c2ed8c3b7008c95d08b038de4a3f6dc103ed70`. Its size 400
and fixed cache 512 make the internal-block path unreachable: every A half
has at most 200 items and fits the cache. The C observation copy retains the
entire original WikiSort, including dormant branches, and reports zero
internal-block entries across all nine inputs. Native implements this actual
benchmark profile, not a general-purpose implementation for larger sizes or
smaller caches. Unused square-root/block-buffer locals and dormant extraction,
redistribution and internal-buffer merging are excluded from the native path;
no different sorting algorithm replaces the executed one.

The owned 2,048-cell i64 workspace stores 800 array fields, 1,024 cache fields,
RNG state and four counters. Test values retain signed 32-bit conversion;
indices preserve original stability. The cached merge prefers A on equal
values. Rotations copy the smaller side into the original fixed-size cache,
move the overlapping side in the correct direction, then restore the cache.
Fixed-point decimal/fractional stepping and floor-power-of-two calculation
are retained. One allocation is reused across all nine inputs and repeated
bodies; only seed/counters reset between bodies. No product dependency grows.

There is an upstream C limitation, preserved in the evidence rather than
hidden: `TestingMostlyDescending` and `TestingMostlyAscending` multiply two
signed ints before widening. Plain UBSan aborts at line 904 on
`27904 * 429496729` (exit 134). Native implements explicit two's-complement
32-bit conversion. All 14,490 C state values agree between plain Clang -O2
and -O2 -fwrapv on the current LP64/RAND_MAX=2147483647 host. The principal
native differential and future comparator use the unchanged plain -O2 C
body; sanitizer validation uses an explicitly labeled -fwrapv variant.
This agreement does not prove portable ISO C semantics or sanitizer success
for the original plain build. Original input-generation overflow remains
upstream debt, not a newly relaxed native guard.

Diagnostics compare 800 value/index fields, the exact RNG state and four
insertion/level/rotation/cached-merge counters before and after each of nine
sorts: 18 × 805 = 14,490 values. Another 805 fields agree after each of
1/2/17/32 complete bodies: 3,220 values. The C observation copy agrees with
unchanged `benchmark_body(1,n)` and `verify_benchmark` at those counts; the
C timing wrapper directly invokes those original functions. The explicit
wrap variant passes ASan/UBSan, all counts 1 through 32, and 14,400 initialized
array-field accesses; the failed plain sanitizer receipt is also saved.
Native batch counts 0/1/2/17/32 return the same wrapper results as C. Index
2047 succeeds and 2048 traps; a fuel-1 body traps. Thirty-two full bodies
remain within the unchanged arena/fuel limits. Counter writes and i64 item
storage remain native overhead included in future measurements.

Compiler SHA-256 is
`abcc1318957af7d3a09cfd66c06d17821b5cf47f4c47d02b5620e9e92a24f02e`,
the byte-identical three-generation native Amu build. Check, compile, extraction
and execution use that compiler/runner; Python and Clang prepare bootstrap
comparison tools. All 97 PRODUCT inventory entries remain unchanged. This
is one-off new algorithm/observation authoring outside existing native
refactor rules, not a refactor-verify or 100% own-source/exec-tracer claim.
Initial authoring corrected a delimiter, the reserved `merge` name and an
ambiguous C observation boundary before the accepted differential. No native
semantic mismatch was observed after check acceptance. Algorithm/RNG pins
are refused under Python -O and regeneration is byte-identical.

Artifacts, every comparison, original selfchecks, both sanitizer outcomes,
overflow-profile equality, provenance, source hashes and a fresh replay are
under `docs/evidence/coscientist-wikisort-full-20261004/`. Unpack replay beside
pinned `upstream`, `runner` and `images/r6m`:

```sh
python3 measure-wikisort-full.py coscientist-wikisort-full-replay --correctness-only
```

Omit `--correctness-only` on quiet asher for 30 rotating paired samples,
32 complete bodies per call, untimed warmup, calibrated calls and load ≤4
before/after each sample. Both paths include all nine inputs per body;
upstream local scale factor 2 is normalized to the explicit body count.
Formal host qualification still requires the existing broader gates; load
alone is insufficient. Reports refuse replacement and persist failures.
Current timing rows are empty and performance/official/formal flags are false.
Historical simplified-port timings are untouched. Next complete picojpeg,
measure the actual C gaps on quiet asher, and rank artifact experiments from
separated gains before changing the compiler.
