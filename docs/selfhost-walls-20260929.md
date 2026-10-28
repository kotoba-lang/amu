# Selfhost walls, 2026-09-29

First refusal of each of the 316 sources on the compiler's classpath (amu `check`, project route,
`--source-path` every src root + `kotoba-lang/lang/compat`), scanned in parallel with
`wall-one.sh`-style single-file checks. This is a scoreboard of the *first* wall of each file, not the
number of walls: a file that clears one meets its next.

| result | files |
|---|---:|
| admitted by `check` | 11 |
| refused | 305 |

## By kind

| kind | files |
|---|---:|
| E. module with only private defns | 56 |
| other | 50 |
| A. dynamic data | 35 |
| A. dynamic data: untyped parameters (needs the compiler-data model) | 29 |
| G. library surface not admitted (coll / text / wasm-type / link) | 25 |
| C. host interop in the ns (:import) | 21 |
| B. #?(:clj)-only bodies (needs a :kotoba branch per function) | 18 |
| N. missing native/kototama modules on the source paths | 12 |
| K. row-polymorphic exports | 12 |
| D. char literals / char ops | 11 |
| H. regex literals in callers | 9 |
| F. typed-set item typing ([:set :keyword] with i64) | 7 |
| I. keyword-as-function callbacks | 6 |
| J. binding forms | 5 |
| L. atoms at top level | 5 |
| M. reduce shape | 4 |

## By message

| files | first refusal |
|---:|---|
| 49 | project module exports nothing: every top-level defn is private |
| 29 | count requires a bounded vector, a typed set or a canonical typed map; got :iN. |
| 25 | qualified call is not an admitted exported import |
| 18 | function body is empty; a function must contain one result expression (a body that is only a `#?(:clj ...)` with no :kot |
| 15 | namespace clause :import is not admitted: host interop (a Java / JS class) is outside the language; the admitted clauses |
| 12 | required module is missing from the explicit source paths |
| 12 | exported function has a row-polymorphic parameter |
| 11 | OK |
| 11 | unknown operation: char is not a builtin, a sugar head, or a function of this module |
| 9 | host regex literal #\ |
| 8 | quoted list has no literal spelling |
| 7 | at least one defn is required |
| 7 | set item type mismatch: this set is [:set :keyword], so every item must be :keyword; this one is :iN. A `#{...}` literal |
| 6 | record-get without a type descriptor requires a record value; got :iN |
| 6 | expression type mismatch: expected vector-iN, got [:set :keyword] |
| 6 | import names a host module by string; a Kotoba module is a simple symbol |
| 6 | map callback must be a named function, an inline fn, or a closure value; got a keyword literal -- a map source is a vect |
| 5 | let requires an even binding vector |
| 5 | def value is stateful/effectful: (atom ...) -- move it into a function or a capability |
| 5 | record get requires a value and one keyword field |
| 4 | reduce fn must be (fn [acc x] single-expr) |
| 3 | expression type mismatch: expected iN, got vector-iN |
| 3 | constant value must be closed bounded integer/string/keyword/boolean/nil/vector/map or non-empty keyword-set data |
| 2 | fn value requires unique arities with zero to four unique parameters |
| 2 | ex-info data map keys must be keywords |
| 2 | constant alias must name a declared constant |
| 2 | expression type mismatch: expected vector-iN, got string |
| 2 | reduce requires callback+collection or callback+init+collection |
| 2 | unknown operation: concat is not a builtin, a sugar head, or a function of this module |
| 2 | some with two arguments is clojure.core/some (a predicate over a collection); in this language `some` is the option cons |
| 2 | try requires exactly one body expression and one catch clause |
| 2 | expression type mismatch: expected [:list :string], got iN |
| 2 | unbound symbol has no value type: target-profile is not a parameter, a let binding, or a function of this module; neares |
| 2 | only ns, def, defn, and defn- are allowed at top level |
| 1 | variadic function deep-merge is used as a value; a variadic defn is specialized per call site and has no single interfac |
| 1 | variadic function addN is used as a value; a variadic defn is specialized per call site and has no single interface, so  |
| 1 | unknown operation: instance? is not a builtin, a sugar head, or a function of this module |
| 1 | variadic function file is used as a value; a variadic defn is specialized per call site and has no single interface, so  |
| 1 | atom must be the init expression of a let binding (atom slice N admits swap!/reset!/deref in straight-line code of the b |
| 1 | deref expects a let-bound atom cell as its first argument; got `buf` (atom slice N) |

## What moved in this round (all measured)

| change | effect |
|---|---|
| `text` twin: `split`/`split-lines` on `typed-list-conj` | `text/split` now admitted on the project route (host oracle: 24 of 26 inputs, the other differs by design) |
| `contains?` on a typed set | clears the `contains? requires a canonical typed map` refusals in `affine` (12 rows) |
| source bound 1 MiB → 8 MiB (ADR 0356) | 30 of 316 sources moved past the size wall |
| descriptor bounds depth 12→64, nodes 64→512 (ADR 0355) | an unrolled s-expression sum type nests 31 levels |
| `typed-list-conj` | run-time-length `[:list T]` on the KIR interpreter and natively on AArch64 (result 1) |

## What is left, and why it is not a list of small fixes

The largest kind (A) is one thing seen many ways: the compiler's passes walk
Clojure data — HIR maps, effect rows, policies, s-expressions — through
unannotated parameters (which default to `:i64`) with `count`, `first`, `get`,
`vector?`. Kotoba needs the compiler's own data model spelled as types: a closed
sum type for s-expressions (now expressible to 31 levels), records for HIR and
policies, and the Clojure accessors resolved on those types the way `contains?`
now is on a typed set. That is a design of the compiler's internal data, then a
port of about 140 modules onto it; it is not a patch series.

Order of attack, cheapest and most certain first:

1. **G** — finish the library surface: `coll` set algebra as twin templates over `[:set elem]`
   (`set/union` etc.), `text/lower`/`upper` (ASCII, documented), `typed/wasm-type`, `link/link?`.
2. **H** — regex literals in callers: 15 literal-separator `split` sites become strings (the host `split`
   already accepts a string); the 26 real regexes need `bounded-regex` or a rewrite.
3. **B, C, D, E, J, L, M** — per-module rewrites with a `:kotoba` branch; mechanical but numerous.
4. **A** — the compiler-data model (records/sum types + accessor resolution). The long pole.
5. **N** — put `kotoba-native` / `kototama` sources on the measurement's source paths.

Then, per ADR 0354, native is the reference: a feature the native compiler needs to build itself
(typed sets, typed maps, `string-upper`) is added to native rather than waited on from wasm32.
