Frozen SOURCE only: diagnostic bounded capture worker and future real pipe/thread
fixture. No actual threads, os.pipe, process/group APIs, setters, native programs
or network were executed during authoring. No GO. No product edits. C2 OFF.

Single capture worker exclusively owns transferred read FDs, selector and output
files, and closes/fsyncs them before stopped acknowledgement. Parent owns only
write FDs. Parent must never close/reuse transferred read FDs even on timeout.
Snapshot cannot hash files without stopped writer acknowledgement and closed
sinks. Failure metadata can be obtained while writer active; raw hashes cannot.
One initial join and one cleanup join are allowed, both bounded by original
absolute deadline; first join timeout remains failure even if cleanup join ends.

Outer/cleanup absolute deadlines are supplied once. First failure clamps capture
drain to min(original deadlines, firstfailure+1s), never reset by later failures.
Worker handles at most64KiB/stream/round, stdout8MiB/stderr1MiB retained prefixes.
Overflow records exact encountered dropped byte count, refuses, never decodes
truncated raw. This count is not a claim about bytes never read after deadline.
Short writes loop; zero/error writes and fsync faults refuse. Snapshot performs
no semantic decode and never grants memory qualification.

Future eight cases: delayed bytes after injected sampler refusal, asymmetric EOF,
open-pipe expiry, stdout and stderr cap+1, three-byte short writes, fsync error, deterministic
blocked-read join timeout with bounded acknowledgement. Only1 capture thread/case,
no writer threads;16 os.pipe calls/32 FDs; no subprocess or group API. Case absolute
deadline3s, suite24s of case budgets plus bounded setup/check overhead. Injected
read waits at most0.2s. Open pipes remain parent-owned writes until worker expiry.

No native sampler gate is relaxed or implemented here. Group authority, watchdog
retirement and uncertain wait must remain serialized by the separate owner
controller; this fixture has no process controller. The separately pinned pure
ownership model rejects group signal/query after retirement or wait and repeated
wait after uncertainty. These tests do not qualify real process cleanup.

source-controls.py invokes only synchronous injected worker logic: fake selector,
clock, read/close/set-blocking/sinks/fsync. It does not call start(), actual join,
os.pipe or threading.Thread. Real fixture is inert until exact root GO, full pins
and two specific SOURCE reviews. No synthetic result substitutes for actual
threaded qualification. Worker/FD close/join reliability on the OS remains HOLD.

If injected fixture setup/write fails, completion is absent. Parent closes its
write FDs and releases bounded read gate, but cannot hash or close active reader
FDs. No retries, deadline extensions or successful memory/guest/performance claim.
Independent review must inspect setup-exception shutdown before authorizing it.

Regular-file write, fsync and close can block despite cooperative clock checks;
no hard OS wall guarantee. Each event and inner short-write step checks the fixed
deadline. Read work capped4096 calls/16MiB observed bytes per case. These caps
refuse instead of extending drain. Join acknowledgement is thread/FD closure
only and never proves OS process closure.

V2 preserves frozen V1 HOLD unchanged. Transactional setup retains parent read
ownership until explicit grant. Worker waits for a one-way grant/deny gate before
any FD, selector or sink access. Any construction/start exception permanently
denies pending ownership; parent closes its reads/writes even if an ambiguous
start later schedules a worker. No missing ident or start exception proves thread
absence. Once granted, only the worker may close reads. Constructor is explicitly
inert. Atomic returned pipe pairs are recorded; arbitrary asynchronous interruption
inside the pipe API without returned FDs remains outside fixture qualification.
Four additional negative setup cases: second allocation, constructor, before-start
exception, after-actual-start exception. Late denied worker touches no FDs and
creates no raw files. Real max12 cases/threads conservatively,24 pipes/48 total
FD allocations, max4 simultaneousFDs,36s case budget plus cooperative overhead.
Blocked-read stage acknowledgement precedes initial join timeout; injected wait
bounded0.5s. The fixed first-failure deadline remains irreversible.
