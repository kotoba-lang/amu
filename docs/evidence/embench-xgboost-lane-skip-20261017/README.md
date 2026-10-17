# M105 XGBoost per-lane walk-skip experiment

Status: **rejected for compiler-source retention**. The candidate passed
exactness, but exploratory timing under heavy host load was slower in all five
ABBA pairs. The source is restored to the four-wide group checks.

## Generate, debate, and rank

The existing kernel interleaves four tree walks and checks for four leaves
after each level. A static profile found that 52.6% of walks finish before the
fifth level. The hypothesis was to keep the four-lane interleaving but add a
`tbnz` before each lane's later walk body, skipping that body's 14 instructions
when its lane is already a leaf.

The counter-hypothesis was that twelve extra lane branches cost more than the
loads and address work they avoid, especially when several lanes finish at the
same level. The earlier width-two experiment also failed to show a gain, so
this candidate ranked behind changes with direct evidence of reduced work. It
was tested because the fixed-size instruction region allowed a precise,
reversible probe.

## Selfhost and exactness

The 416-word `tw-entry` payload retained its 960-byte code region and final
four-lane validation, fallback, and commit. The selfhost build produced the
same 2,554,976-byte compiler image for G1, G2, and G3:

`f7031cd39c3adbca652c2f0a33a72793a3789973c5600c786a087f1670c8b86e`

The G3 compiler rebuilt the pinned Embench xgboost source. Its 66,732-byte
image exactly matched the hand-patched prototype:

`05cac8ddd99914bb5a20cedea5f158bb74749faa7290775bf6b7de3c8919c15e`

The KSEED export table matched the pinned base. The official M104 XGBoost
exactness harness passed at `n=8192`: result `1`, benchmark fuel
`2806009749`, and matching arena accounting.

## Exploratory timing

Five ABBA blocks compared the same-source four-wide image with the
selfhost-generated lane-skip image. All 20 invocations matched result, fuel,
and arena. The host remained heavily loaded: load1 ranged from 24.37 to 34.71,
and measured idle ranged from 6.5% to 39.1%, below the 70% qualification gate.

All five paired lane-skip/four-wide ratios were above one:

`1.0653, 1.1370, 1.1303, 1.0539, 1.0160`

The median paired ratio was `1.0653`; median elapsed times were 4.323 seconds
for lane-skip and 3.962 seconds for four-wide. This loaded-host experiment is
not a qualified performance result, but it gives no reason to retain the
change. No C arm was measured, and no Embench score is claimed.

The normalized values are summarized in
[`candidate-results.json`](candidate-results.json); the official exactness
receipt is [`exactness-report.json`](exactness-report.json), and all 20 raw
timing samples are in [`lane-skip-abba-report.json`](lane-skip-abba-report.json).

## Decision and reproduction

The lane-skip source change was removed. The restored source keeps the original
group checks. `port-source.py` and `restore-source.py` reproduce and reverse
the 416-word transformation; their byte-identical source round-trip passed.

The G1/G2/G3 receipt and rebuilt XGBoost KSEED/image are retained under
`workspaces/codex/amu-xgb-lane-schedule-20261017/attempt-2/`,
`attempt-7/`, `attempt-8/`, and `attempt-10/`. The failed sandbox-only build
attempt and corrected compile-script attempts are retained separately. The only result
that could promote this candidate would be a quiet-host paired measurement;
given the current exploratory direction, prioritize another workload first.
