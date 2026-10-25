# Amu-emitted Darwin root-FD control

This diagnostic moves the earlier Darwin `openat` control into an
Amu-produced executable. It is a step toward the native FS2 provider, **not**
the provider itself. No wire 35 frame is parsed here and the full compiler
still cannot run `check` or `compile` on macOS.

`seed/macos-openat-control-packager.kotoba` packages three 16 KiB arm64
Mach-O images from Kotoba byte and instruction literals. The pinned Amu native
AArch64 root (`285c54f826d5f7f77db6827bc21c622c2c777cea252a1ba4816d8b01351807e1`)
compiled this packager twice byte-identically in a network-disabled Linux
container. The packager then emitted strict, without-beneath, and
without-no-follow-any images. No C compiler, assembler, or libSystem is in
that image-production path. The prior assembly source was used once to derive
and review the instruction words, but was not an input to this build.

The independent [observer](../../../scripts/seed/check-macos-openat-kotoba-probe.py)
checks the source literal against each Mach-O's actual text bytes, the
unchanged bytes outside the two negative-control instructions, the repeated
Amu build, and the lack of dylib loads. It ad-hoc signs copies and executes
them as macOS processes. The [receipt](receipt.json) records 11 cases:

| Result | Actual process result |
| --- | --- |
| Within granted directory, including a nested file | Reads `K`, exits 42 |
| File or directory symlink | `ELOOP` (62) |
| `../` or absolute path | `ENOTCAPABLE` (107) |
| Missing file, missing grant, regular file used as root grant | `ENOENT` (2), `EBADF` (9), `ENOTDIR` (20) |
| Remove `O_RESOLVE_BENEATH` or `O_NOFOLLOW_ANY` | Corresponding escape reads `K`, exits 42 |

Reproduction on Apple Silicon macOS, from this worktree, uses a fresh task
scratch directory. The pinned root may need its normal capability grant for
the read-only repository and the selected output directory. After building
`packager.elf`, repeat the same compile through the native build queue to
`packager-repeat.elf` and retain its admission JSON. Run the packager with
`KEXE_CAP_RESOURCES_35` restricted to the output directory for each mode:

```sh
packager.elf strict.macho strict
packager.elf no-beneath.macho no-beneath
packager.elf no-nofollow.macho no-nofollow
python3 scripts/seed/check-macos-openat-kotoba-probe.py \
  --artifacts "$ARTIFACTS" --output "$NEW_OBSERVATION"
```

The producer is still an AArch64 **Linux** root running in a local container;
it does not qualify the requested Linux-free Mac selfhost closure. The
diagnostic also assumes that an explicit root directory grant arrives at FD
3. The product runtime must wire this to capability admission, validate the
complete FS2 frame and kind, bound allocations and responses, check file type
and size, and implement D/A reads and B/C writes. Those behaviors need a
separate full-compiler readback and refusal suite before any selfhost claim.
