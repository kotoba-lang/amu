# Sglib heap hole candidate (2026-10-17)

Status: exact at the registered workload; exploratory timing was slower on a heavily loaded M1 Max. Not promoted.

The profile region mapped to the Sglib heap stage at image offsets `0x6600–0x6c00`; its sift-down loop is `0x6878–0x68d4`. The loop already holds the displaced heap value in `x14`, but the original swap body writes it to every child on the way down. The candidate writes each larger child into the hole and writes `x14` once at the final position. Fuel accounting remains unchanged at four units per descending step.

Attempt 1 missed a leaf exit and failed with SIGILL at `n=1024`. Attempt 2 directs both leaf and no-swap exits to the final store. Its disassembly is included in `raw/attempt2-heap-down-disassembly.txt`.

Attempt 2 reached a G1=G2=G3 selfhost fixed point and compiled the pinned Sglib source. Registered exactness passed at `n=253952`: result `1`, benchmark fuel `3,858,038,786`, verify fuel `605`, and matching arena accounting. The dynamic instruction median fell about 0.43% versus the matched control.

Ten exploratory ABBA/BAAB blocks all passed exactness, but only 3/10 favored the candidate. Median candidate/control elapsed ratio was 1.0263 (about 2.6% slower); load1 ranged from 23.05 to 33.43. Treat the timing as unqualified and keep the candidate private. No C comparison or official Embench score was made. Raw reports and hashes are in `summary.json` and `raw/`.
