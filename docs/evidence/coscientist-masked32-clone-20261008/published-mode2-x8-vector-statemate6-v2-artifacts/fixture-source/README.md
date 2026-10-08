# Next diagnostic fixture: multidebit and private vector-chain entry

SOURCE intent only. No compiler/native execution, operational runner or GO is supplied by this plan. The frozen single-debit scalar fixture cannot establish repeated fuel reuse or FF-CODE+1 entry. This fixture is a new synthetic test; original19 workload bodies remain unchanged.

Current41 `gn-wrapper`421–435 requires natural parameter loads then RT with the same argument count. A unary `set-one(v)` containing literals0/1 fails this matcher. `set-at(v,i,x)` supplies the exact natural3-argument RT writer shape. Each unary stage places literal index/value at temps1/2 and invokes this charged wrapper before a genuine terminal unary Vec call. `finish(v)` itself contains constants and is not a natural1-argument runtime or identity wrapper.

Expected conditional SIR for stage-a/b: FN(np1,ns1), entryFUEL, LGET(t0,slot1), CONST(t1,index0), CONST(t2,item), CALL(set-at,t0,n3), CALL(successor,t0,n1), RET(t0), END. Actual lowering may differ: observer must record every relevant SIR row, ns/depth/slot mapping and matcher result; the finite model is not a lowering/admission certificate.

Required current source predicates:

- gn-small-call/callee/params901–936: closed typed signature, n<=3, admissible return/parameter types; genuine non-wrapper calls have n<=1 and immediate RET of the same temp.
- gn-small-tail938–948 + assign: original leaf0, np1, ns<=7, dp<=7, outgoing0, closed body and frame0. Each stage must actually become leaf2/freg2, not assumed from source shape.
- gn-chain-target597–608 and mode610–614: unary Vec→Vec, ns/dp1..3, exact FN/nparams/return, body bounds and genuine call count. stage-b's successor finish is genuine, so it can be a private chain target.
- gn-chain-fix773–777: caller vmode2, n1, positive vslot, temp typed as same stable local and target chain admitted. Actual inline writer result/local witness must be observed; a returned-handle semantic fact alone does not satisfy compiler witness.
- vclear782–783 + gn-op-fn2 initialization order949–979: public chain entry first MOVZx5,0, then LDRx8 from CTX-FUEL. Private FF-CODE+1 skips only MOVZ and must still execute the x8 reload. Layout42 lines205–215 checks exact original first word0xd2800005, FX-BL26/AUX1 and B opcode before adding1.
- wrapper charge1733 uses gn-op-fuel; published freg2 must debit/store at both entry and inline wrapper. Descriptor/item runtime code must not overwrite x8 or x7, and no generic returning call may resume using stale x8.

The future complete saved emitted CFG certificate must resolve public/private entries, every branch and literal range, all x8/x7/context writers and operand aliases, ordered fuel/traps, descriptor check cache liveness, allocation and actual inline runtime primitive path. Loader checked_vector_assoc_in_place5539–5553 writes only vector_items and returns the same handle after original checks; this source fact does not by itself prove all inline emitted descriptor behavior or arena lifetime. No hoisting value read, omitted trap/fuel or descriptor trust is authorized.

bench creates a nonempty one-element vector and calls stage-a. Intended ordered writes are1,2,3; final item3 is an intent, not an executed golden. Actual charge count must be derived from emitted/native evidence; do not hardcode a guessed six-charge result. Index0 accesses use real checked paths. Runtime fuel boundary/17arena cases need their own SOURCE registration and reviews after emitted evidence.

Parent requested next finite compiler-only6: OFF/ON this fixture4 plus candidate original statemate compile/extract2. That forthcoming executable registration must retain unchanged original statemate source977d840b, audited fixed candidate e874 proof24128, exact compiler ABI/environment/resource policy and current qualified capture/controller. Candidate adoption/general clobber certificate remains HOLD.
