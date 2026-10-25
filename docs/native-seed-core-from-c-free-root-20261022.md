# The adopted compiler core from the C-free root (2026-10-22)

[ADR 0370](adr/0370-embench-measured-compiler-core.md) makes the 16-module
`seed/MANIFEST` core the compiler to grow. Its condition 3 asks for a
C/JVM/Node-free initial compiler from that lineage. Until this change, the
loaderless bootstrap reached the core's recorded fixed point only by running
`seed/bootstrap/adopted-20261012.bin` through the aarch64 runner. That payload was produced under the removed C
loader. The bootstrap now derives the core from source.

## Route

`scripts/seed/selfhost-bootstrap.py`, step 3:

1. S3, the Linux selfhost closure from the pinned root, compiles
   `seed/CORE-STATIC-MANIFEST` with `--target aarch64-linux --format static`.
   The result is C0, a static image of the core produced by the stack-machine
   emitter (about 6.6 MB).
2. C0 compiles `seed/MANIFEST` (`--target aarch64-macos`) and extracts
   `main`. The result is G1.
3. G1 and then G2 compile the same source through `R-aarch64.elf`, giving G2
   and G3.
4. The script requires G1 = G2 = G3 = `adoption-20261022.json`
   `nativeImageSHA256`. The first run (on adoption-20261017) reproduced
   `b10e3813…8a00`. After the wire-42 adoption round, it reproduced
   `9deed950…`.

`adopted-20261012.bin` is no longer an input. C0 compiles the core in about
32 minutes on an Apple-silicon arm64 Linux VM and over an hour on a hosted
arm64 runner, because C0's code is unoptimized. The core
payload it produces is the optimized one.

## Capacities

The stack-machine image of the core exceeds the AArch64 core's tables.
`seed/00-ns-static.kotoba` is `00-ns` with the static profile:

| Table | Core | Static profile |
| --- | ---: | ---: |
| `MM-CODE-CAP` | 655,360 | 2,097,152 |
| `MM-FIX-CAP` | 98,304 | 262,144 |
| `MM-LITB-CAP` | 262,144 | 524,288 |
| `MM-OUT-CAP` | 3,145,728 | 8,388,608 |
| `MM-WORDS` | 16,646,144 | 24,248,320 |

Later bases shift accordingly, and the heap size is unchanged. The Linux
selfhost closure and `CORE-STATIC-MANIFEST` use the static profile.
`seed/MANIFEST` keeps `00-ns`, so the core's source and payload identity are
unchanged. The bootstrap rejects any difference between the two namespace
files other than these constants.

M is above the old loader's limit of 2^24 items per vector, so the static
runtime (seeds 76 and 77) changes:

- `KXRT-VECTOR-MAX` is now 2^25.
- The `KXRT-ITEMS` arena is now 2^28 items. It is mapped with
  `MAP_NORESERVE` before `RLIMIT_AS` is applied. The core driver re-reads a
  module with a fresh M, and the arena is bump-allocated, so 2^27 was
  exhausted.

## Root re-pin

A compiler embeds its own runtime text in every image it builds. The previous
root's runtime therefore cannot allocate the wider M. The new root
`98d4bcb7…b774` was produced C-free as follows; the receipt records each hash:

1. The previous root (`f19ab1c4…`) built S1n from this source with the old
   capacities.
2. S1n built S2n, which carries the new runtime.
3. S2n built S3w from this source.
4. The chain reached S3w = S4w = S5w = the new root.

## What this does not claim

- C0 is not the product compiler. Its code comes from the stack-machine
  emitter, not the optimizing backend.
- The core's own output is still a payload that runs through the runner. The
  core does not yet emit a standalone static image of an optimized program.
- This change does not cover the rest of M2: one compiler with both the core
  and the Linux targets, and the public CLI and project graph.
