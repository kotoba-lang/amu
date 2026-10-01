# Selfhost wall: content-addressed cache and affected-only verification (2026-10-01)

Speedup 3 of the verification speedups. Goal: on this Mac, do not re-run `amu check` (2 s for an
empty file, 48 s for `kotoba/kir/xml.cljk`) or a differential when nothing it depends on changed.

Premise (docs/selfhost-priority.md rules 8-11, docs/selfhost-bootstrap-boundary-20261001.md): the
product depends on no nbb, Node or JVM. So the *logic* of the cache is Kotoba and the rest is plain
shell; nbb appears only as the bootstrap way to run that Kotoba today, and it is labelled so.

## Parts

| piece | what | class |
|---|---|---|
| `src/kotoba/compiler/wall_cache.cljk` | pure `plan` and `record-digest`: keys, affected closure, record validation, golden keys. `amu check` OK on the project route; the Kotoba reading is executed on the KIR interpreter and equals the nbb reading | PRODUCT-eligible Kotoba |
| `scripts/selfhost-wall/scan-cached.sh` | thin driver: find/awk/shasum, the cache directory, the checker command. No nbb, no Python | plain shell |
| `scripts/selfhost-wall/wall-graph.awk`, `wall-cache-lib.sh` | require graph and hashing for the driver | plain shell/awk |
| `scripts/selfhost-wall/golden-cache.sh`, `golden-wrap.sh` | differential caching, same module | plain shell |
| `scripts/selfhost-wall/wall-cache-plan.cljs` | runs `plan` under nbb (stdin to stdout). **bootstrap-reference**; `WALL_PLAN` replaces it | bootstrap-tooling |
| `scripts/selfhost-wall/wall-cache-conformance.{sh,cljs}` | nbb reading vs Kotoba-route reading | bootstrap-tooling |
| `scripts/selfhost-wall/scan-cached-selftest.sh` | the driver on a synthetic project with a counting stub checker | plain shell |
| `ds-diff.cljs`, `tm-diff.cljs`, `vx-diff.cljs` | `WALL_GOLDEN` hook (host side reused when the file exists, written when not) | bootstrap-tooling (already) |

## The key

    key(f) = sha256 of
      kotoba.wall-key/v1
      H <classpath id> <checker version>
      S <path of f> <sha256 of f's bytes>
      D <path> <sha256>     for every module in f's transitive require closure, in sorted path order

* Require graph: the `[a.b ...` names of the ns form (reader-conditional branches included, so a
  superset of the real graph: a key can be too sensitive, never too stale), resolved like
  `reach-list.py` (classpath `src` roots, amu `src`, `lang/compat`; `.kotoba`, `.cljk`, `.cljc`). A module
  with a twin in `lang/compat` also depends on the twin.
* Classpath id: sha256 of the classpath string. gitlibs and `.m2` entries are pinned by their path.
* Checker version: sha256 of the bytes of the *checker*: every local classpath `src`/`resources` dir that
  holds none of the listed files (the language implementation: sema, kir, ...), `lang/compat`, the grant
  policy, the check script. A dir that holds a listed file (or `WALL_SUBJECT_DIRS`, or amu's own `src`) is
  *subject*: editing it invalidates only the files that require the edited module. `WALL_STRICT=1` also puts
  `nbb/wasm_cli.cljk` in the checker identity.
  Approximation, stated: amu-src modules that `wasm_cli` itself loads are treated as subjects. If you edit
  the checker glue, use `WALL_STRICT=1` or `--no-cache`.
* A record is one file `records/<key>`: `kotoba.wall-cache/v1 TAB key TAB digest` then the verdict line.
  The digest is `record-digest` (sha256 of format, key, verdict); a record whose recomputed digest differs, or
  whose key differs, is deleted and treated as a miss. The directory is `0700`, files `0600`, written by
  temp + rename (the conventions of `nbb/verdict_cache.cljk`). Corruption and mismatch, not forgery.

## Modes

    WALL_CP=... WALL_K=... WALL_AMU_SRC=... WALL_CHECK=/private/tmp/wall-one.sh \
      scripts/selfhost-wall/scan-cached.sh [--affected] [--no-cache] [--changed paths.txt] [-j N] list.txt out.tsv

* default: look up every key, check only the misses, print the hit rate.
* `--affected`: `plan` also derives, by an independent fixpoint, the reverse-dependency closure of the files
  whose bytes changed since the last scan of this list (content comparison, not mtime, not git; `--changed F`
  names them explicitly, e.g. from `git diff --name-only`). Files outside that closure take their verdict from
  the last scan without even reading a record. Files inside go through the cache.
* every run checks the two derivations against each other: **every key miss must lie inside the predicted
  affected set** (when the checker identity is unchanged). A violation prints the file and exits 3.
* `--no-cache` is the uncached reference scan (it still stores).

The checker is any command printing `<file> TAB <verdict>`: `wall-one.sh` today, `check-native.sh` later.
Output format and order are scan.sh's.

## Differential caching

`golden-cache.sh key|get|put`. A golden host output is keyed by

    sha256 of kotoba.wall-golden/v1, name, wall_cache keys of the host function's module(s), case-set CID

where the module key covers the function's transitive require closure and the checker identity, and the
case-set CID is the sha256 of the bytes of every case input (test directories, extra programs, the diff script)
and the limits (`@DS_MAX=300`...). `ds-diff.sh`, `tm-diff.sh`, `vx-diff.sh` use it when `WALL_GOLDEN_CACHE=1`:
on a hit the nbb host side is skipped and only the Kotoba side runs. The golden file's own sha is stored in the
record and re-verified on every `get`.

Honest limit: the saving is the host side's time. For `ds-diff` that is small (host `desugar-expr` is cheap);
the dominant cost of a differential is linking the guest and running it on the KIR interpreter (about 5 ms per
source byte, on nbb). That cost is the *Kotoba side*, which by construction must be rerun whenever the Kotoba
side may have changed; it is removed only by a faster interpreter or by running the guest natively (speedups 1
and 2), not by caching.

## What a selfhost replacement still needs (bootstrap-reference -> Kotoba)

1. `wall-cache-plan.cljs` (nbb): a Kotoba `main` that reads all of stdin and writes stdout (io abilities) and a
   native build of `wall_cache.cljk` with `hash/sha256` lowered. `plan` is pure string-in/string-out and
   already passes `amu check`; what is not demonstrated is building it into an executable with Amu.
2. `WALL_CHECK=check-native.sh`: the checker itself, `amu check` as a self-built binary (the whole point of
   selfhost; until then every miss costs the nbb check).
3. `wall-graph.awk`: a Kotoba `amu graph <files>` printing `N`/`E` lines (the compiler already computes the
   closed graph in `project_files/load-closed-graph`; it needs a command and a `:kotoba` reading of that
   module, which today carries a modified, not yet checked, working copy).
4. `shasum`/`find`/`xargs -P`: a directory walk and a bounded process pool as Kotoba abilities; plain shell is
   acceptable here (not nbb/Node/JVM).
5. The differential's host side is, by definition, a JVM/nbb reference run. It stays bootstrap-reference; the
   cache only makes it a one-time cost.

## Measured (this Mac, wave 14 load, load average 50-130)

Setup: 8 files of the reach list (`base64_text`, the five `nbb/host/*` leaves, `aarch64_cli`, `x86_64_cli`;
156 graph nodes), checker `wall-one.sh`, `-j 3`, a host at load average 40-130 (so absolute seconds are
inflated; the ratios are the point).

| scan | checker runs | hit rate | wall |
|---|---|---|---|
| uncached (`xargs -P3 wall-one.sh`) | 8 | - | 43 s |
| cold cached | 8 | 0% | 45-59 s (graph+hash 0.9 s, plan 0.3 s) |
| warm, nothing changed | 0 | 100% | 1.5 s |
| `--affected`, nothing changed | 0 | 100% (trusted) | 1.2 s |
| touch leaf `nbb/host/hash.cljk` (1 comment line) | 2 | 75% | 39 s (2 checks) |
| restore the leaf | 0 | 100% | 1.6 s |
| touch `decimal_text.cljk` (32 dependents among the 227 nodes of the full list) | 2 | 75% | 44 s |

* Cold cached == uncached: the 8 verdict lines are byte-identical (`sort | cmp`).
* Touching one leaf re-checked exactly the listed files whose require closure contains it (2 of 8), and the
  affected set predicted them (violations 0).
* Full reach list (162 files, 227 nodes) with a stub checker, i.e. the pure overhead of the cache: cold 3.1 s,
  warm 2.1 s, `--affected` 2.6 s. A real full scan is minutes to tens of minutes at this load, so a warm
  rescan costs 2 s instead.
* Affected-set sizes on the full graph (nodes, listed or not): `decimal_text` 32, `nbb/host/hash` 15,
  `project_files` 10, `wall_cache` 0 (nothing requires it).
* `scan-cached-selftest.sh` (synthetic project, counting stub checker): 11 checks pass, including "touching
  mid re-checks exactly mid, top, side", "restoring is a hit", "a corrupt record is not trusted".
* `wall-cache-conformance.sh`: nbb reading == Kotoba reading (KIR interpreter) on 6 inputs; the key equals an
  independent `shasum` of the documented material; `record-digest` likewise.
* A bug found by the selftest and fixed before commit: the id of the first node was empty (awk `n`
  uninitialised), dropping every edge into it. Real-list keys before that fix were wrong for that one node; the
  numbers above are from after the fix.

Differential (`ds-diff.sh`, `WALL_GOLDEN_CACHE=1`, 40 forms from the sema tests): first run `golden: miss`, second
run `golden: hit` with the host side skipped, identical result (`compared: 40 agree: 40 disagree: 0`), 79.1 s
and 79.3 s. No gain at this size: the host side (`desugar-expr` over 40 forms) takes milliseconds and the 79 s is
linking and running the guest. At 500 forms (`DS_MAX=100 DS_TOTAL=500`) the host side took 600 ms in total while
the guest side was still running after 10 minutes (stopped; the guest-side figure is another agent's speedup 1/2).
So for `ds-diff` the golden cache removes under 1% of the time. A tampered golden file is rejected (`golden-cache: rejected`) and recomputed.
