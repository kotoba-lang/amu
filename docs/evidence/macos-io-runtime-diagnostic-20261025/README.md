# macOS capability ABI diagnostic

`seed/macos-io-main.kotoba` calls `:io/write` with `"native\n"` and returns 42.
The pinned Amu-built ARM Linux native compiler compiled this canonical source
to `aarch64-macos` KSEED1 and extracted `main` (135 bytes). The generated
function calls ABI context slot 56 (`pair_new`) for its string literal and
slot 128 (`typed_cap_call`) with wire 37 and string kinds 1/1. These calls
are visible in the extracted AArch64 code and were executed on macOS arm64.

[`runtime.s`](runtime.s) is a **diagnostic** host implementation of just those
two slots. It gives the guest a bounded pair table, a code span, fuel and one
test allow bit for wire 37; it validates the wire, kinds, handle and span
before a direct Darwin `write` syscall. The generated guest code is included
as data with `.incbin`. A no-grant control changes only the wrapper's allow
instruction from `movz x8,#32,lsl #32` to `mov x8,#0`. Both images were
signed and passed strict `codesign` verification on macOS arm64 26.4.

| Diagnostic image | Exit | stdout | stderr |
| --- | ---: | --- | --- |
| Wire 37 granted | 42 | `native\n` | empty |
| No wire granted | SIGTRAP (`-5`) | empty | empty |

The [receipt](receipt.json) pins the source, KSEED1, raw function and both
unsigned/signed image hashes. The Mach-O shell uses platform dyld and no
libSystem load command. The shell was emitted by the Kotoba packager in the
preceding smoke; the additional ABI runtime was assembled with Apple `as`
and staged with Python only for this experiment. **This is not a product
runtime, a user-consent gate, a Kotoba-only Mac build, or a Mac compiler
self-rebuild.** The next
implementation must move the ABI runtime and its bounded authority into the
Kotoba/Amu native build closure, implement the remaining compiler capabilities
and memory arenas, then run the complete compiler on macOS.

The first diagnostic launch trapped before output because the pair-used word
in the stack context was not initialized. Zeroing that word yielded the
positive result above. This is a runtime initialization requirement, not a
guest compiler failure.

## Kotoba-produced diagnostic image

`seed/macos-io-runtime-payload.kotoba` now holds the reviewed 112 AArch64
instruction/data words as canonical Kotoba source. The pinned Amu-built native
ARM compiler produced a Linux-static emitter from it. That emitter writes a
448-byte runtime payload through FS2 for explicit `allow` or `deny` test mode;
an undeclared mode exits 2 without an output file. The allowed payload is
byte-identical to the independently assembled diagnostic section above. The
two payloads differ only in the four-byte instruction slot at byte 20.

The Kotoba Mach-O packager from the preceding smoke then embedded each
Kotoba-emitted payload in a six-command Mac image. Signed copies executed on
macOS arm64 26.4 with the same positive and no-grant results in
[kotoba-receipt.json](kotoba-receipt.json). The pinned
`scripts/seed/check-macos-io-runtime-payload.py` observer checks source and
artifact digests, the guest-code span, Mach-O commands, the single grant-word
difference, strict signatures, the actual output and the rejection.

This repeat build invoked Amu/Kotoba native tools for payload and image bytes;
Apple `as` was used only for the earlier comparison. The executable still
contains fixed bootstrap machine words derived from that diagnostic assembly,
is limited to one local `:io/write` operation and one-digit response, and was
built by an Amu compiler running in a Linux VM. It is **not** a general
Darwin capability runtime, user approval flow, Mac native selfhost compiler,
or Linux-independent AIUEOS build.
