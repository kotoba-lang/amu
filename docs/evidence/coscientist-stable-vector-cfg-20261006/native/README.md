# Portable offline CFG native proof

Copy `native-proof.tgz`, `archive-manifest.json`, and `replay.py` together, then run `python3 replay.py`. Python standard library only. The replayer extracts its own temporary copy, verifies every pinned file, recomputes normalized original19 machine equivalence and fault detectors, independent all-predecessor/constructor models, frame arithmetic, fixture/run tables, and checks retained actual native outputs. No guest native, compiler, solver, SSH or benchmark execution occurs.

Native candidate: eab3a7c26eac2fdf32a3d4736fd8dd1c159b811a6dc6b5ef0f69c1d44b798406, generations 2/3/4. Qualified product baseline: f00e38312ac7278b1b597207054cba521fafa28f30f03d20d237a07fd59647e2.

The archive retains original sources/logs and derived portable scripts. Derivations only replace dependency paths or replace compiler invocation with retained original observer logs. `portable-patches.json` records selected originals. The copied `implementation/ports-correctness.json` is a baseline oracle, not candidate execution evidence; actual candidate runs are `root-proof/ports-semantic.json` and its raw reports.

593 fixtures / 25,658 actual observations preserve the original 508 / 14,523 prefix. Constructor proof covers 576 pairs and 10 synthetic native predicate cases; synthetic raw SIR is diagnostic data, not checked guest programs. Original19 admission has 7 decisions with admitted query visits 69 and 47. Resource proofs retain 161 resource and 209 fuel pairs, 8 caller sentinel pairs, actual frame faults and 32,704 bounded arithmetic cases. Recorded SMT statuses are checked, not rerun.

Timing material is excluded. This finite correctness evidence does not claim universal compiler equivalence, OS stack-ceiling equivalence, product promotion, or performance improvement. The sample guests did not detect omission of frame growth; the actual physical frame invariant did. Source-authoring and control-calibration corrections remain in the archive.
