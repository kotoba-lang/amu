# CRC structural frontier: frozen SOURCE/model HOLD

No repository or pinned source was changed. No compiler, native, SSH, solver, CPU probe or timing was invoked. `inspect.py` ran one finite pure source-data inspection. New algorithm authoring would be a one-off exception: the existing AST refactor rules do not implement this admission/emission algorithm. No such product algorithm was authored here because the current direct rule is not admitted.

## Actual applicability

Current original body is `bench/embench/batch-ports/crc32.kotoba`. Its expression is exactly `T[(crc XOR octet)&255] XOR (crc >>> 8)`. The immutable table is split into sixteen 16-entry literals selected by a signed branch tree. Seed/SIR OP-TAB explicitly guarantees a pooled immutable i64 table and an unsigned index-bound trap, without runtime allocation.

The saved typed observer at `vector-typed-observer-native-v8/ports/crc32/observer-records.json` has byte-identical workload source. Its FN3 rows213..225 compute the index, CALL FN1, logical shift and XOR. FN1 contains sixteen OP-TABs, branches and entry FUEL. This is a complete semantic recurrence across the call edge, not the <=32-instruction straightline local scalar region supported by current `di-body`. It contains OP-CALL, OP-TAB and branches, all outside that admission. The observer is historical: identical source bytes do not prove its producer is current41. This uncertainty is retained, not promoted to current typed output evidence.

Current41 has no explicit CRC32 feature authority/transport. `gn-run-open` exposes only function-open parameters. A historical measured-host feature receipt is copied as data, not an execution authorization for a new compilation or host. Unconditional instruction emission would violate generic target fallback.

Therefore the direct whole-recurrence lowering is HOLD with zero product candidate. Implementing an emitter before closing these admissions would be a dead/unqualified optimization.

## Precise directional expression certificate

Let T be an exact immutable256-element table; T[i] is eight reflected IEEE steps of i under polynomial0xedb88320. Let c be an unsigned64 carrier and d an arbitrary unsigned64 carrier. All XOR and shifts below are carrier operations; shifts are literal8/32/24, not signed shifts.

`R(c,d) = T[(c XOR d)&255] XOR (c >>> 8)`

The narrow certificate requires c in0..0xffffffff and gives `R(c,d)=CRC32B(low32(c),low8(d))`, zero-extended to64. The current typed carrier is :i64, not a u32 type; a width invariant must be demonstrated from initial4294967295 and every reaching recurrence edge before using this equation. This source loop supports that inductive invariant mathematically, but no current optimizer certificate proves it.

Without a c-width premise, the exact value equation is `R(c,d)=zext64(CRC32B(low32(c),low8(d))) XOR ((c >>> 32) << 24)`. The independently authored finite model checks73 basis-and-zero cases (64 state+8 data+zero); the original narrow law checks41. Both maps are GF(2)-linear, so these checks establish the stated finite model equations once that linearity premise is accepted. They do not establish ISA encoding or compiler semantics. c=2^40,d=0 is the retained narrow counterexample: original4294967296 versus narrow0.

## Minimal graph-rule admission

Root at an ordinary typed caller expression with both state/data captures defined before use, no intervening effect, and exact masked index flowing into a statically resolved pure reader. Reader admission must prove the entire closed CFG: one i64 input/result; original entry FUEL position/transaction; complete signed selector branches covering0..255; exactly sixteen checked immutable literal reads; exact return joins; no calls, runtime allocation, memory mutation, cap operations, division, float, FADDR entry replacement or malformed/unclaimed fields. Literals are checked by values, never namespace/function/workload names. Bounds on CFG nodes, literals, emitted words and sites are explicit and fail closed.

The smallest implementation direction retains the original caller recurrence's XOR/USHR and substitutes only the proven T(index) call edge with `CRC32B(0,index)` for a certified u8 index. This avoids the c-width premise entirely and preserves every original caller i64 operation. It is a value decomposition of the recurrence, not an unguarded replacement of the whole source expression. A broader state-CRC fold needs either the width certificate or the extra high-carrier XOR equation above.

At that edge, retain the original nonleaf caller frame/allocation and argument evaluation order. Execute the callee's original private fuel debit before its result; fuel exhaustion stores0 then BRK exactly as the leaf transaction, success publishes remaining fuel at the original success boundary. Preserve original input captures and caller-owned x7/x8/x19..28/live temps. No charge aggregation, hoisting, removal or substitute result reuse is admitted. For a proven masked index, every selected OP-TAB bounds check is mathematically safe; removing it still requires a control/evaluation certificate that there is no observable trap/read effect. If index provenance is unknown, generic original call executes unchanged. Keep all generic reader definitions, public exports and FADDR paths unchanged. No full-body algorithm replacement, C host substitution or arena change occurs.

A narrower alternative can preserve every original reader branch, entry fuel, call and TAB bound trap and replace only each exact table-slice value load: after guard idx<16, emit `CRC32B(0,idx+offset)` for certified immutable slice T[offset..offset+15]. This has concrete current source-data applicability but is a different prospective local rule. It is recorded, not implemented or claimed as the complete recurrence optimization.

## ISA boundary and next gates

Local docs identify IEEE versus Castagnoli polynomial and historical CRC32 availability. They do not independently bind CRC32B encoding, operand32/8 behavior, zero extension, NZCV behavior, aliasing/zero-register rules, or the explicit deployment feature authority. Those exact ISA properties remain unresolved; use primary Arm documentation before authoring an encoder. No web lookup was needed to reach the present HOLD.

1. Bind a readonly current typed KIR/SIR/FREC observer to the exact current source/compiler lineage; prove complete reader CFG, entry fuel and caller root. This requires a separately bounded authorized run, not reuse of historical source hash as producer evidence.
2. Specify explicit target CRC32 feature input, build/container/export identity, and false/unknown-feature byte-identical generic fallback.
3. Choose the call-edge T(index) decomposition or branch-preserving table-slice rule, then author copied native Kotoba source with finite admission caps. Independent SOURCE review must verify ISA and frame/descriptor/fuel transaction obligations before native builds.
4. Typed controls include unknown/negative/256 table indices, changed/mutable table, wrong polynomial, high64 state, all chunk boundaries, wrong mask, call alias/live prefix, generic/FADDR coexistence and original fuel boundary traps. Actual faults must break independent checks. Whole original19 resource/semantic comparison, register canaries, selfhost fixed point and all required gates precede a fresh samehost full19 timing campaign.

Existing session53145 and remote timing were untouched. No speedup, current19 performance, official score or full selfhost completion is claimed.
