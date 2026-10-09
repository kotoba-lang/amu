SOURCE-only proposal; no runnable native driver, GO, network or product edits.
One-off diagnostic authoring. C2 OFF. Old strict guest8 stays FAIL after two calls;
remaining six were not executed. This proposal never reuses the old completion.

Qualified prerequisite is independent actual capture fixture V2 report73087c1d:
eight capture/four setup cases only. It proves controlled pipe/thread observations,
not native Popen integration, grant-boundary interruption or memory admission.

Popen pipe ownership integration

Use exact unbuffered Popen stdout/stderr objects, no prior reads or other owners.
Before starting capture, parent duplicates both readFDs. Parent closes both original
Python objects before capture grant; retained Popen wrappers are closed/idempotent
and cannot later close a reused integerFD. Worker receives only duplicate readFDs.
No detach of a still-owning FileIO or inherited raw integer without removing its
object ownership. Duplication uses at most two extra pipe FDs (four parent readFDs
transiently); after original close, only two transferred reads remain. Child writes
and selector/sink/journal FDs are separate from this bound; exact total must be
specified in future runnable pilot, not inferred from the capture fixture.

transfer_popen_reads is an inert injected hook. Seconddup/construction/start
failure before grant permanently denies worker ownership and closes duplicates
in parent. Thread start failure is ambiguous; denied late worker cannot touch
reads. An interruption after grant is different: parent must not close duplicates;
only worker closes. Request refusal with original absolute deadlines and bounded
stop acknowledgement; if unavailable, no active-writer hashes or completion.
Do not infer absence from thread.ident, exception or missing acknowledgement.
Unreturned-FD interruption inside duplication/pipe syscalls remains unqualified.

Capture keeps independent fair64KiB rounds,8MiB/1MiB retained prefixes,4096 reads/
16MiB observed byte budgets, unchanged firstfailure+1s drain clamped to original
outer/cleanup deadlines. Join and regular-file I/O wall guarantees are cooperative.
Parent-owned stream close failures, sink errors and unacknowledged capture block
completion. Native controller must retire group authority under watchdog lock on
uncertainty and before wait. No PID/group operations after retirement or uncertain
wait; no retries. The hooks do not implement that native controller.

Explicit proposed memory policy version

crc-sampled-physical-memory-with-termination-gap-diagnostic-v1 separates sampled
physical-memory observations from semantic/fuel/arena qualification. It does not
claim the old strict memory gate passed. Missing footprint is unavailable, never0;
finite samples do not establish hardpeak or complete memory coverage.

Only fresh, typed ESRCH(errno3) from declared owned-group API stages
leader-getpgid/member-getpgid/member-rusage can be a diagnostic termination gap,
and only with prior accepted leader-birth-bound sample, no other refusal, complete
both-stream EOF, stopped/error-free/nontruncated capture, exact direct-child
normal closed0 wait within original deadline, no uncertain wait, permanently
retired group authority/no subsequent group operations, pinned loader wait
protocol. A normal direct-child wait does not independently prove all descendants
closed. Neither EOF nor this classification proves ESRCH was caused by termination.
It merely labels one unavailable observation associated with completed capture.
Threshold/budget/identity reuse/membership mismatch/othererrno/unknownstage remain
refused. The saved old ProcessLookupError lacks precise fresh typed stage and
cannot be relabelled. It remains FAIL and missing stdout cannot be recovered.

Required typed provenance is NOT implemented/qualified here. A new copied adapter
would need exact stage-bound exception conversion for getpgid and libproc rusage,
retaining PID/birth/accepted sample history and first-refusal reason. Broadly
catching ProcessLookupError or accepting an empty inventory is prohibited. Without
that evidence, classify_memory returns refused. API exception provenance and
native controller serialization remain runtime HOLD, not a native-ready plan.

Fresh future pilot scope remains original four adjacent OFF/ON pairs, eight calls:
prefix-crc1,2,1024 and bench1; own OFF1352/1224 and ON1392/1264. Same exact17 env,
zero grants, fuel1M/call, pinned7618 lineage and accepted repair/extract identities.
Up to8 wrappers/8 guest child starts, max2 owned members/group. Semantic acceptance
requires all pairs closed normal with original answers and exact equal structured
reports/fuel/all17 arenas/raw hashes. Memory classification is recorded separately:
termination gaps can never produce COMPLETE_STRICT_OLD_MEMORY_POLICY. No timing,
hardpeak, fixedpoint, full19 or C-or-better claim. Fresh output/key/version prevents
repeating the identical failed policy gate under a new name without review.

Before any native GO: freeze a runnable copied driver/typed adapter and exact FD
ledger; deterministic actual fixture for Popen-like object duplication/seconddup
failure/close failure, pregrant ambiguous start, postgrant interruption with worker
stopack and active writer hash refusal, delayed EOF, ESRCH stage+threshold/budget/
identity negatives, serialized watchdog-retire-wait ordering and uncertain wait.
Use injected process APIs; no native programs in that fixture. Two SOURCE reviews
and separately bounded fixture GO first. Then root decides whether the diagnostic
memory policy is acceptable for a new eight-call native preregistration. Current
SOURCE has no native launch entry and cannot bypass those prerequisites.

V2 SOURCE implementation additions and operational HOLD

Typed adapter copies the strict adapter and annotates existing getpgid/list/rusage
call sites only. It records contextVersion, attempted stage/PID, query ordinal,
errno and kernel-oserror versus kernel-failed-return. No extra kernel query.
Refusal/identity/budget checks remain separate; unknownstage or untyped errors
never receive diagnostic gap admission. The libproc errno is captured immediately
after the existing call. group-list is excluded from eligible gap stages.

Controller uses one serialized group-authority lock; retirement precedes watchdog
stop acknowledgement and exactly one direct-child wait. Retired group queries
and second wait are rejected. Prior accepted sample PID/birth must match the
provided direct-child binding on every accepted sample; failed PID must belong
to an already accepted sample. Policy is explicitly v2; raw expected answer,
fuel/all17 counters and resource journals must be complete before gap observation.
Nine pure controller cases and six transfer cases are injected; no real APIs.

Still operational HOLD: callback wiring for exact expected raw parser/all17 counter
comparison, full original resource-journal verifier, pinned loader proof, actual
Popen PID-to-first-accepted-birth binding, watchdog join/retirement callbacks and
valid-last durable memory receipt writer. Controller currently holds samples in
bounded memory and explicitly reports sampleReceiptPersistenceQualified=false.
An internal candidate observation is not native gate completion. Capture transfer
helper covers postgrant stopack but actual Popen duplicate/grant interruption
fixture remains unexecuted. No launch entry is supplied.

Proposed bounds:8 cases,16 process starts,2 members/group,1 capture thread/call
plus1 watchdog thread/call (max2 simultaneous),2 duplicate readFDs,4 temporary
parent readFDs; native full FD ledger unqualified. SOURCE event budget4096 with
8 slots reserved for retirement/wait; at most4088 group query events/call,
strict sample bounds unchanged90502 but controller budget may refuse sooner.
Memory journal future16MiB/call, setter64KiB, raw8MiB/1MiB; no persistence claim.
Missing total native FD predicate and journaling/wiring block runtime GO.

V3 repair of independent no-failure binding finding

Preserves frozen V2. Every controller admission now requires both accepted
leader PID/birth binding and pinned loader wait protocol, including no-failure
strict branch. Three exact negatives (missing birth, wrong birth, loader=false)
refuse and strictOldMemoryPolicyPassed staysfalse. A pure positive no-failure
fixture checks the intended branch with all bindings supplied; it is not actual
native qualification. Earlier operational HOLD items remain unchanged.
