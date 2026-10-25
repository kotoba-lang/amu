# Mac Amu → AIUEOS kernel admission probe

The signed Mac F5 full compiler from the
[Mac-only continuation](../mac-full-selfhost-20261026/README.md) ran with a
private FD3 source directory. It emitted a 385,536-byte static x86_64 Linux
ELF from `seed/macos-utf8-main.kotoba`, SHA-256
`1e61a5c1f7593e174bd5b40b64dadf88e553aea3f5eda7b844e8a76af4196a8b`.
The pinned ARM Linux root emitted byte-identical ELF from the same source.
This is a target-codegen comparison, not an AIUEOS kernel or Linux-free
bootstrap qualification.

For the actual AIUEOS kernel graph, the source was staged from AIUEOS commit
`ec0ca6793819e05ed781438f6c167d171038ee99`. The kernel entry SHA-256
was `06adca9a324db5f6eb2b335a7a0af8de9859ca1e5db992a1b5692dd7e3ff0d0c`;
the owner dependency manifest SHA-256 was
`9c02cbbea836a3636f53bb78eac55c28cd2852aa4dd7c31bee4e109698ff1694`.
All 15 declared owner files matched their manifest hashes before staging.
Mac F5 `modules` completed with exit 0, discovering 15 modules. Its
[module list](modules.stdout) is SHA-256
`3dd1c58fd87f2cffd4e36478b9790f89d276bdab6e51b802d879e14af884c6ab`.

A KSL1 lock was constructed from that exact module list with the current
source hashes, relative entry and eight source roots. The
[lock](kernel.ksl) was 1,991 bytes, SHA-256
`cbcb077f4d9a8e54715073daa304f151003c155697985c5d42a5f5d72ce53d6b`.
Without the lock, `check` returned the expected E6015 unpinned-project
refusal. With the lock, the Mac diagnostic runtime stopped at image-relative
`0x31c0d8`, `brk #0x36`. LLDB read wire 35, request kind 8, response kind
8, vector handle 4, and the exact 16 item request
`NUL KSL1 NUL kernel.ksl`. The source-lock operation is the private
bounded byte request defined in `seed/02-io.kotoba`; the current Mac FS2
provider routes kind 8 to B/C only. The next runtime work is a scoped
regular-file KSL1 read with a one-MiB limit, exact read/EOF, status 0/1
response, and missing/symlink/type/size refusal controls. No AIUEOS kernel
compile or boot is claimed by this probe.
