# Fixed vector state: SOURCE frontier

Status: SOURCE inspection complete; allocation-eliding immutable scalar replacement rejected under the requested observables. No product candidate authored, no product edits, no compiler/loader/native guest, network, setter, or timing calls. Python inspected fixed source bytes only. Prior guest8 workspaces were untouched.

The apparent premise is incorrect for the two original ports. They carry mutable, affine `:vector-i64` handles through private functions and return the same handle after `vector-assoc!`. Neither port contains persistent `vector-assoc`. A positive `batch` allocates one zero-filled state vector, length169 for statemate and17 for nsichneu, outside the repeated state-machine body. No vector allocation occurs inside either repeated body. Consequently removing per-iteration persistent vector copies cannot improve these ports: that operation is absent. This is a source law, not a dynamic profile or a proof that performance cannot eventually approach C.

## Exact source binding

`source-inspection.json` pins all16 modules in repository MANIFEST order, the MANIFEST, original ports, comparison matrix, pinned local original C sources, loader source, scalar-DAG document, and independently audited current baseline artifact. The manifest reconstruction is module bytes plus a newline after each module:

- Current16 unity: `953f80e04da6819bfacea3a867c3e07d7492f4230dcb2618be53691df4be9418`.
- Source41: `4ed9b5600505c33013c966d266a977a3d4ccd56ad3cdc425b1805acf390b95f3`.
- Current native producer: 858392B, `761856bb455de5d36021e177be8f3a0bbf65772dd66cbdf29c8e114f8cbe3d93`.
- Current producer independent saved audit: `71c2a49c36a353a83f5df816193e9b128555b5ac9c7220d2a75b7d7b4f156096`.

Historical measured LC5f and DAGd3 producers are separate lineages. Their measurements or old typed observers are not witnesses for current7618 compilation of these ports. Matrix source pins match the inspected original ports; its historical artifact pins are not substituted for current typed/compiler evidence.

## What the original programs actually ask the backend to do

|Source syntax inventory|statemate|nsichneu|
|---|---:|---:|
|Functions / private functions|538 /535|265 /262|
|Functions returning vector handle|531|261|
|Local function call syntax sites|1483|519|
|If syntax sites|132|158|
|Vector read sites: literal /dynamic index|334 /2|10 /13|
|In-place write sites: literal /dynamic index|0 /1|8 /4|
|Persistent assoc sites|0|0|
|Maximum parameter count|3|7|

Counts are complete parsed syntax inventories, not executed calls, emitted branches or hot instruction counts. Statemate's one dynamic write is the three-argument `put` wrapper; its callers supply many constant indices. Existing `gn-wrapper` recognizes exact natural-parameter wrappers and can inline a validated in-place store with its original entry charge. Therefore1483 call syntax sites must not be described as1483 surviving machine calls.

Statemate `body` composes clear-bits, initialization, interface and FH_DU via hundreds of vector-returning helpers; `repeats` carries the original handle. Nsichneu `run-full` traverses126 transitions after reset-counts, reusing the original17-cell handle. Its `t2` has7 arguments and runtime index arithmetic; `put-output` indexes from the current P3 count. Private parameters/results escape the individual function into other private functions. Whole-program nonescape needs a graph proof; intraprocedural nonescape is false for those edges.

The public `stage-cell` entry points seed state and read a caller-selected final cell. A batch-only proof that ignores cells omitted from final batch verification would lose this observable. A generic specialization must keep all exports, FADDR uses, aliases and ordinary paths valid; admission must use graph/type facts, never names.

The pinned C sources represent state with globals/direct arrays and much larger bodies. Nsichneu uses volatile count/array globals; do not assume C eliminated all reads/writes. Statemate stores many fields as char/int/unsigned long rather than the port's uniform i64 cells. The C code has no Kotoba fuel debit or handle/index trap contract. These structural differences explain plausible overhead sources: retained fuel checks, handle/index validation, register/spill traffic and helper boundaries. Source inspection cannot rank their cost, quantify a gap, or establish that C-like speed is impossible. No current C disassembly/timing or current original-port emitted witness is claimed here.

## Why unrestricted allocation elimination is refused

The17 declared allocator fields are pairs, string-pool-bytes, vectors, vector-items, heap-bytes, conj, conj-tail, conj-region, conj-copy, copied-words, reserved-words, regions, scope-releases, string-regions, string-region-appends, string-copied-bytes and string-reserved-bytes. Loader `KEXE_ARENA_USE` reports vector/table/item high-water marks, not merely final live use. Heap bytes include16 bytes per vector descriptor plus8 per item.

Even `(let [v (vector-alloc 2)] (vector-at v 0))` has one descriptor/two items and32 vector-related heap bytes from a fresh arena; replacing it with scalar0 has zero. If the available item budget is1, allocation traps while scalar0 succeeds. Persistent assoc always copies a full slice and interns another handle; eliminating a dead length2 assoc changes descriptor/item use and failure paths as well. Counter-only shadow charging is insufficient without preserving handle intern order, actual arena capacity, zeroing/write order, high-water/scope accounting and failures: alloc advances items before descriptor interning, so descriptor exhaustion may expose a different partial prefix than item exhaustion. Immutable full SROA can retain the actual original allocation transaction, but it is then value-access promotion rather than allocation elimination.

In-place assoc allocates nothing, returns the same handle and writes exactly one word after valid-handle/index checks. Its vector/table/item counters already have zero allocation delta. Retaining original allocation and stores therefore avoids the principal allocator-observability obstruction to load forwarding. It does not prove ownership, index safety, fuel or register correctness.

## Existing rules and a narrow distinct frontier

Current source41 `gn-inl`/`gn-wrapper` already inline vector-at, vector-assoc! and count for bounded temp shapes. `gn-vread`, `gn-vpair`, `gn-vstep` cache a validated handle's descriptor/base/length. Chain mode carries descriptor state across certified private handle chains; chain reads/stores still check index and load/store the cell. The stable read-only loop proof admits vector-at and excludes in-place writes. ScalarDAG `di-shape` admits only scalar i64/bool parameters/results,1..5 arguments, at most7 locals/depth and32 straight-line instructions; it rejects branches, runtime operations and vector values. These rules do not constitute full state-cell scalar replacement. Existing region allocation reduces eligible allocation/copy paths; it does not remove declared accounting or turn these in-place state transitions into immutable copies.

One narrow new generic rule is **constant cell value forwarding after an original validated in-place store**. Candidate location is `gn-rt-set` (source41 line1644) to record one finite witness after `gn-chain-store` succeeds, and `gn-rt-at` (line1635) to return a constant only if the same handle/index witness still dominates. This is authoring guidance, not an implemented or admitted candidate. Initial scope should use one known i64 constant cell in one straight-line basic block, retain every store and allocation, and avoid introducing a retained runtime register. The rule differs from descriptor caching because it forwards cell content. Start with direct RT sites; wrapper forwarding requires a separate exact wrapper-charge witness and no call-wide inference.

Required proof prerequisites before product authoring:

1. Current typed SIR identifies an actual eligible store/read pair in the same basic block, exact local/descriptor identities and constant index/value. Raw syntax constants passed to another function do not meet this requirement.
2. The original checked store remains at its original position with original handle/index/value evaluation and same error prefix. Its successful checks prove the later identical handle/index access safe. Preserve read operand evaluation; reject trap/effect-bearing operand construction unless retained exactly. Do not replace invalid-handle or out-of-range accesses using merely a static length assumption.
3. No alias/content write, handle reassignment, call/indirect call/capability, unknown runtime operation, arena reset/release, label/join/branch or lifetime boundary intervenes. A single-cell witness clears on every unproved operation. Coalesced local identities must be invalidated by actual descriptor writes. The affine source checker alone is not a current emitted alias proof.
4. Every original OP-FUEL and branch-demanded entry debit remains in the same evaluation order, including successful completion at remaining fuel0. No helper is removed in the initial rule, so no new callee-frame/OS-stack obligation is silently claimed. A wider private-island rule would require explicit frame/trap/fuel-prefix proof and retains an honest OS-stack-limit limitation.
5. Allocation/table/item accounting and all17 counters remain exact because allocator operations, arena memory writes and scopes are retained. No fake allocator shadow counters or capability changes. Generic reader/public/FADDR path remains original.
6. `gn-fin`/result descriptors, live prefix, physical register mapping, ctx/fuel registers and descriptor caches remain consistent. Snapshot all touched compiler fields before attempting a rule; on finite witness/code-cap refusal restore exact original generic emission and fixup counts. Admission and mutation controls must test invalidation, alias store, wrong cell, negative/out-of-range index, stale handle, fuel-before-write, register prefix and rollback.

No current typed pair is yet established. The statemate writes occur in `put`, with later reads commonly in other vector-returning functions; nsichneu contains dynamic-index writes and helper crossings. Initial intraprocedural forwarding may have little or zero useful coverage. Do not widen across calls just to admit these workloads. Full17/169-cell promotion cannot assume all cells fit the existing10-register callee-saved bank; spill layout, private graph cloning, indirect/public fallback and dynamic indexing require a separate proof and cost study.

## Smallest next gate

Prepare a separately reviewed bounded read-only observer of current7618 compilation for both exact original sources. It must inventory the complete FN/SIR graph, all vector allocations/reads/in-place and persistent writes, calls, entry/recur fuel sites, descriptor assignments and selected emitter paths, with full node/token/FIX/export relations and ordinary-vs-observed artifact byte identity. The small CRC observer's bounds are not sufficient by assumption for538/265 source functions. Pin a finite complete capacity before running, fail closed on truncation, and report zero admitted pairs as a valid negative outcome. First decide whether a direct same-block retained-store constant forwarding pair exists; otherwise reject this narrow rule's applicability rather than author dead optimization. Only after that evidence should a copied Kotoba product candidate and OFF/ON fuel/trap/all17-counter controls be prepared. Native/full19/fixedpoint/performance gates remain future independent work.
