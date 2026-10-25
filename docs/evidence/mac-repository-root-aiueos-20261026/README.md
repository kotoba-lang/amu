# Repository-local Mac bootstrap to AIUEOS diagnostic VM

This records the first root on the pre-`c9d13f3` Amu source. After merging
that newer `main`, the root was regenerated from the changed 47-module graph;
see [the current-main rerun](../mac-repository-root-main-c9d13f-20261026/README.md).

The candidate root in `seed/bootstrap/aarch64-macos/root.json` contains a
signed arm64 Amu full compiler and a signed Kotoba Mac packager. Both are
checked into this branch, with exact digests, source pins and no declared
dynamic library loads. They are diagnostic bootstrap images, not release
signatures or a general Darwin runtime qualification.

The compiler source combines Amu main `0ff0d4b23d26f482e045a3312a26a4cce6d1a6b7`
with the AIUEOS user target from PR #1574 head `a064a454a379705e9de1487efa6d0748415e1293`.
The packager source is byte-identical to
`seed/macos-fs2-runtime-packager.kotoba` in draft PR #1580 head
`fcf711f1ad9bc07518394a15eca00b6079667be3`.
The first Mac compiler/packager lineage in that PR had a one-time ARM Linux
producer bridge. These checked-in root images were subsequently emitted,
signed and self-rebuilt on Mac; this gate itself launched no Linux, JVM,
Node or C compiler process. That historical bootstrap is distinct from
ongoing Mac-only execution and from an independently trusted release root.

Starting from the repository root with no scratch executable input, the
Mac gate rebuilt the 47-module source at F1=F2. Its container SHA-256 was
`90b1c43c973108a6976b9f25c71d24b918e1bf35878be26ab7385278c03b61e0`.
The newly compiled packager repackaged itself byte for byte, and its
full-compiler unsigned output matched F2. The gate emitted the same
8,280-byte AIUEOS scalar user ELF as the earlier CPL3 QEMU fixture
(`7f5a8c0a31b5bdf191410f007973413d16e497a20ae7fe86c734b9fea85808b1`)
and refused undeclared `:io/write` with E7101 and no ELF. A wrong compiler
digest failed before output creation. See `mac-selfhost.json`,
`packager-bootstrap.json`, and their queue receipts.

The same repository-local images were passed to AIUEOS draft PR #509's
ordinary Apple Silicon desktop build entry with its exact source owners,
QEMU and OVMF pins. Kotoba/Amu native processes built font, 31-module
workspace kernel, EFI and 8 MiB GPT/FAT16 media. The exact media SHA-256
was `c7d4088475ac68944e5c28d94c206a74abf4063d08252545bfbfe89ffbc7671b`.
Private-QMP QEMU passed 11 local-draft commit, cold-restart and refusal
observations without VNC, password, network listener or manual guest keys.
The three PNGs show committed `ab`, cold-restored `ab`, and `abd` after
rejecting an orphan state. `aiueos-build.json` and `aiueos-qemu.json`
bind those observations to the root image digests.

To repeat the Mac selfhost gate from this checkout, use a new private output
directory under `github/workspaces/`:

```sh
python3 scripts/seed/native_build_queue.py --phase amu-mac-repository-root -- \
  python3 scripts/seed/check-aiueos-user-macos-native.py --output "$OUTPUT"
```

To repeat the AIUEOS build, use the `build-native-desktop-macos.py` entry
from AIUEOS PR #509, pass this checkout as `--amu-source`, and pass the
two `seed/bootstrap/aarch64-macos/*.macho` files and SHA-256 values from
`root.json` as compiler and packager. Also supply the canonical owner repo
root, digest-pinned QEMU/OVMF, a new output directory, and
`--profile local-draft`. The command's artifact roles and refusal checks
are recorded by that entry and `aiueos-build.json`.

This proves a Mac-hosted source-to-QEMU diagnostic path. It does not prove
the initial bootstrap without historical Linux, complete FS2 runtime or
native corpus, a registered Itonami user app or model/tool turn, D2 signed
workspace, trusted root distribution, release installation, or physical
hardware. PR #1574's ARM root/public compiler conflicts and exact-head CI
remain separate open gates.
