Packaging note: this is the historical pre-adoption README. Its script `replay.py` is saved here byte-identically as `native-replay.py`; run that filename. Its unchanged-golden statement describes the archived pre-adoption stage. The later explained artifact update is recorded in source-adoption.json.

# Portable scalar DAG native proof replay

Copy only `native-proof.tgz`, `archive-manifest.json`, and `replay.py` into an empty directory. Run `python3 replay.py` (Python 3.12+). This extracts an immutable selected payload, checks every payload hash, and recomputes original source mathematics, actual SIR DAG admission, machine projection, permanent fixtures and cap accounting from retained observations. It does not execute native binaries, invoke a solver, measure performance, or promote a product.

The current candidate native seed is 761856bb455de5d36021e177be8f3a0bbf65772dd66cbdf29c8e114f8cbe3d93; the distinct qualified baseline is eab3a7c26eac2fdf32a3d4736fd8dd1c159b811a6dc6b5ef0f69c1d44b798406. Source snapshots and original selected file origins/hashes are retained. This is selected current proof closure, not the full owner file pin sets. Old intermediate compiler candidates, stale observer metadata, timing, remote artifacts, serialized compiler intermediates and duplicate seed0/1 are excluded.

Original golden remains unchanged and differs: seven original BL instructions each become the two-word pure scalar callee body without RET. The portable fixture machine audit recomputes all seven transformations and every remaining word, branch/fixup, function offset and literal pool relationship; semantic expectations remain the original hand-written593/25658 table. The retained FAIL golden summary stays present beside this independent classification.

Baseline `ports-correctness.json` is a copied previous baseline oracle; candidate actual code/results/fuel/traps reside separately under implementation/ports and root-proof. Prospective SMT10 statuses and sources are retained and pinned; no fresh solver result is claimed. Native source mutants and their observed results/refusals are retained; no new native execution is claimed.

This replayer is a bootstrap source-authoring adaptation. Portable copies alter dependency paths only. Original frozen sources are preserved, and patch provenance is explicit in portable-patches.json. The shared machine projection verifier is disclosed; constructor source interpreter and DAG oracle were independently authored.
