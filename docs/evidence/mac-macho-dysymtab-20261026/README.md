# Mac root Mach-O relocation-command repair

The `macos-15` CI [run #40235233442](https://github.com/kotoba-lang/amu/actions/runs/40235233442)
accepted the current 47-module source digest, then the signed root compiler
exited with signal 11 before compiling F1. Its narrow crash summary found
`EXC_BAD_ACCESS` at `0x48` in dyld's `forEachRebase_Relocations`, while reading
the executable's relocation metadata. The old unsigned wrapper had neither
`LC_DYSYMTAB` nor `LC_SYMTAB`. Apple's [Mach-O loader definitions](https://github.com/apple-oss-distributions/xnu/blob/main/EXTERNAL_HEADERS/mach-o/loader.h)
define both commands and require the symbol table when a dynamic symbol
table is present.

`seed/macos-fs2-runtime-packager.kotoba` now emits both commands with zero
offsets and counts because this image has no symbols or relocations. The
unsigned header has nine commands and 472 command bytes; macOS codesign adds
the tenth signature command. The Mac gate parses and requires exactly one
empty command of each kind before executing an image. The previous signed
root was rejected by that check.

The one-time [transition](transition.json) used the earlier checked-in Mac
compiler to compile the changed Kotoba packager source. The old-format
packager produced a temporary new-program image; that program produced a
new-format packager and then reproduced its own unsigned bytes exactly. The
new packager wrapped the same compiler raw bytes. The new signed root pins are:

- compiler: `e6c60547ae09ec750f1cb4da36099971fbedaa84064adb7c534c59cc94670e1d`
- packager: `ee9c89221aa7025b3eb2bf8fe3a44d554bfb9405d957e1048d2a5a1cbccd4452`

The [repository-default Mac gate](mac-selfhost.json) then passed F1=F2 with
unchanged compiler container
`8f932700219ccd15b9ac980db8f978084a11577831f3114e3842ec9da074a638`,
packager self-rebuild, user ELF and E7101 refusal. Its [queue receipt](mac-selfhost-queue.json)
records exit 0. The new roots were fed to AIUEOS #509's ordinary Mac entry:
[build](aiueos-build.json) and [private-QMP cold-restart gate](aiueos-qemu.json)
passed all 11 cases. The 8 MiB media retained SHA-256
`c7d4088475ac68944e5c28d94c206a74abf4063d08252545bfbfe89ffbc7671b`.
The unattended Itonami debug entered `a b` and checked guest state and
visible pixels; see [receipt](itonami-debug.json) and [screenshot](itonami-debug.png).
No VNC, guest password, NIC, Linux, JVM, Node or C compiler process was used
in these local gates.

The exact-source `macos-15` Apple Silicon [CI run #40235646430](https://github.com/kotoba-lang/amu/actions/runs/40235646430)
completed successfully: it staged the same 47-module source digest, produced
matching F1 and F2 container digests, rebuilt the packager, emitted the same
AIUEOS user ELF and exited 0. This closes the Mac root's current CI crash
gate, while the local AIUEOS boot and Itonami debug remain separate VM
evidence. Full native ARM/x86 integration,
registered Itonami agent turn, D2 workspace, release and physical hardware
remain separate open gates.
