# Current producer continuation / checked-state emitter observer

Copied Kotoba diagnostic SOURCE only. Original product files and all workload bodies are untouched. This is new observational instrumentation, not a rule-shaped product refactor; no existing `amu refactor` rule provides branch-arm compiler telemetry. The one-off copied-source authoring exception is recorded here. The Python author only reads/writes source and verifies exact reversal/parenthesis balance; it never invokes compiler/native/SSH/solver APIs.

## Three producer lineages

* Current baseline: exact16 `seed/MANIFEST` modules, concatenated in order with one newline each. `unity-baseline.kotoba` is source, **not yet a qualified executable**.
* Measured LC G3: native966824 B / `5f4f591a1eb3bb46d3042a3463805a5cfb0897b766ee2de4909088be3369e1af`. Saved original statemate/nsichneu outputs and C timings belong to this lineage. It may bootstrap this separate diagnostic but cannot substitute for fresh current-baseline output identity.
* Historical v8 observer: source/SIR/FREC/native census used to locate possible targets. It is pinned as history only; no current admission/path/frame assertion comes from it.

## Concrete observer insertion

`41-observer.kotoba` equals current41 after reverting the four declared function edits and removing the appended helper block. Author-time exact reversal is checked. `unity-observer.kotoba` changes only this module. No new diagnostic helper writes M/G/FN/SIR/CODE/FIX or alters selection predicates. Printing and diagnostic vector/string allocation consume runtime resources and have **not** been qualified; exact native target/container/export equality and resource admission are mandatory.

1. `gn-op-call`: record the **selected existing branch**, wrapping its actual result. Existing w/q/mask/reader/dag evaluations and cond order remain unchanged; no predicate is re-evaluated by observer. Arms:1 affine-reader,2 scalar-mask,3 clamp,4 mask-writer,5 sign-wrapper,6 straight wrapper/identity,7 scalarDAG,8 generic delegation.
2. `gn-call-generic`: record its actual selection:9 immediate scalar-result CALL/RET tail branch,10 ordinary generic BL. These nested events are details of arm8, not additional logical calls.
3. `gn-loop`: save immutable scalar pre-code/fix/cache/context/height values, call original `gn-ins` once, then emit `CTEMIT`: SIR index/op, code/fix half-open ranges, consumed-SIR skip count, actual leaf/frame/fuel-register/context/cache state. At OP-FN this exposes actual selected frame: leaf2 is current small-tail mode, leaf1 ordinary leaf, leaf0 nonleaf; the copied original `gn-op-fn2` remains unedited. Dead/skipped CALLs have no arm event and must not be classified as emitted generic calls.
4. `gn-run-open`: before generation and after generation dump full declared SIR and all16 FN fields; final unresolved code words/fixup records. This is before layout and must be resolved using the pinned current42/final container, not treated as final machine bytes.

Schema notes: `CTCALL`: i,f,t,n,arm,startCode,startFix,leafBefore,frameBefore,ctxBefore. `CTCALL-END`: i,arm,endCode,endFix,leafAfter,frameAfter,ctxAfter,err,vmodeAfter,vslotAfter,heightAfter. `CTEMIT`: i,op,startCode,endCode,startFix,endFix,skip,leaf,frame,fuelFlag,freg,ctxAfter,err,vmodeBefore,vslotBefore,ctxBefore,heightBefore,vmodeAfter,vslotAfter,heightAfter. Scalar before values are captured before the in-place emitter mutates M; rereading M later is not used as a before snapshot.

`ct-ready` bounds diagnostics to SIR32768/FN1024/CODE131072/FIX16384 and success state. Out-of-range/failing final dumps emit CTHOLD and no complete acceptance; no result is truncated into a passing count. Source consumers must require both complete CTDUMP-END records and exact declared coverage, distinguish nested arm events, reconcile all skip/dead sites, and reject any missing record. These caps cover historical site counts but do not prove current counts. Read access is to already accepted compiler emitter state under original invariants; malformed arbitrary compiler-memory safety is not claimed.

## Current guards to audit from actual records

Current scalarDAG accepts i64/**bool**, 1..5 arguments, <=7 slots/depth, straight-line <=32 SIR certificate. It rejects branches, RT/CALL/FUEL, immediate RET/RES2 successors, unsafe argument banks, and exhausted shared256site/4096word growth budgets; rollback is retained.

Current small-tail is distinct: <=1 argument, <=7 slots/depth, no outgoing stack arguments, recognized small result/parameters, closed uniquely owned labels, preserved FUEL, restricted inlined RT operations and wrappers or same-result immediate-tail calls. Actual final leaf/frame mode comes from CTEMIT, not source call counts.

Current generic-tail requires n<=7, immediate OP-RET, same result temp; it runs existing epilogue/context/argument preparation and emits a target branch via the chain fixup. Ordinary generic calls retain save/args/context/BL/vclear/take. Already-elided frames cannot be counted as new fusion benefit.

OP-RT sites and wrapper arm6 are paired with SIR slot/arity and CTEMIT cache transitions to inspect current descriptor-check emission and `gn-vclear`. Repeated checked mutable reads are not hoisted or memoized by this observer.

## Separate descriptor-cache hypothesis

Root identified exact loader `checked_vector_assoc_in_place` that checks descriptor/index and only writes vector_items, returns same handle without allocation or descriptor modification. This suggests preserving **descriptor metadata**, not item values, across that exact operation might remove redundant descriptor checks. This remains a separate hypothesis requiring loader/version pinning, actual emitter-path evidence, complete lifetime/allocation/alias/unknown-writer/context contracts and preserved item read/write/trap/fuel ordering. No pointer fastpath, cache retention, item-value reuse, or performance claim is implemented here.

## Bounded next pilot and prerequisites

Without a reusable newly qualified current native baseline, prospective sequence is at most12 child calls: bootstrap current baseline compile/extract2; baseline builds observer compile/extract2; current baseline compiles/extracts unchanged statemate/nsichneu4; observer compiles/extracts those same bodies4. All child processes close; first failure stops; no retry. If root's concurrent current-producer qualification supplies exactly matching native baseline, a later fresh prereg may bind it and remove the first2 calls; no borrowing across unmatched lineages.

This SOURCE currently has **no executable runner or native GO**. Future runner must freeze exact loader/native/source argv and capabilities, source/read-role closure, current platform identity, child/time/CPU/memory/file/stream budgets. stdout/stderr streams must be separated from regular file limits, and Darwin memory accounting must use the qualified watcher rather than unsupported RLIMIT_AS. Proposed stream cap128MiB per compile is a resource bound to implement/check, not a truncation allowance. Native compilation of helper syntax is untested; balance is not type acceptance.

Acceptance requires current-baseline vs observed whole KSEED/native bytes, exports, offsets, features and typed FN/SIR equality; complete parser coverage; independently reconstructed fixup/layout ranges and actual branch modes. No workload execution is needed for this first observation; no timing, fixedpoint, full19 result, C goal achievement, or emitter optimization follows from the two-workload pilot. Next implementation must target semantically removable emitted operations revealed here, preserve ordered state/fuel/trap and callers, then undergo full original19 semantic/fixedpoint and quiet C measurements.
