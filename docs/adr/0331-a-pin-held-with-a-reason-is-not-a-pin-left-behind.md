# ADR-0331: A pin held with a reason is not a pin left behind

- Status: accepted; the hold it decided was LIFTED 2026-09-12 (see the last section)
- Date: 2026-09-03

## Context

ADR 0330 advanced every pinned dependency in `deps.edn` to its own main, because
24 unlanded worktree bumps had left two QEMU proofs unreproducible from landed
code. `io-ipld` is the one that did not move, and this records why, because
"lagging" and "held for an argued reason" look identical from outside the file
unless the reason is written down.

The workspace rule this follows: a pin behind its upstream default branch is a
defect **unless** the reason not to advance is recorded next to it, so that a
reader can tell a decision from an omission.

## The measurement

Advancing `io-ipld` `1a2e10cf` → `48ba4049` (28 commits) turns
`kotoba.compiler.ipld-adl-test/guest-output-must-be-canonical-dag-cbor` red in
one case out of four:

```
FAIL in (guest-output-must-be-canonical-dag-cbor) (ipld_adl_test.clj:92)
a non-canonical encoding decodes cleanly and is still refused
expected: (= :adl-output-not-canonical (:code data))
  actual: (not (= :adl-output-not-canonical :adl-output-not-a-node))

FAIL in (guest-output-must-be-canonical-dag-cbor) (ipld_adl_test.clj:94)
expected: (= [2 1] [(:output-bytes data) (:canonical-bytes data)])
  actual: (not (= [2 1] [nil nil]))
```

The other three cases in that test — a canonical node passes, a truncated node
is refused, trailing bytes are refused — stay green in both directions, and the
whole namespace is green with the pin held. So the change is scoped to exactly
one claim.

## Why that failure is not a test that needs updating

The case exists to assert a **layering**, and its own comment says so:

> The source grammar is closed over byte strings, so a transform can be lowered
> faithfully and still return bytes the codec would not have written. Decoding
> alone does not separate those cases.

Its fixture is `18 05` — CBOR's two-byte `uint8` spelling of 5, where the codec
would have written the one-byte `05`. It decodes to a perfectly good integer, so
only re-encoding and comparing shows anything is wrong, and
`:adl-output-not-canonical` with `[:output-bytes 2 :canonical-bytes 1]` is the
ADL capability saying it did that comparison.

io-ipld `01b6453` ("canonical DAG-CBOR corpus, and enforce the canonical form")
makes the **decoder** reject non-minimal integer encodings. At `48ba4049` the
fixture therefore never reaches the ADL check: decoding fails first, and the
case answers `:adl-output-not-a-node`.

Changing the expectation to the new code would be one line. It would also leave
`:adl-output-not-canonical` with **no input in this repository that can produce
it** — a refusal path that cannot fire, reported by a green suite. That is the
shape ADR-2608136000 exists to refuse ("a check that measured nothing returns
the same value as a check that measured and found nothing"), and the fix for it
is never to make the assertion agree with the silence.

The honest alternatives are both outside a pin-consolidation commit:

1. Establish that the ADL-level canonicality check is genuinely subsumed by the
   decoder at `48ba4049` — i.e. that **no** byte string decodes cleanly and
   re-encodes differently — and then delete the check and its code rather than
   keep a dead one.
2. Find a form that still decodes and still re-encodes differently at
   `48ba4049`, and move the fixture to it.

Either is a question for io-ipld's owner and for whoever owns the ADL
capability. Neither is answerable by measuring one fixture.

## Decision

Hold `io-ipld` at `1a2e10cf`, with the reason in `deps.edn` beside the pin and
in this ADR. Advance `io-multiformats` to `561fe7df` regardless: that commit
only replaces the npm package `@noble/hashes` with `kotoba-lang/org-nist-sha2`,
which was already in this closure, and the full suite is green with it.

Nothing in the K16 pure-native programme depends on the io-ipld advance. The
three things it carries — a byte-exact `dag-pb` codec, canonical DAG-JSON, and
the `@noble/hashes` drop — reach this repository through the IPLD ADL capability
and the module-lock CID, neither of which is on a `.kotoba` compile path.

## Consequences

- `io-ipld` will read as 28 commits behind until the question above is
  answered. The comment in `deps.edn` says which question, so the next reader
  does not have to re-measure to find out whether it is a decision or neglect.
- The blocked advance is a **finding for io-ipld**, not a defect in this
  repository: a decoder that enforces canonical form is strictly better, and it
  is only this test's fixture — chosen when the decoder did not — that stops
  discriminating because of it.

## 2026-09-12: the hold is lifted

The argument above is unchanged and was re-measured today; what changed is that
both things it protected have left this repository.

1. **The test cannot run.** `ipld_adl_test` imports `java.nio` and the module
   it exercises, `kotoba.compiler.ipld-adl`, is itself JVM-only
   (`FileAttribute`). ADR 0347 removed the JVM route; neither file runs on any
   route this repository has. A hold that keeps a test discriminating is worth
   nothing while the test cannot fire either way -- that is the same shape this
   ADR refuses, from the other side.

2. **The open question has a measurement on both shas.** Decoding then
   re-encoding under nbb, with only the io-ipld sha changed:

   | input | at `1a2e10cf` | at `3e48e468` |
   |---|---|---|
   | `18 05` (uint8 spelling of 5) | decodes to 5, output 2 bytes, canonical 1 -- the ADL refusal fires | refused by the decoder: "bytes are not canonical DAG-CBOR" |
   | `a2 61 62 01 61 61 02` (`{"b" 1 "a" 2}`, keys unsorted) | decodes, keys unsorted | refused by the decoder |
   | `fa 3f c0 00 00` (float32 1.5) | refused: "unsupported simple/float" | same |
   | `9f 01 ff` (indefinite array) | refused: "indefinite/reserved length unsupported" | same |

   Four non-canonical shapes; at `3e48e468` none reaches the ADL check. That is
   evidence for option 1 above (the check is subsumed by the decoder), not a
   proof over all inputs. If `kotoba.compiler.ipld-adl` is ever ported to the
   nbb route, the test's non-canonical case should be re-asked against the
   decoder of the day, and if no input reaches `:adl-output-not-canonical`,
   the check should be deleted rather than kept dead.

Cost of the hold, measured at amu `46d91a25` on the project route: 9 of the
61 "requires an explicit :export vector" refusals named an `ipld.*` namespace
or `kotoba.value.codec`. The pin moves to `3e48e468` (ahead 62, behind 0) with
this section's summary beside it in `deps.edn`. The advance adds
`dev-protobuf` to the closure -- `ipld.dag-pb`'s wire codec, a real dependency
and not excluded.

