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
   a value. A record crossing a function boundary is still refused by the
   native oracle (exit 65), as an annotated one is: floor `:native-handles`.
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
   Hosted (`wasm32-browser`) compiles these forms; both native targets refuse
   them, as they refuse the same forms written by hand: `record-assoc` is not
   natively qualified (exit 70) and the verifier does not see a record through
   a `let` operand (exit 65) -- floor `:native-handles`.
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
   (`wasm32-browser`) compiles these forms; both native targets refuse them at
   the native artifact oracle (exit 65), as they refuse a record crossing a
   function boundary: floor `:native-handles`. Programs admitted before are
   unchanged -- every new row slot was a refusal.
   Still open: a vector literal of records, a map literal bound by `let`
   before it reaches a row, and retiring the keyword->i64 map outright (floor
   `:literal-typing`: those literals are lowered from their source before any
   type is inferred); the specialization CID derived from the generic's
   (floor `:specialization-identity`; until then a specialization's CID is its
   own monomorphic KIR's, which seals the record).
4. **Function values.** A function type carries its effect row; a closure is a
   one-word handle (code, environment) under aggregate ABI v8 and may be a
   record field or vector element. A stored function's effects are part of the
   record's type, so nothing ambient enters. (The ADR 0352 internal error on a
   stored closure becomes either this or a named refusal.)
5. **Strings by code unit, by name.** `count` of a string stays refused (it
   has two answers). `string-code-unit-count`, `string-code-unit-at` and
   `subs` over code units are primitives; browser's `#?(:clj ...)` interop
   branches gain a `:kotoba` branch that calls them.
6. **Hiccup is syntax for a node ADT.** `Node = Text string | Elem tag attrs
   [Node] | Frag [Node]` over ABI v8's recursive `[:ref q]`. A hiccup literal
   desugars to it at compile time; runtime shape tests over hiccup become an
   exhaustive `variant-match`.
7. **Allocation is charged like fuel.** Every constructor debits the same
   64-bit ledger fuel uses (kotoba-kir ADR 0268, amu ADR 0333). The ADT
   node/depth ceilings stop being language constants and become the budget
   the caller grants; a DOM tree is bounded by what it was given, not by 64.
8. **Admission by definition graph.** The 1 MiB bound moves from linked source
   bytes to per-definition size and closure count; a module is its definitions
   (as ADR 0300 already identifies it), so cssom's 1 MB file is admitted
   definition by definition.
9. **Native handles at loop boundaries.** kotoba-native qualifies record,
   vector and closure handles as loop-helper boundary types and retires
   `map-new`, so every form above compiles for both native targets.

Then browser moves, whole component by component (text-edit, input, surface
with cssom and dom-gpu), and the hosted engine switches to amu's output of
the same source. The kernel's mirrored objects (aiueos ADR-0223..0234) retire
as each module lands.

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
