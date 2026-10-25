# Complete FS2 codec / capability source extension

This extends the complete canonical filesystem-wire and filesystem capability
modules. It does not claim the old compiler IO/resolver/materializer namespace
or native runtime is integrated or qualified. No compiler, provider, byte
implementation, generator or test was executed; no tests were added.

## Public surface

All original names, typed parameters/results and public function bodies stay:

- filesystem-wire: request / answer / entries;
- filesystem: app-data / browse;
- fs-tree: all six public exports and its entire source are unchanged.

The shared acknowledgement predicate is factored through raw marker bytes.
It still checks the entire five-byte NUL-F-S-2-NUL marker before reading any
payload. No unacknowledged empty-answer fallback is added.

New canonical functions:

| Owner | Export | Parameters | Result |
| --- | --- | --- | --- |
| filesystem-wire | request-bytes | form, string path, bytes tail | Result bytes/error |
| filesystem-wire | answer-bytes | bytes response | Result bytes/error |
| filesystem | read-bytes | string path | Result bytes/error |
| filesystem | read-range | string path, i64 offset, i64 length | Result bytes/error |
| filesystem | write-bytes! | string path, bytes payload | Result bytes/error |
| filesystem | append-bytes! | string path, bytes payload | Result bytes/error |

## Byte-preserving request/result route

request-bytes accepts only write/append forms 1/2. It reuses the full original
form/path validation, encodes only the FS2 header/path as UTF8, then appends
the raw payload with bytes-concat. Embedded NUL, nonUTF8 values and former
separator tokens remain payload data. Empty path and full-span NUL in the
path refuse before a capability call.

read-bytes emits form 0 with no tail. read-range emits form 4 with the owning
offset:length decimal tail; negative offsets/lengths return a typed fs error
before calling the provider. Native range/window/resource refusals remain
terminal. No partial/truncated result is promoted to a successful full read.

Reads use typed-cap-call on fs/app-data with string/bytes (kind proposal 9).
Writes/appends use bytes/bytes (kind proposal 8). These match the complete
contract signatures and native kind/form selector, not primitive type codes.
Both sides use wire 35 under the original effect/capability declaration.

answer-bytes validates the complete acknowledgement and returns bytes-slice
after byte 5, with no string decoding. Absent and empty data still carry the
acknowledgement and become empty bytes. Construction errors propagate as
typed Results; native authority/provider/resource failures are not caught or
replaced by successful empty values. Write primitives return the unchanged
provider payload; they alone do not prove durable atomic publication.

## Preserve the actual compiler IO domain

Language per-value bounds remain 65536 bytes for strings and bytes, including
frame/acknowledgement overhead. These are existing value limits, not a new
file-size acceptance limit. A raw wire function is not an 8 MiB file API.

The historical compiler IO module has seven public names, including its
max-artifact-bytes value: read-text-file, read-artifact-text-file,
read-bounded-bytes-file, write-bytes!, write-text! and write-set!.
Its real semantics still require a complete canonical port:

- Preserve at least the existing 1 MiB source / 8 MiB artifact text domains,
  raw size checks before UTF8 decoding and growth checks after reading.
- Preserve bounded binary reads with no-follow regular-file validation,
  observed-size windows and post-read change checks; do not replace that
  domain with the wire's 64 KiB value limit.
- Preserve normalized distinct target paths, one parent, private same-device
  staging, 0600-before-data (or requested mode), complete writes, file fsync,
  ordered renames, directory fsync before the next member, and the commit
  marker last. Do not call a raw write primitive atomic-output completion.
- Preserve cleanup/refusal facts and the declared platform boundary. Linux
  native evidence cannot silently qualify a Windows/JVM durability rule.

This needs complete chunked/streaming values plus parser/hash/caller handling,
or a separately justified complete value-contract change. Concatenating
chunks into an out-of-domain string, reducing source/file limits, dropping
atomic-publication operations or restoring a hosted fallback is not accepted.
The old IO source is retained as labelled port provenance; only its obsolete
claim that canonical source cannot spell byte calls is corrected here.

## Remaining qualification order

Complete canonical GMIR/kind/signature/type/value lowering and both ISA
encoding; native runtime/provider/FS2 and exact updated C1/handler artifacts;
the full codec/caller/IO representation closure; actual native positive,
refusal, path, authority, resource and corpus evidence; admitted component
artifacts/Definition CIDs and reviewed owning mains/immutable locks; actual
whole self-rebuild and native-only CDCI/controller. All remain unqualified.

No C-loader pin/header equality, CLJK sugar, KBB-first or hosted oracle is a
new acceptance condition. No profile/lock/CID/workflow/protection/live service
or production route changes in this source extension.

## Source inspection

The complete wire/capability/tree source graph has 30 functions and 17 public
names (11 original names preserved, six added), 14 imported calls within
that graph and 89 typed Result uses. Source API/arity/type-position checks
have no findings. All original public function forms are identical; the
tree source and historical IO executable forms are unchanged. The five
acknowledgement bytes match the owning native marker as data. Only the
catalog's proposed answer-kinds subtree changes; its wire/forms/confinement
data and the full language grammar/value bounds remain identical.

These are AST/data/Git comparisons, not compilation or runtime equivalence.
