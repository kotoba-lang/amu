# ADR-0319: The pin advance retired four tests, and one marker with them

- Status: accepted
- Date: 2026-09-02

## Context

ADR-0318's packaging change needs kotoba-native at or past `91033a9`
(`kotoba.native.image-scratch`), and the two new heads need kotoba-sema,
kotoba-kir and kotoba-verifier at or past their own merges. Advancing those
four pins turned nine assertions in this repository red, in tests that have
nothing to do with a writable region or a function's address. This ADR records
what they were and why the fix is what it is, because absorbing another
stream's behaviour change silently is how a suite stops meaning anything.

**Measured**: this repository's suite at the merged main is 1287 tests / 9337
assertions, 0 failures. With the four pins advanced and nothing else changed,
1289 / 9364 with **9 failures**. Both numbers were taken, in that order, before
anything was edited.

## What changed upstream

**kotoba-kir reversed a rule about `:abort`.** `effect-row-from-hir`'s
docstring now says a member of `control-effects` "passes through unchanged: it
carries no wire id, so there is no catalog lookup to make and nothing a lookup
could get wrong". Four tests here rested on the opposite -- that `:abort` names
no authority, so the bridge refuses -- and used
`test/nbb/fixtures/abort-callee.kotoba` to reach the refusal marker. An
aborting definition is identifiable now.

**kotoba-sema made one refusal more specific.** `(atom 1)` outside a `let`
binding position is refused as `:kotoba.error/local-state-atom-position` where
it used to fall to the generic `:kotoba.error/ambient-forbidden`.

## Decision

**The ambient row is updated, not relaxed.** The claim that suite makes is that
ambient forms always REJECT, and they do; `(some? e)` is what carries it. Only
the code is more precise. Relaxing the assertion to accept either code would
lose the thing the row is for.

**The four identity tests keep their purpose and change their fixture.** They
exist to prove that an unbridgeable row is REFUSED with a marker rather than
given an invented name, and that purpose is still reachable -- through the
other refusal the same upstream docstring names: "a wire id the catalog does
not name is refused ... the only way to reach such an id is a literal
`(cap-call N x)` in source, and a name invented for it would be a lie sealed
into an identity". `test/nbb/fixtures/unbridged-effect.kotoba` is that program.

The behaviour that replaced the old premise is asserted in its own right --
`an-aborting-definition-is-identifiable-now` -- rather than left implicit in
the absence of a test. A rule that changed should be visible as a rule, not as
a gap.

## A marker this leaves unreachable, and it is not this stream's to fix

`:dependency-unavailable` marks a definition that is unidentifiable *because a
callee is*. The old fixture reached it because `:abort` does NOT propagate -- a
call never puts it on the caller's row -- so `safe-div` was refused and `main`
was merely blocked by it. A capability effect DOES propagate, so under the new
fixture `main` carries the unnamed wire id itself and is refused under
`:unbridged-effect`.

Nothing in this suite reaches `:dependency-unavailable` any more. Reaching it
needs a callee whose row is unbridgeable and a caller whose row is not, and a
propagating effect cannot produce that pair. Recorded here and left in the test
as a named gap rather than papered over with a marker assertion that would pass
for the wrong reason.

## Consequences

- Suite after: 1290 tests / 9376 assertions, 0 failures.
- The `aggregate-abi` pinned-closure test carries the four new SHAs with the
  reason for each advance beside it, as it has for every previous one.
