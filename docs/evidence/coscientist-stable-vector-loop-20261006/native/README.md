# Stable-vector native proof: portable offline replay

Copy `replay.py`, `native-proof.tgz`, and `archive-manifest.json` together. Run `python3 replay.py` with Python 3.12 or newer. Standard-library only; no Kotoba compiler, native guest execution, SSH, network, benchmark campaign, solver, or repository checkout is required.

The replayer extracts an owned temporary snapshot, verifies every pinned source/log/binary, rebuilds unchanged fixture expectation tables, checks retained actual outputs, and recomputes normalized machine-code and bounded constructor CFG/admission proofs. Derived Python audit sources use paths relative to the extracted snapshot and consume retained logs instead of invoking a compiler. Exact original sources and the derivation record remain in the archive.

Timing artifacts, timing preparation/remote scripts, and current remote evidence are excluded. Incidental elapsed fields in raw correctness runner JSON are retained as original observations but are never interpreted as performance evidence. `implementation/ports-correctness.json` is explicitly a copied baseline oracle, while candidate artifacts are identified by `ports-build.json`, `observer/admission.json`, and the fixed-point compiler hash.

Recorded SMT statuses and source files are checked; no fresh solver execution is claimed. Final write-artifact bytes are checked; intermediate filesystem history was not recorded. This finite replay does not establish universal compiler, authority, concurrency, OS stack-limit equivalence, or C-level performance.
