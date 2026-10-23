# Bounded kernel memory windows in the selfhost object route (ADR 0373) -- evidence, 2026-10-23

Host: macOS arm64, podman machine, linux/arm64 (and linux/amd64 for the x86 object
route check). No C compiler or loader in the lineage. Sources: this branch rebased on
origin/main b09d9635 (the combined compiler F of JUN-331, tiers pr/main/full); the root was
re-pinned to the new fixed point (db5c3467). A first pass of this evidence on 1585cb48 is
superseded: the independent review of 2026-10-23 (below) found defects, which are fixed here.

| check (rebased, F1 = db5c3467) | result |
|---|---|
| `selfhost-bootstrap.py --tier pr` | `PASS_LOADERLESS_SELFHOST_BOOTSTRAP pr F db5c3467feb660d0 root differs (re-pin to F1) adoption image 24 cases`; F1 = F2 |
| `check-kernel-memory.py` conformance | load 3676 runs / store 3676 / subregion 5028 / load-u32-16k 6176, 0 deviations, now also "no access before a trap" for reads |
| `--cases seed/tests/kernel-memory` | `PASS_KERNEL_MEMORY_ADMISSION 15 cases` |
| `--break` | the 16 condition-code mutants and six more (the 512 and 16384 bounds, the +4 of `index + 4` and of `length - index >= 4`, the lea displacement of load and store) are each seen red |

| the five current aiueos desktop objects (`browser-damage`, `-frame`, `-frame2`, `-ime`, `-reduce` of aiueos main 2026-10-23, one export renamed to its C symbol, `main` dropped) | compiled by F1 (db5c3467); `verify-kotoba-kernel-object.py` prints `AIUEOS_KOTOBA_OBJECT_OK` for each (sizes 15556, 9699, 85788, 105719, 49927 bytes) |

Review findings fixed: the stubs were taken for the store, subregion and 16 KiB load on the static route
(`M[197]` guard in `xk-intr`); the harness checked only writes before a trap; the mutant set was
condition codes only; ADR 0373 claimed more than the slice enforces (it now lists the three admitted shapes of
the first slice -- helper-parameter bases, an unrooted length, a literal base -- as "not claimed").

## First pass (superseded), 1585cb48

| check | result |
|---|---|
| `scripts/seed/selfhost-bootstrap.py` | `PASS_LOADERLESS_SELFHOST_BOOTSTRAP S2=S3 3b7872d4bfc9c0fa ... adopted G1=G2=G3 24 cases`; S1 = S2 = S3 |
| adopted core | G1 = G2 = G3 equal the adoption receipt: `seed/MANIFEST`'s sixteen files are unchanged |
| re-pinned root | the new `aarch64-linux-static-root.elf` (3b7872d4) compiles the selfhost unity to itself (root -> S1 == root) |
| `check-kernel-memory.py` (conformance) | load 3676 runs / store 3676 / subregion 5028 / load-u32-16k 6176, 0 deviations from the specification |
| `check-kernel-memory.py --break KIND-OP[-N]` | load-ja-1, load-ja-2, load-jz-1, load-jae-1, store-ja-1, store-ja-2, store-jz-1, store-jae-1, sub-jz-1, sub-ja-1, sub-ja-2, load16k-ja-1, load16k-ja-2, load16k-jz-1, load16k-jae-1, load16k-jl-1: each seen red |
| `check-kernel-memory.py --cases seed/tests/kernel-memory` | `PASS_KERNEL_MEMORY_ADMISSION 15 cases` (7 accepted, 8 refused E7106) |
| `check-x86_64-aiueos-object-cfree.py` | `PASS_LINUX_X86_CFREE_AIUEOS_KERNEL_OBJECT_ROUTE 8 objects 30 refusals` (static image and C-free runner byte-identical) |
| all five desktop objects (`browser-damage`, `-frame`, `-frame2`, `-ime`, `-reduce`; one export, C symbol) | compiled by the selfhost compiler; `verify-kotoba-kernel-object.py` OK for each |
| aiueos `guest-browser-maximize-control`, those five linked into KERNEL.ELF | exit 0 on QEMU (the longest chain; every stage before it must pass); every serial-only gate classifies exit 0 on that boot (15 profiles; `flow-parity` needs the hosted answer file and is not in this method) |
| aiueos `guest-browser-damage`, the damage object alone | exit 0 on QEMU: ops=211 text-px=2330 hash=5581e21a, bytes=1870144, screendumps identical to their whole-screen ones |

Not claimed: the other 107 of the 112 attested aiueos kernel objects, `kernel-region-report`, replacing
the shipped `browser-*.o` (an aiueos change: sources, provenance recipe, digests),
the whole Browser/CSSOM graph (`:browser-component` stays open).
