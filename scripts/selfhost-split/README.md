# selfhost-split

> **Superseded.** This prototype is now `amu refactor` (`plan`/`apply`/`graph`/`partition`/`split`/`verify`, nbb only, no Python): see `docs/refactoring.md`. Kept as the reference the port was checked against.

AST-based tooling for cutting a very large `.cljk` namespace (first target:
`kotoba-sema/src/kotoba/compiler/frontend.cljk`, ~22.5k lines, 912 top-level forms) into
independently portable modules, so the Kotoba-route port (`amu check`) can proceed per module,
in parallel, instead of as one 22k-line wall.

Stdlib-only Python 3 (no EDN library needed) for analysis and extraction; nbb only for the
verification runs. Nothing here edits the repo `src` tree: all output goes to a scratch directory.

## Pipeline

```
run-split.sh SRC.cljk WORK            # = analyze.py partition + extract.py
python3 roundtrip.py SRC WORK/split   # structural check: every form, byte-identical, exactly once
python3 verify.py --sema <kotoba-sema> --orig SRC --split WORK/split --out WORK/v [--all] [--raw]
node ... crosscheck-reader.cljs SRC WORK/graph.edn   # Python parser vs. repo reader (kotoba.sema/read-forms)
python3 consumers.py <dirs> --split-report WORK/split/split-report.json --report   # facade-unsafe consumers
```

| file | role |
|---|---|
| `cljparse.py` | concrete-syntax parser with exact offsets; reader conditionals (`#?`, `#?@`) are ordinary nodes so every dialect branch is analysed |
| `sourcegraph.py` | top-level forms, defined names (per reader-conditional feature), docstrings, `^:dynamic`/`^:private`, scope-aware reference extraction (let/loop/fn/defn/for/doseq/destructuring/`binding`/`case`...) |
| `analyze.py graph` | `graph.edn`: nodes, weighted edges, SCCs, dynamic vars (defined in / read by / bound by) |
| `analyze.py partition` | `partition.edn` + `partition.json`: module partition, sizes, cross-module edge count, blocking cycles, plan to open the biggest cycle |
| `extract.py` | writes the modules and a facade (scratch dir) |
| `roundtrip.py` | proves the cut lost/duplicated nothing |
| `verify.py` | runs the sema tests on the original and on the split, compares failing sets |
| `consumers.py` | finds (and, as a verification overlay, retargets) `binding`/`with-redefs`/`alter-var-root`/`set!` on facade vars |
| `names-frontend.json` | labels for the auto-detected modules (`{anchor-form-name: label}`) |

## How the partition is chosen

1. Atoms are the strongly connected components of the reference graph, so a cycle is never cut
   (a require cycle cannot exist).
2. The *driver* (the form that sequences the passes: `analyze-forms**`) is auto-detected as the
   largest-closure form that directly calls >= 3 big, distinct passes. Its direct callees are the
   pass roots (desugar, infer, validate, rewrite-record-projection, row, state-ability, ...).
3. Every atom gets its *owner set*: the roots whose transitive closure contains it. A dependency
   always has a superset owner set, so grouping atoms by owner set gives a module graph that is a
   DAG by construction (0 backward edges).
4. Owner-set groups are merged greedily (strongest connection, token-vocabulary affinity, size cap,
   minimum module size) while the quotient stays acyclic, until the requested count remains.

## Extraction rules

* Forms are copied byte-for-byte with the comments before them. The only edits are `defn-` -> `defn`
  and dropping `^:private` (cross-module access).
* Each module gets: `ns` with only the `:require` specs its code uses (original reader-conditional
  wrappers kept), `:refer` of exactly the names it takes from earlier modules (names that exist only
  on some platforms are referred under the same `#?@` condition), the `#?(:kotoba (:schemas ...))`
  clause when it mentions those record types, and a `(declare ...)` for forward references inside
  the module (the original `declare` forms are regenerated, their comments carried along).
* The facade keeps the original ns name and `:kotoba/export` map and re-exports every name
  (`(def x module/x)`, keeping `^:private`/`^:dynamic`, platform conditions respected).

## Known limitation: writes through the facade

`(def x module/x)` is a different Var from `module/x`. Calls and reads are identical; `binding`,
`with-redefs`, `alter-var-root` and `set!` on a facade var do not reach the module that owns it.
`consumers.py` lists these write positions (for the frontend: `sema.cljk`'s eight `max-*`
`with-redefs`, and `type_directed_arithmetic_test`'s `*numeric-resolution-final*` binding);
`verify.py` runs the split with patched copies of those consumers (retargeted to the owning module)
and shows the unpatched behaviour for comparison.
