# Durable file replace and sleep in the static runtimes (JUN-359, JUN-360)

Two more runtime forms in `seed/76-x86_64-static-rt.kotoba` and
`seed/77-aarch64-static-rt.kotoba`. murakumo needs them for its lease voters'
state, its topology replica's file, and its proposer's backoff.

## Wire 35: `FSYNC_SEP` and `RENAME_SEP` (JUN-359)

The capability catalog already defines both forms (`:fs/app-data` `:forms`);
the selfhost static runtimes refused them until now.
- **`<path>FSYNC_SEP`** opens the file or directory beneath the scope, as
  every wire-35 open does, and fsyncs it. It answers `"1"` once `fsync(2)`
  returned, and `"0"` when the path cannot be opened or the flush fails.
  Bytes after the token trap.
- **`<from>RENAME_SEP<to>`** opens each parent directory beneath the scope
  and renames the last component with `renameat(2)`. So no component of
  either path is followed out of the scope. It answers `"1"` once
  `renameat` returned, and `"0"` otherwise: outside the scope, a parent
  that leads out of it, or a missing file.

Together with `WRITE_SEP` they replace a file durably: write a temporary,
fsync it, rename it over the file, then fsync the directory. `fsync` and
`renameat` were already in the scope's seccomp set.

## Wire 7: `sleep <ms>` (JUN-360)

`:clock/now` (#1518) answers `wall` and `monotonic`. It now also takes
`sleep <ms>`, with ms decimal 0..60000:
- **The sleep.** It is `clock_nanosleep(CLOCK_MONOTONIC)` for that long,
  resumed with the remaining time after EINTR.
- **The answer.** It is the monotonic reading after the sleep, as for
  `monotonic`.
- **Traps.** Anything else traps.
- **Seccomp.** The filter admits `clock_nanosleep` only with wire 7 granted.

With wire 23 `:entropy/draw` for the jitter, a static image can back off
for a random time.

## Verification

Measured on 2026-10-23 on arm64 Linux, in the podman machine. No C compiler
or loader, no hosted compiler and no emulation were used. Receipts are in
[`evidence/durable-sleep-20261023/`](evidence/durable-sleep-20261023/).

- **The root** (`root-chain.json`).
  1. The previous root (`048244b3…`) compiled `seed/FULL-MANIFEST` from this
     source to F1.
  2. F1 rebuilt itself to F2, with the same container and a new runtime
     wrapper.
  3. F2 rebuilt itself to F3 = F2, which is pinned as `88afda89…`.
- **`selfhost-bootstrap.py --tier main`** from the new root
  (`selfhost-bootstrap-main.json`) passes:
  - F1 = root;
  - the core route gives the adoption image;
  - the runtime boundary corpus, the 24 runtime cases, hardening and
    capabilities, and wasm32-browser;
  - G2 = G3 = G1 through the aarch64 runner;
  - P rebuilds the core;
  - the Linux selfhost closure rebuilds itself.
- **`check-durable-sleep.py`** (new; `durable-sleep.json`), 9 cases:
  - **The replace.** A guest writes, fsyncs and renames a file, then reads
    `hello` back, and the temporary is gone. It renames a file over an
    existing one and over a file in another directory of the scope, and
    fsyncs the scope directory.
  - **`"0"` with nothing moved.** Fsync of a missing file, a rename of a
    missing file, a rename to outside the scope, and a rename through a
    symlink that leads out of the scope.
  - **Traps.** Bytes after `FSYNC_SEP`.
  - **Sleep.** The monotonic reading after `sleep 200` is at least 200 ms
    later, and `sleep 0` works. `sleep 60001`, `sleep 1x`, `sleep ` and an
    ungranted wire each trap.
  - **Controls.** A compiler without fsync in the scope's seccomp set, and
    one without `clock_nanosleep`, each die of SIGSYS.
- **Regressions with the new root.** `check-io-read.py` passes its 12 cases.
  `check-spawn-runtime.py` passes its 18 grant and 31 wire cases.

## Open

- **x86_64 execution.** The x86_64 runtime carries the same change with
  its own numbers: fsync 74, renameat 264, clock_nanosleep 230, and its own
  `O_` flags. It is cross-built only. Running it needs an owner-approved
  host (JUN-316/317/318).
- **Durability across a power cut.** What is checked is that `fsync`
  returned, not what the device did.
- **A sleep interrupted by a signal.** It resumes with the remaining time,
  but no case delivers a signal.
