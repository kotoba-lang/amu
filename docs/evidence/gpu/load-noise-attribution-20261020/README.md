# load-noise-attribution-20261020 — does host load PREDICT the chain's IQR noise? corpus analysis over all 196 retained GPU-SGRE-CHUNK runs (JUN-58, the #1396 attribution question): weak, tail-and-one-stratum driven, NOT uniform — and the flip cell's sign is the load-sensitive one

## The finding this tick

**The chain's open load-noise attribution question (#1396) gets its first
corpus-wide answer: host load1 at run start does predict the SPEEDUP-iqr
noise level, but weakly and unevenly — the pooled association is carried
by the extreme-load tail and by ONE shape stratum (the flip cell), not by
a uniform load→noise law.**

Measured over all **196 unique verified GPU-SGRE-CHUNK runs** recorded in
`docs/evidence/gpu/` (whole-file sha256 de-duplicated; population fixed in
the analyzer docstring before outcomes were inspected):

- **Pooled:** Spearman **rho(load1, SPEEDUP-iqr) = +0.2685**, permutation
  **p = 0.0002** (20,000 permutations, seed 20261020). Positive, detectable,
  weak.
- **Fixed load bands** (chosen before inspecting outcomes):
  `load1<=8` clean 13/15 (86.7%) · `8<load1<=16` clean 76/88 (86.4%) ·
  `load1>16` clean 65/93 (**69.9%**) — the chain-clean rate (iqr<=0.05)
  drops ~17 points above load1 16. But band medians are **not monotonic**
  (median iqr 0.0241 / 0.0176 / 0.0303), the low band is n=15, and the
  2x2 Fisher exact (clean rate, >16 vs <=8) is **p = 0.2268** — the band
  contrast alone does not clear significance at this n.
- **Robustness:** excluding load1>30 drops rho to **+0.1838** (p=0.0131) —
  the tail matters. Within-shape strata (shape pooling confound check):
  only **W=64 chunks=32** shows the association (**rho +0.3426, p=0.0237**,
  load1 5.27–62.39); W=64 chunks=31 (rho +0.0352, p=0.87), W=64 chunks=1
  (+0.1144, p=0.68), W=64 chunks=24 (+0.1000, p=0.72) show **nothing**.
- **Secondary, per sign cell** (the two cells have different expected
  signs, so they are stratified — a pooled draft was discarded before
  recording on exactly this confound): the **anchor chunks=31** reads
  gap>0 in **0/24** runs at every load band (median gap −13,809 /
  −11,898 / −13,879 ns/dispatch) — sign stable under load. The **flip
  cell chunks=32** reads gap>0 in **6/7** (load1<=8), **8/10**
  (8–16), **14/26** (load1>16) — sign stability degrades exactly where
  the noise association lives.

## What this bounds, honestly

- **Direction supports the #1396 hypothesis but does not close it.** Load
  was never manipulated, its source is still **UNATTRIBUTED**, one host
  (Apple M1 Max / MoltenVK 1.3.357), one probe family; sweep-mates are not
  independent (permutation p treats runs as exchangeable — it is
  anti-conservative under within-sweep correlation, so the quoted p-values
  are upper bounds on evidence strength). Correlation is not cause: a
  third factor (e.g. whatever generates the load — other sessions' GPU
  traffic) could drive both.
- **This is a stronger attribution step than any single batch** (196 runs
  vs 6–12 per probe) and it re-uses already-recorded measurements; no new
  GPU run was dispatched this tick, so nothing here contends for the GPU.
- **Consequence for the sign series:** the flip cell's sign breaks are now
  load-graded (6/7 → 8/10 → 14/26 positive), which is the pattern a
  noise-driven "flip" predicts and a true phase transition does not — but
  n per band is 7–26, the series count rule is untouched (still **one
  flip in twenty-five**), and no transition is re-adjudicated by this
  analysis. The chain's void rule (sign unanimity + IQR-clean) stands.

## Protocol

- **Population:** every `*.log` under `docs/evidence/gpu/` (recursive)
  carrying (a) a `GPU-SGRE-CHUNK\tSPEEDUP` line — GPU-SGRE-LOAD (30 runs)
  and GPU-SGRE-WSWEEP (8 runs) are **excluded** (different probe/protocol,
  not pooled), (b) `RESULT verified=true` (failed/truncated attempt logs
  carry no SPEEDUP line and drop out: 59 unique logs skipped), (c) an
  `uptime` `load averages: <load1>` line. 255 log files scanned → **196
  unique runs**; byte-identical duplicate copies found: **0** in this tree
  (the chain-carry copies of tick 1346/1416 are not merged here yet).
- **Rule carried from the chain's analyzers:** chain-clean = SPEEDUP
  iqr <= 0.05 (the floor-share clause of the void rule is cell-relative
  and is not applied corpus-wide; it cannot re-adjudicate anything here).
- **Analyzer:** `analyze-load-noise.py`, self-contained (stdlib only),
  deterministic — output byte-identical across three consecutive runs
  (sha256 `ab069d60…` for `analyze-load-noise.txt`, verified this tick).
- **Design amendments during the tick, recorded:** section 4's pooled
  sign view was replaced by the per-cell stratification after the pooling
  confound was spotted, **before any output was recorded**; the discarded
  draft is not evidence and is not quoted anywhere. Bands, rule, seed and
  population were fixed in the analyzer before the first run.

## States

- implemented (code + test): nothing in src/test this tick — evidence-only
  diff (one analyzer + its output + this README under docs/evidence/gpu/).
  **Gate not run** (nothing to gate). Suite base state carried from PR
  #1388's exact-base run (16F/15–17E, red set outside every amu-gpu diff,
  not green) — not re-measured this tick.
- measured (this document + `analyze-load-noise.txt`, all numbers above):
  the load1↔iqr association across 196 recorded runs, the band clean
  rates, the per-cell sign-by-band counts. Every number comes from the
  recorded logs through the committed analyzer.
- UNMEASURED: the causal direction (load → noise) — needs a manipulated
  or low-load-matched comparison; the load SOURCE (still unattributed);
  the flip rate; the `:arm` / `:unknown` workgroup rows
  (`:measured? false` stays false — nothing here touches
  `kotoba.compiler.accelerator-targets`).

## Files

- `analyze-load-noise.py` — the analyzer (population, rule, statistics,
  seeds all in-file).
- `analyze-load-noise.txt` — its output, byte-identical on re-run
  (sha256 `ab069d601e628f824527a4904c89fe1f0fac02436ce85bb7e822a543793b783e`).
