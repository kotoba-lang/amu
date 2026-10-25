# Darwin mapped pair and typed output diagnostic

`seed/macos-mapped-io-runtime-packager.kotoba` emits one Mach-O image from
Amu-generated `seed/macos-io-main.kotoba`. Its fixed ABI-v11 slice allocates
a 256 MiB pair arena and a 16 MiB mark arena through Darwin `mmap`, installs
`pair_new` in context slot 56, and installs a bounded typed capability in
slot 128. The typed handler accepts wire 37 (`:io/write`), string/string kinds,
an explicit test grant, a valid pair handle, a nonnegative code-span offset,
and at most 64 output bytes. It makes one local stdout write. No other
compiler runtime slot or capability is implemented by this image.

The packager source was compiled with the pinned Amu ARM Linux static root
in a network-disabled local Podman container. That native compiler emitted
the packager, which emitted the unsigned Mach-O images. Python only stages
inputs and observes results. Apple `as` was used earlier to derive and review
the fixed instruction words; it was not in this production path.

The [observer](../../../scripts/seed/check-macos-mapped-io-runtime.py)
pins the source, compiler, raw main, packager and both images by SHA-256;
parses the Mach-O header, load commands, segment extents, guest bytes and
selected ABI words; and requires the allowed and denied images to differ
only at the grant instruction. A second allowed image was byte-identical.
Undefined mode and short guest input both exited 2 without an artifact.
Signed copies passed strict macOS code-signing verification and executed on
Darwin arm64 26.4:

| Image | Exit | stdout | stderr |
| --- | ---: | --- | --- |
| Allowed wire 37 | 42 | `native\n` | empty |
| No grant | SIGTRAP (-5) | empty | empty |
| Zero pair capacity | SIGTRAP (-5) | empty | empty |
| Zero output bound | SIGTRAP (-5) | empty | empty |

The exact hashes and signed-copy results are in [receipt.json](receipt.json).
The earlier version exited 42 without output because it indexed pair records
from the count pointer. The final source loads the separate pair-arena base
from context offset 296 before accessing a record.

This is a host-observed diagnostic slice. It is not a complete Mac compiler,
Mac self-rebuild, trusted user consent, or Linux-free build closure. The
remaining ABI slots, full Amu compiler image and F1=F2=F3 Mac fixed point
remain open under JUN-417.
