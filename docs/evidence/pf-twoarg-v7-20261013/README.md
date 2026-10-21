# Guarded two-argument fuel caching and comparison folding

This snapshot extends the existing private, source-guarded scalar frame from
three parameters to two. It preserves phase/table priority and folds the exact
returned-value copy across a fuel reload. It keeps the original fuel debit,
trap edge, context ownership and arena accounting.

The source unity is `ff6523711c6e37345fa75524d8d0e4f228d8dee4a99bffe59b36bf6b1d9f7f0f`;
the stable native compiler is
`c0687a55b1f264eebb546c15f24f09a34f1036c646636e58a71e9b70063e459c`.
Standard native builds reached the same fixed point in two generations, and
the standard main integration check independently verified three generations,
34 policy refusals, exact result 42 and the original 19 source images.

All 39 stable program images, containers and sources are identical to the v3
candidate whose original 95 profile, 76 low-fuel and 312 interaction observations
passed. Those 483 observations are inherited by whole-image identity; they are
not presented as fresh v7 executions. Four images differ from the previous
adopted main: official/functional Picojpeg and SG.

Fresh controls include 52 lookup cases, 54 scalar pairs and 480 comparison
pairs over five operators, six signed constants, four loop lengths and four
fuel levels. The portable CI test additionally compares the previous adopted
main directly with the newly self-built compiler for those 480 pairs. Results,
raw output, fuel and all 17 arena counters must match. A separate whole-word,
reference, pool and export audit proves exactly 20 copy removals and 10
out-of-range refusals at -4096 and 4096.

The physical proof archive preserves the compiler transition map, cache/context
CFG results and boundary instruction map. Its manifest pins each complete
result. Earlier source auditors are preserved in the
[public candidate archive](https://github.com/kotoba-lang/kotoba-lang/tree/main/docs/benchmarks/embench-candidates-20261013/verification-tools).
They require their pinned dependencies and Python without optimization;
these results alone are not standalone verifier programs.

Fresh full19 measurements use the unmodified upstream Embench driver/formula,
GSF 8192 for the translated ports and 32768 for C, with normalization. The
observed Kotoba time/C ratio is **3.087016568611168**. This is exploratory,
not a certified official Kotoba Embench score, and the total-C goal is unmet.

One predeclared OFF/ON/OFF/ON block measured the two changed programs. SG's
median time decreased **0.3624%**, with both individual pairs faster. Pico's
median increased **0.0137%**, with mixed individual pairs. The program-only
full19 differential estimate is **0.0184% shorter**, binding the other 17
programs to this cycle's fresh measurements of their identical images. It is
a single-cycle observation, not a statistical claim or a stable total gain.
No 5% acceptance cutoff applies.

All measured bodies exceed 0.5 seconds. Raw pre/post CPU idle and background
idle must each reach 70%; at most three CPU-only attempts are permitted, the
first passing attempt is selected, and rejected attempts are retained.
No old elapsed values or fastest-sample selection are used.

Local evidence remains under `/Users/junkawasaki/github/workspaces/codex/`:

- `embench-pf-twoarg-20261013/compare-priority-v7/`: complete proofs, controls and failures.
- `embench-total-C-round86-v7-20261013-v1/`: full19 measurements, custody and independent review.
- `embench-pf-twoarg-v7-round86-fixed4-20261013/`: one changed-program comparison block.
- `embench-twoarg-v7-main-selfbuild-20261013-v1/`: standard selfbuild and native CI controls.
- `embench-twoarg-v7-main-policy-source19-20261013-v1/`: standard policy/source integration check.

Other variants and prior failures remain preserved. Source inclusion and these
measurements do not establish a merge; the PR and fresh remote-main readback
determine integration status. Continue the full original19 goal after merge,
prioritizing the largest measured gaps and accepting validated small gains.
