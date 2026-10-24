# Native FS2 and reader integration candidate

The measured `seed/MANIFEST` compiler remains the only semantic compiler.
Its type checker and lowering admit the five catalogue FS shapes: ABI kinds
1 (string/string), 8 (bytes/bytes), 9 (string/bytes), 10
(string/list of bytes), and 11 (list of bytes/list of bytes). Only wire 35
admits the added combinations. Runtime form admission still narrows each
shape to the operations in the FS2 contract. Raw requests require FS2.

Both Linux emitters append `seed/72-linux-fs2.kotoba`. It implements the
original A–P forms, Q/R/S managed output, and the T exclusive-publication
extension. T uses Linux renameat2 with RENAME_NOREPLACE through scoped parent
FDs. It never overwrites a destination and refuses ENOSYS without a rename
fallback. See the [Linux rename manual](https://man7.org/linux/man-pages/man2/rename.2.html).
Individual byte values retain
their 8 MiB limit. Segmented requests retain each segment and are validated
before I/O; reads and replies split into bounded chunks. Their aggregate
uses the existing pool and item budgets. Output resource admission precedes
mutation. Exact RANGE windows use a regular no-follow nonblocking FD and
name unavailable windows as `fs/range-unavailable` with exit 126.

Managed output journals creation, the parent/directory identity, generated
`index.tmp` members and live FDs in private memory. Exclusive member creation
precedes mode application, complete writing, fsync and checked close. FD
journal entries are consumed before close, including failed close/EINTR.
The common exit path cleans managed output on normal return and registered
fault, budget, INT and TERM signals. Critical creation/journal transitions
block asynchronous INT/TERM/ALRM/XCPU and restore the prior signal mask.
Cleanup uses no guest allocation, callback or fuel. A replaced directory or
uncaptured creation is preserved and reported as `KEXE_CLEANUP
{:incomplete}`; cleanup never guesses ownership or deletes a published target.
An original failure keeps its diagnostic/exit; cleanup failure changes an
otherwise successful zero exit to nonzero.

Keyword interning previously shared the public 4096-datom KGraph. Large
canonical reader inputs exhausted it. `seed/73-keyword-intern.kotoba` adds
private context slots 96/104 and a separate bounded 262144-row arena (6 MiB),
allocated before resource limits and seccomp. Public slots 80/88 retain the
4096-row append-only, last-write-wins graph and its refusal. Keyword rows
survive guest arena rollback and cannot be changed by public graph writes.
Artifacts using this extension require the corresponding pinned native
runtime; context version alone does not qualify an older image.

The compiler's own text and binary I/O now uses acknowledged FS2 operations,
including the driver, container writer and linked output writer. Its private
bounded source-lock read operation remains distinct from ordinary FS access.
KSL1 keeps canonical path/root pins. KSL2 adds a closed namespace-to-block-path
mapping with a bijection to exact SHA-256 file records and no root fallback.

`kotoba.compiler.module-lock` derives raw SHA-256 source CIDs, validates locks,
verifies bytes before strict UTF-8 decoding, loads only reachable modules and
emits KSL2. Its metadata extraction does not type-check or admit programs.
The adopted compiler checks and links those exact inputs. The writer uses
private managed staging, file fsync, exclusive publication, directory fsync
and discard, comparing an existing block's exact bytes instead of replacing
it. The explicit loader callback returns a checked result; the historical
ambient resolver arity is retired.

## Qualification state

Initial ARM Linux candidates have passed all nineteen FS2 form positives,
non-UTF-8 raw roundtrip, a 10 MB split-header segmented roundtrip, malformed
and scope refusals, normal/fatal/fuel/CPU/wall/INT/TERM cleanup, publication
preservation, and a directory replacement control that preserves both the
replacement sentinel and moved owned data while reporting incomplete cleanup.
These runs are candidates, not owning-main or public-product qualification.

The current cleanup leaf also passed all22 original golden inputs in a native
fault model. Seven expected observations intentionally preserve data more
strictly: failed identity probes preserve members and the directory; failed
member removal prevents rmdir. The original inputs remain unchanged. This
unit result does not establish all actual-kernel faults or race windows.

The T operation passed both exclusive-publication preservation and a real
kernel ENOSYS control, using the VM default seccomp profile plus that one
denial. The refused publication exited126 and the managed directory was
removed without publishing the destination. Existing current-runtime
segmented/resource/signal/replacement controls also passed.

Native Definition graph tests cover acyclic and recursive identity, rename
and reorder invariance, changed-body closure, the 8/9-member SCC boundary,
effect refusal propagation, schema closure and cache/export material.
Native module-lock tests retain historical source/graph CID vectors and
exercise tampering, unpinned dependencies, namespace mismatch, invalid UTF-8,
missing blocks and duplicate aliases. Native resolver output and writer
replay both compiled, packed and executed through the adopted compiler.

The explicit path-loader test is a bounded two-module callback fixture.
General path discovery, package/signature/admission, checked-KIR Definition
graph integration and full public CLI/target behavior remain open.

The repository's canonical Form reader was built through the measured core
with a source lock, packed into native ARM ELF, and used to read the complete
current `surface-status.edn` (version 1/profile 6) and `cli.edn` (12 commands
and their flags). This is reader execution, not implementation of all CLI
verbs. Full CLI/target, Definition/package CID, fault matrix, actual x86,
complete selfbuild/Embench/MIR/GMIR/CDCI, main/CI readback and cleanup remain
required before the encompassing issues can be completed.
