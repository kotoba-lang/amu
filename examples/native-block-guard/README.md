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
