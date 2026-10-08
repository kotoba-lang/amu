SOURCE design only; no GO, native rerun or product edits. Author of guest8 SOURCE,
not an independent saved actual reviewer.

Saved evidence: OFF prefix-crc1 closed0, result3523407757, fuel4, all17 arena
counters zero. ON closed0 after one accepted memory sample, then sampler raised
ProcessLookupError; cleanup group signal raised PermissionError. ON stderr291 B
contains complete zero counters; stdout0 B means unavailable, not proven absent
from the child or semantically different. Six later cases were unexecuted.

Cause in the source: the selector loop reads available events, then synchronously
samples. Any sampling exception exits to finally, which closes remaining pipes
without draining. Available stdout can arrive between that read and the failing
sample. Current refusal remains correct for memory admission; loss of raw bytes
is a separate capture limitation. Do not infer a code-semantic failure from it.

Proposed bounded capture design

1. Start a dedicated local pipe capture worker immediately after successful Popen,
   before constructing/querying the sampler. Only this worker owns the two read
   FDs and raw output files. Nonblocking selector reads both streams fairly,
   at most64KiB per stream per round. Retain at most8MiB stdout/1MiB stderr;
   overflow records retained/dropped counts and truncation, never decodes it as
   a complete report. No PID/group/memory or wait API in this worker.
2. Capture continues independently when memory sampling fails. Record exception
   stage and typed reason separately from guest report/closure. Do not retry a
   failed inventory, synthesize zero members, or turn it into a successful sample.
   Any identity/membership/rusage uncertainty retires group signaling authority
   permanently under the same monotonic anchor lock used by the watchdog. Stop
   and join the watchdog before wait. No subsequent group query or signal.
3. After identity uncertainty, request only bounded local pipe draining: budget
   min(1 second, remaining original outer deadline, remaining30-second cleanup).
   EOF on both pipes can end it early. This is a raw-capture grace, not an extra
   execution budget and not evidence of group absence. No native rerun/new call.
   A quiet open pipe expires; preserve bounded partial raw bytes and mark EOF
   unavailable. Pipe EOF never restores retired signaling authority.
4. On policy failure with still-established identity, signal only before any
   wait and only under retained authority. Before waiting, retire authority.
   Identity uncertainty already retired it, so no signal is attempted in that
   branch. Wait only on the exact saved Popen direct child, with existing finite
   deadline. Any wait exception permanently marks closure uncertain; no poll,
   second wait or later group operation. Close parent-owned pipe FDs after the
   capture worker has stopped. Capture/wait can share bounded cleanup elapsed
   time but neither may extend outer/cleanup deadlines.
5. Fsync bounded raw/journal files and publish valid-last failure receipt even
   if a structured report becomes available. Keep separate fields:
   captureStatus, pipeEOF, truncation, semanticObservation, memoryAdmission,
   directChildClosure, cleanupErrors, signalingAuthorityRetired. A complete
   equal ON report can support a partial semantic observation only; failed
   memory admission still stops the gate and forbids successful completion.

The capture worker must not be abandoned if join fails: record capture closure
uncertain, retain ownership of files until bounded termination/FD retirement,
and do not publish hashes while another thread can write. An implementation
needs a single FD-owner stop handshake; no cross-thread close/reuse race.
This is a design requirement, not a claimed implemented guarantee.

Strict memory sampler and adapter remain unchanged. Hardpeak/AS and transient,
startup/EOF gaps remain unavailable. A lost-identity child may remain unclosed;
retiring authority correctly limits cleanup ability. Report that limitation
instead of signaling an uncertain group or proceeding to another case.

Deterministic test preregistration before native

Use injected clock, selector, pipe events, sampler and direct-child waiter;
no subprocess/OS APIs. Cover delayed stdout after sampler failure; prebuffered
stdout/stderr; asymmetric EOF; quiet open pipe; overflow and short writes;
sampler inventory/member/identity/threshold/budget exceptions; uncertain wait;
watchdog/retirement ordering; capture-worker join timeout; deadline already
expired. Assert byte prefixes/caps/EOF flags, fsync+hash only after stopped
writer, exact first-failure/no retry, no group operation after retirement/wait,
and no qualification from bytes/EOF/direct-child exit alone.

The accompanying model covers finite policy traces only. Actual threaded FD
ownership, OS process lifetime, journal fsync failure and pipe closure need
an independent SOURCE review and separate finite deterministic fixture before
any native proposal. No recovery of bytes already lost from this saved run.
C2 OFF; no performance, full19, fixedpoint or paired-runtime PASS claim.
