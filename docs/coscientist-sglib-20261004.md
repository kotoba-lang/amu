# Selfhost SGLIB combined: all six algorithms, untimed

`bench/embench/batch-ports/sglib-combined.kotoba` now runs the original six
container algorithms. The historical simplified insertion-sort/sum port and
its timing table remain unchanged. Native selfhost Amu check and compile
accept the complete alternative. C-or-better remains unachieved: asher is
still unreachable, and no local diagnostic time is a performance result.

The pinned Embench commit is `09c2ed8c3b7008c95d08b038de4a3f6dc103ed70`.
All source hashes are recorded in the evidence manifest and enforced by the
oracle generator, including `combined.c`, `sglib.h`, and BEEBS allocator
`beebsc.c`/`beebsc.h`. Compiler SHA-256 is
`abcc1318957af7d3a09cfd66c06d17821b5cf47f4c47d02b5620e9e92a24f02e`,
from the byte-identical three-generation native Amu build. Native check,
compile and extraction use that executable, without Node/nbb/JVM fallback.
Python authors observation adapters and Clang builds C references outside
the product path; all 97 PRODUCT inventory entries remain unchanged.

The work includes:

- The SGLIB quicksort partition rules, smaller-side continuation, explicit
  64-entry start/end stacks, and two-element final exchange.
- Doubly linked list insertion before the current node, locating the first
  node, iterative linked merge sort, rebuilding previous links, and traversal.
- Twenty hash buckets, membership checks, list insertion, and bucket/chain
  traversal in the original order. The benchmark's null subcomparators and
  equality filters are fixed in this profile.
- The 101-element circular queue's insertion and removal sequence.
- The heap's original insertion parent `i/2` and deletion children `2*i+1`
  and `2*i+2`, preserving its exact array states.
- Red/black insertion, mirrored discrepancy fixes, recoloring and rotations,
  membership search, black root, and the original 128-entry path/pass iterator
  with inorder yields. The diagnostic records all 100 traversal identities.

The original shuffled 100 values are retained as a static indexed selector,
not replaced by a sorted or reverse-sorted input. C pointers become owned
node identities in allocation order. The 1,760-cell workspace represents
array, list, hash, queue/heap, tree, quicksort stacks and iterator state.
The diagnostic adds 100 trace cells; production keeps 1,760. BEEBS heap-byte
accounting matches this 64-bit profile's 24/16/24-byte list/hash/tree nodes
and 6,400 requested bytes within its 8,192-byte heap. Actual C pointer storage,
stack allocation, static table lookup and owned-vector/selector costs differ;
timing must include those differences rather than infer equivalence of cost.

Evidence:

- 3,805 values match C at six completed stages, including node links, hash
  buckets, queue/heap arrays, tree colors/links and all 100 iterator yields.
- 1,128 defined final state values from the actual production body match C.
- A further 4,512 values match after 1/2/17/32 complete bodies: 9,445 comparisons
  total. C oracle selfchecks compare the unmodified benchmark's array, list,
  hash, tree-node fields, result 15050 and original verifier for each count.
- Batches 0/1/2/17/32 agree. Workspace index 1759 succeeds, 1760 traps, and
  fuel 1 traps. Product fuel/handle/arena guards are unchanged.
- The observation adapter and unchanged allocator pass AddressSanitizer and
  UndefinedBehaviorSanitizer over selfchecks 1 through 32 and every cell at
  all six stages (11,160 reads).
- Regeneration is byte-identical. All four modified upstream files are
  refused with Python assertions disabled. Canonical attribution changes
  leave the audited native bytes unchanged.

The first complete-source draft returned failed verification. Reflection
identified two incorrect continuations: a short trailing list run must
preserve an earlier merge's outer continuation flag, and popping an iterator
path must check whether its parent should yield before descending right.
The initial source/native result is retained as rejected evidence. Both
corrections are checked by the full structural and repeated-body comparisons.

The C oracle includes upstream unchanged. Its observation-only copy extracts
the exact inner benchmark body and adds snapshots/visit recording; the timed
C adapter calls the unmodified body. Private queue/iterator state is observed
in that copy; uninitialized padding and inactive iterator slots are excluded.
These are bounded original-profile comparisons, not a proof for arbitrary
inputs, duplicate allocation patterns, all SGLIB operations or every target.
This is new algorithm authoring; existing Kotoba AST refactor rules do not
cover it, and no product source is edited.

Artifacts are in `docs/evidence/coscientist-sglib-20261004/`. The research
archive includes native/C artifacts, provenance, all reports, rejected draft,
sanitisers, bootstrap inventory and generation/pin receipts. Unpack the fresh
measurement bundle beside pinned `upstream`, `runner`, and `images/r6m`:

```sh
python3 measure-sglib-full.py coscientist-sglib-complete
```

The harness checks and compiles all exports, verifies the differential and
guards, refuses existing reports, and persists differential failures. Timing
uses 32 bodies per call, one untimed warmup, calibrated counts, 30 rotating
samples per arm, and load <= 4. CPU-idle and formal native performance-gate
qualification remain separate. Timing rows here are empty; no speed ratio,
optimization promotion, official Embench score or 100% selfhost claim follows.

Three adapted workloads still lack complete alternatives: picojpeg, qrduino
and wikisort. The performance decision remains a matched asher comparison
and evidence-based ranking of optimization hypotheses. C-or-better is open.
