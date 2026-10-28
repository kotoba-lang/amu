# Same-local vector descriptor reuse: no original writer admitted

The native prototype is correct on independent tests but does not shorten any
original Embench writer. Reject it before timing and keep the qualified
[small-tail-frame product](coscientist-small-tail-frame-20261006.md) unchanged.
The all19 original aligned-body C-or-better goal remains unachieved; no official
Embench score or new speedup is claimed.

## Hypothesis and implementation

The preceding census found119 statemate terminal-only functions combining direct
vector reads and expanded writer calls. This is a static count, not a time share.
The registered prototype reserves x3 for vector length and x4 for the item base
only in existing mode2 with at most3 locals/temps, no spill/outgoing frame or
returning call. Its first original read retains the original handle and index
checks, capturing the same descriptor in those spare registers. A compile-time
same-local witness permits an exact closed, typed, uncharged natural-parameter
writer to keep its own index check while eliminating redundant descriptor checks.
Labels, branches, unknown calls/effects and root replacement clear the witness.
No computation result is memoized and no cache is connected to the product.

## Native proof and actual original code

Four native generations are byte-identical:837320 bytes, SHA256
`4b28bafcdbc03f85dbc3724dcf3325b36604471942c4fd1b9ce08154c1f9ff09`.
Independent27 new fixtures exercise the intended mode2 using a genuine closed
terminal sink.6,300 full-state oracles check signed extremes, aliasing, changed
handles, write bounds, zero values, division traps, insufficient fuel and all11
allocated items including partial writes.209 original19 partial-state and38
resource comparisons agree with the product. The existing508 fixtures and14,523
executions pass; their emitted blob and unit golden remain byte-identical.
Native guard probes reject31 instruction-field changes,11 metadata/call changes,
7 mode changes, open metadata, duplicate labels and invalid callees.

The independently observed original19 SIR, frames, local/depth/leaf metadata and
fuel instructions are unchanged.18 guest images are byte-identical. statemate
captures descriptors at119 reads, but **zero original writer sites use them**:
the actual put wrapper contains an entry FUEL instruction and is correctly
refused by this uncharged-only matcher. All original code-word counts are equal.
Independent fixtures show11 words saved per admitted uncharged write and22 for
two writes; this does not establish benefit on the original workloads. There is
no timing run, product source change, gate qualification or integrated adoption.

## Next prospective experiment

A separately registered successor may accept the exact optional leading FUEL,
including its reserved fields and owned label. Existing mode2 published fuel
uses x16/x17 and context memory; it leaves x3/x4 intact. The successor must keep
that same five-word charge **before** the original write bounds check. Insufficient
fuel must trap before any write with the same published remaining fuel and items.
Arbitrary standalone FUEL, effects and branches remain witness barriers. Fresh
native proof, actual charged-site instruction audit and unchanged-rule paired
product/candidate/C timing are prerequisites; product gates and committed-source
integration are still required before adoption.

Current definition identity content-addresses checked normalized typed KIR and
its profile/effect/interface/dependency contract. A computation recipe can also
be content-addressed, but reusing a result additionally requires the inputs,
state, effects and resource semantics to be sealed. This experiment executes
fresh inputs and reuses only a locally proven descriptor. Native DefCID/artifact/
result caching remains unconnected. See the
[identity contract](coscientist-content-address-20261005.md).

[Summary](evidence/coscientist-local-vector-write-20261006/summary.json),
[instruction audit](evidence/coscientist-local-vector-write-20261006/instruction-audit.json),
[next hypothesis](evidence/coscientist-local-vector-write-20261006/next-hypothesis.json),
[authoring corrections](evidence/coscientist-local-vector-write-20261006/authoring-corrections.json),
[complete native replay archive](evidence/coscientist-local-vector-write-20261006/native-proof.tgz)
and [checksums](evidence/coscientist-local-vector-write-20261006/checksums.sha256)
retain the independent oracle, actual emitted snapshots and initial test-authoring
failures. These research fixtures use one-off authoring; product generation files
were not modified.
