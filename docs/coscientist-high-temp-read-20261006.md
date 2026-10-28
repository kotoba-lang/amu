# High-depth vector reads: correct native prototype rejected by timing

Both changed original workloads fail the prospective promotion rule. Matmult's
mean time is4.31% shorter and SHA-256's0.40% shorter, but neither reaches a1.05
speed ratio or a mean gap larger than summed standard deviations. Reject the
complete prototype. Product source remains the qualified affine-reader algorithm
at baseline report HEAD `1bcf0f9803e822da22611f6087ac5a054416b251`.
C-or-better across all19 original workloads remains unachieved. These aligned
native body comparisons are **not official Embench scores**.

[Summary](evidence/coscientist-high-temp-read-20261006/summary.json),
[independent timing audits](evidence/coscientist-high-temp-read-20261006/timing-summary.json),
[checksums](evidence/coscientist-high-temp-read-20261006/checksums.sha256).
The native and timing archives preserve prototype/source/compiler/C/runner pins,
actual machines, native receipts, hand expectations and all accepted/rejected rows.

## Content identity and the experiment

The [identity investigation](coscientist-content-address-20261005.md) confirms that
checked definition identity hashes normalized typed KIR, semantic/desugaring
versions, effects, interface and dependencies. This is content addressing of an
implementation. It does not establish equality of every mathematically equivalent
implementation or identify a particular execution. An invocation recipe would
add canonical immutable inputs and explicit handlers/state; that recipe is itself
content addressed. A reusable native specialization artifact must also identify
compiler/optimization version, target and runtime ABI.

The measured native SIR route lacks linked DefCID metadata/result caching. Current
compile/verdict cache code elsewhere is not proof that this native command uses
it. Mutable handles alone do not identify values. Result reuse cannot silently
change fuel, traps, effects, resource limits or partial writes. All bodies below
execute freshly. Optimizing the generated implementation can improve those fresh
executions independently of compile/test artifact reuse.

The preceding [loop descriptor experiment](coscientist-loop-descriptor-20261006.md)
found high-temp reads still falling back to a C helper: matmult has1 at temp6,
SHA-256 has5 at temps6..10; the other17 original guests have none. These are
actual native-emitter observations, not inferred source counts or time shares.

This prototype preserves original nonleaf prescan/register/frame assignment and
original live-prefix saves. It stages vector/index in free x0/x1, restores x7,
retains the original ordered handle/index checks and item load, then uses original
result/alias protection. It does not hoist checks, cache descriptors or remove
fuel. Actual `gn-ctx` loads context and records it as known; the inline sequence
preserves x7. There is no ABI/x18/policy/capability change.

All four native seed generations are byte-identical,811216B with SHA-256
`f7ec6ea57d1eda8693bd8fcde01748fc9bc6d22adfc5ce8476a4c07fcd033a29`.
All19 original source/result/fuel receipts match current product. Only matmult
and SHA-256 machines change:10296→10340B and9680→9916B. Diagnostic and quiet
emitter guest bytes match for all19. An independent post-timing machine audit
verifies the exact15-word ordered-check/load template at all6 added original sites
and all33 high-depth hand callers. Its initial transcription/end-bound authoring
corrections did not change compiler code or test expectations.

## Correctness sealed before timing

- Fresh native342-fixture regression executes all4196 original runs with unchanged
  authoritative expectations. Real/test code, literal bytes and function offsets
  match, apart from2 test-only zero padding bytes. No golden update.
-15840 independent hand-state comparisons cover33 callers, depths6/7/10/31/63,
  computed live register/home prefixes, signed extremes, valid/invalid raw handles
  and indices, coalesced results, calls before/after the read, overwritten aliases,
  loops, changing indices, skipped access and five fuel budgets. Results, remaining
  fuel, complete vector items, traps and supervisor reports match.
-96 actual open-import comparisons replace a7-argument helper with a linked
 7-argument function that charges fuel, allocates and returns77. The diagnostic
  allocator clobbers x7. Reads of the newly allocated handle, invalid reads and
  partial-fuel execution retain live prefixes and exact supervisor state.
-40 resource-limit cases compare allocation after valid/invalid reads. Full
  descriptor tables preserve partial zero-item writes; full item budgets retain
  original items. Invalid reads prevent the later allocation and fuel charge.
-209 comparisons cover all19 original workloads at n0/1/2 and eight partial-fuel
  budgets. Full item state, results, remaining fuel and traps agree.

These16185 full-state comparisons and4196 regressions were sealed before timing.
The later exact machine-template audit is explicitly additional evidence.
New Kotoba algorithm and hand-fixture authoring is a one-off exception to the
mechanical AST refactor rule; it is not a mechanical product rewrite. After timing
rejection, product gates/integrated rebuilding are not rerun and the preceding
qualified product remains current. No launcher switch, rung update, process-start
capability grant or100% selfhost claim follows.

## Fresh quiet measurements

Apple M4 zebulun; unchanged pinned C/runner and original bodies. Each workload has
30 accepted rotating product/candidate/C triples from31 attempts. Rules remain
load<=4, background idle>=90%, interval>=50ms, relative SD<=10%, speed ratio>=1.05
and mean gap larger than summed SD. Accepted/rejected order, statistics, sources,
artifacts, offsets, compiler generations, C/runner/spec and preflight receipt pins
are independently audited. No identical-code retiming to seek a pass. The other
17 byte-identical guests are not retimed; no fresh all19 aggregate is claimed.

| Workload | Product ns/body | Prototype ns/body | C ns/body | Shorter time | Product/C time | Decision |
|---|---:|---:|---:|---:|---:|---|
|matmult-int|21814.94|20874.87|925.61|4.31%|23.57x|Reject|
|nettle-sha256|2745.73|2734.81|215.75|0.40%|12.73x|Reject|

Matmult mean gap940.07ns is below summed SD2843.08ns; SHA gap10.92ns is below
84.70ns. Both candidates remain substantially slower than C.

## Next registered hypothesis

The replacement still performs call-preparation spills despite having no call.
Actual `gn-save` stores pending REG/unknown temps0..6 from x9..x15 and converts
metadata to HOME. Those registers are disjoint from the inline sequence's
x0/x1/x7/x16/x17 scratch/context registers. Test eliminating those stores while
retaining original nonleaf frame, alias protection, ordered checks and fuel.
Do not assume success from fewer instructions. Repeat independent state proofs
and prospective timing for every changed original guest before product promotion.

[Registered hypothesis and identity requirements](evidence/coscientist-high-temp-read-20261006/next-hypothesis.json).
It is not yet implemented, measured or promoted. Native DefCID artifact-cache
integration and invocation-result reuse remain separate work.
