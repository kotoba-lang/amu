# Native block guard candidate (JUN-767)

This isolated pure Kotoba example models a small, fail-closed subset of the
host's target-bound destructive operation policy. It checks an eight-word
session/target/geometry/expiry/approval ticket against independently supplied
host observation, rejects internal, mounted and nonexclusive devices, consumes
one ticket and validates a bounded sector range without offset addition or size
multiplication overflow. Session and identity components are opaque positive
numbers here, not real disk identities or cryptographic tokens.

This is **not an authorization mechanism** until a native host owns both
records, independently obtains and revalidates device identity and exclusive
access, obtains a trusted human decision, and prevents a guest from providing,
modifying, reusing or fabricating either record. Consuming a mutable vector in
this single-threaded fixture is not atomicity under races or across processes.
There is no raw-device I/O, capability grant, trusted prompt, locking,
flush, reopen, cache protection or app integration here. Do
not use this candidate to write to any disk. A passing fixture cannot qualify
JUN-767 or prove the safety of attached SSDs.

Run `AMU=/absolute/path/to/bin/amu TMPDIR=/workspace/scratch ./check.sh`. The
actual selfhost native Kotoba program runs 21 positive/refusal assertions; two
independently compiled mutants must be detected. This is a component check only.

## Scoped regular-file exercise

`TMPDIR=/workspace/scratch ./check-file-host.sh` compiles the exact guard and
a synthetic host fixture using the pinned native macOS Amu root, extracts and
packages the generated code, ad-hoc signs it and executes it with a fresh
FD3-scoped directory per case. An external observer checks the file itself:
the synthetic allowed case writes four bytes, and nine synthetic denials plus
a missing or non-directory FD3 produce no fixture file. These records and choices are created
by the test program itself: they are not trusted user approval, device identity
or an OS authorization boundary. This exercises a real regular-file effect,
not arbitrary-offset block I/O or physical storage. The public CLI still
does not grant its ordinary guests filesystem or device access.

## macOS fixed-offset regular-file control

`TMPDIR=/workspace/scratch ./check-macos-offset.sh` uses the pinned Amu
macOS root and packager to build a Kotoba image generator, then uses the
generated, ad-hoc-signed executable on a fresh private 8192-byte file opened
as FD3. The generated code checks `fstat64` for a regular file, performs a
four-byte `pwrite` at offset 4096, calls `fsync`, and checks a `pread` from the
same offset. An external comparison checks the entire file. Read-only,
character-device and missing descriptors must refuse; the read-only file must
remain unchanged. The image carries no dynamic library load command.

This is a fixed diagnostic, not a reusable provider, a genuine approval, a
physical block device, or a durability/power-loss qualification. It is not
linked to the guard or application. It deliberately rejects character devices,
which include macOS raw disks. The test opens only its own private file;
passing it does not authorize or enable access to any connected disk.

The literal ARM64 instruction words in `seed/macos-offset-control-packager.kotoba`
were derived once on 2026-11-02 using Apple clang 21.0.0 (clang-2100.1.1.101),
`clang -target arm64-apple-macos -c offset-control.s`, where the `.s` file
had the bytes retained as `offset-control-reference.txt`, followed by `xcrun llvm-objdump --macho
--disassemble`. The inert assembly reference has SHA-256
`ccbc4535d37e3c74d0b026b937e2fd8feac56f3e4952a12371d3a1317103cedb`;
the one-off object had SHA-256
`e3acb36553c4c042ff20a979501e31bbb4fa2d1971dfff584b73049cf8321e33`.
The test and generated code do not run clang, an assembler, C code or a C
loader. The checked-in Kotoba words are the build input; the reference is
inert review material only.

## macOS read-only raw geometry control

`TMPDIR=/workspace/scratch ./check-macos-geometry.sh` builds a separate
Amu-generated, ad-hoc-signed macOS ARM64 image with no dylib load command.
The test creates its own 4 MiB disk image, attaches it read-only without a
filesystem, and passes its raw character-device descriptor as FD3. The program
checks the descriptor is a character device, calls `DKIOCGETBLOCKSIZE` and
`DKIOCGETBLOCKCOUNT`, and writes their 16-byte representation to stdout. The
observer compares the returned 512-byte block size and 8192-block count with
fixed expected bytes; a regular file, `/dev/null`, and a missing FD refuse.
The harness detaches the image it attached. If detach fails it retains the
scratch directory so the image is not silently discarded.

This control issues no disk writes and contains no path selection, exclusive
claim, approval, physical-target identity, hotplug handling or app integration.
The 16 bytes represent only the device's reported geometry, which is not a
capacity verification. No physical SSD is accessed by this test. It does not
prove arbitrary devices permit raw access or that their controllers report true
sizes.

The checked-in instruction words were derived once on 2026-11-02 from the
inert `geometry-control-reference.txt` using Apple clang 21.0.0
(clang-2100.1.1.101), `clang -target arm64-apple-macos -c geometry-control.s`,
then `xcrun llvm-objdump --macho --disassemble`. The reference SHA-256 is
`38969c6fe142d970661a12757cd84f8926e5fe51c0307c84bdc7235d4229d08c`;
the one-time object SHA-256 is
`de56c6a6f1ad23972de783312fbe1177a7e88f494833a96fbad575a1312a085a`.
Neither clang nor the reference is invoked by the native build/test.
