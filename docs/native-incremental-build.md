# Native incremental build goal (JUN-332 / JUN-358)

The active goal is persistent build reuse per DefCID/SCC and an actually
measured PR native CI wall time of at most 20 minutes when compiler/core
inputs are unchanged. The native compiler cold-build goal of 10 minutes is
already measured separately. A cache hit is not a qualification verdict.

The preceding source/image qualification run 40191488005 took about 73
minutes. Its x86 label-control group spent 1113.177 seconds rebuilding ten
whole-prefix images and 81.130 seconds executing semantic controls. This is
the first repeated-build workload to improve. Longest-first scheduling was
adopted in PR1577; its estimated savings are not a measured 20-minute result.

## Dependency order and acceptance

1. **Native identity codec.** Port the canonical payload-v2 representation
   before producing identities in the native frontend. Preserve the six
   sealed inputs and distinguish definition identity from build identity.
2. **Checked producer and recursive groups.** After native checking, normalize
   binders, replace direct definition references with CIDs, and implement
   the existing `scc-v1` rule (canonical member permutations, limit eight).
   A missing dependency/effect bridge or oversized group yields no identity.
   Reuse an entire SCC; never invent per-member independence inside a cycle.
3. **Native relocatable objects and persistent store.** Seal each build key
   with its DefCID/SCC, compiler image, target/ABI, layout, optimization
   profile/options, dependency/interface closure and resource-proof contract.
   Persist symbolic relocations for definitions, literals and local labels;
   never reuse already linked addresses. Verify stored content and current
   source/lock relationships before linking. An absent, stale, corrupt or
   mismatched entry rebuilds or refuses, without a legacy host fallback.
4. **Warm mutation builds, fresh execution.** Run the original full-prefix
   semantic oracle and all nine guard-removal mutants on both native ISAs.
   Measure cold/warm and one-definition/dependency/SCC edits with identical
   producer, host, workload and limits. State which objects were reused and
   which were rebuilt. Native admission, controller decisions, effects and
   runtime receipts are always freshly executed.
5. **PR CI and adoption.** Apply artifact reuse only in the permitted PR
   tier. Keep the complete uncached main/full derivation. Compare actual
   end-to-end workflow start/completion times, recording runner queue time
   separately; neither an individual group nor a simulation closes the goal.
   Preserve every existing case, refusal, lock/fuel/arena assertion, public
   entry and native controller boundary. Review, merge, read back affected
   source/image pins and clean up owned merged worktrees.

## First native codec boundary

`seed/04-definition-cid.kotoba` provides a bounded native encoder/validator
for the normalized payload-v2 DAG-CBOR domain and CIDv1 dag-cbor/sha2-256.
It reuses the admitted pure native SHA-256 from `seed/03-source-sha256.kotoba`.
The canonical representation remains owned by
`kotoba.kir.definition-identity` in osaho, as specified by ADR0300. Frozen
vectors are copied byte-for-byte from kotoba-lang's pinned contract; their
owner revision and source digest are recorded alongside them.

This first codec admits ASCII text, blocks up to 64KiB, fewer than 8192
nodes and nesting up to 64. Unsupported input refuses. It is deliberately
not an alternative identity scheme: admitted bytes reproduce existing
payload-v2 bytes and CIDs. Decoded-value ordering, rather than CBOR byte
ordering, governs sets/map keys. Duplicate keys/sets/dependencies, unknown
tags, nonminimal CBOR, missing sealed fields, malformed dependency CIDs and
unbridged effect rows refuse. Broader Unicode/CID-codec input needs its own
parity evidence before widening this bounded profile.

The standalone native gate constructs all ten frozen payloads with native
code and compares both the bytes and CIDs. It also independently hashes
the supplied frozen bytes and executes malformed-input and boundary checks.
Seven independently built guard-removal mutants must actually accept a
forbidden block or fail the paired boundary check, demonstrating that these
controls exercise their named validators.
Python stages fixed bytes, starts processes and records observations; it
does not normalize definitions, encode CBOR or emit machine code.

This module is **not yet in FULL-MANIFEST**. Existing production source/image
pins are unchanged. A successfully hashed supplied payload proves content
identity only: the checked frontend producer, SCC identity, relocatable object
store and end-to-end timing criteria above remain open. Caller-supplied
payloads and hashes never grant execution authority.
