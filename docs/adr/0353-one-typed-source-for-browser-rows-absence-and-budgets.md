# ADR 0353 — One typed source for browser: rows, absence, hiccup nodes and budgets

- Date: 2026-09-25
- Status: Accepted (owner decision, 2026-09-25). Decides ADR 0352.
- Ladder: `docs/language-ladder.edn` — one floor per change below, each closed
  by its own test on `origin/main`; climbed by the superproject loop
  `cloud.itonami.bot.amu-language` (skill `amu-language`).
- Amends when their floors land: ADR 0005 (exports), ADR 0028 (truthiness),
  the shared ADT budget (osaho `adt-node-limit` 64 / `adt-depth-limit` 12),
  ADR 0005's 1 MiB linked-source bound.

## Context

ADR 0352 measured why kotoba-lang/browser's reducers do not compile: they are
Clojure over open maps and hiccup, and amu's application profile is closed and
static on purpose. It offered A (a dynamic value), B (caller-driven inference)
and C (one typed source for both engines).

Read closely, the reducers use four kinds of dynamism, and each is a static
idea spelled dynamically:

| browser writes | it means |
|---|---|
| `assoc` / `dissoc` / `merge` on an open map | a record whose field set grows or shrinks |
| `nil` in a map, then `when` / `if-let` / `cond->` | presence or absence of a value |
| `string?` / `vector?` over hiccup | a closed sum: text, element, fragment |
| a function stored in a map | a function value with an effect row |

None of them needs a type carried at run time.

## Decision

**Not A.** A dynamic Clojure-data value would give up all three properties the
language exists for: safety (ADR 0028's no coercion, no truthiness), speed
(runtime tag checks and a collector), and code identity (types leave the
definition CID, ADR 0300).

**C, reached through a principled B.** kotoba-lang/browser becomes one source
that amu compiles for the hosted engine (cljs / wasm32) and for the kernel
(x86_64-aiueos-kernel-v1, aarch64-macos). To make that source read like the
Clojure it is today, the language gains:

1. **Exports from publicity.** A module's export vector is its public
   top-level definitions (`defn`, `def`); `defn-` is private. An explicit
   `:export` still wins. The interface CID is computed from the public set.
   (Amends ADR 0005; closedness is unchanged — the set is still exact.)
2. **Absence, not nil.** `nil` as a map-literal value makes that field
   `[:option T]` and absent. Truthiness exists on `:bool` and `[:option T]`
   only; `when`, `if-let`, `when-let`, `cond->`, `some->` over an option
   desugar to `option-match`. Numbers, strings and records are never truthy.
   (Narrows ADR 0028's "no truthiness" to "no truthiness except presence";
   coercion stays refused.) Landed 2026-09-25 (floor `:absence`, gate
   `nil-field-is-absence-test`) with one measured cut: a literal learns T
   from the record its context names (a declared record result, a record
   field); `nil` with no record in context is refused by name, and the row
   inference of point 3 is what will supply T there. Strings and records are
   refused as tests. Numbers landed the same day as floor `:bool-predicates`
   (gate `numbers-are-never-truthy-test`): an `:i64` test is refused by name
   ("if test is :i64, and a number is never truthy: ...") through every form
   that reaches `if`, including `and` / `or` / `not` and a `filter`
   predicate, and the six predicate operations whose KIR answer is still the
   legacy 0/1 `:i64` (`record-equal`, `typed-map-equal`, `typed-set-equal`,
   `hetero-vector-equal`, `task-ready?`, `object-cas-won`) are elaborated to
   `(= op 1)`, so the language sees `:bool` and the backends are unchanged.
   Ten amu sources that tested numbers were migrated with their expected
   values unchanged; five aiueos kernel sources (`journal-plan`,
   `journal-record-build`, `mutable-object-build`, `service-registry-build`,
   `value-handle-arena`, all testing a 0/1 `write-u32` answer) are refused
   by this amu (exit 65; the first four have committed objects) and must be
   migrated when aiueos next re-attests its objects. No aiueos source uses the
   six elaborated operations, so no other aiueos object changes because of
   this floor. `task-ready?` stays one linear consume: the ownership check
   sees through its elaboration.
3. **Row-polymorphic records with principal inference.** An unannotated
   parameter's type is inferred from its uses as a row: `(defn f [m] (:a m))`
   is `{:a T | r} -> T`. `assoc` extends the row, `dissoc` shrinks it,
   `merge` and `select-keys` are row operations; a vector of records is an
   ordinary type. Every row variable is instantiated at compile time
   (monomorphization); each specialization's CID is derived from the generic
   definition's CID and its type arguments, so ADR 0300's compile-once cache
   holds. There is still no dynamically shaped record boundary (ADR 0214): the
   shape is known at every call. The bounded keyword->i64 map is retired.
   Landed 2026-09-25 as three floors, because they are three changes. Floor
   `:row-records` (gate `row-polymorphic-record-inference-test`): a parameter
   read as a record (`(:a m)`) or passed on to a row parameter is the row
   `{:a T | r}`, and its function exists only as `f__row_<i>_<record>`, one
   specialization per record type a call passes, typed at that record; the
   generic is dropped. Refused by name: a non-record argument ("argument 3 to
   f is i64, and parameter m of f is the row {:a T | r}: only a record
   satisfies a row"), a record lacking a field the row reads, an exported
   generic (an export has one ABI: annotate it or `defn-`), a generic used as
   a value. A record crossing a function boundary, annotated or a row
   specialization, compiles for both native targets since floor
   `:native-record-boundary` (point 9).
   Floor `:row-operations` (gate `row-operations-extend-and-shrink-test`,
   2026-09-26): on a record, `assoc` of a field it has keeps its type (the
   value must be the field's type, no coercion), of one it lacks extends it;
   `dissoc` / `select-keys` shrink it, naming only fields it has and keeping
   at least one; `merge` assoc's every field of a record or keyword-keyed map
   literal. A changed field set is the anonymous closed record a map literal
   with those fields lowers to, never the keyword->i64 map. kotoba-sema
   elaborates each to `record-new` / `record-get` / `record-assoc`, so KIR and
   the backends see nothing new; a parameter a row operation uses is a row.
   Refused by name: a missing field ("dissoc names field :z, which record
   :b/s does not have: a row shrinks only by fields it has"), a record left
   with no field, a computed field, a non-record receiver or merge operand.
   Hosted (`wasm32-browser`) compiles these forms, and since floor
   `:native-record-operations` both native targets do, hand-written forms
   too (point 9).
   Floor `:row-unification` (gate
   `row-literal-join-and-loop-unification-test`, 2026-09-26): a keyword map
   literal written as a row argument is that row's record, the anonymous
   closed record of its fields typed by its values (`(f {:a 3})` runs as
   `f__row_0_kotoba_map_literal_a`); two parameters that are the branches of
   one `if` are one row and read what it reads, so `(defn- pick [m n] (if (>
   (:a m) 6) m n))` returns its record; a loop helper -- and so a `reduce` /
   `map` closure -- is generic with its function; a slot's reads include those
   of the rows it is passed on to, so a missing field is refused at the
   outermost call. Refused by name: two record types at one join ("arguments
   (mk) and (mt) to pick are [:ref :b/s] and [:ref :b/t], and parameters m
   and n of pick are branches of one if, so one row: a row is one record type
   at each call"), a literal lacking a read field, a coerced field, a
   non-record, an exported generic, an `:i64` if test. Hosted
   (`wasm32-browser`) compiles these forms. Natively, since floor
   `:native-record-boundary`, a join returning its record (`pick`), a loop
   helper and a `reduce` closure over a declared record compile for both
   targets with the oracle verified, and since floor
   `:native-record-operations` a projection of the join itself (`(:a (if c
   m n))`) does too. Programs admitted before are
   unchanged -- every new row slot was a refusal.
   Floor `:literal-typing` (gate `record-vector-and-map-literal-retirement-test`,
   2026-09-26): a literal is typed by its items. kotoba-sema's `type-literals`
   runs once every signature is known and before rows are specialized, so a
   keyword map literal is the anonymous closed record of its fields wherever
   it is written (a `let` binding of one passed to a row is that row's record;
   `(defn- m [] {:a 3 :b 4})` answers `[:record :kotoba.map-literal/a+b ..]`),
   and a vector literal of non-`:i64` items is a typed vector -- `[:list T]`
   when every item is one T (`(nth [(mk) (mk)] 1)` is the record, at any
   index), the heterogeneous `[:vector [T ..]]` otherwise. The keyword->i64
   pair map is no longer what a literal is: reading a key a literal lacks is
   refused ("record field must be a declared keyword literal"), not 0, and a
   literal is not counted. Refused by name beside it: a coerced field, a
   record as an `if` test, `=` over records, a typed vector item used as an
   i64. Native: a literal record compiles for `x86_64-aiueos-kernel-v1` and
   `aarch64-macos`; a `[:list record]` does too since floor
   `:native-handles`.
   Floor `:specialization-identity` (gate
   `specialization-cid-derived-from-generic-test`, 2026-09-27): a
   specialization's definition CID is a function of its generic's body and the
   record types it is specialized at, and of nothing else -- not the generic's
   name, the specialization's name (`f__row_0_b_s_2` around a taken name), the
   caller or the module. That was measured to hold already: kotoba-sema
   monomorphizes before KIR and ADR 0300 hashes the monomorphic KIR, whose
   body names callees by CID and carries the record descriptor inline, and
   whose interface seals the schema. So two modules specializing one generic
   at one record share the CID, a recursive generic and a loop helper included,
   and it is the CID of the hand-written twin `(defn- f [m [:ref :b/s]] ..)`;
   a private rename of the generic leaves ADR 0300's cache material equal.
   The floor first asked for a CID derived from "the generic definition's
   CID". There is none: the generic never reaches KIR, and inventing an
   identity for it is what ADR 0300 refuses; deriving the specialization's
   from it would also have split the specialization from its hand-written
   twin, i.e. broken the compile-once sharing the floor is for. The gate pins
   both directions -- sealing a definition's name turns its seven sharing
   assertions red, dropping the body and the schemas turns "another body" and
   "another schema" red. Not done: a report field naming the generic and type
   arguments a specialization came from (provenance, unsealed); it needs a
   kotoba-hir function key and is not what identity or the cache rests on.
   A CID is target-independent (`definition-cids` takes no target). Native:
   since floor `:native-record-boundary` the gate's modules, generic,
   hand-written and recursive alike, compile for both
   `x86_64-aiueos-kernel-v1` and `aarch64-macos` with the oracle verified.
4. **Function values.** A function type carries its effect row; a closure is a
   one-word handle (code, environment) under aggregate ABI v8 and may be a
   record field or vector element. A stored function's effects are part of the
   record's type, so nothing ambient enters. Split on 2026-09-27 into two
   floors. `:stored-closures` (gate `stored-closure-in-record-and-vector-test`,
   landed 2026-09-27): the ADR 0352 internal error was not a missing type --
   kotoba-sema built a record literal's (and a `record-new`'s) fields as a lazy
   seq, so the `fn` was lowered after the binding holding the lambda counter
   had ended; each defn and lambda body is now realized inside its binding. A
   closure stored in a record field or vector element is called out of it on
   the KIR interpreter, compiles for `x86_64-aiueos-kernel-v1` and
   `aarch64-macos` (the aarch64-macos kexe printed 11 and 10 under
   `tools/kexe_loader.c`), and its capability is in the caller's effect row.
   `:function-values` (gate `function-value-in-record-test`, landed
   2026-09-27): a closure is a function, not a number. kotoba-sema's closure
   analysis (`infer-closure-refinements`), which already knew which words are
   closures -- a let-bound fn, a call whose result is a `[:fn ...]` contract,
   a `[:fn ...]` record field -- refuses every number operation over one
   (`a function value is not a number`) and `=` (`a function value has no
   equality`). A fn literal where a record field is declared `[:fn ...]` is
   lifted under that contract; a number there, or a value that is not a
   closure, is refused. The closure stays the one-word `(lambda-id,
   captures)` handle; KIR, which has no function type, receives the field as
   `:i64`, as a `[:fn ...]` result or parameter contract already reached it,
   and a module with no such field keeps its HIR and CIDs. Both native
   targets compile it, oracle-verified through the CLI; the aarch64-macos
   kexe of a capturing fn stored in a `[:fn ...]` field and called with 5
   printed 15 under `tools/kexe_loader.c`. Not yet: a closure reaching an unannotated parameter
   is that parameter's `:i64` (the analysis propagates requirements toward
   callers, not closure-ness toward callees), and a closure in a map-literal
   field or vector element is an `:i64` field or element. A DECLARED effect
   row is floor `:function-effect-rows`: `[:fn ...]` has no effect component
   today, so a stored closure's effects are the caller's by inference only.
5. **Strings by code unit, by name.** `count` of a string stays refused (it
   has two answers). `string-code-unit-count`, `string-code-unit-at` and
   `subs` over code units are primitives; browser's `#?(:clj ...)` interop
   branches gain a `:kotoba` branch that calls them. Landed (kotoba-sema
   `baeddf12`, gate `string-code-unit-primitives-test`) as library heads over
   `string-code-point-at` / `string-substring`, so every backend answers the
   same; an index outside the string traps out of bounds, and a `subs` bound
   inside a surrogate pair traps as splitting a code point (UTF-8 cannot hold
   a lone surrogate). Each call walks the string from its start: O(n).
6. **Hiccup is syntax for a node ADT.** `Node = Text string | Elem tag attrs
   [Node] | Frag [Node]` over ABI v8's recursive `[:ref q]`. A hiccup literal
   desugars to it at compile time; runtime shape tests over hiccup become an
   exhaustive `variant-match`.
   Landed 2026-09-30 (kotoba-sema `25618d31`, gate
   `hiccup-literal-is-node-adt-test`). The type is the language's, named
   `[:ref :kotoba.hiccup/node]`: `[:text :string] | [:elem [:ref
   :kotoba.hiccup/elem]] | [:frag [:list [:ref :kotoba.hiccup/node]]]`, the
   element `{:tag :keyword, :attrs [:map :keyword :string], :children [:list
   [:ref :kotoba.hiccup/node]]}` (a record inside a variant must be its own
   schema, so there are two). A module that names it gets both schemas and may
   not redeclare them. The literal is typed by its context, as `nil` was in
   point 2: where a node is expected -- the tail of a function or `fn` declared
   to return one, an argument at a parameter declared one, a literal's child --
   a tag-headed vector is an element, `[:<> ..]` a fragment, and a string, a
   `:string` parameter or a `str` / `subs` call is text. It is a source rewrite
   before desugaring, so the literal is the hand-written `variant-new` /
   `record-new` / `typed-list-new` and has their definition CID. Elsewhere a
   vector literal is still a vector, and a module that does not name the type
   is returned unchanged (no existing CID moves). A shape test over a node
   (`string?` / `vector?` / `seq?` / `sequential?` / `coll?`, in a `cond`, an
   `if` or alone) is a `variant-match`; in a branch that one case reaches, the
   node is that case's payload -- the string, the element record, the child
   list -- as browser's `render-content!` reads it. Refused by name: a shape
   test that misses a case or is unreachable, a shape a node never has
   (`map?`), a number, keyword or `nil` child or attribute value (no coercion;
   absence is not a child), a node as an `if` test, `=` over nodes. Measured
   cut: a child that is neither a literal, a string-typed parameter nor a
   `str` / `subs` call must be a node (a string from a record field is written
   `(str ..)`), and an attribute value is a string (browser's `:style` map is
   not yet a node attribute). Hosted: `amu check` exits 0 and
   `wasm32-browser` compiles. Native: both `x86_64-aiueos-kernel-v1` and
   `aarch64-macos` refuse at the typed-values gate (`:kotoba/target-rejected`,
   exit 65 since `:native-handles`) -- the node's `[:list T]` is qualified
   natively since `:native-handles`, its `[:map :keyword :string]` attrs are
   not: floor `:native-hiccup-node`.
7. **Allocation is charged like fuel.** Every constructor debits the same
   64-bit ledger fuel uses (kotoba-kir ADR 0268, amu ADR 0333). The ADT
   node/depth ceilings stop being language constants and become the budget
   the caller grants; a DOM tree is bounded by what it was given, not by 64.
   Landed 2026-09-30 on the reference semantics (osaho `635bea6d`, gate
   `allocation-charged-to-fuel-test`). Measured before: fuel counted function
   entries only and a self-tail loop's re-entries are free, so a loop built
   1,000 records under `:fuel 2`; the one ledger that counted constructors,
   `:cells`, is unmetered unless the embedder names it. Now `kotoba.kir`
   debits one unit of the run's fuel at every constructor
   (`cell-constructor-ops`: record, variant, option / result, list, set, map,
   vector, pair, document), metered cells or not, and the trap names the
   constructor (`:operation record-new :allocation true`). The price is exact:
   the 1,000-record loop needs 1,002 (was 2), a 100-cell cons list -- 201
   nodes, 200 deep -- needs 507 (was 306), a program that constructs nothing
   pays nothing new, and the compile-time oracle pays the same (one unit short
   it is inconclusive, not refused). The 64 / 12 had stopped bounding a value
   at superproject adr-2609242100 P2 (2026-09-24); they bound a type
   DESCRIPTOR, which is checker work per type, a static language size like the
   32 record fields -- not an allocation. Refused, as before and now by the
   budget: allocating past what the caller granted (`budget/fuel`, and
   `budget/cells` when metered). Native: both forms compile for
   `x86_64-aiueos-kernel-v1` and `aarch64-macos`, and the aarch64 kexes
   printed 499500 and 4950 under `tools/kexe_loader.c`; but the targets keep
   their own counters. aiueos objects (`reproduce-kotoba-objects.cljk`,
   aiueos `ca7fc504`): 116 scanned, 112 byte-identical (`differs=0`), 4 not
   compiled -- the four sources point 2 already names as testing a 0/1
   `write-u32` answer.
   On the hosted targets (floor `:allocation-budget-targets`, gate
   `target-constructors-charge-fuel-test`, kotoba-script `58d75dae`,
   kotoba-wasm `7ff9ad0d`): restricted ESM's `cell()` calls `charge()` before
   its cells debit, and wasm32 puts the fuel global's charge in front of every
   constructor and of the vector literals it keeps in locals. Measured before:
   ESM's `cell()` debited cells only, and wasm32's loop helpers are
   zero-charge, so a module compiled with `:fuel 1` built 1,000 records. Each
   target keeps its own per-entry counting (ESM charges every loop iteration,
   wasm32 none), so the least budgets differ -- the 1,000-record loop needs
   2,002 on ESM (was 1,002) and 1,001 on wasm32 (was 1); the 100-cell list 707
   (was 506) and 505 (was 304) -- but the price of allocating is the
   reference's on each: 1,000 records cost 1,000 units and 300 vector literals
   300, on the reference, ESM and wasm32 alike. One unit short, ESM throws
   `budget/fuel` and wasm32 traps `unreachable`.
   On native (floor `:allocation-budget-native`, gate
   `native-constructors-charge-fuel-test`, kotoba-native `d625d554` -- its ADR
   0089 -- with kotoba-gmir `6c3651f9` and kotoba-mir `205f2a93`): every
   constructor is preceded by an inline decrement of the context's fuel word
   (`:fuel-charge`, offset 8, the entry prefix's own bytes), placed before the
   operands and before the rewrites that lower one source constructor into
   several; `vector-region` charges the literals it keeps in locals. Measured
   before, under `tools/kexe_loader.c` with `KEXE_FUEL` on aarch64 and x86_64:
   no constructor paid -- the 1,000-record loop answered under 1,002 units like
   the loop that builds nothing, the 100-cell list under 506, 300 vector
   literals under 102. After: 2,002, 707 and 402 on both ISAs, the reference's
   price (1,000, 201, 300), and one unit short the loader reports
   `budget/fuel`. The charge is not pure, so the bulk pre-charge declines a
   counted loop that constructs: 400 steps cost 402 without records, 802 with.
   kotoba-verifier re-derives an artifact by re-emitting it through
   kotoba-native, so it re-derives the charges with no change of its own;
   `amu compile` verifies both forms for `x86_64-aiueos-kernel-v1` and
   `aarch64-macos`. aiueos objects (`reproduce-kotoba-objects.cljk`, aiueos
   `ca7fc504`, compiled by this amu): 116 scanned, 112 byte-identical
   (`differs=0`; `drift` only records the other amu revision), 4 not compiled
   -- the same four as above. No kernel object constructs, so none moves.
8. **Admission by definition graph.** The 1 MiB bound moves from linked source
   bytes to per-definition size and closure count; a module is its definitions
   (as ADR 0300 already identifies it), so cssom's 1 MB file is admitted
   definition by definition.
   Landed (floor `:definition-admission`, gate
   `admission-by-definition-graph-test`; mechanism amu `c51059d9` with
   kotoba-sema `max-definition-source-bytes`): kotoba-sema refuses one
   top-level form over 1 MiB (`top-level definition exceeds admission
   limit`) and a whole input over 8 MiB; the linker refuses one linked
   definition over 1 MiB (`linked definition source exceeds byte limit`) and
   a definition whose dependency closure is over 1,024 definitions
   (`definition dependency closure exceeds limit`); the corpus stays capped
   at 8 MiB (`project source bytes exceed limit`). Measured 2026-09-30 on
   cssom `9224d359`: `cssom/layout.cljk` is 1,083,132 bytes in 373
   top-level forms, the largest 24,303 bytes, the largest closure 311 of 311
   `defn`s (the linker's symbol scan) -- a root requiring `cssom.layout`
   (with kotoba-lang/text and dom-gpu on the source path) now reads past
   size and stops at a semantic wall instead (the first:
   `qualified call is not an admitted exported import`, in
   `kotoba.lang.text`). The gate's fixture
   is the same shape at 1,125,902 bytes: before the bound moved it was
   refused whole (`source exceeds 1 MiB admission limit`); after, its
   linked source is over 1 MiB, it analyses and answers 7,680 on the KIR
   reference, and it compiles for `x86_64-aiueos-kernel-v1` and
   `aarch64-macos` with the oracle verified. The gate also found the closure
   scan crashing on nbb when a body leaf is a js BigInt (a let binding's
   `1`); the scan now tests `symbol?` before the set lookup. Still bounded
   at 1 MiB: the ROOT file named on the command line, which the CLI reads
   through `bounded-edn/max-source-bytes` before any parsing (the
   conformance suite asserts that refusal); a large module is admitted as
   a dependency on `--source-path`.
9. **Native handles at loop boundaries.** kotoba-native qualifies record,
   vector and closure handles as loop-helper boundary types and no form
   lowers to `map-new` (since floor `:empty-map-literal`, below), so
   every form above compiles for both native targets. Split on
   2026-10-01 into three floors, because measuring showed three changes in
   three places (ladder comment), and the third again the same day into
   `:loop-slot-types` and `:native-handles`.
   Floor `:native-record-boundary` (gate
   `native-record-function-boundary-test`, landed 2026-10-01): a declared
   record (`[:ref q]`) as a parameter or result compiled natively and was
   refused at the native artifact oracle (exit 65, cause
   `unknown-schema-reference`). The backends always carried it as the
   one-word pair-chain handle; the closed program the artifact seals and the
   verifier re-executes (`kotoba.kir/native-program`) kept `:schemas` only
   for a recursive table, while `[:ref q]` survives lowering in exactly one
   place, a function's `:param-types` / `:result`. The table now joins the
   program when a signature names a reference (osaho `756c64c6`), and
   kotoba-verifier re-derives that need -- a table that neither recursion
   nor a signature reference into it needs stays refused as module shape
   (`718befe6`). Nothing in codegen moved; a module none of whose signatures
   names a reference seals the program it sealed before. Measured: the
   gate's programs answer 3, 9 and 2 under `tools/kexe_loader.c` on aarch64
   and x86_64 (the latter under Rosetta), and `amu compile --target
   x86_64-aiueos-kernel-v1` / `--target aarch64-macos` exit 0 with `:oracle
   {:status :verified}`. Refused by name: an i64 where a record is declared,
   `=` over records, a record as an `if` test, and a record as the entry's
   result on native (the typed-values gate, exit 65 since
   `:native-handles`).
   Floor `:native-record-operations` (gate `native-row-operations-test`,
   landed 2026-10-01): the row operations and a join's projection compile
   natively. Before, `assoc` of a present field elaborated to `record-assoc`,
   which `kotoba.kir`'s native gate had no case for (the typed-values
   refusal, exit 70); `assoc` extending, `dissoc`, `select-keys` and `merge`
   elaborate to `(record-get T (let [receiver m] (record-new T ..)) :f)` and a
   join projects `(record-get T (if c m n) :f)`, and kotoba-verifier's record
   projection resolved neither operand ("runtime KIR record projection
   rejected", exit 65), hand-written too. Now osaho qualifies `record-assoc`
   with `record-get`'s checks (`ab22ed51`); kotoba-native lowers it on both
   record routes -- a fresh pair chain re-projecting the other fields, or the
   slot bundle with one register replaced (`ace48fd6`); and kotoba-verifier
   sees a record through a `let` (a let naming a record parameter binds its
   handle; a flattened let-bound record is still not forwarded), through an
   `if` whose two arms denote one record, and through an update of the record
   its operand is, else "runtime KIR record update rejected" (`1e1b69a6`).
   Measured: the gate's twelve programs -- six row operations, a row
   parameter, an update chain, the join's projection, two hand-written KIR
   forms, and an update that never crosses a boundary -- answer under
   `tools/kexe_loader.c` on aarch64 and x86_64 (Rosetta) what the reference
   answers (9, 11, 5, 2, 11, 4, 16, 7, 12, 2, 2, 7), and `amu compile
   --target x86_64-aiueos-kernel-v1` exits 0 with `:oracle {:status
   :verified}` for each. Refused by name, on both targets: a coerced field, a
   join over two records, a record as the entry's result (the typed-values
   refusal, exit 65 since `:native-handles`), a record left with no field, a
   record as an `if` test, a non-record merge operand.
   Floor `:loop-slot-types` (gate `loop-slot-record-list-closure-test`,
   landed 2026-10-01, split from `:native-handles` because the loop slot was
   kotoba-sema's alone and refused before any target): a `loop` desugars to
   a helper whose parameters are its slots, typed from its one call site --
   before literals were typed, so a map-literal slot was `:map` ("expression
   type mismatch: expected map, got [:record :kotoba.map-literal/a+b ..]")
   and a captured vector literal of records the `:i64` placeholder ("count
   requires a bounded vector, ...; got :i64."). And the body desugared
   without its slots as lexical bindings, so a closure slot was not callable
   ("unknown operation: f is not a builtin, ..."), while `(+ f 1)` and `(=
   f g)` over a closure slot never called were admitted, answering 2 and 1.
   Now kotoba-sema (`442e6d78`) re-resolves the helpers' slots once literals
   are typed, to a fixed point; a loop's bindings are lexical bindings with
   their callable contracts, as a `let`'s are; a slot whose argument is a
   closure is a closure to the `:function-values` analysis, called or not;
   and a nonzero number literal where a closure slot or parameter is, is
   refused by name -- it was called as a handle and trapped
   `invalid-pair-handle`, a declared `[:fn ...]` parameter included (0 stays
   admitted: the empty lazy sequence's word). Measured: record and closure
   slots answer 4, 4, 8, 3 and 12 under `tools/kexe_loader.c` on aarch64 and
   on x86_64 (Rosetta), and `amu compile --target x86_64-aiueos-kernel-v1` /
   `--target aarch64-macos` exit 0 with `:oracle {:status :verified}`; list
   slots answer 10, 10 and 3 on the reference and compile for
   `wasm32-kotoba-v1`. Refused by name: a slot recurred to another record, a
   coerced field, a record or closure slot as an `if` test, `=` over records
   or closures, a list item used as an i64, a closure slot as a number, and
   a number recurred into a closure slot.
   Floor `:native-handles` (gate `native-record-vector-closure-boundary-test`,
   landed 2026-10-01): a `[:list T]` of records was refused natively by the
   typed-values gate (`typed-list-new` not qualified) wherever it was written
   -- a let, a loop slot, a parameter -- and the CLI answered that refusal,
   `:phase :target`, with exit 70, the internal-error code. Now osaho
   qualifies `typed-list-new` / `typed-list-nth` over one-word item handles,
   a record through `[:ref q]` included, and `[:list T]` is a native handle
   type, so a loop helper or a function takes one (`0310fb54`);
   kotoba-native lowers them to the typed set's word arena, a `vector-conj`
   chain and `vector-at`, `vector-count` already walking the carrier
   (`7b5b8fb8`); kotoba-verifier re-derives both heads and sees a record
   through an item of a list of records (`32d8a4a2`). `:target` exits 65 on
   both CLI routes. "The forms of every floor above" was measured by
   compiling, for both targets, every program the frontend-only gates of
   `:absence` .. `:expression-absence` admit (82): two more were refused by
   kotoba-verifier after codegen had compiled them -- a let-bound record
   local, which forwarded only for a parameter (`(let [m (assoc (mk) :d 4)]
   (:a (dissoc m :b)))`), and a record whose field holds a declared reference
   (`(:a (:x (assoc (mk) :x (mt))))`); both forward now, in the same
   verifier commit. The rest are refused natively by design, exit 65: handle
   structural equality (`record-equal`, `typed-set-equal`, `typed-map-equal`,
   `hetero-vector-equal`) and a record as the entry's result. `map-new`: no
   map literal with fields lowers to it and both ADR 0352 reproductions are
   records that compile natively; the empty literal `{}` did, until floor
   `:empty-map-literal`. Not reached: `:hiccup-node`'s
   programs, whose node schema reaches a `[:map :keyword :string]`, which has
   no native representation (exit 65, "does not qualify the boundary type
   [[:ref :kotoba.hiccup/node]]") -- floor `:native-hiccup-node`. Measured: a program summing a list
   parameter, a list of map-literal records and a list loop slot answers 2327
   under `tools/kexe_loader.c` on aarch64 and on x86_64 (Rosetta), the two
   forwarded projections with a flat one answer 791 on both, and `amu compile
   --target x86_64-aiueos-kernel-v1` / `--target aarch64-macos` exit 0 with
   `:oracle {:status :verified}`. Refused by name: `=` over lists of records,
   a list as an `if` test, a list item as an i64, an index out of range (the
   oracle traps `list-index-out-of-bounds`, so no artifact is sealed). Found
   on the way and refused before any target: a `[:list T]` loop slot after a
   row read of a let-bound map literal types as `:i64` -- floor
   `:loop-slot-beside-row`.
   Floor `:native-hiccup-node` (gate `hiccup-node-compiles-natively-test`,
   landed 2026-10-01): every `:hiccup-node` program was refused by both
   native targets by the typed-values gate, because the elem's
   `[:map :keyword :string]` attrs had no native qualification -- a program
   that never read an attribute could not build a node. Now a `[:map K V]`
   whose key is a scalar native code compares by content (i64, bool, string,
   keyword) and whose value is any one-word handle is a native handle type:
   osaho qualifies `typed-map-new` / `-count` / `-contains` / `-get` /
   `-assoc` / `-dissoc` (`eb39dba5`); kotoba-native lowers them to the
   `[:list T]` word arena with keys and values interleaved -- the
   `string-index` representation, no ABI bump -- searched by appended
   helpers (`string=?` for a text key, the word compare otherwise), `assoc`
   of a present key re-appending its entry as `kotoba.kir` does, and past 31
   entries trapping through an out-of-range `vector-at` (`83eecc0e`);
   kotoba-verifier re-derives the heads and sees a record read out of a map
   of records (`4410753e`). Measured: the 11 `:hiccup-node` programs whose
   entry answers a word and 8 typed-map programs compile for
   `x86_64-aiueos-kernel-v1` and `aarch64-macos` with the oracle verified;
   `test/nbb/native_word_ops.cljk`'s typed-map fixture answers the same 10
   rows on the reference, restricted ESM, and the aarch64 and x86_64
   (Rosetta) code under `tools/kexe_loader.c` (`493307224`, `14`, `6`, `50`,
   `-1`, `1`, `0`, `3160`, `304038`; 32 entries trap `map-too-large` /
   SIGILL). Refused by name: `=` over maps, a map as an `if` test, a map
   value used as another type, an assoc past 31 entries; natively, exit 65:
   `keys` / `vals` (entry order is not a native operation), a record key,
   and -- as for every native program -- a string entry result ("native
   artifact oracle value rejected"). Walking `window-node`'s whole tree with
   the mutually recursive `size` / `size-list` answers 13 under
   `tools/kexe_loader.c` on aarch64, and `amu compile` verifies the oracle for
   both targets; under the plain `kbb` engine's default host stack the
   reference interpreter exhausts it (`host/stack-exhausted`), which is why
   the gate pins the smaller trees.
   Floor `:empty-map-literal` (gate `empty-map-literal-is-typed-test`,
   landed 2026-10-02; point 3's retirement of the keyword->i64 map, carried
   to the literal that still produced it): `{}` desugared to `(map-new)`, the
   pair map, whatever the program put in it -- `(assoc {} :a 1)` was that map,
   `(get {} :a 0)` answered 0, `{}` where a record was declared was
   "expected [:ref q], got map", and a `match` map pattern refused a record
   scrutinee ("match map patterns admit the bounded map only; this scrutinee
   is a record"), which since `:literal-typing` meant every literal one.
   Now kotoba-sema (`0632bed0`): `(assoc {} :k v ..)` is the record of the
   keys it assoc's, the literal `{:k v ..}` (fields in key order, a repeated
   key's last value winning); `{}` where its context declares a record is
   that record with every field absent, so only an all-option record has an
   empty literal, and where it declares `[:map K V]` that map, empty; an
   integer or string first key is the typed map it already was; a match map
   pattern on a record decides presence from the type -- a field it has is
   present, an arm naming a key it lacks does not match and is folded away
   rather than typed; the trap synthesizer no longer writes `(map-new)` as a
   `:map` default. Measured: the gate's 14 programs answer on the KIR
   reference what they answer under `compile-source` for
   `wasm32-kotoba-v1`, `x86_64-aiueos-kernel-v1` and `aarch64-macos-kotoba-v1`
   with the oracle verified, and none lowers to `map-new`; `amu compile
   --target x86_64-aiueos-kernel-v1` / `--target aarch64-macos` of a program
   using all three (assoc into `{}`, a two-arm match, an all-option `{}`)
   exit 0 with `:oracle {:status :verified}`. The gate was red on kotoba-sema
   `442e6d78` (5 failed, 25 errored assertions), green on `0632bed0`. No
   aiueos kernel source (127 on disk) writes `{}`, `match`, `map-new` or a
   `:map` type, so no kernel object can move. Refused by name: `{}` with
   nothing to type it ("an empty map literal {} has no row to extend: ..."),
   read, counted, let-bound or spelled `(map-new)`; a record context whose
   field is not an option; a coerced field; a record as an `if` test; `=`
   over records; a key the record lacks. Found and left to its own floor
   (`:row-get-and-match`): `(get m :a)` is not a row read, so a `match` over
   an unannotated parameter is refused before specialization.
   Floor `:row-get-and-match` (gate `row-get-and-match-read-a-row-test`,
   landed 2026-10-02): a row was read off `(:a m)` only. `(get m :a)` left
   the parameter the provisional `:i64`, read through the retired
   keyword->i64 map, so passing a record was refused "expression type
   mismatch: expected map, got [:record ...]", and a `match` map pattern --
   which projects its scrutinee with `get` -- over a parameter was refused
   "expected map, got i64". Now kotoba-sema (`21e3a23f`): `(get m :a)` reads
   `:a` off the row as `(:a m)` does; `(get m :a d)` makes `m` a row without
   requiring `:a` (a record without it answers `d`, as on any record); a
   match map pattern over a parameter, through the temp `match` binds it to,
   makes it a row, and each specialization decides its arms -- a key the
   record lacks does not match and the arm is folded away (the row
   specializer now keeps a rebuilt form's metadata, which carries the
   pattern's projection marker). Measured: the gate's 10 programs answer on
   the KIR reference what they answer under `compile-source` for
   `wasm32-kotoba-v1`, `x86_64-aiueos-kernel-v1` and
   `aarch64-macos-kotoba-v1` with the oracle verified; `amu compile --target
   x86_64-aiueos-kernel-v1` / `--target aarch64-macos` of a program with a
   `get`-with-default row and a two-arm match over a parameter, each called
   with a declared record and a literal lacking `:b`, exit 0 with `:oracle
   {:status :verified}`. The gate was red on kotoba-sema `0632bed0` (19
   errors), green on `21e3a23f`; kotoba-sema's own suite has the same 44
   failures before and after (all pre-existing). No aiueos `.kotoba` source
   (184) writes `(get`, `(match` or a defaulted keyword lookup, so no kernel
   object can move. Refused by name: a get with a computed key on a record
   ("get on record q has the computed key k: a record's fields are static,
   so the field a get reads is a keyword literal; a computed key needs a
   [:map K V]"); a `get` without a default of a field the record lacks; a
   non-record argument to a row; a coerced field; a record, or a number read
   off one, as an `if` test; `=` over records.
   Floor `:loop-slot-beside-row` (gate
   `loop-slot-typed-beside-a-row-read-test`, landed 2026-10-02): a loop's
   slots are typed from its helper's call site in the enclosing body, and that
   body is typed before `rewrite-record-projection` gives `(:a ys)` its
   descriptor. Inference read the descriptor-less `(record-get ys :a)` as the
   3-arity form, taking the local for the descriptor -- an internal failure
   ("nth not supported on this type"), swallowed as an independent error --
   so a body that read a row before its loop left every slot the `:i64`
   placeholder: `(let [ys {:a 1}] (+ (:a ys) (loop [zs [(mk) (mk)] i 0] ...
   (count zs))))` was refused "count requires a bounded vector, a typed set
   or a canonical typed map; got :i64." while the loop alone answered 2. Now
   kotoba-sema (`965feb37`) types a descriptor-less `record-get` as that
   rewrite will rewrite it: a record or declared `[:ref ..]` answers its
   field, a canonical typed map `typed-map-get`, the keyword->i64 map
   `map-get`. Measured: the gate's 3 programs answer 3, 12 and 8 on the KIR
   reference and under `compile-source` for `wasm32-kotoba-v1`,
   `x86_64-aiueos-kernel-v1` and `aarch64-macos-kotoba-v1` with the oracle
   verified; `amu compile --target x86_64-aiueos-kernel-v1` / `--target
   aarch64-macos` of the floor's program exit 0 with `:oracle {:status
   :verified}`. The gate was red on kotoba-sema `21e3a23f` (3 failures, 12
   errors of 18 assertions), green on `965feb37`; kotoba-sema's own portable
   suite has the same 39 failures and 5 errors before and after (all
   pre-existing). Refused by name, as without the row read: a list item as
   an i64; a number recurred into the list slot ("expected [:list [:ref
   :b/s]], got i64"); a field the record lacks; a row read off a number
   ("record-get without a type descriptor requires a record value; got
   :i64"); a record as an `if` test.

Then browser moves, whole component by component (text-edit, input, surface
with cssom and dom-gpu), and the hosted engine switches to amu's output of
the same source. The kernel's mirrored objects (aiueos ADR-0223..0234) retire
as each module lands.

Measured on text-edit (2026-10-02, kotoba-sema `965feb37`, browser
`8671500`). The source needs only mechanical changes: a `:kotoba` branch for
`code-unit-at` and for a `code-unit-count` helper (`count` of a string stays
refused), and the nil guards over values that are never absent dropped (`(or
n lo)` on an `:i64`, `(or (:text/selection state) ..)` on a vector -- a number
or a vector is never truthy). The compiler then refused it in six places, so
floor `:browser-text-edit` is split and blocked by the five still open
(`docs/language-ladder.edn`): an internal error on nbb only (an integer
literal hashed by ClojureScript, `closure_uid_.. on bigint '0'`, located to
the module, not yet to a pass), a `nil` field whose T only a later `assoc`
names (`:text/composition`), an i64-vector record field natively
(`:text/selection`), `max` / `min` on typed Wasm, and how a Clojure-readable
source states an export's ABI -- `state` is a row, which an export cannot be,
and `text` is unannotated, so `:i64` -- which needs an owner decision. The
multi-arity `move-caret` / `move-to` with a `{}` options map were not reached.
The sixth landed as floor `:let-rebinding` (gate
`let-rebinding-is-nested-shadowing-test`): text-edit rebinds names as Clojure
does, its state parameter by a `let` (`(let [state (normalize-selection
state)] ..)`) and a local again in one `let` (`a (clamp a 0 n)`). Row
inference left a parameter the body rebinds anywhere the provisional `:i64`
("argument s to norm is i64, and parameter s of norm is the row {:a T | r}:
only a record satisfies a row"), and a repeated binder was "duplicate let
binding" while the nested `let` that shadows it was admitted. kotoba-sema
(`531e89d8`) now reads a parameter only where it is in scope (`row-scope`) and
nests a repeated binder (`nest-repeated-let-bindings`); a nested `let` was
already what every later pass read, and the affine analysis never treated a
rebound name as one thread. Measured: the gate's four programs answer 2, 4,
10 and 13 on the KIR reference and under `compile-source` for
`wasm32-kotoba-v1`, `x86_64-aiueos-kernel-v1` and `aarch64-macos-kotoba-v1`
with the oracle verified, and text-edit's `normalize-selection` answers 32 on
the reference (its vector field and `max` / `min` are the floors above);
`amu compile --target x86_64-aiueos-kernel-v1` / `--target aarch64-macos` of a
twice-rebound row parameter exit 0 with `:oracle {:status :verified}`. The
gate was red on kotoba-sema `965feb37` (3 failures, 17 errors of 23
assertions), green on `531e89d8`; kotoba-sema's portable suite has the same
39 failures and 5 errors before and after (identical lists, all
pre-existing). Refused by name, as before: a read after the rebinding is the
new value's (a field it lacks, a number read as a record), a parameter read
only after it is rebound is not a row, a rebound name has its new type, a
record as an `if` test, a repeated parameter.

The internal error landed as floor `:cljs-literal-hash` (gate
`text-edit-analyzes-on-nbb-test`). Located on kotoba-sema `531e89d8` by
wrapping every frontend var on nbb: `specialize-row-parameters` scans every
call argument for a row-polymorphic function used as a value with
`(contains? generics arg)`. Past eight generics that map is a hash map, an
integer literal is a ClojureScript BigInt, and a BigInt has no hash. Either
of text-edit's `move-caret` / `move-to` is its ninth row generic (the floor
above had not reached them); nine one-line functions over a row are enough,
and the JVM was never affected. kotoba-sema (`8d3320fc`) asks `symbol?`
before it hashes. Measured on nbb: the gate was red on `531e89d8` (6
failures, 4 errors of 11 assertions, every one the `closure_uid` error),
green on `8d3320fc`; nine generics answer 36 on the KIR reference, and
`amu compile --target x86_64-aiueos-kernel-v1` / `--target aarch64-macos`
exit 0 with `:oracle {:status :verified}`; kotoba-sema's portable suite has
the same 39 failures and 5 errors before and after (identical lists). With
nine generics, refused by name as before: a row generic used as a value, a
number passed to a row parameter, a record as an `if` test. text-edit (its
`:text/composition` field left out, which is floor `:absent-field-from-assoc`)
now answers a refusal in the language's words, at `delete-backward`'s
`(insert-text state "")`: "argument state to insert-text is i64, and
parameter state of insert-text is the row {:text/caret T :text/selection T |
r}: only a record satisfies a row" -- floor `:rebound-row-argument`, not yet
minimized (each of its ingredients is admitted alone).

## Selfhost foundation floors (appended 2026-09-26)

Superproject adr-2609242330 measured that compiling amu with amu needs the
data model amu's own source uses -- EDN of arbitrary shape (HIR, KIR, ns
forms) -- on every target, native included. Those floors are appended to the
ladder after the browser floors, one change each, and close by their gates
like the rest:

- `:document-type-predicates` (gate `document-type-predicates-ask-the-kind-test`,
  landed 2026-09-26): `map?`, `vector?`, `keyword?`, `string?`, `integer?`,
  `true?`, `nil?` and the rest ask a `:document` node its run-time
  `document-kind`; a static type answers for itself; an `[:option T]` is
  presence when T answers true. Refused by name: an option whose payload
  answers by value, `nil?` on a type with no absence, `map?` on a `[:ref q]`.
  Native still has no `:document`, so there the program is refused as before
  (`does not qualify document-kind`).
- `:expression-absence` (gate `expression-absence-typed-by-the-present-branch-test`,
  landed 2026-09-26): point 2's absence at expression level. A `when` /
  `if-let` / `cond` with no else and a literal `nil` branch answer nothing, and
  the present branch's type decides: `false` beside a `:bool`, the option's
  none beside an option, `[:option T]` beside any other T. Beside an `:i64` it
  is `[:option :i64]` where the result is inferred (an unannotated `defn`, a
  `fn` literal), and the 0 it always was where the author declared the result
  or the value is a statement, so no program that compiled before changes (the
  42 examples' definition CIDs and the 125 aiueos kernel objects are
  byte-identical). A loop's exits join the same way: a find-first answers
  `[:option T]`. Refused by name: an absent i64 used as the number it would
  hold, two present types, an `if` with no else.
- `:native-abort` (gate `native-abort-compiles-verifies-and-packages-test`,
  landed 2026-09-26): `throw` / `try` on native. The frontend already lowered
  them to `[:result T E]` values; what refused them was admission, not
  lowering -- the verifier admitted only `:state` beside capability calls and
  the compile-time oracle sealed nothing for an `:abort` row. Both ISAs now
  compile an aborting program and agree with the reference, ESM and Wasm; the
  linux-static packager needs no handler for the ability. An ex-info error is
  a `:document`; native admits it since `:native-document`.
- `:native-document` (gate `native-document-values-test`, landed 2026-09-26):
  a `:document` on native. It is the document's canonical EDN text in the
  string handle native documents already were (the dataspace provider's
  boundary), so structural equality is `string=?`, and every operation is a
  rewrite onto the existing string slots plus private helpers kotoba-native
  appends (`kotoba.native.document`) -- no ABI word, no loader code. Bounds
  (32 items, depth 8, 4096 nodes) are re-derived in emitted code and trap
  through the native trap path. 1,000 random document expressions answer the
  same on restricted ESM and the kexe loader on both ISAs (and the KIR
  reference on 640 of them). Still refused on native, by name: f64 documents,
  `document-sha256`, `document-print` / `document-read`.

## What stays refused, permanently

Coercion; truthiness of numbers, strings, records; `eval` and host interop;
structural equality over handles (ABI v8); unbounded allocation; ambient
effects. Each floor's test pins its refusal next to its admission.

## Consequences

The three properties move forward together: static and closed (safety),
monomorphized and unboxed (speed), types and specializations in the
definition identity (code identity). Browser's source changes are mechanical
(`defn-`, `nil`'s meaning, interop branches). Until a floor lands, its old
refusal and ADR stand.
