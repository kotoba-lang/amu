# Sglib tree path candidate (2026-10-17)

Status: exact at the registered workload; promising instruction-count and loaded-host timing signals remain exploratory. Not promoted.

The sampled tree region maps to the Sglib `tb-entry` kernel at `0x9250`. After `tree-find` proves that an input value is absent, the kernel replays every recorded level to validate the equivalent `tree-insert` descent. At every visited node, the search comparison is nonzero; insertion compares the same value at the unchanged node, so both choose the same direction. Duplicate values exit through the found branch before insertion.

Attempt 3 jumped directly to leaf insertion and got the final tree result and arena right at `n=1024`, but benchmark fuel was 1,741,824 lower because it also skipped the recorded-path cursor advance required by the later `tree-fix` pass. Attempt 4 skips the root/side checks while preserving the 24-byte-per-level cursor advance. Its disassembly is in `raw/attempt4-tree-path-disassembly.txt`.

Attempt 4 reached a G1=G2=G3 selfhost fixed point, compiled the pinned Sglib source, and passed registered exactness at `n=253952`: result `1`, benchmark fuel `3,858,038,786`, verify fuel `605`, and matching arena. Three instruction-count runs had a median about 6.5% below the matched control. The unchanged-image ±2% diagnostic gate flags this as out of range; the registered exactness result is separately PASS.

Ten exploratory ABBA/BAAB blocks all passed exactness. The candidate was faster in 7/10 blocks; median candidate/control elapsed ratio was 0.9903. Ratios ranged from 0.8448 to 1.2075 and load1 ranged from 38.59 to 50.74. This loaded-host sample is not qualified timing evidence; keep the candidate private pending a quiet-host paired rerun. A same-predecessor compiler check compiled all 19 pinned ports from both control and candidate G3. Only `sglib-combined` changed native image; the other 18 images, KSEED files, and exports were identical. The candidate then passed registered exactness for all 19 workloads, including result, fuel, and arena checks. The exactness report records host elapsed fields only as diagnostics, not benchmark results. This bounds the compiler change to Sglib in this suite but makes no runtime-speed claim. See `raw/attempt4-crossworkload-image-diff.json`, `raw/attempt4-crossworkload-exactness.json`, and the paired build reports.

No C comparison or official Embench score was made. Raw reports and hashes are in `summary.json` and `raw/`.
