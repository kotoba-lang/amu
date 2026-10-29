# Plain emitters: inline vector access, a register cache, short constants and a flat allocator path (2026-10-28)

Local diagnostic evidence for one source change. No score, no quiet-host
timing, no native CI verdict: the selfhost-native workflow (arm64 and x86_64
kernels, no emulation) and the macOS gate remain the qualification.

## Why (what Goose does that these emitters did not)

[Goose](https://aardappel.github.io/goose/) gets its speed from its memory
model rather than from a cleverer optimizer: no allocator calls (growth is a
pointer bump on a data stack), flat inline data, bounds checks emitted inline
next to the access and removed when provable, and whole-program compilation
in which nothing is a call that need not be.

Amu's adopted AArch64 core (`seed/41-a64gen`) already works this way: vector
reads and writes are inline, descriptor-checked loads and stores, T2 keeps
values in registers, and the measured Embench kernels are hand-scheduled. The
two *plain* stack-machine emitters did not:

* `seed/70-71` (x86_64) called the runtime through the context table for every
  `vector-at`, `vector-assoc!` and `count`, and for every item of a vector
  literal. Each helper was itself a chain of naive calls
  (`kxrt-vector-at` -> `kxrt-vlen` -> `kxrt-vec` -> `kxrt-gl` -> `kxrt-g`).
* `seed/80` (aarch64-linux static, runner and packed images) did the same, and
  materialised every constant with four `movz/movk` words.
* Both stored every value to its frame slot and loaded it back for the very
  next instruction.

These emitters matter more than their size suggests. The x86_64 one compiles
the public product `bin/amu` itself, the CDCI roles (the adopted core as an
x86 static image is the `amu-selfhost` gate) and every x86 guest, including
the Embench ports on the x86 route. The aarch64 one compiles the runtime that
every C-free aarch64-linux image runs on, the selfhost Embench route included: on
that route aha-mont64 spent about 55% of its instructions in the runtime's
vector allocator (`[hi lo]` tuples), about 800 instructions and 21 calls per
two-item allocation.

## The change

* **Inline vector access** (`seed/71`, `seed/80`): `vector-at`, `vector-assoc!`
  and `count` read the v11 context words 312 (&used), 320 (descriptors) and 328
  (items) and emit the helpers' own checks in their order: handle
  `(h - 1) <u used`, index `i <u length`, failure = the helpers' refusal (`ud2`
  / `udf #0`, SIGILL). A fresh `VEC`/`VECP` vector receives its items by direct
  stores inside its own descriptor's view (the zero-highwater invariant holds).
  Contract text: `seed/X86_64-LINUX-ABI`, "Inline vector access".
* **Register cache** (runtime profile only): `M[190]` = the frame displacement
  whose word rax (x9 on aarch64) holds, `M[191]` = `CODE-N` right after the
  store or load that made it so. Every emitted byte and every `LABEL` clears
  it, so it only describes the fall-through point straight after that
  instruction; a reload there is dropped, or becomes `mov r, rax`. Binary
  operations and compares load the second operand first when the register
  already holds it. Profiles 0 and 2 (scalar ELF, kernel objects, Kototama)
  never use it and emit unchanged bytes.
* **Short constants** (`seed/80`, runtime profile): `movz` for 0..65535 and
  `movn` for -65536..-1; four words otherwise and for every fixup.
* **Flat allocator path** (`seed/76`, `seed/77`, one template):
  `kxrt-vector-alloc` and `kxrt-vnew` read and write their globals through
  one `G` with the inline `kxrt-load64`/`kxrt-store64` intrinsics instead of
  the `kxrt-gl`/`kxrt-gs`/`kxrt-item` call chains. Same checks, writes and
  order; the descriptor/highwater/region-map writes are unchanged.
* **Pins**: the new images are the fixed points of the new source. Every x86
  static image changed, so the native Kotoba gate's 192 case-image hash words
  (`seed/cdci/kotoba-gate.kotoba`; source, result, exit and fuel words
  unchanged), the controller's gate pins (`seed/cdci/controller.kotoba`), the
  two role source hashes (`seed/79-native-cdci.kotoba`) and
  `seed/cdci/policy.json` (roles marked as needing fresh native
  qualification) follow, with the root, product and macOS source-phase
  descriptors.
* **Check**: `scripts/seed/check-inline-vectors.py` with
  `seed/inline-vector-cases.json` (19 programs x 2 fuel budgets x 2 targets,
  expectations recorded from the helper-call compiler `aa021865…`), run on both
  native ISA jobs of `selfhost-native.yml`.

## What was checked locally

Host: Linux x86_64 (4 vCPU, shared). AArch64 runs used qemu-user 8.2.2 built
locally with two test-only patches (`seccomp(2)` accepted without installing a
filter, `openat2(2)` passed through); this is measurement tooling outside the
build closure and does not qualify anything.

* Fixed points: x86_64 F1 = F2 = F3 = `bin/amu` (`67612009…`, 8,593,920
  bytes, was 9,458,176); aarch64 packed root F1 = F2 (`5bc428f0…`, 3,568,128
  bytes, was 3,625,472) with container `64562138…`, derived under qemu from the
  previous root through an interim candidate; the x86_64 compiler that root
  emits is byte-identical to `bin/amu`.
* Native x86_64 rehearsal of the CI tail (the arm64 proof was a local
  stand-in): `check-complete-x86` F1=F2=F3, `check-native-cdci`
  PASS_NATIVE_KOTOBA_CDCI (24 cases, 18 refusals, parent-death cleanup),
  `check-public-native-product`, `check-native-kotoba-early`,
  `check-native-identities`, the io-read/durable-sleep/spawn/private-store/
  sleep-resume runtime checks and all 17 x86 gate-plan groups (including the
  zero-watermark and runtime-profile mutation gates, whose source anchors now
  name the flat allocator text).
* All 24 pinned runtime cases (`seed/static-cases.json`) pass as static images
  on both targets.
* `check-inline-vectors.py`: PASS on both targets (76 runs).
* The 19 Embench-derived ports (`bench/embench/reproduce-20261015/ports`,
  `bench-verify` through the native runner): result 1 with **identical total
  fuel and all 17 arena counters** to the previous compiler on both routes.
  The aarch64 payload bytes (a64gen) are unchanged for all 19.
* The CDCI roles rebuilt by the new compiler: the `amu-selfhost` gate still
  compiles `seed/MANIFEST` to the pinned core container `0efb5556…`.

## Measurements (diagnostic only)

`measurements.json` holds every row (result, fuel, arena counters, metric).

| series | metric | new / old (geomean, 19 ports) | exact |
| --- | --- | --- | --- |
| x86_64 route, native, n/128 | runner CPU seconds | **0.170** (5.9x faster) | 19/19 |
| x86_64 route, n/1024 | instructions executed | 0.219 | 19/19 |
| aarch64 route (a64gen payloads), n/16 | instructions executed | 0.982 (aha-mont64 0.712, slre 0.989, others 1.000) | 19/19 |

"exact" = result 1 with the same total fuel and all 17 arena counters as the
previous compiler. On x86_64 the largest gains are on the vector-heavy ports
(nsichneu 0.047, huffbench 0.078, xgboost 0.077, matmult-int 0.081); crc32
(0.83) is scalar table code and slre (0.76) spends most of its time in string
helpers, which this change does not touch. On aarch64 only the runtime's
allocator changes, so only allocation-heavy aha-mont64 moves (the runtime
part per two-item allocation went from about 800 to about 440 instructions).

Compiler work on x86_64 (wall clock, same host):

| work | old | new |
| --- | --- | --- |
| `bin/amu` compiles `seed/FULL-MANIFEST` to x86_64 static (self-compile) | 37.9 s, 36.6 s | 11.8 s, 11.9 s |
| the `amu-selfhost` CDCI gate compiles `seed/MANIFEST` (same container `0efb5556…`) | 429.0 s | 65.8 s |
| compile the 19 Embench ports (x86_64, sum) | 10.2 s | 2.4 s |

The `amu-selfhost` gate is the adopted core compiled by this emitter; CI
recorded 1,036.4 s for the same step on the old image
(`docs/evidence/x86_64-core-static-20261023`).

## Not claimed

* Not an Embench score, official or translated: no C arm, one shared host, and
  the AArch64 numbers are emulated instruction counts.
* The adopted core and its measured M104 lineage (`seed/MANIFEST`,
  `seed/41-a64gen`) are unchanged. On macOS (the M104 host) neither the
  payloads nor the Mac packager runtimes change; on aarch64-linux the payloads
  are byte-identical and only the runtime's allocator path changes.
* Stack use per helper call drops; a program that overflowed the stack still
  traps the same way, but a recursion close to the limit can now go deeper.
