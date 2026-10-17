# M105 xgboost width-two hand-patch experiment

Status: exactness passed; performance remains unqualified and does not support promotion.

## Candidate construction

The current M105 source at `6103f5cf` was rebuilt from adopted native bootstrap `6b158aa8`. G1, G2, and G3 all produced the 2,552,512-byte compiler image `b10e381344a1f5a8b82cac981c0011bd20ecbcc4b48dd5f5dce97364c74e8a00`; the build used the pinned native C loader and no JVM, Node, or Graal fallback. The compiler regenerated the xgboost port byte-for-byte: 66,052 bytes, image SHA-256 `1c4aab16450da5b1deef581688d13b1995b87fa0238789cff8563ddc941a400d`.

The hand-patch reorders only the 16 emitted 14-instruction walk bodies in payload offsets `0x13c0..0x1780`. It walks lanes 0/1 together and then lanes 2/3, with a pair-leaf check after the root and each of steps 2 through 4. The eight pair checks fit in the same 960-byte region as the original four-wide checks. The four-lane bounds/leaf validation, fallback, and commit at `0x1780` remain byte-identical. Compiler source did not change. The result is a 66,052-byte payload with SHA-256 `15496f2a07e7e37e3c694a423acb08ad7527b30b2f320c5190a40aedab94cd8b`.

## Exactness

The official M104 xgboost exactness harness passed for `n=8192`. Result was `1`, benchmark fuel was `2806009749`, and the arena report matched the expected record. All 20 timed invocations also matched result, fuel, and arena.

## Exploratory timing

Five ABBA blocks compared the current width-four image and the hand-patched width-two image with the same separated timer, warmup, input, and caps. No C arm was measured. The host was heavily loaded: load1 ranged from 49.4 to 64.1; raw idle ranged from 0.02% to 14.6% for width four and 0.07% to 6.5% for width two.

| Measure | Width four | Width two |
|---|---:|---:|
| Median elapsed time | 6.743 s | 6.626 s |
| Range | 4.719–18.617 s | 5.446–18.962 s |

Paired width-two/width-four ratios were `1.024, 1.014, 1.057, 1.089, 0.649`; their median was `1.024`. Four pairs point slower for width two, while one extreme outlier reverses the aggregate median times. The samples are noisy, overlap broadly, and fail the 70% idle qualification gate. They establish neither a speedup nor a regression. Do not promote this hand-patch into the compiler on these data.

## Reproduction

From the repository root, run the scripts in this directory in order. Give every `--out` a fresh subdirectory under `scratch/workspaces/codex/`:

1. `rebuild-current-selfhost.py` verifies the pinned source closure and rebuilds G1/G2/G3 from the adopted bootstrap.
2. `compile-current-xgboost.py` compiles the pinned xgboost port and verifies image SHA `1c4a…`.
3. `handpatch-width2.py` emits the pair-major image from the width-four payload.
4. `exactness-width2.py` wraps the candidate with the unchanged KSEED export table and runs official exactness.
5. `time-width2-abba.py` repeats the five exploratory ABBA blocks. Its result is not a qualified Embench score.

The reports, input/output payloads, source receipt, pair-patch disassembly, and reproduction scripts are retained here. Full sampled timing and host-load readings are in `width2-abba-report.json`.
