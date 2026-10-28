# ADR 0367 (DRAFT) — Seed targets beyond aarch64-macos: Linux and aiueos through the loader ABI, not new emitters

- Date: 2026-10-04 (agent SELF)
- Status: **Proposed (draft)**. Nothing in the tree depends on it; it decides the order of work once the seed builds the
  amu image (milestone (f), docs/selfhost-selfbuild-20261004.md).
- Related: ADR 0365 (opt-in seed backend), ADR 0366 (one packaged native entry, `nbb/x86_64_cli` carries the packagers),
  docs/selfhost-minimal-reach-20261002.md section 0 decision 1 (first 100% is aarch64-macos only),
  docs/selfhost-bootstrap-boundary-20261001.md, docs/selfhost-status-20261004.md 2.8.

## Context

The seed emits one thing: AArch64 code for the C loader's context ABI (context pointer in x7, runtime helpers through
context slots, fuel at `[x7,#8]`, capabilities through `typed_cap_call`; design section 2.2). On macOS that code runs
under `tools/kexe_loader.c` in command mode or packaged (`KEXE_EMBEDDED`, scripts/seed/package.sh).

The product still has targets the seed does not serve, so they go through nbb (boundary item (e) of the 2026-10-04
state): `aarch64-linux-static` and `aarch64-aiueos-kernel-v1` (route: `nbb/x86_64_cli` after ADR 0366, with the ELF64 /
PE32+ / linux-static packagers), plus every x86-64 target. Measured facts this draft rests on:

- the minimal reach set already cut the packagers out of the image (14 modules, 16.5k lines: `native/linux-static`,
  `native/elf64`, `object/elf64`, `object/pe32plus`, `packaging/pe32plus`, `verifier/linux-static`, ...);
- `tools/kexe_loader.c` (13,055 lines) already has `__linux__` branches (seccomp filter, `syscall`, `prctl`) next to the
  `__APPLE__` ones, and flushes the instruction cache with `__builtin___clear_cache`; it has not been built or run on
  Linux in this tree (no Linux host here: **E**);
- the seed has no x86-64 encoder (40-a64enc only).

## Options

| | what it is | new code (E) | keeps one seed backend? | risk |
|---|---|---|---|---|
| A. loader-ABI targets | the seed's AArch64 code unchanged; per OS a loader build: `aarch64-linux` = kexe_loader.c built for Linux (dynamic libc), `aarch64-linux-static` = the same loader linked statically (no libc at run time beyond what the static link carries) with the code embedded (`KEXE_EMBEDDED`), packaged by a seed-compiled packager that writes the ELF | loader port and CI on a Linux host ~0.5-1 kloc; an ELF writer in Kotoba ~1-2 kloc (or the existing `object/elf64` compiled by the seed) | yes | the static target today promises "no loader": A changes that contract (the loader becomes part of the executable). Needs an ADR amendment of the linux-static target definition |
| B. port the cut packagers | compile `native/linux-static`, `object/elf64`, `packaging/pe32plus` ... from source with the seed and call them in the image | 16.5k lines through the R6 scan (their walls unmeasured) | yes (the packager wraps big-backend code today: it would wrap seed code instead) | the packagers expect `machine_ir` output conventions (syscall stubs emitted by the big backend); unmeasured |
| C. seed emitters per OS | the seed itself emits syscall-based runtime code (no loader): a second runtime ABI in 41-a64gen | 3-6 kloc of seed code + a runtime in AArch64 | no (two runtime ABIs in one backend) | a third copy of the runtime semantics (fuel, traps, arenas) to keep identical |
| D. defer | keep nbb for these targets, labelled bootstrap; rule 11 counts aarch64-macos only | 0 | yes | the product path keeps node for two targets; the boundary count cannot reach 0 |

## Decision (proposed)

1. **D now, A next.** Until the seed builds the aarch64-macos amu image (milestone (f)), the Linux/aiueos targets stay on
   the nbb route, refused by name in any seed-built `amu` (`target <name> is not served by this build`), and labelled
   bootstrap in the boundary count. No seed module grows a second ABI.
2. Then **A for Linux**: one loader source, built per OS; the seed's code bytes are target-independent within AArch64.
   The first gate is the 19 Embench ports under a Linux-built loader (correctness exports = 1, same code bytes as macOS:
   the code must be byte-identical across OSes, which is a cheap, strong check of A's premise).
3. **aiueos-kernel** needs a freestanding runtime (no host OS under it): neither A nor B is enough by itself. It stays on
   D until a freestanding loader exists (the loader's runtime helpers without libc), which is its own ADR.
4. **x86-64** stays out (the minimal reach set's decision 1); a seed x86 encoder is not planned.

## Consequences

- The seed keeps exactly one emitter and one runtime ABI; target work is loader and packaging work, testable without
  touching the seed's fixed point (the seed's bytes do not change when a target is added).
- The `aarch64-linux-static` contract changes under A (a loader is inside the executable). If that is unacceptable, the
  fallback is B, measured first with selfbuild.sh's scan over the cut packagers (they are not in the reach list today).
- Until A lands, `bin/amu`'s nbb route for these targets is the only remaining node use on an aarch64 product path that
  the seed-built image cannot remove; the boundary page should count it under its own label, not as "progress".

## Open (to measure before accepting)

- Build `tools/kexe_loader.c` on an AArch64 Linux host and run the 19 ports from the seed's macOS-produced code bytes.
- Whether the seccomp policy of the Linux loader admits the seed's capability wires (35/37/38/39, never 20).
- The size of a Kotoba ELF writer (the cut `object/elf64` through the seed: walls unknown).
