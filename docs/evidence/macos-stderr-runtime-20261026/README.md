# Separate Mac diagnostic output grant and full compiler no-argument CLI

This diagnostic extends the [bounded string runtime](../macos-concat-runtime-20261026/README.md). The Kotoba packager installs a wire 39 (`:io/write-error`) handler at ABI-v11 slot 128. It accepts string kinds 1/1, checks the request handle and bounded literal or pool span, requires the stderr allow bit independently of stdout, writes all bytes to Darwin fd 2, and returns the decimal byte count as a pool-backed string. Other wires branch to the preceding diagnostic handler. Build inputs `stdout`, `stderr`, and `deny` select exactly one output grant or none; they are explicit test controls, not trusted user approval.

The reviewed [`runtime.s`](runtime.s) is assembly derivation evidence. The two cross-helper branches in its object were relocated into fixed words in [`macos-stderr-runtime-packager.kotoba`](../../../seed/macos-stderr-runtime-packager.kotoba). The final image build compiles and runs only Kotoba/Amu native sources; Apple `as` is not in that build path. The pinned Amu compiler and Kotoba packager still run in a network-disabled ARM Linux container.

The independent [Mac observer](../../../scripts/seed/check-macos-stderr-runtime-probe.py) pins sources, raw mains, packager, image bytes and the [Linux root oracle](linux-root-noargs-oracle.json). It checks Mach-O layout, helper words, the granted instruction, byte-identical repeated full-image output, and that each allow/deny image pair differs only in its grant word. It then signs fresh copies, verifies signatures and checks process results. Its [receipt](receipt.json) was measured on Apple Silicon macOS 26.4.

| Mac case | Exit | stdout | stderr |
| --- | ---: | --- | --- |
| `:io/write-error` with stderr grant | 42 | empty | `diagnostic\n` |
| `:io/write-error` with stdout grant | SIGTRAP (-5) | empty | empty |
| `:io/write` with stdout grant | 42 | `native\n` | empty |
| `:io/write` with stderr grant | SIGTRAP (-5) | empty | empty |
| Concatenation with no output grant | 42 | empty | empty |
| Full compiler, no output grant | SIGTRAP (-5) | empty | empty |
| Full compiler, stderr grant | 2 | empty | exact Linux root no-argument usage |

The full compiler now completes its **no-argument CLI route** on Mac and returns the same exit and bytes as the pinned Linux root. The diagnostic `:cli/args` provider still returns an empty string, so this does not exercise `check`, `compile`, file access, or a Mac self-rebuild. General UTF-8 validation, remaining ABI slots, trusted operation approval, Linux-free build closure, AIUEOS media/build/boot, release and physical qualification remain open. JUN-417 and JUN-89 stay In Progress.
