# Complete canonical IO output-set source

Source candidate only. io.kotoba now exposes all seven historical IO names,
including write-bytes! arities 2/3. The new interface uses logical byte/text
buffers, typed ordered entries and Results; max-artifact-bytes is a zero-arity
accessor. All parent/parser/hash/CLI callers must adapt explicitly. No old
constant binding, flat-string compatibility bridge or hosted fallback is
claimed. No tests were added/run; no implementation/compiler/generator/
provider or native artifact was executed.

## One write, full payload

Proposed kind 11 is list<bytes>/list<bytes> on existing wire 35/provider 5/
handler 7, WRITE/APPEND plus proposed stage-member (16/Q). The codec validates a logical buffer and prefixes
one encoded FS2 header/path chunk; all payload chunks remain bytes. Native
code validates the outer list, every inner descriptor/span/byte word and total
i64 size before asking the sealed op-6 charge policy. It then creates one raw
request span using real pool budget. The original WRITE/APPEND operation keeps
one opened descriptor for the complete content. No per-chunk reopen or
truncation is substituted.

Six new named private words at 1704..1744 retain request offsets/counts/total/
progress; they are reset before use and remain inside the reserved header.
The two passes do not yield or invoke guest callbacks; the intervening owning
sealed charge decision is pure. The x86 alias-safe six-word C3 save/restore
boundary and independent ISA maps remain. Both kinds 8 and 11 validate the
path span as UTF8; arbitrary payload NUL/nonUTF8 remains data. Raw/segmented
calls require FS2 and cannot enter the legacy token path.

## Complete source publication sequence

All entries, content invariants, text encoding, modes and parents are checked
before staging creation. Paths are normalized with the canonical POSIX
component, original spelling is retained for results/errors, normalized
targets must be distinct and all entries share one parent.

Mode None selects 0600; Some(0) retains 0000. Preserve the original six-octal-
digit nonnegative domain (0..262143), then permission bits only. No flag above
0777 is granted. Text entries validate global UTF8; raw bytes never acquire
a fabricated text view.

MKTEMP requests a new private 0700 directory under that parent. For every
member, in caller order, FS2-only stage-member creates EMPTY with exclusive
no-follow 0600 creation, applies mode, writes the ENTIRE logical payload,
fsyncs and checks close, all through ONE descriptor. The tail is octal mode,
NUL, then raw content. Success acknowledges exactly "1" after all steps;
absence returns "0" and cannot appear to be an empty successful write.
The descriptor is not reopened after mode 0000/0400. All members complete
staging/fsync before publication starts. All sixteen prior forms/IDs/echo
meanings remain; only kind 11 admits Q. No legacy token is added.

Publication preserves caller order: atomic rename (replacing a destination
symlink without following it), then directory fsync BEFORE the next rename.
The caller's commit marker therefore remains last. No subset sort, early
marker, skipped flush, bytes-before-mode or cross-parent staging is allowed.
Linux-native source does not qualify Windows durability/ACL behavior.

Controlled Result failures preserve original path/operation/cause. Cleanup
attempts only the known index.tmp members then the private directory, after
both staging/publication Result outcomes. Ordinary 0/1 cleanup answers retain
force semantics. Protocol/encoding failures are surfaced, never successful
empty data. If cleanup protocol fails, return primary and cleanup facts with
publication :complete or :not-established; a failed primary may already
have published some targets. Published target files are never deleted as
cleanup. Native stage syscall failures remain terminal; detailed stage
failure diagnostics are still a qualification requirement.

## Real remaining cleanup and qualification

A native terminal authority/resource/provider trap may exit without returning
a Result. This source does NOT pretend that language-level finally runs after
exit_group. A real admitted native unwind/provider cleanup mechanism and its
full positive/refusal/resource evidence remain necessary to qualify that
behavior; private staging may remain after a terminal trap. The requirement
is kept open, not silently removed or caught into success.

General list/record/runtime admission, canonical GMIR/kind/signature/type/value
lowering and both ISA encoders, exact updated C1 AND handler artifacts, full
caller/parser/hash integration, permissions/no-follow/atomicity/crash/resource
corpus and platform evidence, Definition CIDs, reviewed mains/locks and actual
self-rebuild/native CDCI/controller remain open. Default budgets do not prove
large files fit. Existing corpus files are preserved as port provenance; their
hosted execution is not a new gate.

Static source scope: 26 sources/44 schemas/688 imported calls/575 record uses/
1116 type positions, no findings in API/arity/record/type-position/lexical/
loop/Git/data checks. Both write-bytes! arities and the exclusive-open/fchmod/full-write/
fsync/checked-close then rename/directory-fsync source order are read, not run.
All 105 private offsets are unique, aligned and inside the reserved header.
No profile/lock/CID/workflow/protection/live-service/production change.
