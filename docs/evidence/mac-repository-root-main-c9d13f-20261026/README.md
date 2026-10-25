# Mac root regenerated for Amu main c9d13f3

This records the first root after merging `c9d13f3`. The subsequent
[macOS 15 dyld repair](../mac-macho-dysymtab-20261026/README.md) replaced its
Mach-O wrapper and signed images without changing the compiler container.

The Amu branch merged `origin/main` at `c9d13f39091e7fd7e62e0cbd6707f15c874dad2f`.
The 47 ordered modules in `seed/FULL-MANIFEST` now form a 3,462,309-byte
unity source with SHA-256
`60c49f2fb1a49175a3ad2a7efd5cd7bd21f68c5d91f3455663be9656e34006fd`.
The prior signed Mac compiler/packager built a new signed Mac root from that
source. The new checked-in compiler SHA-256 is
`26cab76fd0b791b5821b9c6b6572b424b6947ee0c4394dff683302b800d341b5`;
the packager remains
`dc165c5d899fbe895e70e9e75ca2edc62fa072a556276916792bba629b9c43e1`.
Both passed strict Mac code-signature verification and declared no dylib loads.

The [default root gate](mac-selfhost.json) passed again from only the
repository-local signed images, without explicit image arguments. F1=F2
container SHA-256 was
`8f932700219ccd15b9ac980db8f978084a11577831f3114e3842ec9da074a638`;
the Mac packager repackaged itself and the full compiler byte for byte before
signing. The gate emitted the 8,280-byte AIUEOS user ELF, refused undeclared
`:io/write` with E7101 and no ELF, and recorded native queue admission in
[mac-selfhost-queue.json](mac-selfhost-queue.json). This invocation launched
no Linux, JVM, Node or C compiler process. The historical first-root producer
lineage and release-trust limit are described in the [initial record](../mac-repository-root-aiueos-20261026/README.md).

Using that new root, AIUEOS draft PR #509's ordinary Mac entry built font,
31-module local-draft kernel, EFI and 8 MiB GPT/FAT16 media. The media SHA-256
remained `c7d4088475ac68944e5c28d94c206a74abf4063d08252545bfbfe89ffbc7671b`.
The [AIUEOS build receipt](aiueos-build.json) and [private-QMP cold-restart
receipt](aiueos-qemu.json) record 11 passing save, restore and refusal
observations with no VNC or NIC. The new one-command debugger also passed
`--goal 'a b'`, asserting the guest text and actual visible glyph pixels;
see its [receipt](itonami-debug.json) and [screenshot](itonami-debug.png).

To rerun the root gate, set `OUTPUT` to a fresh private workspace directory:

```sh
python3 scripts/seed/native_build_queue.py --phase amu-mac-root-default -- \
  python3 scripts/seed/check-aiueos-user-macos-native.py --output "$OUTPUT"
```

This is a source-bound diagnostic path. Exact-head native ARM/x86 CI, complete
Mac runtime corpus, initial bootstrap provenance, the actual registered
Itonami agent turn, D2 signed workspace, release and physical hardware remain
separate open gates.
