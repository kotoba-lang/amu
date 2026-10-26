# Segmented compiler input source

Source candidate only. No implementation/compiler/generator/provider or tests
were executed; no tests were added. The old seven-name IO namespace is not
wholly replaced: output-set publication and parent/parser/hash/resolver/
materializer callers remain open.

## Full file, bounded values, one descriptor

Proposed kind 10 is string/list<bytes> on existing wire 35 / provider 5 /
handler 7, READ/RANGE only. The unchanged provider operation keeps ONE opened
descriptor for the full read. Only after the complete trusted internal span
and acknowledgement exist does native code partition the response. Reopening
the path per chunk could mix same-size files across a rename and is refused
as an implementation strategy.

The converter reserves K+1 descriptors and N+K item words for N acknowledged
bytes and K chunks. Inner lengths obey byte/vector limits and 65536; K obeys
the outer list/vector bound. All stores precede counter publication. This
uses the existing typed-list/vector representation containing byte handles.
It creates neither a new primitive byte type nor an oversized string.

Aggregate size uses actual run budgets. Default settings are not proof that
an 8 MiB workload fits. The full response may consume a read span, a framed
copy and byte item words; all must be admitted and measured.

## Complete logical buffer and input unit

io_buffer.kotoba has 16 public operations and their full helper closure:
constructors, checked append/concatenation, counts/chunk lookup, byte cursor,
prefix removal, validated text view and code-point cursor. Construction
counts all chunks and guards i64 overflow. Empty chunks normalize away;
prefix removal shares immutable slices. No aggregate flattening occurs.

Cursors are constructor-produced values and advance through chunks without
rescanning prefixes. UTF8 validation walks the complete logical sequence,
including split multibyte characters. It preserves all seven canonical
refusal categories and first-failure order, deciding the second byte before
later truncation. Bad-continuation offsets name that byte; other errors name
the sequence start. No replacement decoding, ASCII-only restriction, BOM
stripping or chunk-local UTF8 conversion is used. U+FEFF remains data under
the canonical byte-preserving contract. Old host decoder quirks are not
native parity evidence; actual complete corpus qualification remains open.

The FS2 codec checks all five acknowledgement bytes across empty/short chunks
and removes exactly those bytes. An unacknowledged empty response refuses;
an acknowledged empty answer yields a real empty buffer.

io_input.kotoba implements read-text-file (1048576 raw bytes),
read-artifact-text-file (8388608), read-bounded-bytes-file (caller maximum),
and a native zero-arity max-artifact-bytes accessor. Results are logical text/
byte buffers. This is an explicit typed interface needing parent/caller
adaptation, not a flat string or the old constant binding.

Metadata requires exactly four nonnegative decimal fields and guards i64
accumulation, mode and kind. Invalid data cannot become zero. Text checks
observed RAW size before READ and actual total before UTF8 validation,
including growth after STAT. It uses full READ, preserving its readable-path
domain instead of silently substituting regular-file-only RANGE.

Binary input retains no-follow/regular-file/size checks, ONE RANGE covering
the observed window (including zero size), actual length equality, and
post-read presence/kind/size checks. This is not an immutable snapshot or
same-size-mutation proof. Native range/authority/resource traps remain
terminal; no catch turns them into successful empty data.

## x86 source correction

The assembler maps x86 s0..s4 to t4..t8. Earlier unexecuted byte fragments
mixed those aliases. The byte/chunk fragments now save six C3 words and use
only the distinct ctx/t0..t8/a1..a4 core. Request charging saves descriptor
facts, restores s0 for state operands, and recovers ctx BEFORE restoring t4.
Outputs survive restoration in argument registers. Both ISA maps were read
as data; no emitted code was generated or executed.

## Remaining closure

Complete canonical GMIR/kind/signature/type/value lowering and both ISA
encoding, general record/list/runtime admission, exact updated C1/handler
artifacts, complete parent outputs and caller/parser/hash adaptation, actual
native positive/refusal/resource/authority/path/corpus evidence, Definition
CIDs, reviewed owning mains/locks and real self-rebuild/native CDCI controller
remain required. No C-loader pin, hosted oracle or legacy host fallback is
introduced. No profile/lock/CID/workflow/protection/live route is activated.

## Static source evidence

The combined graph reads 24 sources, 41 schemas, 624 imported calls,
544 record uses and 948 type positions. API/arity/record/type-position,
lexical binding, loop/recur and Git/data inspection has no findings. All
existing public parameters and prior vector/bytes primitive bodies remain.
The 14-register byte core is physically distinct under both actual ISA maps;
six-word save/restore and ctx recovery order are inspected as source.
The canonical seven UTF8 reason names and the single bounded RANGE call
shape are read without evaluating them. This is not code generation,
execution, complete static type checking or native equivalence evidence.
