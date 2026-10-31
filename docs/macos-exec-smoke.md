# Kotoba Mach-O loader and Darwin I/O smoke

`seed/macos-exec-smoke.kotoba` emits a fixed, thin arm64 `MH_EXECUTE` image.
Its entry reads at most 16 bytes from stdin into its stack through the
observed Darwin arm64 `x16` syscall selector and `svc #0x80`, writes exactly
those bytes to stdout, then exits 42. EOF exits 43. A separate
Clang-assembled control gave the same outcomes on this Mac before the Kotoba
source was changed. This is a format, loader, and minimal host-I/O probe, not a
compiler or Amu runtime. The executable requires
`MH_NOUNDEFS | MH_DYLDLINK | MH_TWOLEVEL | MH_PIE` (`0x00200085`);
omitting the first three leaves a
structurally recognizable, signable image that macOS kills before the entry.

## 2026-10-25 local evidence

| Input or result | SHA-256 / observation |
| --- | --- |
| Source | `b5fec1a80ea43645cd549d5e57c54802cbdef1eb048300a1a95c62b7bd9a776c` |
| Pinned Amu ARM Linux selfhost root | `cd65664a146bb0eea13577d5d9687467a22700fe91820a12001f1ddb0dc9b4c9` |
| Selfhost-built emitter, `aarch64-linux` static ELF | `0906ceed0d5db556c4ecb49973517355876941920c1dc94ad4f3d2f112065ced` |
| Kotoba-emitted unsigned Mach-O | `cd82530784cae0c2b9b42125fb82f2a3725269b62a34cccb53c2199664109644` |
| macOS arm64 signed diagnostic copy | `codesign --verify --strict` passed; `abc\n` echoed with exit 42; empty stdin exited 43; 17-byte stdin returned the first 16 bytes with exit 42; signed SHA-256 `2d845d80db12777bf4c942566125887e6cbce8f7c266a30e17555f0c4a113bbd` |
| Signed copy missing dynamic-link flags | signature passed; exit `-9` in Python subprocess |
| FS2 write outside granted root | emitter exit `3`; no output file |

The emitter was built and run by the pinned selfhost root in a network-disabled
ARM Linux container, under `scripts/seed/native_build_queue.py`. Two independent
emissions had identical unsigned bytes. On Apple Silicon,
`scripts/seed/check-macos-exec-smoke.py UNSIGNED_MACHO NEW_OUTPUT_DIR` signs
**copies** with the system `codesign`, verifies them, executes the positive and
negative controls, and writes a JSON receipt. Python stages and observes; it
does not emit the Mach-O. The negative control changes only the header flags.

This proves that Kotoba can emit bytes accepted by the Mac loader after local
diagnostic signing and perform one bounded Darwin stdin/stdout/exit sequence. The
raw syscall sequence is local ABI evidence, not a general or release-qualified
Darwin capability contract. **As of the 2026-10-25 evidence above**, it did not
remove the Linux build-host dependency, provide a macOS Amu full compiler,
implement its file/clock/memory/authority capabilities, self-rebuild F1–F3, or
qualify AIUEOS media/release. Those were separate JUN-417 gates. The first
two have since been closed; see the status update below.

## Status update, 2026-10-28 (JUN-417)

Code and receipts supersede the sentence above on two points. Read against
`seed/bootstrap/aarch64-macos/root.json` (status `diagnostic-candidate`) and
[`docs/evidence/mac-no-linux-reproduction-20261028/`](evidence/mac-no-linux-reproduction-20261028/README.md):

* **A macOS Amu full compiler exists.** `amu-full-root.macho` (arm64 Mach-O)
  rebuilds the 48-module FULL source on Apple Silicon: F1 and F2 containers are
  identical (`e031180f…`), the packager rebuilds itself, and the AIUEOS user
  target is emitted. Reproduced on an Apple M1 Max, macOS 26.4, in 32 s with no
  Linux, JVM, Node or C compiler process.
* **The Linux build host is not needed to produce the Linux compilers.** From
  that Mac fixed point, `check-macos-cross-linux-candidates.py` produces an
  x86_64 compiler byte-identical to `bin/amu` (`b8652a6d…`) and an aarch64 root
  byte-identical to `seed/bootstrap/aarch64-linux-static-root` (`20dd57c6…`);
  its receipt records `linuxProcessInThisGate: false`. The produced ELFs were
  not executed on Linux in that gate (`MAC_NATIVE_CROSS_ARTIFACTS_UNEXECUTED`).

## Status update, 2026-10-29 (JUN-546)

Code supersedes the 2026-10-28 refusal. The Mac runtime now **implements
`arena-scope`**: context ABI slot 224 pushes four allocator counters on a
256-deep LIFO and slot 232 pops them, following the Linux runtimes
(`seed/76-x86_64-static-rt.kotoba`, `seed/77-aarch64-static-rt.kotoba`). The
saved counters are the pair count (behind ctx+0x120), the pool use (ctx+0x198),
the vector handle count (ctx+0x3e88) and the vector item use (ctx+0x3e98).
The context tag is checked; enter at depth 256 and leave at depth 0 fail; every
saved counter is validated against the live one before any restore. A failure
writes `seed: arena-scope failed (Mac runtime)` to stderr and exits 70, the
Linux status for a scope failure. The Mac item arena is a bump allocator that
assumes everything above its use is zero (Linux zeroes up to a high-water mark
at allocation instead), so leave zeroes the item words it releases. The routines
are hand-assembled AArch64 words in `seed/macos-fs2-runtime-packager.kotoba`
(derived once with the system assembler, like the rest of that runtime) placed in
a gap of the runtime text; their LIFO lives at ctx+0x1000, DATA no other routine
of the image touches (checked by disassembling the runtime and the FS2
callbacks, and by the fixed point below).

`scripts/seed/check-macos-arena-scope.py` (Mac CI job) compiles, packages,
signs and runs the repository oracles `seed/tests/native-arena-scope.kotoba`
(600,000 scoped allocations that fit only if every counter is restored,
nested scopes, f64 results; depth 256 passes, depth 257 exits 70) and
`seed/tests/native-zero-watermark.kotoba`, a nested-scope program, a raw
leave-without-enter main (exit 70), and the unscoped negative control, which
still traps at the original budget. The packager source changed, so
`root.json` moved through the two-phase writer (`--phase source`, JUN-545):
the new packager is the pinned one and `expectedFixedPoint.packagerUnsignedSha256`
follows it. The pinned **compiler** image is unchanged and still carries the
earlier runtime (it never calls arena-scope); adopting the new runtime into it is
the writer's `--phase final`. A compiler packaged with the new runtime
reproduces the same container (`46daf3fa…`) and its own unsigned image
(a local run, not a receipt).

Still open, and not claimed here: the Mac runtime is a diagnostic profile, not
a qualified one. The Mac root's status stays `diagnostic-candidate`; updating the
remaining pinned descriptors is receipt-driven (`scripts/seed/write-bootstrap-descriptors.py`,
JUN-545 and JUN-547); the AIUEOS release bundle's own build is tracked separately
(JUN-548); physical hardware and release qualification are separate gates.

## Status update, 2026-10-31 (JUN-707)

The same failure shape as JUN-546, at context ABI slots 96 and 104. Every
prelude keyword path through `__r6-kwreg` (`keyword-from-string`,
`keyword-name` on a new name, `document-keyword-value`) calls them: they are
the private keyword intern rows, `seed/73-keyword-intern.kotoba` on Linux.
The Mac wrapper installed neither, so a `bin/amu run` program that interned a
keyword died of SIGSEGV (exit 139). `document-kind` and `keyword?` never
reached the slots and kept working, which is why the gap stayed hidden.

The slice-setup stub now branches to `ki-words` at `KI-START` (3720, in the
free span after the CLI helper in every mode). That block installs both slots
and holds the two routines:

- **Put** appends `(entity, attribute, value)` rows to a private 6 MiB
  anonymous mapping made on first use. The base is at ctx+1800 and the count
  at ctx+1808, the Linux G+776/G+784. The mapping is outside every arena, so
  arena-scope rollback never changes an interned name.
- **Get** returns the newest matching value or INT64_MIN.

There are at most 262144 rows, as on Linux. A wrong context tag, a failed
mapping or a full table writes `seed: keyword intern failed (Mac runtime)` to
stderr and exits 70.

`scripts/seed/check-macos-keyword-intern.py` (Mac CI job) runs four programs:

| Program | What it checks | Exit |
|---|---|---|
| `seed/tests/macos-keyword-intern.kotoba` main | 1,800 Unicode keywords interned twice, with identity and name round trips; a literal keyword; `document-keyword-value`; a keyword interned inside arena-scope | 0 |
| exhaust-main | more names than 262144 rows hold | 70 |
| raw main | slot 96 called with a context whose tag is not 11 | 70 |
| plain positive control | a program without keywords | 0 |

The pins moved the same way as for JUN-546:

1. A staged packager run (the old packager builds the new one).
2. `--phase source`.
3. The descriptor-bound Mac gate.
4. The cross check (the Linux images are unchanged).
5. `--phase final`.
6. `repin-derived-pins.py`, which rebuilt the public CLI.

The compiler container fixed point is unchanged (`7d09635f…`). Before the
change, a `bin/amu run` of the keyword probe exited 139; after it, the probe
prints 1.

Still open: the public kgraph slots 80/88 (`__r6-kgput` / `__r6-kgget`) are
not installed on the Mac either, so `seed/tests/native-keyword-intern.kotoba`
(which also writes the public graph) still dies there. That is a separate
gap.
