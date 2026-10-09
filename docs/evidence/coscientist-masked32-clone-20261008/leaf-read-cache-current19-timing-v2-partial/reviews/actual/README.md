# Independent saved V2 timing audit preparation

`validate_saved.py` is standalone offline review code. It imports only pathlib,
hashlib, itertools, json, math, re, sys and tarfile. It does not import SOURCE
operational modules or call processes, native artifacts, SSH, the collector,
compiler, CPU APIs or network APIs. Prior participation: V1 second SOURCE review,
V1 saved-failure audit, V2 second SOURCE review. No operational SOURCE authorship.

No actual timing acceptance has been emitted during preparation. Run only after
root supplies the one completed read-only saved collection and its transport
attempt/archive under the V2 GO workspace:

```
cd /Users/junkawasaki/github/workspaces/codex/vector-leaf-straight-read-cache-current19-timing-actual-review-v2-independent
python3 -B validate_saved.py /Users/junkawasaki/github/workspaces/codex/vector-leaf-straight-read-cache-current19-timing-go-v2-root/collected
```

The exact local GO is pinned to SHA256
`863b669cf86eb14235713ca1403da57a5eb5dda30ac20b2abebc2998f742154f`.
The auditor verifies all nine SOURCE/GO bindings, two exact SOURCE reviews,
complete collector/archive bytes, prior V1 failure acceptance, initial measured
input and compiler/SDKSettings seal inventories, clean environments, every child
receipt/raw stream/EOF/cap, actual waited CPU envelopes, strict nmax telemetry,
calibration rounding and quiet decisions, chronological triples and six-order
blocks, first30 accepted of max90, unchanged body normalization, and fixed19
statistics. Bootstrap, means, sample SD, adoption and C predicates are independently
implemented here; SOURCE statistics code is not imported or executed.

Success writes `report.json` and `recomputed-statistics.json` only after all checks.
An incomplete19 campaign can emit only the distinct saved-partial status with no
subset GM or fixed19 timing acceptance. A campaign failure refuses success and
writes `audit-failure.json`; use a separately prepared finite saved-failure audit.
Source/GO drift, missing evidence or arithmetic disagreement also refuses success.

Pure preparation controls checked exact rational rounding, all six permutations
in fifteen blocks, and degenerate/nondegenerate deterministic20K bootstrap
vectors. No actual collection was read and no operational calls were made.

Limits: saved evidence only; no reviewer live host interrogation or full remote
bank rehash. CPU quiet evidence encloses process setup, warmup, execution and pipe
drain; it is not timed-loop CPU. Input sealing assumes ordinary trusted kernel
metadata and excludes privileged forgery. No SDK whole-tree, official benchmark
score, production cache effect, product adoption or joint95 confidence claim.
