# ADR-0327: Two grammars on one classpath, and nothing compared them

- Status: accepted
- Date: 2026-09-03
- Authority: kotoba-lang
  `docs/adr/ADR-the-authority-names-every-head-the-frontend-admits.md`.
- Pin advanced: `io.github.kotoba-lang/kotoba-sema` `bb0d47c6` → `5bdf5914`.

## The measurement

`kotoba/lang/guest-grammar.edn` is on this repository's classpath **twice**:
once from `resources/` (`:paths ["src" "resources"]`) and once from
kotoba-sema, across the `deps.edn` pin. `io/resource` — which is what
`kotoba.compiler.sema/load-catalog-forbidden` calls — answers with whichever
comes first.

Measured 2026-09-03 across the four repositories that carry a copy, on their
mains, before this wave:

| copy | lines |
|---|---|
| kotoba-lang `lang/guest-grammar.edn` (authority) | 601 |
| kotoba-lang `resources/…` | 601 |
| kotoba-sema `resources/…` | 601 |
| **amu `resources/…`** | **580** |
| **kotoba `resources/…`** | **401** |
| **kotoba `vendor/grammar/resources/…`** | **401** |

This repository's copy was one change behind: local-state slice 1, where the
authority admits a non-escaping `atom`/`swap!`/`reset!` by elaboration and
removed the three heads from `:forbidden-heads`. This copy still forbade them.

**`guest-grammar-conformance-test` could not see it.** That test asserts
`sema/forbidden-heads` is a superset of the catalog's forbidden heads — a
superset check is blind to a stale copy that forbids *too much*. It had been
green throughout.

## Why the check that existed measured nothing

kotoba-lang has `local-and-sibling-vendors-match-authority`, which compares
its authority against `../amu`, `../kotoba`, `../kotoba-sema` and
`../grammar`. Those are west monorepo paths; each is guarded with
`(when (.isFile ...))`, and `authority-vendor-drift` reports an absent path as
`:missing`, which the test tolerates. In a single-repository clone it compares
one file — the authority's own copy of itself — and reports green.

Three of four copies had drifted on main and it said nothing. That is
ADR-2608136000's shape exactly: a check that could not run returns the value
of a check that ran and found nothing wrong.

## Decision

1. **Resync this repository's copy** to the widened authority
   (sha256 `67561e57…`).
2. **Advance the kotoba-sema pin with it.** Resyncing this copy alone would
   leave two different grammars on one classpath, with which one wins decided
   by classpath order.
3. **Compare them, where they cannot be absent.**
   `test/kotoba/compiler/guest_grammar_vendor_test.clj` enumerates *every*
   classpath copy — `ClassLoader/getResources`, not `io/resource`, which
   answers with the first and so cannot see a second — and asserts they are
   byte-identical to each other and to the pinned authority digest.

The failure message names the **differing heads**: the symmetric difference of
`:admitted-builtins` and of `:forbidden-heads`, rather than "the files
differ". It prints `COMPARED <n>` and refuses `n < 2`, because a run that
found one copy has compared nothing and must not read as a pass.

The digest is pinned as a literal in four repositories (kotoba-lang,
kotoba-sema, kotoba and here). That is what makes the next authority edit a
four-repository wave by construction, including in a clone with no sibling to
compare against.

## What the widened authority now says

`:admitted-builtins` named three kernel heads while kotoba-sema's frontend
admitted 114 (53 memory, 8 carried slice, 53 privileged). It now names all
114. No ceiling moves and nothing new is admitted **by this repository** —
nothing here reads the set at all. Its one reader anywhere is
`kotoba.grammar/admitted-heads`, in kotoba-lang/kotoba's vendored grammar
loader, where a missing head is reported as `:unknown-form`. So the effect of
naming the 114 is that kotoba stops calling heads the compiler admits
unknown; whether each has a lowering on the target at hand is still the
compiler's answer, and on wasm and ClojureScript it is no.

## What the kotoba-sema pin advance cost, and why each cost is kept

Four assertions in this repository were pinned to the OLD kotoba-sema's exact
words. All four are corrected rather than loosened:

| test | was | is |
|---|---|---|
| `ambient-and-forbidden-forms-always-reject` `:atom` | `:kotoba.error/ambient-forbidden` | `:kotoba.error/local-state-atom-position` — `atom` left `:forbidden-heads` with local-state slice 1; the source is still refused, by the position rule. `ref` and `volatile!` added beside it as the control, so "refused because ambient mutation is banned" stays distinguishable from "refused because this atom escapes" |
| `typed-sets-are-…-persistent` | a fixture `defn` named `contains?` | renamed `has-item?` — kotoba-sema now reserves admitted operation heads, and the fixture had been borrowing a name the language owns |
| `direct-floating-ordered-collections-fail-closed` ×2 | one `#"direct floating"` regex over three types | each type pins its own code AND its own reason. The map cases stopped saying "direct floating" because the typed-map-key work replaced a shared sentence with two specific ones — **the old regex went red on a message that had become better**, and a regex broad enough to survive that would have accepted any refusal at all |

That last one is the one worth keeping in view. A negative test whose only
assertion is a substring of the shared prefix is a test that has not asserted
its own reason, which is the failure ADR-2608136000 names.

## Verification

```
java -cp "$(clojure -A:test -Spath)" clojure.main -e \
  "(clojure.test/run-tests 'kotoba.compiler.guest-grammar-vendor-test)"
  COMPARED 2   SCANNED 189 admitted-builtins (114 kernel heads)
```

Full suite at the advanced pins: **1298 tests / 9419 assertions, 0 failures,
0 errors, 166 of 166 namespaces**.

The red was not manufactured. Written against the **old** kotoba-sema pin,
the test failed on its first run and named the drift:

```
two classpath copies of the grammar disagree; which one the compiler reads is
decided by classpath order
  amu/resources/…              67561e57…
  kotoba-sema bb0d47c6/…       61e0f867…
  differing heads:
    :admitted-builtins  only-in-first  (111 kernel heads)
    :forbidden-heads    only-in-second ("atom" "reset!" "swap!")
```

That is the drift this ADR is about, found by the check written for it, before
the pin was advanced.
