# XGBoost pairwise leaf-check reassociation

Status: correctness passed; loaded-host timing was mixed and unqualified; not promoted.

## Hypothesis and counter-hypothesis

The four-wide XGBoost early-stop kernel and its final common-commit validation each formed a leaf predicate with three dependent `and` instructions. The candidate reassociated each predicate into two independent `and` operations followed by a combine, shortening the dependency chain while preserving the five checks, branch behavior, and instruction count.

The counter-hypothesis was that the chain is not cycle-critical, or that independent operations add issue pressure next to the existing loads. The M1 Max results did not falsify that counter-hypothesis.

## Build and correctness

The candidate and same-snapshot control both reached G1=G2=G3 selfhost fixed points. Both compiled all 19 pinned ports. Only the XGBoost native image changed; the other 18 images were byte-identical. The XGBoost image remained 66,732 bytes. Official exactness passed for XGBoost at `n=8192`, including result, fuel, and arena accounting.

Disassembly verified the intended change: both images contain 8,141 instructions and five leaf-check groups. Each control group has a three-deep dependent AND chain; each candidate group has two independent first-level ANDs and one combine. This is a structural confirmation, not cycle-level evidence.

## Exploratory timing

Ten same-host ABBA pairs (40 runs) all passed result, fuel, and arena checks. Candidate/control paired ratios were mixed: the median was `0.9891`, and the candidate was faster in 6 of 10 pairs. The raw candidate median was 3.838 s versus 3.708 s for control. Load1 before runs ranged from 34.26 to 41.52, and no quiet-host gate was met. These observations are unqualified and do not establish a speedup.

Keep the candidate unpromoted. Revisit only with quieter paired measurements or stronger cycle-level evidence.

## Provenance and reproduction records

- Candidate fixed point: `efedf55e4bf5faf2811a43607d49b865fcf790a933860a4570eb961ebe7b767a`
- Control fixed point: `1544a204b003bd3b5ec9831be008fcbd5ffa5a91c44f922a4ca13a1dca539588`
- Aggregate evidence: [`summary.json`](summary.json)
- Candidate workspace and raw reports: `workspaces/codex/amu-xgb-pairwise-leaf-check-20261017/attempt-1/`
- Same-source generic no-fusion control: `workspaces/codex/amu-generic-cmp-zero-fusion-20261017/control-1/`
