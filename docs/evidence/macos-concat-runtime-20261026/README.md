# Bounded Mac string runtime, then the next full-compiler boundary

This diagnostic extends the previous [full-main startup probe](../macos-full-runtime-startup-20261025/README.md). The Amu-built Kotoba packager now emits a 256 MiB Darwin string pool, a bounded resolver for literal and pool spans, `string_concat` at ABI-v11 slot 120, and `string_equal` at slot 112 for both spans. The pool lives in an anonymous mapping; its base and used count are held in diagnostic context extensions at byte offsets 400 and 408. Concatenation copies into the pool, preserves the existing 256 MiB bound, and appends at the tail when the left string ends at the pool's current fill. Pair handles remain in the separately mapped 256 MiB arena.

`seed/macos-concat-main.kotoba` exercises code-literal equality, fresh concatenation, pool-backed equality and tail append. The pinned native Amu compiler produced its 694-byte Mac `main`; the Kotoba packager produced that image, the earlier equality fixture, and the same 3,254,848-byte full compiler `main`. The full image was emitted twice with identical bytes. Apple `as` helped derive the reviewed AArch64 words in [`runtime.s`](runtime.s); final image packaging reads the words from canonical [`macos-concat-runtime-packager.kotoba`](../../../seed/macos-concat-runtime-packager.kotoba), with no assembler in the build path.

The independent [Mac observer](../../../scripts/seed/check-macos-concat-runtime-probe.py) pins source and artifact SHA-256 values, checks the Mach-O layout, emitted helper bytes, the generated mains and the native build admissions, then signs and launches fresh copies. Its [receipt](receipt.json) records these measured cases on Apple Silicon macOS 26.4:

| Case | Exit | Observation |
| --- | ---: | --- |
| Previous equality fixture | 42 | Code-span equality still works. |
| New concat fixture | 42 | Fresh and tail concatenation, then equality of pool-backed strings, passed. |
| Code length removed | SIGTRAP (-5) | A literal outside the admitted code span is refused. |
| Full compiler with concat slot removed | SIGSEGV (-11) | The raw return address maps to the former null slot 120 call. |
| Full compiler with concat installed | SIGTRAP (-5) | It advances to typed wire 39 (`:io/write-error`), string kinds 1/1. |

This is a bounded execution probe, not a complete ABI-v11 runtime. The diagnostic CLI still returns only the empty argument string; wire 39, general capability grants, vectors, full UTF-8 validation, and remaining compiler slots are absent. The full compiler did not finish, rebuild itself on Mac, or prove the Linux-free build closure. The root compiler and packager still executed in a network-disabled ARM Linux container. The next runtime step is a separately granted diagnostic-output provider, followed by the compiler's remaining used ABI slots and a real Mac-native self-rebuild. JUN-417 and JUN-89 remain open.
