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
   read, counted, let-bound or spelled `(map-new)` (passed to a row it is the
   record with no fields since floor `:options-map-argument`, below); a record context whose
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
r}: only a record satisfies a row" -- floor `:rebound-row-argument`, below;
since floor `:options-map-argument` it is admitted and answers 3, which the
gate now pins.

The `nil` field landed as floor `:absent-field-from-assoc` (gate
`nil-field-typed-by-the-module-assoc-test`). text-edit starts its state with
`{.. :text/composition nil}` and writes the field in `composition-start`
(`(assoc state :text/composition {:composition/text ""})`),
`composition-update` (the same with `(str text)`) and `composition-end`
(`(assoc state :text/composition nil)`); the literal was refused, "map
literal value at key :text/composition is nil, which makes the field an
absent [:option T], and nothing here says T". kotoba-sema (`7290e22e`) reads
the module's source once per analysis (`module-absent-fields`): a keyword key
written `nil` -- a literal entry or an `assoc` pair -- is an absent field
`[:option T]`, T the one type the module's non-nil values at that key spell.
There `nil` is `(option-none-of [:option T])`, and a value that spells T or a
map / vector literal (typed against T, so `{:composition/text (str text)}` is
that record) is `(option-some-of [:option T] v)`. This is point 2's absence,
as `:expression-absence` has it for a branch: the field is an option because
the module writes `nil` there, not because a value is coerced. A call that
returns T is not wrapped. Measured on nbb: the gate was red on `8d3320fc` (2
failures, 4 errors of 7 assertions), green on `7290e22e` (10 assertions). The
four functions answer 100, 0, 3 and 100 on the KIR reference (`if-let` over
the field, then the code-unit count of `:composition/text`, 100 when it is
absent), and the program compiles for `wasm32-kotoba-v1`. Native is partial.
Construction, `assoc` and presence (the field as an `if` test, answering 6)
compile for `x86_64-aiueos-kernel-v1` and `aarch64-macos-kotoba-v1` with the
oracle verified. Projecting the present record is refused on both by the
verifier ("runtime KIR record projection rejected": `record-get`'s operand is
an `option-value-of`, which it does not type). It was refused before this
floor too: a declared `[:option R]` parameter read the same way gives
"machine IR rejected: branch-value-shape-mismatch". That is floor
`:native-option-record` (since closed, below). kotoba-sema's portable suite has the same 39 failures and 5
errors before and after (identical lists). Refused by name: a key the module
writes `nil` at and two types at (`field :text/composition is nil in this
module ... writes two types at it: [:record ..] and :string`), a `nil` key the
module gives no type (the old message), and a present T from a call written
at the absent field (`expected [:option ..], got [:record ..]`, no coercion).
`composition-update`'s `text` is annotated `:string` in the gate; unannotated
it is `:i64`, which is floor `:export-signatures`.

The rebound row landed as floor `:rebound-row-argument` (gate
`text-edit-rebound-state-is-a-row-test`). A rebound row passed on, in a
`cond`, after a vector destructuring, was each admitted alone; minimizing
text-edit showed what it adds is a helper over a string, `(code-unit-count
value)` in `normalize-selection`. `specialize-row-parameters` ran before the
module-wide parameter inference, so `code-unit-count`'s unannotated `s` was
still the provisional `:i64` inside `normalize-selection`'s specialization;
called with a string, that specialization's result could not be inferred and
stayed `:i64`, and `(let [state (normalize-selection state)] (insert-text
state ""))` passed that `:i64` to a row. kotoba-sema (`275b40a0`) infers
absent parameter types at the start of each specialization round, before
results. Measured on nbb: the gate was red on `7290e22e` (3 failures, 5
errors of 11 assertions, the floor's literal), green on `275b40a0` (11
assertions). The minimal form (`len` over a string, `norm`, `ins` and `del`
each rebinding the row) answers 4 on the KIR reference, compiles for
`wasm32-kotoba-v1`, and `amu compile --target x86_64-aiueos-kernel-v1` /
`--target aarch64-macos` exit 0 with `:oracle {:status :verified}`.
text-edit's `delete-backward` and `delete-forward` answer on the KIR
reference ("abcd", 1..3 selected, deleted either way: "ad", caret 1; the
caret at 4 deleted backward: "abc", caret 3). text-edit itself is refused
natively by its public `empty-state`'s record as an export's result (floor
`:export-signatures`; until `:native-vector-field`, by its vector field) and
on wasm32 at floor `:typed-wasm-min-max` (since closed, below). kotoba-sema's portable suite has
the same 39 failures and 5 errors before and after (identical lists), and
amu's nbb suite the same 13 failures and 2 errors (the policy tests).
Refused by name as before: a number passed to a row parameter, bound by `let`
or not, and a rebound record as an `if` test. With this, text-edit (move-caret
and move-to in) is refused at `(move-caret (empty-state) 1)`: its `{:keys
[extend?]}` options parameter is "expected map, got i64" and the 2-arity's
`{}` "an empty map literal {} has no row to extend" -- new floor
`:options-map-argument`.

The vector field landed as floor `:native-vector-field` (gate
`vector-field-in-record-compiles-natively-test`). text-edit's state holds
`:text/selection [start end]`, a `:vector-i64` field; a vector alone compiled
natively, a record holding one was refused on both native targets by the
typed-values gate ("typed values currently require ... the qualified native
one-word string/record/variant/option/result slice"), for `(nth (:sel s) 1)`,
`(assoc s :sel [..])` and `[a b]` destructuring alike. Three layers each left
the vector-arena handle out of a record: osaho's `native-handle-type?` did not
count it as a one-word member (`3b2eef93`); kotoba-native's `aggregate-abi`
spelled it `:vector`, which nothing produces -- the spelling
`word-result-type?` had already corrected at a function boundary -- so the
module was "machine IR rejected: unsupported-function-module" (`e2da186d`);
and kotoba-verifier's record check had no vector field, "runtime KIR record
construction rejected" (`4a87b807`). The verifier now also refuses any record
holding one at an export (`holds-private-handle?`), so it stays no looser than
`kotoba.kir`, which never put it on `native-boundary-type?`: the kexe loader
has a wire form for a vector, none for a vector inside a record. Measured on
nbb: the gate was red on `eb39dba5` / `83eecc0e` / `4410753e` (every native
assertion the typed-values literal), green on the three new pins (38
assertions). Five forms -- projection, `assoc`, destructuring, the record
through two private functions rebuilt with a computed vector, the record as a
loop slot -- and four text-edit operations over the selection (`insert-text`,
`normalize-selection`, `select`, `delete-backward`, `empty-state` private)
answer the reference's value on `x86_64-aiueos-kernel-v1` and
`aarch64-macos-kotoba-v1` with the oracle verified; `amu compile --target
x86_64-aiueos-kernel-v1` / `--target aarch64-macos` exit 0 with `:oracle
{:status :verified}`, and the record-through-functions program answers 42
under `tools/kexe_loader.c` on aarch64 and on x86_64 (Rosetta).
kotoba-native's suite has the same 34 failures and 9 errors before and after,
kotoba-verifier's the same 22 and 1 (identical lists, host-environment tests),
osaho's passes (256 tests), and amu's nbb suite the same policy-test failures.
Refused by name: the record as an export's result (the typed-values literal;
text-edit's public `empty-state` is refused for this, floor
`:export-signatures`), `=` over it ("equality type is outside the safe value
profile"), the vector as an `if` test, the vector as a number and a number as
the vector (`expected i64, got vector-i64` / `expected vector-i64, got i64`),
and an index out of range (`vector-index-out-of-range`, no artifact sealed).
Measured on the way, not this floor's: text-edit's three operations in one
`main` exhaust the compiler host's stack inside the KIR oracle under kbb's
default stack (`:host/stack-exhausted`, inconclusive, nothing sealed), and in
one process where x86_64 had just run out first, aarch64 answered "native
artifact oracle value rejected" -- two oracle runs of one program
disagreeing, which a host stack overflow caught inside the interpreter would
explain. The same three operations compiled one per program agree with the
reference on both targets.

min and max in a typed Wasm module landed as floor `:typed-wasm-min-max`
(gate `min-max-qualified-on-typed-wasm-test`). text-edit clamps its caret,
`(max lo (min hi n))`. Both compiled on `wasm32-kotoba-v1` only in a module
of plain i64 words; once the module held a string or a record, kotoba-wasm's
typed (KIR v4) emitter took over, and it had no arm for either, so
`(max 0 (string-code-unit-count "abc"))` and text-edit alike were exit 70
"typed Wasm operation is not qualified" `{:operation max}`. The typed emitter
now lowers both as the untyped one does -- `i64.lt_s` / `i64.gt_s` and
`select` -- with each operand evaluated once into an i64 local (kotoba-wasm
`a82bc58e`). Measured on nbb: the gate was red on `7ff9ad0d` (9 failures and
10 errors of 49 assertions, the floor's literal), green on `a82bc58e` (49
assertions); kotoba-wasm's own suite passes before and after (25 tests, 97
assertions). Eight typed programs, `min(3,7)=3` / `max(3,7)=7` and negative
operands among them, answer the reference's value when the wasm32 module is
run by `runtime/browser-host.mjs`, and on `x86_64-aiueos-kernel-v1` and
`aarch64-macos-kotoba-v1` (native never refused these forms); text-edit's
delete-backward / delete-forward program answers 212133 on wasm32 as on the
reference, so `text-edit-rebound-state-is-a-row-test` now pins its wasm32
admission instead of the refusal. `amu compile --target wasm32` /
`--target x86_64-aiueos-kernel-v1` / `--target aarch64-macos` exit 0 on a
clamp over a record's string (the native two with `:oracle {:status
:verified}`). Refused by name as before: min/max over a string, a bool or an
option (`expected i64, got ...`) and any arity but two ("i64 operation arity
mismatch: max takes 2 arguments").

The record an option holds landed natively as floor `:native-option-record`
(gate `option-record-projects-natively-test`). text-edit reads its
composition as `(if-let [c (:text/composition state)] (:composition/text c)
..)`, which kotoba-sema elaborates to `(option-value-of [:option R] o
(record-new R ..))`, the fallback a record of R. On both native targets it was
refused by the verifier, "runtime KIR record projection rejected", and a
declared `[:option R]` parameter read the same way, R a flat record, by
kotoba-native, "machine IR rejected: branch-value-shape-mismatch". Two layers
each left the option's payload out. kotoba-verifier's `record-schema-of` typed
an `option-value-of` only over a `typed-map-get`, so the local `if-let` binds
had no record; it now types any option of a record whose fallback is that
record, the option's declared type equal to the operand's wherever the
operand says one (a local, a record field, a call's result) (`3e8134cd`).
kotoba-native scalar-replaced a module whose records were flat and local, so
the payload word and the fallback's field bundle met at one phi in two
shapes; a record an option holds now selects the pair-chain lowering, as a
record in a variant payload already did (`04a8e0e3`, with
`a-record-in-an-option-lowers-on-both-isas`, red before and green after).
Measured on nbb: the gate was red on `4a87b807` / `e2da186d` (8 errors of 23
assertions with `nil-field-typed-by-the-module-assoc-test`, the floor's two
literals), green on the new pins (23 assertions). text-edit's composition
answers 203, a declared `[:option R]` over a flat i64 record 12 and over a
record holding a string 113, on the KIR reference and on
`x86_64-aiueos-kernel-v1` and `aarch64-macos-kotoba-v1` with the oracle
verified; `amu compile --target x86_64-aiueos-kernel-v1` / `--target
aarch64-macos` exit 0 with `:oracle {:status :verified}`. No artifact was run
under a loader this time. `nil-field-typed-by-the-module-assoc-test` now pins
the native projection (203) instead of the refusal. kotoba-verifier's suite
has the same 22 failures and 1 error before and after (identical lists), and
kotoba-native's the same 34 failures and 9 errors, every one on its known-red
list; amu's nbb suite has the same 13 failures and 2 errors (the policy
tests). Refused by name: a field R does not declare ("record field must be a
declared keyword literal"), the option as a number (`expected i64, got
[:option ..]`), and the option projected as if it were the record
("record-get without a type descriptor requires a record value; got [:option
..]").

The options map landed as floor `:options-map-argument` (gate
`options-map-destructures-as-a-row-test`). text-edit's `move-caret` and
`move-to` take `([state delta] (move-caret state delta {}))` and `([state
delta {:keys [extend?]}] ..)`; text-edit with both was refused at
`(move-caret (empty-state) 1)`, minimized "expression type mismatch: expected
map, got i64". Three things were missing. The lookup a `{:keys [..]}`
parameter desugars to (`__kotoba_destructure_get` off the parameter's
synthetic alias) was not a read of a row, so the parameter stayed the
provisional `:i64` and the lookup became the retired pair map's `map-get`;
`{}` had no type at a row argument; and a key the record lacked was "record
field is not declared". kotoba-sema (`77d2dd84`): the lookup makes its
parameter a row without requiring the key, as `(get m :k d)` does; `{}` passed
to a row is the record with no fields, `[:record :kotoba.map-literal/empty
[]]`; a destructured key the record lacks is its `:or` default, or nothing --
a presence test of that nothing is the constant `false`, and the binding
nothing reads any more is dropped, so the absent option is never built (the
typed wasm32 target has no `option-none` at all: `(let [x nil] 1)` is still
"unsupported typed Wasm expression" there, outside this floor). A refusal
naming the synthetic parameter now shows the pattern, `{:keys [extend?]}`.
The record with no fields was refused by every layer below: osaho's value
type and native gate (`a5db9a89`), kotoba-native's aggregate ABI and its
pair-chain lowering, which skipped a `record-new` with no values -- it is now
the empty chain, 0, with no allocation (`82d3dea1`; its
`aggregate-abi-portable-test` pinned the empty record as refused and now pins
it admitted) -- and kotoba-verifier's record check (`fde6f218`). Measured on
nbb: the gate was red on `275b40a0` / `3b2eef93` / `04a8e0e3` / `3e8134cd`
(8 failures, 11 errors of 19 assertions, the floor's literal), green on the
four new pins (19 assertions). The minimized options (absent 1, `{:extend?
true}` 3: 31) and an `:or` default (508) answer the reference's value on
`wasm32-kotoba-v1`, `x86_64-aiueos-kernel-v1` and `aarch64-macos-kotoba-v1`
with the oracle verified, and text-edit's `move-caret` / `move-to` ("abcd":
left, shift-left 2, move-to then shift-move-to) answer 333113313 on the
reference, on both native targets with `empty-state` private, and compile on
wasm32; with `empty-state` public it is refused natively as before (floor
`:export-signatures`). `amu compile --target x86_64-aiueos-kernel-v1` /
`--target aarch64-macos` of the minimized options exit 0 with `:oracle
{:status :verified}`; no artifact was run under a loader. kotoba-sema's
portable suite has the same 39 failures and 5 errors before and after
(identical lists), kotoba-verifier's the same 22 and 1, osaho's passes (256
tests), kotoba-native's 34 failures and 9 errors on its known-red list once
its empty-record pin moved, and amu's nbb suite the same 13 failures and 2 errors (the policy tests) once `text-edit-analyzes-on-nbb-test` moved its pin from the refusal to the admission (text-edit with move-caret and move-to answers 3 on the reference), `native-allocation-budget-test` left out on both sides: its x86_64 loader hung in Rosetta translation (process state U) on the old pins and the new alike. Refused by name: a
number as the options map, bound by `let` or not ("argument 5 to mv is i64,
and parameter {:keys [extend?]} of mv is the row {| r}: only a record
satisfies a row"); an absent option used as a number ("expected i64, got
option-i64"); `(:k m)`, a required read, off `{}` ("... is record
:kotoba.map-literal/empty, which has no field :extend? that the row ...
reads"); and a record, the empty one included, as an `if` test.

The vector parameter landed as floor `:vector-parameter` (gate
`vector-parameter-takes-the-callers-vector-test`), the first wall of
browser.input. Its hit-tests take a point and a rect the Clojure way,
`(defn- point-in-rect? [[px py] [x y w h]] ..)`, and were refused "unknown
operation: nth is not a builtin, a sugar head, or a function of this module".
An unannotated parameter is the provisional `:i64` until
`infer-absent-parameter-types` reads a type mismatch on it; `(vector-at p 0)`
raised one, but `nth` (what a vector pattern desugars to) and `count` on an
`:i64` fell through to an unknown operation and "count requires a bounded
vector", which name no parameter. kotoba-sema (`3d051f43`): `nth` and `count`
on an `:i64` receiver require `:vector-i64` of it, and a refused synthetic
temp a vector pattern is read through counts as its parameter, so the
parameter is the `:vector-i64` its callers pass. Measured on nbb: the gate was
red on `77d2dd84` (8 errors and 5 failures of 13 assertions, the floor's
literal), green on `3d051f43` (13 assertions). The minimized form (a
destructured parameter, `nth` and `count`: 83) and browser.input's
`point-in-rect?` / `in-titlebar?` / `in-resize-handle?` against a window
record's rect (11101) answer the reference's value on `x86_64-aiueos-kernel-v1`
and `aarch64-macos-kotoba-v1` with the oracle verified, and compile on
`wasm32-kotoba-v1`. kotoba-sema's portable suite has the same 39 failures and
5 errors of 616 tests before and after (identical lists). Refused by name: a
number, a string and a heterogeneous vector passed where the vector is read
("expected vector-i64, got i64" / "got string" / "got [:vector [:i64
:string]]"); a parameter used both as a vector and a number (the uses
disagree, both named); and an item as an `if` test (a number is never
truthy). browser.input's next walls were measured and put on the ladder:
`window-at`'s `filter` / `first` / `reverse` over the `[:list R]` a vector of
window records is (`:record-list-sequence`), and `normalize-event`'s open host
event (`:open-event-row`, which needs a decision: `(:k m)` is a required read
by this ADR, and the event reads keys it may lack).

The record-list sequence landed as floor `:record-list-sequence` (gate
`record-list-filter-first-reverse-test`), browser.input's second wall.
`window-at` is `(first (filter #(point-in-rect? point (:window/rect %))
(reverse (:surface/windows surface))))` over a vector literal of window
records, a `[:list R]`, and was refused three ways: `filter` "expected
vector-i64, got [:list R]" (it desugared to the T4.5 loop that builds a
bounded i64 vector, and a `[:list R]` has no builder), `first` "first
(pair-first) reads a pair chain or a bounded vector", and `reverse` "unknown
operation". `first` of a filter / remove / reverse chain needs no built
sequence: it is a search. kotoba-sema (`942d8764`) fuses the chain into one
loop that walks the source by index -- from its end under an odd number of
reverses -- and answers the first item every predicate admits, innermost
first, as Clojure's lazy filter tests it; it allocates nothing. Its two exits
are typed by the source: over a `[:list R]` the search answers `[:option R]`,
absent when nothing is found; over a bounded vector it answers the item and
traps on an empty result (`(vector-at <empty> 0)`, the trap `(first (filter
..))` always raised there), so a vector program keeps its value. `first` of a
`[:list R]` is `[:option R]`. Two inference gaps on the way were closed in the
same change: a loop helper's captures are settled again after row
specialization (the surface's windows were the placeholder `:i64` in the
generic), and a capture typed `:i64` that the loop body reads as a vector is
refined like an unannotated parameter, which refines the enclosing function's
parameter through the call (`window-at`'s `point`). kotoba-verifier
(`90ff3911`) admits a record field that is a `[:list R]` of one-word items
(kotoba-native's ABI and KIR already did) and a let naming a list item as
that record. Measured on nbb: the gate was red on `3d051f43` / `fde6f218` (2
failures and 12 errors of 17 assertions, the floor's literal), green on
`942d8764` / `90ff3911` (17 assertions). The minimized chains over a
`[:list R]` (29132) and window-at over two overlapping windows (2 on top, 1
alone, absent outside: 912) answer the reference's value on
`x86_64-aiueos-kernel-v1` and `aarch64-macos-kotoba-v1` with the oracle
verified, and compile on `wasm32-kotoba-v1`; a vector program keeps its value
(22) and its trap. `amu compile --target x86_64-aiueos-kernel-v1` / `--target
aarch64-macos` of window-at exit 0 with `:oracle {:status :verified}`; no
artifact was run under a loader. kotoba-sema's portable suite has the same 39
failures and 5 errors of 616 tests before and after, kotoba-verifier's the
same 22 and 1 of 53 (identical lists), and amu's nbb suite the same 13
failures and 2 errors (the policy tests) besides the gate,
`native-allocation-budget-test` left out on both sides: its x86_64 loader
again hung in Rosetta translation (process state U). Refused by name: what `first` answers over a list used as a record ("record-get
without a type descriptor requires a record value; got [:option [:record
..]]"); a number as the list ("expected vector-i64, got i64"); a bare
`reverse` ("reverse is admitted only where first reads it .. a reversed
sequence of its own needs a list builder this profile does not have"); and a
`filter` over a `[:list R]` that `first` does not read ("expected vector-i64,
got [:list R]"): materializing a list needs a list builder (a `typed-list-conj`
on KIR, Wasm and native), which no floor has asked for yet. Measured on the
way and left: a module with no private function exports every function, its
synthesized loop helpers included, so a loop over a `[:list R]` there is
refused natively ("typed values currently require .. the qualified native
one-word .. slice": a list is no export's ABI); an unannotated parameter
handed an option, `(defn- a-of [o d] (if-let [r o] ..))`, stays the
provisional `:i64`; and native rejects `(vector-at v (vector-count v))` in an
`if` branch at machine IR ("unknown-parameter").

The record field update landed as floor `:record-field-update` (gate
`update-writes-a-record-field-through-f-test`), measured on browser.surface.
browser.surface writes a field through the function that changes it --
`(update surface :surface/next-window-id inc)`, `(update surface
:surface/input-log conj e)`, `(update w :window/rect (fn [[_ _ ww hh]] [x y ww
hh]))` -- and `update` was no head: it fell through to a call of an undefined
function, refused at its function argument, "unbound symbol has no value type:
inc". kotoba-sema (`b1c48883`): `(update m k f x ..)` is `(let [m' m] (assoc
m' k (f (k m') x ..)))`, the read and the write the author would otherwise
spell, so the field keeps its type (assoc's rule) and the read is the required
read `(k m)` already is; a `fn` literal of the call's arity is applied as a
`let`, so a destructuring parameter means what it means there; a module's own
`update` keeps it. Measured on nbb: the gate was red on `942d8764` (5 failures
and 4 errors of 10 assertions, the floor's literal), green on `b1c48883` (10
assertions). browser.surface's field updates over a surface and a window
record answer 141523 on the reference and on `x86_64-aiueos-kernel-v1` and
`aarch64-macos-kotoba-v1` with the oracle verified, and compile on
`wasm32-kotoba-v1`; `amu compile --target x86_64-aiueos-kernel-v1` / `--target
aarch64-macos` of the same program exit 0 with `:oracle {:status :verified}`;
no artifact was run under a loader. kotoba-sema's portable suite has the same
39 failures and 5 errors of 616 tests before and after (identical lists).
Refused by name: `f` answering another type than the field holds ("expected
i64, got string"); a key the record does not have, through a row parameter
("... which has no field :surface/focus that the row {:surface/focus T | r} of
parameter s reads"); a number as the map ("record-get without a type
descriptor requires a record value; got :i64"); an absent `[:option T]` field
handed to a function of T ("expected i64, got [:option :i64]"); and `update`
without a function. `update` is not yet declared in the grammar authority
(`guest-grammar.edn`, whose digest is pinned in four repositories), as `mapv`
and `remove` are not.

browser.surface's other walls were measured and put on the ladder. Its first
function, `empty-surface`, is refused at `{.. :surface/focus nil ..}`: the
module writes the field only from expressions (`open-window`'s id,
`close-window`'s `(:window/id (peek remaining))`), and a present T from an
expression at an absent field is the coercion `:absent-field-from-assoc`
refuses, so `:absent-field-from-expression` needs a decision. An empty vector
field (`:surface/apps []`) is `:vector-i64`, so a record conj'd onto it is
"expected i64, got [:record ..]" (`:empty-vector-field`); a record literal
holding a vector of records is not typed as a record
(`:record-list-field-literal`). Measured and not yet floors: `(str "w" n)` of
an i64 ("expected string, got i64") and focus-window's two-argument `some`
(refused by design: `some` is the option constructor).

The empty vector field landed as floor `:empty-vector-field` (gate
`empty-vector-field-typed-by-the-module-conj-test`), measured on
browser.surface. Its surface starts `{.. :surface/apps [] :surface/windows []
:surface/input-log [] ..}` and grows them with `(update surface
:surface/windows conj window)`; `[]` was the bounded `:vector-i64`, so a
record conj'd onto it was "expression type mismatch: expected i64, got
[:record ..]", and a `[:list R]` had no builder at all ("conj requires a typed
set [:set item-type] or a bounded :vector-i64 / :vector-f64"). The builder is
a new KIR head, `typed-list-conj`: osaho (`738d8eb9`) appends at the end, as
Clojure's `conj` on the vector the source wrote, bounded by
`canonical-list-item-limit` (16384, a `:list-too-large` trap past it) and
charged one cell, and admits it on the native word slice beside
`typed-list-nth`; kotoba-verifier (`44fd1b56`) verifies it as
`typed-set-conj`; kotoba-native (`0ecca92a`) lowers it to `vector-conj` on the
list's word arena; kotoba-wasm (`fc6c8459`) calls `list-conj-i64` /
`list-conj-ref`, imported only by a module that builds a list, and
`runtime/browser-host.mjs` answers them; kotoba-script (`66bf70b5`) emits the
append inline, so its prelude -- and every other ESM artifact's bytes, its 66
parity goldens -- is unchanged. The typed-value conformance corpus gains
`:typed-list-conj-i64` and `:typed-list-conj-reference`, executed on the
reference, the ESM artifact and wasm on the browser host (28 vectors pass).
kotoba-sema (`4befca1e`) reads the
field the way `:absent-field-from-assoc` reads a nil one: a keyword key
written `[]` in the module is a list field when the module's own source
spells what it holds -- the items `(update m k conj v ..)` conj's at that key
and the items of a vector literal written there. One spelled item type R
other than `:i64` makes the field `[:list R]` and `[]` there `(typed-list-new
[:list R])`; spelled `:i64` items, or none, leave it the `:vector-i64` it was,
so no existing definition CID moves. `conj` onto a `[:list R]` is
`typed-list-conj`, and a vector literal where a `[:list T]` is expected is that
list, each item typed against T. Measured on nbb: the gate was red on the old
pins (2 failures and 4 errors of 8 assertions), green on the new (9 with the ESM assertion). A
browser.surface slice -- two windows opened with spelled window records
carrying a `:window/rect` vector, two scrolls logged -- answers 2387206 on the
reference, on `x86_64-aiueos-kernel-v1` and `aarch64-macos-kotoba-v1` with the
oracle verified, on `wasm32-browser-kotoba-v1` run on
`runtime/browser-host.mjs` under node, and as the `:js-kotoba-v1` ESM artifact
run under node (the gate checks wasm32's magic and the ESM source);
`amu compile --target x86_64-aiueos-kernel-v1` / `--target aarch64-macos` of
it exit 0 with `:oracle {:status :verified}`; no artifact was run under a
loader. The constructor is private there: a public function returning the
surface record is an export, floor `:export-signatures`. kotoba-sema's
portable suite (40 failures, 5 errors of 616 tests), kotoba-verifier's (22
failures, 1 error of 53) and kotoba-native's (35 failures, 9 errors of 463)
have identical failure lists before and after, on the same classpath; osaho's
(256 tests) and kotoba-wasm's (25) pass; the typed-value conformance corpus
passes its 26 vectors on the new host. Refused by name: a key the module
conj's two item types at ("... this module conj's two types at it: .. and ..;
a list holds one type"), which is browser.surface's own input log, whose
keyboard, scroll and text events are three shapes (`:input-log-events` needs
a decision); a number conj'd onto a list of records ("expected [:record ..],
got i64"). An item only an expression gives -- register-app's `app`
parameter, open-window's merged window -- spells nothing here; floor
`:list-item-from-expression` below types it. R is what the source spells, as
an absent field's T is: a map literal's expression values spell `:i64`, so
browser.surface's `{:event :keyboard/key :window-id window-id :key key}` is
typed with i64 fields.

The expression item landed as floor `:list-item-from-expression` (gate
`list-field-typed-by-a-conj-expression-test`), measured on browser.surface:
register-app's `(update surface :surface/apps conj app)` with `app` a
parameter, and open-window's `(update surface :surface/windows conj window)`
with `window` a merge, were refused "expression type mismatch: expected i64,
got [:record ..]" -- the field stayed `:vector-i64` because an expression
spells no item type. kotoba-sema (`dee5a5d2`) calls a `[]` key whose items
spell no type but `:i64` open, and lets inference type it: a `conj` onto an
open field notes the type its item is inferred to have, and `analyze-forms*`
analyses the module again with the noted types, as if spelled, until a pass
notes nothing new (the keys are finite; the passes are bounded at 16). One
non-`:i64` type R makes the field `[:list R]`; two types, or R beside an
integer literal conj'd there, are the conflict two spelled types already
were. A note is a fact about the source -- the type an item has where it is
conj'd -- so a pass that refuses still contributes them. `app` alone is not
typed by anything in register-app's body, so a parameter of a row function
that is only conj'd onto an open field rides along with the row (added to
`row-generics` after its fixed point, so passing it on makes nothing else a
row): specialized at the record a call passes, left as it was for anything
else -- an integer conj'd through a parameter keeps the `:vector-i64`, and no
definition CID moves. Two record parameters spell a specialization name past
`max-symbol-chars` (139 characters for register-app), which the verifier
refused as "runtime KIR function shape rejected"; the name is now cut to fit,
with the `_k` suffix keeping a cut name distinct. Measured on nbb: the gate
was red on the old pin (2 failures and 5 errors of 9 assertions), green on
the new (9 of 9); a browser.surface slice -- two apps registered, two windows
merged from parameters -- answers 2240520 on the reference, on
`x86_64-aiueos-kernel-v1` and `aarch64-macos-kotoba-v1` with the oracle
verified, and compiles to wasm32 and the `:js-kotoba-v1` ESM artifact (the
gate checks wasm32's magic and the ESM source; neither was run). `amu compile
--target x86_64-aiueos-kernel-v1` / `--target aarch64-macos` of it exit 0 with
`:oracle {:status :verified}`; no artifact was run under a loader. amu's kbb
suite (286 tests) has the same 13 failures and 2 errors, all in
`policy-grant-count-test`, before and after; kotoba-sema's own suite does not
load on its pins (`kir/host-stack-exhausted?` unresolved) before or after.
`:empty-vector-field`'s gate pinned the old refusal of register-app; that
assertion moved here as the admission. Refused by name: two inferred types
at one key ("... this module conj's two types at it: [:record ..app.id+app.title
..] and [:record ..app.id ..]; a list holds one type"), and a number conj'd
onto the inferred list of records ("expected [:record ..], got i64").
Measured behind it, before and after alike: the real open-window merges a
literal that reads the window it merges (`{:keys [app-id title ..] :as
window}`, then `(merge {.. :window/title (or title app-id id) ..} (dissoc
window ..))`), refused "record-get without a type descriptor requires a
record value; got :i64" where `(merge {:window/id "w" ..} window)` is
admitted -- floor `:merge-literal-reads-its-row`.

That landed as floor `:merge-literal-reads-its-row` (gate
`merge-literal-reading-its-row-test`). Two causes, measured apart. Literals
are typed (`:literal-typing`) before rows are specialized, and in the generic
a field read off the row has no type yet, so `{:t (:title w)}` stayed the
untyped literal; and a literal one of whose values spells a type --
open-window's `:window/state :normal` -- is lowered to its record at desugar,
every value that spells none taking `:i64` there, so `(:title w)` sat at an
`:i64` field. Either way the specialization's result kept the provisional
`:i64` and its caller was refused. kotoba-sema (`be68d75c`) types the
literals in each specialization round before inferring results, and
`type-literal` retypes a literal's own anonymous record at a field it
defaulted to `:i64` when the value there infers to another type (that was a
mismatch before, so nothing admitted moves). Measured on nbb: the gate was red
on the old pin (6 errors of 9 assertions), green on the new (9 of 9); an
open-window slice -- two windows, the merged literal reading app-id / title /
rect / document off the window and merging it dissoc'd, then conj'd onto
`:surface/windows` -- answers 24879700 on the reference and on
`x86_64-aiueos-kernel-v1` / `aarch64-macos-kotoba-v1` with the oracle
verified, and compiles to wasm32 and the `:js-kotoba-v1` ESM artifact (the
gate checks wasm32's magic and the ESM source; neither was run). Refused by
name: a merge onto a number ("argument 5 to ow is i64, and parameter w of ow
is the row {:title T | r}: only a record satisfies a row"), a read of a field
the row lacks ("... which has no field :title that the row {:title T | r} of
parameter w reads"), and `(or title ..)` over a title the record has ("if
test must be bool or an option" -- a string's truthiness). Measured behind
it, each on its own and before and after alike: next-window-id's `(str "w"
n)` of an i64 ("expected string, got i64", floor `:integer-str`); on native,
a row rebound by its own `update` ("runtime KIR record update rejected" at
verify, floor `:native-rebound-row-update`); and open-window's `(or title
app-id id)` / `(or rect [..])` fallbacks, which need a decision
(`:destructured-key-fallback`). The `[id surface]` pair next-window-id
returns, destructured, is admitted.

`(str "w" n)` landed as floor `:integer-str` (gate
`str-formats-an-integer-test`). `str` was desugared to a `string-concat` nest,
which requires two strings. kotoba-sema (`de903367`) keeps `str` through
desugar and resolves it in the type-directed rewrite: a `:string` part is
itself, an `:i64` part is `string-from-i64`'s decimal printer, and the parts
are the same `string-concat` nest, so a string-only `str` lowers as before. A
record, vector or option part is refused by name ("str of a record is refused:
str formats a string or an i64, and an aggregate is not printed implicitly")
-- no implicit printing, no coercion. One reading is kept rather than changed:
an unannotated parameter that `str` formats is still refined to `:string` (a
text builder's text parameter, browser.text-edit's insert-text), so `(defn- id
[n] (str "w" n))` called with 1 stays refused "expected string, got i64"; an
`:i64` `str` formats is one the source types -- a field (next-window-id's
counter), a literal, arithmetic, an annotated parameter. The printer was
fixed on the way, each fault measured by the gate: the most negative long
negated to itself and trapped in `string-substring` (now the magnitude of
`(quot n 10)` and its last digit); the recursive printer exhausted the
reference interpreter's 32 frames at 19 digits, and a 19-deep concat or `if`
chain did too (now three chunks zero-padded to 19 digits, balanced trees);
and native lowering refused a `10^18` literal (`unsupported-value`; no
literal past `10^9` now). Measured on nbb: the gate was red on the old pin (9
of 9 assertions), green on the new (10 of 10). A next-window-id slice -- id
`"w12"`, `(str "(" -7 ")")`, the most negative long, `(str 0 9 10)`, each
byte-compared with what Clojure's `str` prints -- answers 3420111 on the
reference and on `x86_64-aiueos-kernel-v1` / `aarch64-macos-kotoba-v1` with
the oracle verified, and compiles to wasm32 and the `:js-kotoba-v1` ESM
artifact (magic and source checked; neither was run). `amu compile --target
x86_64-aiueos-kernel-v1` and `--target aarch64-macos` of next-window-id exit
0 with `:oracle {:status :verified}`. Programs that already called
`string-from-i64` get the new printer, so their definition CIDs move.

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
