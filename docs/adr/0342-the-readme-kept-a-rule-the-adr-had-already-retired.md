# ADR-0342: The README kept a rule the ADR had already retired

- Status: accepted
- Date: 2026-09-07
- Relates: ADR-0300 (definition CIDs key the cache), ADR-0326 (the amendment
  this README missed), superproject
  `adr-2609077000-amus-definition-cids-are-unison-shaped-measured`

## Context

The owner asked whether Amu actually hashes definitions correctly and whether
it is genuinely Unison-shaped. It is; seven properties were measured on
`origin/main` at `78cdc2e1`, JVM-free, and the superproject ADR carries the
procedure. Two of them disagreed with this repository's README rather than
with the compiler.

**The `:abort` example was stale.** The README said a definition the identity
cannot seal is *"today, one whose effect row carries the tracked control effect
`:abort`, which names no capability"*. Measured, an aborting definition gets a
real CID and reports `:effect-row #{:abort}`. That is correct behaviour:
kotoba-kir `984a507` (2026-09-02) put `:abort` in the closed `control-effects`
set, kotoba-lang adjudicated it, and **ADR-0300 section 4 was amended for it on
2026-09-03**. The amendment names the pin it advanced and the arguments that
survive. The README was not touched, so for four days the repository's front
page taught that an aborting function has no identity while its own ADR taught
the opposite.

**The cache claim did not name its route.** The README said renaming a private
function means *"the compile is served from cache and reports
`:definitions-recompiled 0`"*. Measured through `bin/amu compile --jvm-free`,
an unchanged module recompiled twice reports `3` both times: the one-shot CLI
has no cache, by design, and `compile-uncached!` says so in a comment. The
claim is true on the worker route, where an unchanged recompile answers
`:cache :hit` with `0` and a renamed module answers `:cache :miss` with `0`.
Nothing is broken. But a reader who measures the documented number on the
documented command gets a different answer, and the first conclusion available
to them is that the cache does not work.

## Decision

**1. Both README paragraphs are corrected, and the correction says what it
corrects.** The `:abort` paragraph now states the actual refusal domain -- a
wire id no catalog names, or a keyword outside the closed set -- and records
that it named `:abort` until 2026-09-07. The cache paragraph now names the
worker route and the `:cache` key that distinguishes *not consulted* from
*missed*.

**2. A retired rule is retired in the README in the same commit as in the
ADR.** ADR-0300's amendment was exemplary about the pin, the adjudication and
the surviving arguments, and still left the rule standing in the one document
a new reader opens first. An amendment that moves a decision must move every
place that states it as current, or the retired version is what gets read.

**3. When a document states a number a reader can measure, it names the
command that produces it.** `:definitions-recompiled 0` without `amu worker`
beside it is a claim that fails on the obvious command. This is the workspace
rule about not writing measured values into standing prose, in its other form:
if a value must appear, the invocation that yields it appears with it.

## What is not claimed

- No defect in the compiler was found. All seven measured properties held.
- ADR-0300 section 4 needed no change; it was already right.
- Byte-identical CIDs between the JVM route and the JDK-free nbb route are
  asserted by this repository's tests and were **not** re-measured here. The
  superproject ADR says so rather than repeating the claim.

## Reproduce

    amu definition-cids <file> --jvm-free      # per-definition CIDs
    amu compile <file> --target wasm32 --jvm-free --output <out>
    amu worker --target wasm32 < requests.ndjson   # the cached route

Rename a private function, its parameter and its call sites: every CID and the
emitted bytes stay identical. Change one body: the definition, its caller and
its caller's caller all move. Widen a record used as a parameter type: the
reader's CID moves with its body untouched.
