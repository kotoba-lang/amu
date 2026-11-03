# Darwin FD-bound directory snapshot identity diagnostic

This separate fixed-function helper emits an ADI2 frame without changing the
existing ADI1 helper. It accepts only an already-open directory FD 3. One
`fstat64` reads the device and inode of that FD, the helper rewinds it, reads
at most 4096 bytes of dirent64 records and requires a second read to reach EOF.
The output is lowercase hex plus LF: `ADI2`, little-endian u32 record byte
length, zero-extended little-endian u64 device, little-endian u64 inode, then
the directory records. The receiver must check the process exit, full frame,
all record bounds and names, and compare identity with its own trusted open FD.

On one Darwin ARM64 Mac, a native diagnostic packager emitted a signed helper.
Its identity matched `fstat` of the supplied FD, including after an advanced
directory cursor. After renaming that directory and creating another at the
original path, the new FD had a different identity and the old open FD retained
its original identity. A regular-file FD, extra command-line argument and an
over-limit directory were refused. `verify.py` exercises these task-owned
fixtures and removes them; it requires a separately built helper.

This is identity metadata, not authentication, a lock, an atomic snapshot,
proof against inode reuse, or a verified recovery path. An untrusted caller
can forge both a frame and expected identity. A trusted host must obtain and
retain the FD and helper output, enforce exclusive ownership, bind its
filesystem reads and the inventory to that exact object, and handle failures.
No model, loader, recovery service, real deployment or resource governor was
run. ADI2 is a diagnostic local format, not a proposed external standard.

- Source SHA-256 `f38afc65c1d01cfe90f602f7d0331684730db60a0f0b4b77ee75fc7c6968a392`.
- Signed diagnostic packager `dbbe9a7bfa29e5b721d6cbd186db5dc280dc024b72d9067c1ad2dccac3f69648`; signed helper `8f8e63db8e32c532f650bb9504ae4dad29c1e7bff79baf6824339dd1b51746aa`.
- Compiler `920954769b8fdc51cf50dfcab5c44a4e56cf01f261806a153b21488ba81ac4e6`; diagnostic FS2 packager `4114499dc10bd321070a221f88847b8708565f7d80e87c4ed84b28e599e3c41e`.
