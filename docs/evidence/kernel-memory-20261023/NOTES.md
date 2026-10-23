# Bounded kernel memory windows in the selfhost object route (ADR 0373) -- evidence, 2026-10-23

Host: macOS arm64, podman machine, linux/arm64 (and linux/amd64 for the x86 object
route check). No C compiler or loader in the lineage. Sources: this branch on
origin/main 1585cb48.

| check | result |
|---|---|
| `scripts/seed/selfhost-bootstrap.py` | `PASS_LOADERLESS_SELFHOST_BOOTSTRAP S2=S3 1bc6f4ce58b7bc30 ... adopted G1=G2=G3 24 cases`; S1 = S2 = S3 |
| adopted core | G1 = G2 = G3 equal the adoption receipt: `seed/MANIFEST`'s sixteen files are unchanged |
| re-pinned root | the new `aarch64-linux-static-root.elf` (1bc6f4ce) compiles the selfhost unity to itself (root -> S1 == root) |
| `check-kernel-memory.py` (conformance) | load 3676 runs / store 3676 / subregion 5028, 0 deviations from the specification |
| `check-kernel-memory.py --break KIND-OP[-N]` | load-ja-1, load-ja-2, load-jz-1, load-jae-1, store-ja-1, store-ja-2, store-jz-1, store-jae-1, sub-jz-1, sub-ja-1, sub-ja-2: each seen red |
| `check-kernel-memory.py --cases seed/tests/kernel-memory` | `PASS_KERNEL_MEMORY_ADMISSION 13 cases` (6 accepted, 7 refused E7106) |
| `check-x86_64-aiueos-kernel-object-cfree.py` | `PASS_LINUX_X86_CFREE_AIUEOS_KERNEL_OBJECT_ROUTE 8 objects 30 refusals` (static image and C-free runner byte-identical) |
| `browser-damage.kotoba` (one export, C symbol name) | compiled by the selfhost compiler, `verify-kotoba-kernel-object.py` OK, same bytes from the S3 and S4 generations |
| aiueos `guest-browser-damage`, that object linked in | exit 0 on QEMU: ops=211 text-px=2330 hash=5581e21a, bytes=1870144, five screendumps identical to their whole-screen ones |

Not claimed: the other `browser-*.kotoba` objects (other operations, tiers),
`kernel-region-report`, replacing the shipped `browser-damage.o`, the whole
Browser/CSSOM graph (`:browser-component` stays open).
