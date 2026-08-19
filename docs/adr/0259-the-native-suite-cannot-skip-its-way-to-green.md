# ADR 0259: the native conformance suite cannot skip its way to green

Status: accepted

## Context

`kotoba.compiler.lang-native-conformance` is the suite that answers whether the
language actually reaches the native backend — 20 pure-native cases compiled,
signed, and executed as real machine code through the kexe loader.

It had two ways to report success having executed nothing.

**Nothing ran.** `tender-native-available?` is checked per case. When the
dependency cannot be resolved, all 20 return `:status :skipped`, so `failed` is
empty and the old verdict

```clojure
:ok? (and (empty? failed)
          (or (seq skipped)      ; skip-all is soft ok when dep missing
              (= passed (count cases))))
```

was **true with `passed 0`**. `-main` exited 0.

**Nothing to run.** `(run-suite {:cases []})` gives `passed 0` and
`(count cases) 0`, so `(= passed (count cases))` holds and `:ok?` was true
again — measured, not reasoned.

The test could not catch either, because its count assertion was inside
`(when-not (:skipped? report) ...)`: **the one check that would have noticed
"nothing ran" was skipped by the very condition that caused it.**

These are the first two questions of superproject ADR-2608136000 — what does a
check return when its input is absent, and when it cannot execute at all? A
value equal to a pass is the defect. It is the same shape as that ADR's
`root-permit-index` (297 reports over absent input) and the same shape as the
reach floor added to `kexe_parser_fuzz.c` two days ago, where a deliberately
broken `inspect_string_result` survived 20,000 cases the target never reached.

## Decision

`run-suite` reports a `:status` of `:measured`, `:could-not-measure`
(dependency absent) or `:no-cases`, and `:ok?` is true only when the backend was
actually exercised: no failures, at least one case, no skips, and every case
passed. `-main` exits **2** when it could not measure — neither 0 nor 1, so
"the native backend is fine" and "the native backend was never reached" do not
leave by the same door.

The test drops the `when-not` guard and asserts `:status` is `:measured`. Under
the `:test` alias `kototama-native` is an `:extra-dep`, so the suite must be
able to measure there; if it cannot, that is a finding about the environment and
should be loud rather than silent.

## This is latent, not active

Measured 2026-08-19 on the authoring workstation: the suite really does run,
20/20 against `:aarch64-kotoba-v1`, no skips. The green was honest. The skip
path is reached only when `kototama-native` cannot be resolved — which is
exactly the situation in which a green is worth least.

Worth stating plainly because the fix removes a false green that nobody had
observed being emitted. What was observed is the mechanism, by driving it:
`with-redefs` on `tender-native-available?` reproduces `:ok? true, passed 0` on
the old code.

Also note `:ok?` was not a boolean there — `(and ... (or (seq skipped) ...))`
returns the seq of skipped cases, so the old report carried twenty maps in the
field callers read as a verdict.

## Evidence

`lang_native_conformance_test.clj`, 3 tests / 35 assertions, all three paths
pinned separately:

| path | status | ok? |
| --- | --- | --- |
| dependency absent (`with-redefs`) | `:could-not-measure` | false |
| empty manifest | `:no-cases` | false |
| two genuinely failing cases | `:measured` | false, `failed-count 2` |

The third row is the one that keeps the floor honest: a real red must not be
laundered into "could not measure".

Restoring the old `:ok?` expression fails exactly the two new assertions, with
`actual:` showing the real production shape — twenty cases carrying
`:status :skipped :reason :tender-native-missing`.

Full amu suite after the change: 1,099 tests, 8,302 assertions, 0 failures.
CLI exits 0 when measured; the unmeasured path computes exit 2.

## What this does NOT claim

- that a false green was ever emitted in CI — no such receipt was found, and
  this suite is not one of the four fleet gates for amu
- any change to what the 20 cases cover, or to native coverage itself
- that the other conformance suites in this repo have been audited for the
  same shape
