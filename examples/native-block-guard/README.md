# Native block guard candidate (JUN-767)

## Disk Arbitration claim-state query control

`TMPDIR=/workspace/scratch ./check-macos-da-claimed.sh` builds a separate
native diagnostic that looks up Disk Arbitration, creates a session, and
queries `_DAServerDiskIsClaimed` for a NUL-terminated disk name on stdin. It
checks RPC status and a boolean reply and sends a session-release message.
Its test queries a newly attached private virtual disk and requires a boolean;
it also rejects a nonexistent disk, missing input and unterminated input. The
test does not independently establish whether the returned boolean is correct.

The query is read-only and establishes neither an exclusive claim nor a stable
target identity. Its result can change immediately after the query and must
never authorize a write. Session-release send and audit-token limitations in
the following controls still apply. No physical disk is opened or modified.

The interface oracle was the pinned Apple `DAServer.defs` described below;
the inert `da-claimed-reference.txt` was assembled once on 2026-11-02 with
Apple clang 21.0.0 (clang-2100.1.1.101). Its SHA-256 is
`26fd8fa584b9df782ac0a4d4ac21f0116611fa93795d0f6f201c8891012f574e`,
and the object SHA-256 is
`30c595f99fd344511fb072ae029f2dc15f924b75965fd6ab691c583bb0673b29`.
The normal native build consumes Kotoba instruction words without MIG, clang
or a libSystem load command.

## Disk Arbitration session control

`TMPDIR=/workspace/scratch ./check-macos-da-session.sh` builds an Amu-emitted
Darwin ARM64 control which obtains a bootstrap port, looks up the Disk
Arbitration service, creates a short-lived session using a special reply port,
then sends the session-release request. It checks the returned message shape
and nonzero session port. Separately emitted invalid-service and invalid-RPC
mutants must refuse. A prior regular-reply-port attempt was terminated by
macOS with `EXC_GUARD / REQUIRE_REPLY_PORT_SEMANTICS`.

The release is a one-way Mach message: successful send does not independently
prove server-side cleanup. Service audit-token interpretation remains
unqualified as described below. This control does not identify, claim, unmount,
read or write a disk, and does not obtain user approval.

The one-time `xcrun mig` interface oracle used Apple DiskArbitration
`diskarbitrationd/DAServer.defs` at commit
`a542bda934211dc3c301bfdcc7f21349c4164a85`, SHA-256
`ad03feb8ab44c5bfcbc423212c0c87ea0751b56347761273f1e9f525979deda0`,
and the pinned launchd definitions recorded below. The inert reference was
assembled once on 2026-11-02 with Apple clang 21.0.0
(clang-2100.1.1.101): `da-session-reference.txt` SHA-256
`2a7a991cae8553b5b74a1720e8fe98cb54ad644dc7222bd5566f1e50b3640dc2`,
object SHA-256 `14aa90aafe91ccc455bdbb8d6f65238cb6b324f5f827d7b3fd3da6cf8db6651e`.
Normal native builds consume Kotoba instruction words without MIG, clang or a
libSystem load command.

## Disk Arbitration service lookup control

`TMPDIR=/workspace/scratch ./check-macos-da-lookup.sh` builds a separate
native Darwin ARM64 diagnostic. After acquiring its bootstrap port, it sends
the launchd `look_up2` Mach request for Disk Arbitration and checks the reply
descriptor count, nonzero port name, and audit trailer; a mutated service name must
refuse. The current control checks the trailer's effective-UID word as used by
the examined Apple launchd client, but the audit token is documented as
opaque, and this is not a portable or production-qualified identity check.
It does not create a Disk Arbitration session, claim or unmount a disk,
obtain user consent, or access any storage device.

The one-time interface oracle was `xcrun mig` applied to Apple launchd
`job.defs` and `job_types.defs` at commit
`d448a1c8f70a61202f8705f94337f686b87c30c4`; their SHA-256 hashes were
`a177ddb03afbe5ef4483ff4c6173759bdff055327b03d3a186944c78a08d245f` and
`4f0913150edc5a4fc41f51f63ffcfc64c65723769253fa39437f8698975f861b`.
The inert `da-lookup-reference.txt` was then assembled once on 2026-11-02 by
Apple clang 21.0.0 (clang-2100.1.1.101); the reference SHA-256 is
`599e5cc0253faeb03c355c2b930843b038c141f816ae737ced470538e6f2f472`
and the object SHA-256 is
`9d13b5029412447eac31588cabbc69807a14d16ac164c5cde21da5391b6d5e85`.
The native build uses only the Kotoba instruction words, without MIG, an
assembler or a libSystem load command.

## Mach bootstrap-port control

`TMPDIR=/workspace/scratch ./check-macos-mach-bootstrap.sh` builds a native
Darwin ARM64 diagnostic using the pinned Amu compiler and Kotoba packager.
It obtains its own task and reply ports, sends the kernel task special-port
request through `mach_msg2_trap`, and checks the complex reply and nonzero
bootstrap send right. A separately generated invalid selector must refuse.
The process exits immediately; it does not contact Disk Arbitration, enumerate
or claim a disk, open a device, or request user approval. The reply checks do
not qualify Mach IPC for other messages or macOS versions. An earlier attempt
using `mach_msg_trap` was terminated by macOS with `EXC_GUARD` /
`INVALID_OPTIONS`; the passing control uses `mach_msg2_trap` instead.

The inert `mach-bootstrap-reference.txt` was derived on 2026-11-02 using Apple
clang 21.0.0 (clang-2100.1.1.101), `clang -target arm64-apple-macos -c
bootstrap.s`, and `xcrun llvm-objdump --macho --disassemble`. The reference
SHA-256 is `146f7f32758f31776912b0f31ec32752b09bd4d86919a9f14aa5e7274a1a257f`;
the one-off object SHA-256 is
`140eb78bd1d7f8afa86bcc901fc9de207da4ce79480c59fecfbf5ee72cc0d6e8`.
Normal native builds use the checked-in Kotoba instruction words without an
assembler or libSystem load command.

## Variable sector write fixture

`TMPDIR=/workspace/scratch ./check-macos-pwrite-fixture.sh` builds a native
control that accepts an eight-byte sector index followed by exactly 512 bytes
of data on stdin, writes one sector to FD3, calls `fsync`, and compares a
`pread` of the entire sector. The control requires a character device with
8192 reported 512-byte sectors, a fixed marker in sector zero, and an index
between 1 and 8191. The test itself attaches and identity-checks its own
private virtual image before opening it, and compares the whole backing image
after detaching. It exercises three locations and rejects out-of-range index,
short payload, read-only, regular/missing FD, wrong marker and wrong geometry.

The fixed marker and geometry can be imitated: they are **not physical-device
identity, an exclusive claim, trusted user approval, or an authorization**.
Never pass a physical disk to this fixture. `fsync` plus immediate readback
and backing-image comparison do not qualify persistence on real hardware.
The 4096-byte sector path and real-device I/O are not implemented here.

The inert `pwrite-fixture-reference.txt` was derived on 2026-11-02 using
Apple clang 21.0.0 (clang-2100.1.1.101), `clang -target arm64-apple-macos
-c write.s`, followed by `xcrun llvm-objdump --macho --disassemble`. The
reference SHA-256 is
`5163537b9c97a42d4f1eff48698fa948364522a4e60a4db15ff693e1ac6bc249`,
and the object SHA-256 is
`6fcec61956537a632af27977c0b9660d96314792aca849cbf119e409a0b0216b`.
The normal native build uses Kotoba instruction words without an assembler.

## Bounded read-only pread control

`TMPDIR=/workspace/scratch ./check-macos-pread.sh` builds a Kotoba-emitted
macOS ARM64 diagnostic. Given an already opened character device on FD3 and
an eight-byte little-endian sector index on stdin, it checks the reported
block size (512 or 4096), block count, index and signed byte-offset bound;
it then reads exactly one sector with `pread` and writes it to stdout. It has
no path selection, identity, claim, consent, write or durability capability.
The test uses only its own read-only 4 MiB virtual image, compares three
512-byte sectors to independently generated bytes, and exercises missing,
short and out-of-range requests and invalid descriptors. The 4096-byte path
and physical devices have not been exercised by this control. Device geometry
is untrusted, and this test cannot establish device capacity.

The inert `pread-control-reference.txt` was derived on 2026-11-02 with Apple
clang 21.0.0 (clang-2100.1.1.101), `clang -target arm64-apple-macos -c
pread.s`, followed by `xcrun llvm-objdump --macho --disassemble`. The
reference SHA-256 is
`137d8b892dd72d3e0cebfbfae0235351ed971da5eba7d4489ecc184cfaa43d02`,
and the one-off object SHA-256 is
`2c3cb2fb3ed6ce4b88e8a385d02525bf25e8f43abe51308698130f3436ea92f8`.
Normal builds use the checked-in Kotoba words, not clang or an assembler.

## Guard candidate

This isolated pure Kotoba example models a small, fail-closed subset of the
host's target-bound destructive operation policy. It checks an eight-word
session/target/geometry/expiry/approval ticket against independently supplied
host observation, rejects internal, mounted and nonexclusive devices, consumes
one ticket and validates a bounded sector range and translates it to a byte offset and byte
count without overflowing signed 64-bit arithmetic. Session and identity components are opaque positive
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
actual selfhost native Kotoba program runs 28 positive/refusal assertions; three
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

## Fixed raw-device image control

`TMPDIR=/workspace/scratch ./check-macos-raw-fixture.sh` builds an Amu-native
macOS ARM64 test image. The harness constructs its own 4 MiB raw file, marks
its first sector, attaches it as a virtual disk, and independently checks its
current DiskImages backing-path/device association before opening it. The
native image accepts only a character FD reporting exactly 512-byte blocks and
8192 blocks and containing the eight-byte test marker at sector zero. It reads
that sector, writes it at byte offset 4096, calls `fsync`, reads back and
compares all 512 bytes. After detach the observer compares the complete backing
image against a separately constructed expected file. A read-only descriptor,
wrong marker, wrong geometry, regular-file FD and absent FD must refuse; the
negative backing files must remain byte-identical. Detach is attempted only
while the current image/device association matches; if it cannot be verified
or detach fails, scratch is retained for inspection.

This fixed control is **not a general raw-device provider or a trusted
approval**. Its deliberately narrow geometry and marker are not a secure
identity mechanism, nor a substitute for exclusive claim. The helper and
harness are for disposable virtual images only; do not pass a physical disk.
The `fsync` return and immediate readback do not prove cache bypass, device
persistence through reset, or power-loss behavior. It is not connected to the
policy candidate or the application and does not qualify either SSD.

The inert `raw-fixture-reference.txt` was derived once with Apple clang 21.0.0
(clang-2100.1.1.101), `clang -target arm64-apple-macos -c raw-control.s`, then
`xcrun llvm-objdump --macho --disassemble`. Its SHA-256 is
`35ef456fee6ebf0a8f18a1219b1256a47b48a12595e23acacefd8967fff965ec`; the
one-time object SHA-256 is
`7524aeea8f3e7f108adc50d55fb2c1767f308c8a4e68fde6b26e437ab3f617e3`.
The reference bytes are review material; native build/test use the checked-in
Kotoba instruction words, not clang, an assembler, C or a C loader. The
harness uses Python only to observe the current DiskImages attachment list for
safe test-device ownership and cleanup.

For a separate read-only diagnostic, `TMPDIR=/workspace/scratch
./build-macos-geometry.sh /absolute/new-output` builds and signs the same FD3
geometry control. It refuses an existing output. The caller chooses and opens
FD3; the image checks only that FD3 is a character device and that the two
read-only geometry ioctls succeed. It does not discover, identify, claim,
unmount or write a device, and it does not obtain authorization. Use outside
the isolated image test requires a separately scoped and reviewed host.

The raw-image gate also detaches the successful image and reattaches the same
backing file read-only. A separately generated Amu-native verifier then checks
the full 512-byte target sector. A fresh image with a corrupt byte after the
marker must be rejected and remain unchanged. This is a virtual-device
reattach test; it does not establish a hardware power cycle or bypass the
host/device caches.

The verifier's inert `raw-readback-reference.txt` was derived once with Apple
clang 21.0.0 (clang-2100.1.1.101), `clang -target arm64-apple-macos -c
raw-readback.s`, then `xcrun llvm-objdump --macho --disassemble`. The
reference SHA-256 is
`90161b17b0287824824e473036fcc8c6dc5539d77d749b959e356778854ed018`; the
one-time object SHA-256 is
`fa15bf0d33caf6b74f62971fac919ae1ea19836f370218679c5e6b0a6a6f1051`.
Native build/test use only the checked-in Kotoba words, not the reference,
clang, an assembler, C or a C loader.

## Native terminal-choice fixture

`TMPDIR=/workspace/scratch ./check-macos-tty.sh` builds an Amu-generated,
fixed-message macOS ARM64 executable. It makes sure stdin and stdout are
terminals with the same nonzero device number, displays a warning naming only
the marked 4 MiB **test fixture**, and accepts exactly `YES` plus newline.
An observer supplies synthetic PTY responses and verifies yes, no, extra input,
non-terminal pipes and different terminals. The executable performs no disk
I/O, creates no authorization grant and does not take a disk path or identity.
A PTY can be driven by another process: this is not evidence of a human choice
or a trusted approval, nor can the static message authorize a real device. It
is not linked to the disk writer, the guard or a native host.

The inert `tty-approval-reference.txt` was derived once using Apple clang
21.0.0 (clang-2100.1.1.101), `clang -target arm64-apple-macos -c
 tty-approval.s`, followed by `xcrun llvm-objdump --macho --section=__text
--full-contents`. The reference SHA-256 is
`d28c642a7b4813bec172310a80af79a2a393293c08a74b0c068ad7af1fa51cfa`;
the one-time object SHA-256 is
`ecec5d9b6d99cd3f21694a14db7f41e83a6b790fdda5c293ee59cb3f03a8ee93`.
The native build/test use checked-in Kotoba words, not the assembly reference,
clang, an assembler, C or a C loader. Python operates the synthetic PTYs and
observes the compiled program; it does not supply a real user decision.

## Combined choice and raw I/O fixture

`TMPDIR=/workspace/scratch ./check-macos-raw-choice.sh` builds a single
Amu-generated native executable that checks the fixed 4 MiB test geometry and
marker, verifies the input and output are the same terminal, presents the
fixed test-only warning, and accepts `YES` before its one fixed-sector write,
`fsync` and readback. On fresh task-owned virtual images, the test observer
injects `NO`, `YES`, and no-terminal cases through a PTY; denial or missing TTY
must leave the target sector zero. A successful write is followed by detach,
read-only reattach and the independent native full-sector verifier. Wrong
geometry, marker, read-only FD and corrupted readback are refusal controls.
The observer checks the temporary backing-image/device association before
opening FD3, and the harness checks the complete backing bytes and safe detach.

This is an integrated **fixture**, not an Itonami capability or a real user
approval. The PTY is controlled by a test process; equality of TTY devices
cannot prove a human chose `YES`. The message contains only the fixed test
identity, and the geometry/marker are not a physical-device identity or
exclusive claim. No application may use this as a production approval or pass
it a physical disk. `fsync` and virtual reattach do not establish physical
power-loss behavior or cache bypass.

The inert `raw-choice-reference.txt` was derived once using Apple clang 21.0.0
(clang-2100.1.1.101), `clang -target arm64-apple-macos -c raw-choice.s`, then
`xcrun llvm-objdump --macho --section=__text --full-contents`. The reference
SHA-256 is `8e63a67a2886ab9b7801630aa4c478031a890c577c9fede6118eb899aa52ec74`;
the one-time object SHA-256 is
`364579fc5a01ad1a7328775bde0e06e9de7d6bf85dac816cbf1a14ce19832b31`.
The build/test consume checked-in Kotoba words, not the reference, clang,
an assembler, C or a C loader. Python opens the verified test-image FD and
injects synthetic PTY input as a test observer only.

## Self-open read-only geometry control

`check-macos-open-geometry.sh` tests a separate Amu-generated image which
opens its sole pathname argument with `O_RDONLY | O_NONBLOCK | O_NOFOLLOW`,
requires a character device, and reads the two geometry ioctls. It emits no
user data and has no raw write calls. A read-only temporary disk image returns
512/8192; a final-component symlink, regular file, `/dev/null`, missing path
and absent argument refuse. Missing-path and symlink tests check the native
open errno separately. This test does not protect intermediate path components,
identify a physical device, establish exclusive access or authorize a write.
The device's geometry remains a self-report.

`build-macos-open-geometry.sh` builds the same signed test executable at a new
absolute output path. The caller is responsible for restricting and validating
any pathname before calling it. It is not a production broker.

The inert `open-geometry-reference.txt` was derived on 2026-11-02 using Apple
clang 21.0.0 (clang-2100.1.1.101), `clang -target arm64-apple-macos -c
open-geometry.s`, then `xcrun llvm-objdump --macho --disassemble`. Reference
SHA-256: `6daea4a9b650c13d946c7a4ffc463b02b12596528947fc8633539acddc40beda`.
One-time object SHA-256:
`a915a96cdaef59192bd0693050943e17e129c3e2ac5b309267ec98f26f1ee562`.
The native build/test consume checked-in Kotoba words, not clang, assembler,
C, a C loader or the inert reference. The temporary image is detached only
after an independent image-path/device association check.

## Multiple sample control

`TMPDIR=/workspace/scratch ./check-macos-raw-samples.sh` extends the combined
choice fixture to four fixed, aligned positions in its private 4 MiB virtual
image. The Amu-generated native code writes four address-tagged test blocks,
flushes, reads them and compares each complete 512-byte block. The harness
compares the entire backing image with independently staged expected bytes.
It also builds a deliberate mutation which forces all writes onto one offset;
the native reader must reject that mutation, and the observed image must match
that mutation's independently staged bytes. Synthetic `NO` and no-TTY cases
must leave all four sample sectors untouched. This is a deliberately injected
software alias, not a real counterfeit-controller measurement.

These fixed sample offsets and deterministic fixture tags do not implement the
F3 algorithm or establish the capacity or durability of any physical disk.
The fixture has no physical-device identity, exclusive claim or trusted human
approval. Never pass it a physical disk. PTY responses are injected by the test.

The inert `raw-samples-reference.txt` was derived once on 2026-11-02 using
Apple clang 21.0.0 (clang-2100.1.1.101),
`clang -target arm64-apple-macos -c raw-samples.s`, followed by
`xcrun llvm-objdump --macho --section=__text --full-contents`. Reference
SHA-256: `3a1ea9f1499252e0dfd0be11cd686043f278a5978dadfb9f286e57a841b1f8b6`.
One-time object SHA-256:
`8aed640e7b0389e6ee6fe0e0b39d88e93baf02d2f0c955c0756bdbd89bce3603`.
The checked-in Kotoba emits the native code; normal build/test do not execute
the reference, clang, an assembler, C or a C loader. Python stages independent
fixture bytes and drives synthetic PTY choices; it does not supply human consent.
