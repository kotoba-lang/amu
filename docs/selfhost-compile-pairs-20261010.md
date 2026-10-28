# crc32 and matmult-int on the Kotoba compile route: the pair arena (2026-10-10)

The self-built amu image's product `compile` (nbb.cli's Kotoba `run!` over kotoba.compiler.native-artifact, status
doc section 8) refused two Embench ports the host compiles: `bench/embench/ports/crc32.kotoba` and
`matmult-int.kotoba` (exit 120, `KEXE_TRAP {:kind :budget :reason :budget/cells :arena :pairs}` at the 64 Mi pair
ceiling). The other 17 ports give the host's artifact. This note finds the cause the way
docs/selfhost-lazy-sequence-vectors-20261009.md did, by measuring each phase.

## 1. Which phase allocates the pairs

The image run of crc32 (`build/fp/g3/amu compile ... --policy` with `KEXE_ARENA_USE=1`): the pair arena runs out after
85 s, with 67,108,864 pairs (all of the budget), 21.8 M vector handles and 56.0 M vector items in use. statemate
(783 B of source, 448 B of code) needs 2.0 M pairs for the whole compile.

`seed/tests/compile-pairs/probe.sh` builds a probe entry against the image's own objects (build/fp/g3/o, 172 objects,
seed r6n) and runs nbb.cli's steps one stage at a time with the image's budgets. Nothing is reclaimed on this route, so
a stage's high-water mark minus the mark of the stage it extends is that phase's allocation. crc32 (pairs at the end
of each cumulative stage):

| stage | pairs |
|---|---:|
| frontend (`sema/analyze`) | 258,194 |
| + `lower!` (kir/lower, oracle) | 259,664 |
| + `native-program` | 259,890 |
| + `compatibility-form` | 260,497 |
| + `definition-identity/describe` (no emit) | 286,178 |
| + kotoba.native.aarch64 `emit-program` | **53,377,289** |
| `compile-unverified` (all of the above, sealed artifact) | 53,561,188 |

The emitter allocates 99.5% of the pairs, and nbb.cli runs it twice: once in `assemble` and once more in the verifier's
code-region check, which re-emits the program, as the host verifier does. So crc32 needs about 2 x 53 M pairs. On
matmult-int (29,864 B of code), one emit already traps at 66.7 M pairs.

Inside `emit-program` (crc32, cumulative from `native-program`):

| emitter step | module (repo, revision in the image) | pairs | vector items |
|---|---|---:|---:|
| rewrites + helper augmentation | kotoba-native | 433,796 | |
| `machine-ir/lower-kir-module` (KIR -> GMIR) | kotoba-native 752cdf2 | 2,764,508 | 8,135,770 |
| `mir/select-target-result` | kotoba-mir 60d4174 | 9,883,590 | 9,747,445 |
| `machine-ir/hoist-program-consumers` | kotoba-native | 10,013,831 | 24,520,226 |
| `mir/allocate-registers-result` | kotoba-mir | 29,353,761 | 27,858,397 |
| `coalesce-program-moves`, `lower-mc` | kotoba-native | 37,697,899 | 28,036,973 |
| `encode-mc-module` (no fuel prefixes) | kotoba-native | 42,319,687 | 28,632,807 |
| whole `emit-program` (+ fuel instrumentation: `counted-self-recur-plans-of-gmir` again) | | 53,377,289 | 30,392,971 |

amu's own code in this route (native-artifact, definition-identity, provenance, nbb.cli) allocates less than 0.3 M
pairs on crc32. None of the emitter modules are amu's: kotoba.native.* is kotoba-native, kotoba.mir is kotoba-mir,
and kotoba.form is kotoba-hir. The image farm has them at those repos' `agent/dual-runtime-port-D` heads (blob
match).

## 2. Proportional, accumulated, or quadratic

All three, and the volume is in upstream code:

- **The per-instruction constant is the main part.** One Form value (`kotoba.form`'s record) costs 5 pairs and 1
  vector (probe `u:kwf`, `u:intf`: 1,000,000 creations = 5,000,000 pairs and 1,000,000 vectors). A `form-get` that
  misses costs a second Form (`u:get-miss`: 10 pairs), because it answers a fresh `(nil-form)`. kotoba-mir's
  helpers `fget` / `fhas?` / `kassoc` build a key Form on every lookup: `(form/form-get m (form/keyword-form k))`.
  The file has 506 `fget` uses and 101 `kassoc` uses. kotoba-native's machine-ir already avoids this with `kslot`
  ("every Form is seven pairs and a vector, and the native heap is not reclaimed yet"), but kotoba-mir does not.
  A straight-line function (a let chain of k arithmetic bindings) costs pairs linear in k: 2.17 M, 4.25 M, 8.57 M
  and 17.8 M for k = 50, 100, 200, 400, about 3,700 pairs per byte of code.
- **Accumulation.** The host runs the same passes and its GC frees each temporary. On this route nothing is
  reclaimed (seed 21-check `ck-r6m-arena`: `arena-scope` compiles as `do`), so a whole compile needs the sum of
  all temporaries, twice over because of the verifier's re-emit.
- **A quadratic part, in two kinds.**
  1. kotoba-native's vreg tables: `vt-put` copies the whole table with `vector-assoc` on every definition and use.
     This happens in `gmir-defs`, `dce-used`, `hoist-use-table` (three tables) and the hoist loop's `def-orig`,
     so the vector items grow as instructions x vregs. On matmult-int, `lower-kir-module` uses 16.5 M items and
     `hoist` another 31 M.
  2. Control flow: per doubling of nesting depth, nested `if`s cost x2.9 to x3.0 in emitter pairs while the code
     only doubles. Measured with 16-element vector arms of depth 2 / 4 / 8 / 16: 3.0 M, 6.9 M, 17.9 M and
     52.4 M pairs for 2,212, 4,380, 8,720 and 17,396 B of code. crc32's `table-at` is exactly this shape at depth
     16, and matmult-int's `expected-at` is depth 20 with 20-element arms.

Pairs per byte of code over the ports: statemate (448 B) 2,000 (fixed cost), aha-mont64 1,400, md5sum 1,160,
nettle-sha256 1,150, ud 1,770, crc32 2,985, matmult-int > 2,230 (trap).

## 3. The fix: upstream (kotoba-mir, kotoba-native). Nothing in amu to change

amu has no bug or accumulation of its own here. The only amu-side lever is the verifier's second emit. Dropping it
would weaken the verifier twin, which re-derives the code the way the host verifier does. It would also not be
enough, because one emit of matmult-int exceeds the ceiling. So it stays. Raising the pair budget is not available
either: the image already runs at the loader ceiling (`KEXE_PAIR_MAX` 64 Mi), and the vector-item budget is at its
ceiling too (`KEXE_VECTOR_ITEM_MAX` 128 Mi).

The minimal upstream changes, measured on a copy of the image farm with only these files changed (dependents rebuilt
with seed r6n; repos not edited):

**A. kotoba-mir `src/kotoba/mir.cljk` (branch agent/dual-runtime-port-D 60d4174), Kotoba reading only:** keyword-keyed
lookups without a key Form, as machine-ir's `kslot`:

```clojure
(defn- kslot [m [:ref :form/r] k :keyword] :i64
  (let [xs (form/kids-of m) n (vector-count xs)]
    (loop [j 0]
      (if (>= (+ j 1) n) -1
        (let [x (typed-list-nth [:list [:ref :form/r]] xs j)]
          (if (and (form/is-keyword? x) (= (form/keyword-value x) k)) j (recur (+ j 2))))))))
(defn- fget [m k :keyword] (let [j (kslot m k)] (if (< j 0) (form/nil-form) (typed-list-nth [..] (form/kids-of m) (+ j 1)))))
(defn- fhas? [m k :keyword] (>= (kslot m k) 0))
(defn- kassoc [m k :keyword v] (let [j (kslot m k)]
  (form/assoc-form m (if (< j 0) (form/keyword-form k) (typed-list-nth [..] (form/kids-of m) j)) v)))
```

(the type annotations as in the file; `form-get` finds the first key that is `eq` to the given one, so the answers do
not change).

**B. kotoba-native `src/kotoba/native/machine_ir.cljk` (branch agent/dual-runtime-port-D 752cdf2), Kotoba reading
only:** `vt-put` writes in place, `(vector-assoc! (vt-grow t (inc i)) i x)`. Every caller threads the table as a
loop accumulator and never reads the version before the write. The one place that looks like an exception is
`hoist-use-table`'s inner loop, which starts from `last` and is then repeated on `last` itself by `last-p`. That
second loop writes the same values, so the result is the same either way. Upstream should confirm linearity at each
of the 10 call sites when it takes this change.

| crc32, `emit-program` | pairs | vector items |
|---|---:|---:|
| image (as built) | 53,377,289 | 30,392,971 |
| A | 14,116,220 | |
| A + B | 14,116,244 | 13,194,782 |

| matmult-int | pairs | vectors | vector items |
|---|---:|---:|---:|
| image, one emit | > 66.7 M (trap) | | |
| A, whole compile (`compile-native` + provenance + texts) | 46,478,511 | 29,313,252 | 128,466,238 (95.7% of 128 Mi) |
| A + B, `emit-program` | 23,082,516 | 14,157,470 | 25,437,603 (was 62,979,290 with A alone) |

A alone gets both programs under the pair ceiling, but it leaves matmult-int at 95.7% of the vector-item ceiling. B
removes the instructions-x-vregs copying. The whole-compile peaks with A + B are in section 4.

## 4. Verification (A + B, through the compile-cli entry built from source)

Peaks of the whole compile with A + B (the probe's `full`: `compile-native` with the verifier step, provenance, both
texts), at the image's budgets:

| program | pairs (of 64 Mi) | vectors (of 64 Mi) | vector items (of 128 Mi) |
|---|---:|---:|---:|
| crc32 | 28,370,191 (42%) | 16,840,059 | 27,634,644 (21%) |
| matmult-int | 46,478,507 (69%) | 29,262,278 (44%) | 53,382,864 (40%) |

These need no change to any budget or ceiling.

The product entry: nbb.aarch64-cli's Kotoba `run`, routed as the image routes it (a two-line entry calling it with
the argv). It is built from this tree's sources by seed r6n against the image's objects (build/fp/g3/o) with A and
B applied. Its aarch64-cli, nbb.cli, native-artifact and bounded-edn objects are byte-identical to the image's.
The comparison is `seed/tests/compile-cli/run.sh`'s, with its guest wall and CPU limits raised for a load average
of 210-290. It covers the 19 Embench ports plus every 4th program of the harness's 372-program corpus (93), 112 in
all:

- crc32 and matmult-int: BOTH-ACCEPT, seal SAME, provenance SAME, stdout SAME, publication SAME-SHAPE (they were
  HOST-ONLY, exit 120, pair arena).
- The other 110 rows are identical to the image's own runs (status doc section 8: compile-corpus-image /
  compile-embench-image) in all 12 comparison columns and the guest message: 90 BOTH-ACCEPT SAME (89 SAME-SHAPE,
  1 SIZE-DIFF), 16 BOTH-REFUSE, 1 BOTH-REFUSE-CLASS-DIFF, 3 HOST-ONLY, all as before. With the two Embench ports
  the totals are 91 SAME-SHAPE + 1 SIZE-DIFF accepted.

The image itself was not rebuilt, because nothing in amu changed. Its fixed point (section 8) stands. A rebuild
belongs to the step that brings A and B into the farm.

## 5. What remains

- A and B have to land upstream (kotoba-mir and kotoba-native `agent/dual-runtime-port-D`). Then the image farm takes
  them, by a selfbuild-inputs overlay like osaho's interp/target or by a new snapshot, and the image is rebuilt to
  its fixed point. Until then the image keeps refusing crc32 and matmult-int.
- Even with A + B, the route allocates thousands of Forms per machine instruction and reclaims none of them. The
  remaining volume is in kotoba-mir (`select-target`, the allocator) and kotoba-native (KIR -> GMIR, hoist's
  `form-insert`, which copies the whole instruction list for each hoisted instruction, and encoding). The general
  cure is reclamation (a seed rung that makes `arena-scope` real) or a reclaiming compiler image. Programs a few
  times larger than matmult-int (about 30 KB of code) will reach the ceilings again.
- kotoba.form (kotoba-hir): `form-get` on a miss allocates a fresh nil Form. A shared nil would save 5 pairs per
  miss on every route.
