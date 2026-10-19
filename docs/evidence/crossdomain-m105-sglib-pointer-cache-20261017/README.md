# Sglib pointer-cache kernel candidate (2026-10-17)

Status: exact at the registered workload; exploratory timing completed on a loaded M1 Max; not promoted.

The candidate keeps the pinned Sglib C-derived port unchanged. In the exact-shape `lp-entry` kernel, it carries the current left and right node addresses through the merge loop and updates only the side that was selected. This removes one `madd` address calculation from each repeated comparison. The kernel grows from 18 to 20 words, so six raw branch targets in the surrounding body also needed adjustment.

## Matched build and exactness

The control and candidate were both rebuilt from the same predecessor selfhost G3. The control reached G1=G2=G3 at SHA-256 `1544a204…`; the candidate reached G1=G2=G3 at `320de9b9…`. Both compiled the same pinned Sglib source, SHA-256 `2122b300…`.

At registered `n=253952`, the candidate passed official exactness: result `1`, benchmark fuel `3,858,038,786`, verification fuel `605`, and the arena report matched. Its three dynamic instruction counts were 30,826,044,918; 30,822,792,331; and 30,820,515,892. The median was 0.99522 of control (about 0.48% fewer instructions) and 0.99295 of the preregistered instruction count, within the diagnostic ±2% gate.

An earlier static patch omitted branch relocations. Those private attempts did not complete even at `n=1024`; the sampled loop and disassembly exposed the missed targets. Attempt 4 fixes all six. Its disassembly confirms the targets at `0x3fe8`, `0x3ff8`, `0x4014`, `0x4044`, `0x4120`, and `0x4138`. The unsuccessful attempts remain in the workspace for audit.

## Exploratory timing

Ten alternating ABBA/BAAB blocks completed with all 40 measurement runs exact. The candidate was faster in 9/10 blocks; the median candidate/control elapsed-time ratio was 0.98678. Ratios ranged from 0.93215 to 1.10896. The first block was slower, and load1 ranged from 16.33 to 29.46, so this is not a quiet-host result and does not qualify a performance claim.

At `n=1024`, the exact single-run elapsed values were 10.044 ms for control and 10.265 ms for candidate. That one pair is noisy and points the other way. The candidate remains private until a quiet-host paired rerun confirms the direction. No C comparison or official Embench score was made in this experiment.

## Branch target repairs

The 8-byte insertion changes destinations after the kernel body. The private raw machine-code sequence did not relocate these branches automatically:

| Candidate branch site | Correct target |
|---|---|
| `0x3fe8 b.gt` | `0x4140` |
| `0x3ff8 b.lt` | `0x4140` |
| `0x4014 cbz x12` | `0x412c` |
| `0x4044 cbz x9` | `0x4124` |
| `0x4120 b` | `0x4010` |
| `0x4138 b` | `0x3ff0` |

## Next experiment

The earlier guest profile ranked heap sift-down (`0x6600–0x6c00`) and tree search/insertion/rebalance (`0x9200–0x9b00`) behind list merge. Continue with heap sift-down first: map its C-derived source to the emitted kernel, state an exact-preserving hypothesis, and retain a same-predecessor control before measuring.

## Raw evidence

Copied reports and the complete candidate disassembly are in [raw/](raw/). Reproduction scripts and all private attempts are in `workspaces/codex/amu-sglib-list-merge-pointer-cache-20261017/`.
