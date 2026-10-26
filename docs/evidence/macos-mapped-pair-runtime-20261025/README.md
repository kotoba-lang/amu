# Darwin ABI-v11 `pair_new` with mmap-backed arenas

The Amu native root compiled `seed/macos-pair-main.kotoba` for `aarch64-macos`
and extracted its 67-byte generated `main`. The Kotoba source
`seed/macos-mapped-pair-runtime-packager.kotoba`, compiled by Amu to a native
ARM Linux tool, packaged that `main` into a 32,768-byte Mach-O. Its Darwin
wrapper uses syscall 197 (`mmap`) to reserve a 256 MiB pair arena and a
16 MiB mark arena, installs ABI-v11 slot 56 and the arena pointers, then
calls the generated code. The helper checks the full runtime's declared
16,777,216-pair bound before writing a pair. The wrapper checks the returned
handle, count, offset, length and `abc` bytes, then exits 42.

On Apple Silicon macOS 26.4, the signed image exited 42 with no output.
Five separately signed controls failed with no output: removing slot 56
caused SIGSEGV; invalid flags on either `mmap` caused SIGTRAP; forcing zero
pair capacity caused SIGTRAP; changing the literal `c` to `d` caused
SIGTRAP. A repeat emission was byte-identical. A 12-byte input returned 2
and created no image. The source, tool, image and control digests are in
[receipt.json](receipt.json).

`scripts/seed/check-macos-mapped-pair-runtime.py` is the independent Mac
observer. It pins inputs and artifacts, checks Mach-O layout and key wrapper
instructions, signs copies, and runs the positive and negative controls.
Python neither emits the positive Mach-O nor implements the helper.

This is still a diagnostic image accepting only the 67-byte generated
payload. It exercises one pair and does not prove the full 256 MiB working
set or the capacity boundary under load. Other ABI slots, vectors, pools,
typed capabilities, CLI/FS2, full compiler execution and native self-rebuild
remain open. Compilation and packaging still ran inside a local Podman Linux
VM, so Linux-free build closure is not established. This result does not
qualify AIUEOS, Itonami, or a production release.
