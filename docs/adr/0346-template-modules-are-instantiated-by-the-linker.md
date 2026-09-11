# ADR 0346: Template modules are instantiated by the linker, not typed by the language

## Status

Proposed (2026-09-11). Implements the superproject's `adr-2609113100`
("option C"). The spelling below is the decision being asked for; it is not
yet in the grammar authority (see "Grammar authority").

## Context

Kotoba has no type variables. A parameter is annotated with a concrete value
type or defaults to `:i64`, so a library generic over its element type --
`kotoba.set.union` over `[:set :i64]` and over `[:set :symbol]` -- could only
be written twice, by hand, in two files that differ in one token.

Measured 2026-09-11 on `b57284d6` with those two files written out by hand
and a root requiring both: link ok, five distinct definition CIDs, CIDs
unchanged when the aliases are renamed, and `main` answers 5 through
`runtime/browser-host.mjs`. The language already accepts each instantiation;
what was missing was a way to write the template once.

## Decision

Add NO typing to the language. Add two clauses the LINKER reads and strips
before the frontend sees a module:

```clojure
;; template module, kotoba/set/union.kotoba
(ns kotoba.set.union
  (:params [elem])                      ; type parameters: simple symbols
  (:export [union]))
(defn union [s1 [:set elem] s2 [:set elem]] [:set elem] ...)

;; importer
(ns root
  (:require [kotoba.set.union :as ui :with {elem :i64}]      ; binding
            [kotoba.set.union :as us :with {elem :symbol}])
  (:export [main]))
```

`kotoba.compiler.project/link-source` instantiates the template once per
distinct binding by substituting the bound type form for the parameter
symbol in the template's READ FORMS, then analyses the result exactly as it
analyses a hand-written module. `kotoba-sema` is unchanged and never sees a
parameter symbol: the two instantiations above are byte-for-byte the two
hand-written files that were measured, and carry the same definition CIDs
(pinned in `test/kotoba/compiler/project_template_test.clj`).

### Where a parameter symbol is a type

Decided the way the frontend itself decides it (`parameter-type-item?`): a
type is a keyword or a vector whose head is a keyword. The symbol is
substituted

1. anywhere inside a keyword-headed vector (`[:set elem]`, `[:map :string
   [:list elem]]`, the type argument of `typed-set-new`, a result annotation);
2. in the type slot after a parameter pattern in a `defn`/`defn-` parameter
   vector (`[s1 elem]` -> `[s1 :i64]`);
3. in the result slot after that parameter vector;
4. in the values of the template's OWN `:with` maps, which is how a template
   forwards its element type to a library it requires (`:with {elem elem}`).

It is NOT substituted in a value position: `(let [elem 1] (+ elem 1))` inside
a template still means the local. A parameter symbol at a PATTERN position of
a `defn` parameter vector is refused (`[elem]` would otherwise mean "an i64
named elem" in a module whose header says `elem` is a type). A parameter
symbol that survives substitution anywhere it is not a bound local is refused
by the linker -- "template parameter elem reaches the frontend unsubstituted"
-- rather than handed to the frontend, which would report an unbound variable
in a synthetic text.

The residual ambiguity is the frontend's own: a VALUE vector literal whose
head is a keyword and which names a local spelled like a parameter would be
rewritten. The alternative -- a closed list of type-constructor keywords --
would silently stop substituting the day the frontend grows one, and the
loose-parameter check would then refuse the template. One rule, shared with
the frontend, was preferred.

### Identity and keys

Modules are keyed by `[namespace binding]` (binding as a sorted map; nil for
an ordinary module, whose key is the bare namespace as before). Two importers
binding the same template the same way reach one key and one analysed
module; two bindings are two modules with disjoint function and lambda-ID
ranges. The cycle guard stays on the namespace, so a template requiring
itself under another binding -- an unbounded family -- is refused as a cycle.

Definition CIDs of an instantiation do not depend on the importer's alias
(measured: renaming `ui`/`us` to `a`/`b` moves no CID) and are equal to the
CIDs of the same module written by hand.

### Fail closed, both ways, by name

- A template reached without a binding -- as a project dependency without
  `:with`, as the root, or as a single file -- is refused: "template module
  kotoba.set.union declares (:params [elem]) and needs an instantiation:
  require it with :with {elem <type>}". On the single-file path the
  frontend's generic clause refusal is renamed at the reporting boundary by
  `kotoba.compiler.diagnostic/refine`, the same way `(:require ...)` is.
- `:with` on a module that declares no `:params`; `:with` naming a parameter
  the template does not declare; `:with` missing a declared parameter;
  `:with` binding a parameter to something that is not a type form; `:params`
  that are not distinct simple symbols, or more than eight.

### Bounds

`:params` and `:with` are bounded by `max-template-parameters` (8). An
instantiation is a module against `max-project-modules` (256) and its
functions count against `max-project-functions` (1024). Nothing new is
unbounded.

### Locks, digests, source maps

`--module-lock` is unchanged: the lock pins SOURCE TEXTS by namespace, the
template is one block, and the bindings live in the importer's (pinned)
source, so the lock's CID already covers them. Measured: the lock built from
the template project has two blocks and compiles to the same bytes as the
path-resolved build. Per-module source digests are keyed by namespace
(`project/module-namespaces`), so a template appears once however many times
it is instantiated; `:kotoba.module/order` carries the linker keys. The
source map records `:binding` on every entry an instantiation wrote, and a
refusal raised inside an instantiation says which one: "... in kotoba.set.union
with {elem :symbol}".

A project that declares no `:params` and no `:with` links to byte-identical
output: the same `definition-cids` before and after (pinned), plain namespace
keys in `:module-order`, and source-map entries of the same shape.

## Grammar authority

`kotoba-lang/lang/guest-grammar.edn` does not know either clause. Landing
this needs, in `:core-form-shapes` (or the namespace-header entry the
authority chooses):

- `ns`: an optional `(:params [sym ...])` clause -- simple symbols, distinct,
  at most 8 -- marking the module as a template that the single-module path
  refuses;
- `ns :require`: the spec shape `[namespace :as alias :with {param type}]`
  beside `[namespace :as alias]`, with `:with` values restricted to value-type
  forms (or the requiring template's own parameters).

The grammar is sha-pinned in four repositories, and this one's
`test/kotoba/compiler/guest_grammar_vendor_test.clj` compares copies, so the
authority moves first and the pins follow in one wave. This ADR does not do
that wave.

## Consequences

A library generic over one element type is written once. The frontend, the
KIR, and every backend are untouched; what a backend cannot lower for a
concrete type, it still cannot lower for that type reached through a
template -- the restricted-ESM emitter has no lowering for typed sets, for
instance, and that fact is about the backend, not about linking.
