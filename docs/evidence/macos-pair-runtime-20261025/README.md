# First Darwin ABI-v11 runtime slot: `pair_new`

The Amu native root compiled `seed/macos-pair-main.kotoba` for
`aarch64-macos` and extracted its 67-byte `main`. That generated code loads
ABI-v11 slot 56 and calls it to create a string-literal pair. The separate
Kotoba source `seed/macos-pair-runtime-packager.kotoba`, compiled by Amu to a
native ARM Linux tool, emitted an 81,920-byte PIE Mach-O with a writable
64 KiB `__DATA` segment. Its wrapper installs a bounded pair table, pair
count and mark pointers in the context, sets code base/length and fuel, then
calls the generated `main`. The wrapper checks the returned handle, pair
count, offset, length and `abc` bytes before exiting 42.

On Apple Silicon macOS 26.4, a strictly verified ad-hoc signed copy exited
42 without output. Three signed controls failed without output: removing
slot 56 caused SIGSEGV, forcing zero pair capacity caused SIGTRAP, and
changing the literal `c` to `d` caused SIGTRAP. A second native emission was
byte-identical. A 12-byte raw input returned 2 and created no image. The
exact root/source/tool/image hashes and controls are in [receipt.json](receipt.json).

The helper implements the ABI-v11 `pair_new` data shape with a 1-based
handle and a 1,024-pair bound. It is the first executed Darwin runtime slot,
not the complete Amu runtime. The other full-compiler slots, vectors,
string pool, typed capabilities, CLI/FS2, runtime budgets, sandboxing and
self-rebuild remain open. Compilation and packaging still ran in a local
Podman Linux VM; this result proves Mac execution of one generated runtime
operation, not a Linux-free build chain. No full compiler image was launched.

`scripts/seed/check-macos-pair-runtime.py` is the independent Mac observer.
It pins the source and artifact bytes, checks the Mach-O and generated slot
call, signs copies and runs the positive and negative controls. Python does
not emit the positive Mach-O or implement the helper. The packaged source
accepts only this 67-byte diagnostic raw shape; it is not a general
application packager.
