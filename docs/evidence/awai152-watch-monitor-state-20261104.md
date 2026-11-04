# Diagnostic watcher monitor state

The previous `WP02` framing functions could validate individual frames but did
not define what a host should do after a missed deadline, duplicate sequence,
clock rollback or watcher loss. `darwin-watch-monitor-step` adds a pure native
transition candidate with host-owned state. The original four-field state was later
replaced as described below; callers must initialize the five-field format. Ready and heartbeat frames are bound to the request. Only valid,
in-order observations within a caller-supplied monotonic deadline advance the
state; polls do not renew the deadline. Timeout, rollback, process loss, bad
status, unexpected EOF, malformed or out-of-order frames and invalid state
become `unknown`. A successful final frame becomes an observed exit, not an
allocation release or proof that children stopped.

On one local Apple Silicon Mac, the selected actual source and test cases ran
in a signed native source-unity fixture. Cases covered ready, ordered heartbeat,
exact timeout boundary, expiry, rollback, watcher loss, duplicate sequence,
premature event, bad exit and EOF. A separately built deadline-bypass mutant
failed. Source-unity/image SHA-256:
`8fc25d7c56b995e26dc32eda3a81ae21ed45c7d71ecb6c2d6025e49e0a2546f0` /
`d8d99562b87bba02ebe41829f5c576b1cdc1720b6ddca10bf0bbba4303168ebc`.
A second signed native fixture replayed a real request, readiness, two
heartbeats and an exit frame emitted by the previously pinned diagnostic
watcher on a short owned child; an independently built sequence-bypass mutant
failed the duplicate-frame control. Replay source/image SHA-256:
`b454af6e4d2fdbe8a9beb12c92029f55352e933b14b8eee4478e7f61f0602a1f` /
`24bd5a32100655a188c188d4a3d526a1c00407aabedcf7e5bd4f9e28d7741def`.
The replay used synthetic timestamps to test decisions; it does not test a
real host deadline or a continuous native supervisor.

The caller must bind the source and helper to its own authenticated pipe,
initialize state and monotonic time, drain and timestamp input without treating
buffered data as fresh, retain and reconcile the durable reservation, and
separately establish whole-workload termination. State is volatile and accepts
trusted observations; it is not a supervisor, durable ledger, kernel resource
limit, distributed fence, production release or selfhost qualification. No
model, persistent service, resource release or real workload was run.

## Poll-to-poll clock rollback correction

The earlier state retained only the last ready/heartbeat time. Consequently,
if a poll observed time 130 after a heartbeat at 120, a subsequent poll or
exit at 125 could be accepted. The state is now `[phase next-sequence
last-frame-ms timeout-ms last-observed-ms]`, initialized as `[0 1 launch-time
timeout launch-time]`. Every accepted poll updates the last observed time but
does not extend the heartbeat deadline. A backward timestamp, inconsistent
state, or the older four-field format is rejected as unknown. This is a
source-level interface change; no existing state may be silently migrated.

The updated selected source and cases passed in a signed local Darwin native
source-unity diagnostic, including rollback after poll and exit after rollback.
Both an always-expired deadline mutation and a mutation restoring the older
last-frame-only rollback comparison were detected. Source/image SHA-256:
`290ec24b870491e44ade916eb9a1b922e7b9e3e24bf9ed3c0df83f92e85bb5cf` /
`e38fd090cee2f3cea508d849a0c84d5937f6f7a58675b600974a605892b06b22`.
The earlier real-frame replay above predates this interface change; it does
not prove the revised state against a live watcher. The host supervisor and
other qualification limitations above remain open.
