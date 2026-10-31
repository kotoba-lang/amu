# Plain emitters: inline vector, pair and string access, a register cache, short constants and flat runtime paths (2026-10-28/29)

Local diagnostic evidence for one source change, made in two rounds. No score,
no quiet-host timing, no native CI verdict: the selfhost-native workflow
(arm64 and x86_64 kernels, no emulation) and the macOS gate remain the
qualification.

## Why (what Goose does that these emitters did not)

[Goose](https://aardappel.github.io/goose/) gets its speed from its memory
model rather than from a cleverer optimizer: no allocator calls (growth is a
pointer bump on a data stack), flat inline data, bounds checks emitted inline
next to the access and removed when provable, and whole-program compilation
in which nothing is a call that need not be.

Amu's adopted AArch64 core (`seed/41-a64gen`) already works this way: vector
reads and writes are inline, descriptor-checked loads and stores, pair reads
and a code-relative string's ASCII bytes are read in line (the R4 rule), T2
keeps values in registers, and the measured Embench kernels are
hand-scheduled. The two *plain* stack-machine emitters did not:

* `seed/70-71` (x86_64) called the runtime through the context table for every
  `vector-at`, `vector-assoc!`, `count`, `pair-first`, `pair-second`,
  `string-length` and `string-code-point-at`, and for every item of a vector
  literal. Each helper was itself a chain of naive calls
  (`kxrt-vector-at` -> `kxrt-vlen` -> `kxrt-vec` -> `kxrt-gl` -> `kxrt-g`;
  `kxrt-code-point-at` -> `kxrt-ps`, `kxrt-saddr` (-> `kxrt-span`, `kxrt-pf`,
  `kxrt-ps`), `kxrt-valid` -> `kxrt-pair` -> `kxrt-gl` ...).
* `seed/80` (aarch64-linux static, runner and packed images) did the same, and
  materialised every constant with four `movz/movk` words.
* Both stored every value to its frame slot and loaded it back for the very
  next instruction.

These emitters matter more than their size suggests. The x86_64 one compiles
the public x86_64 product (`bin/amu`, now `bin/amu-linux-x86_64`) itself, the CDCI roles (the adopted core as an
x86 static image is the `amu-selfhost` gate) and every x86 guest, including
the Embench ports on the x86 route. The aarch64 one compiles the runtime that
every C-free aarch64-linux image runs on, the selfhost Embench route included: on
that route aha-mont64 spent about 55% of its instructions in the runtime's
vector allocator (`[hi lo]` tuples), about 800 instructions and 21 calls per
two-item allocation. On the x86 route slre spent about 88% of its
instructions in the string helpers (`(at s i)` = `string-length` +
`string-code-point-at` per character).

## The change

Round 1 (2026-10-28):

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

Round 2 (2026-10-29), for slre's string path:

* **Inline pair reads** (`seed/71`, `seed/80`): `pair-first` (64) and
  `pair-second` (72, which is also `string-length` and `string-byte-length`)
  use the same handle check from the v11 words 288 (&pair-used) and 296
  (pairs), then load the word. `xr-desc`/`xa-desc` take the two context
  offsets, so the vector bytes are unchanged.
* **R4 string reads** (`seed/71` `xr-cpa`, `seed/80` `xa-cpa`):
  `string-code-point-at` follows the rule 41-a64gen already uses
  (`gn-rt-cpa`, `seed/SIR :a64 :r4`): when the pair is valid, its offset is
  code-relative (>= 0), its length >= 0, `i <u length` and
  `offset + length <= code_length` (word 392), the byte at code_base (word
  384) + offset + i is returned in line if it is below 0x80. Every other case
  (a pool string, a non-ASCII byte, an index or handle out of range) calls the
  helper, which checks, validates and refuses exactly as before. A
  code-relative string is valid UTF-8 by construction (seed/HEADS, R4 rule),
  so the only thing skipped is the helper's "validated" mark, which nothing
  observes. The explicit length-sign check is stricter than 41-a64gen's. Contract text:
  `seed/X86_64-LINUX-ABI`, "Inline pair and string access".
* **Flat string helpers** (`seed/76` = `seed/77` text): `kxrt-pair`,
  `kxrt-span` and `kxrt-code-point-at` read their globals through one `G`
  (or one context) with the inline intrinsics; `kxrt-code-point-at` reads the
  pair once and takes the validated fast path in line. Same checks, order and
  refusal. These serve pool strings and every route whose guest still calls
  the helper.

Both rounds:

* **Pins**: the new images are the fixed points of the new source. Every x86
  static image changed, so the native Kotoba gate's 192 case-image hash words
  (`seed/cdci/kotoba-gate.kotoba`; source, result, exit and fuel words
  unchanged), the controller's gate pins (`seed/cdci/controller.kotoba`), the
  two role source hashes (`seed/79-native-cdci.kotoba`) and
  `seed/cdci/policy.json` (roles marked as needing fresh native
  qualification) follow, with the root, product and macOS source-phase
  descriptors.
* **SIR budget**: every whole-compiler build counts against `MM-SIR-CAP`, and
  the identity-resource gate's producer (FULL-MANIFEST without its entry, plus
  the native test modules) went from 151 (x86 target) / 133 (aarch64 target)
  spare dummy functions on main to none with these emitter paths (E3001). The
  emitters' fixed instruction runs are now constant tables read through
  OP-TAB (`xr-run`, `xa-run`; byte-identical output), and the static profile
  grows only its SIR capacity, as it grew TOK, NODE, LITB and OUT before:
  `seed/MEMORY-MAP` gains `[:s MM-SIR-CAP 589824]` (+98,304 records, MM-WORDS
  31,457,280 < 2^25), `seed/gen-static-ns.kotoba` requires that seventh row,
  and `seed/00-ns-static.kotoba` is its native output. The normal adopted
  `seed/00-ns.kotoba`, the core source and container, the heap size and every
  guest image are unchanged; the amu-selfhost role (built from
  `seed/CORE-STATIC-MANIFEST`, which uses the static namespace) has a new
  image that still compiles `seed/MANIFEST` to `0efb5556…`. With it the
  producer has room for 992 more dummy functions on the x86 target (at least
  160 on both targets; the first limit is then E101 region 6, not SIR), against
  151 on main before this change. Main landed the same capacity change on its
  own as #1670 (JUN-556). After that merge, this change no longer differs from
  main in `seed/MEMORY-MAP`, `seed/gen-static-ns.kotoba`,
  `seed/00-ns-static.kotoba` or `scripts/seed/selfhost-bootstrap.py`. The
  generator reproduces `seed/00-ns-static.kotoba` byte for byte from main's
  row order.
* **Check**: `scripts/seed/check-inline-vectors.py` with
  `seed/inline-vector-cases.json` (39 programs x 2 fuel budgets x 2 targets:
  19 vector programs from round 1, 16 string and 4 pair programs from round 2;
  expectations recorded from the helper-call compiler `aa021865…`), run on
  both native ISA jobs of `selfhost-native.yml`. The string programs cover
  literals, multi-byte UTF-8 lead and continuation bytes, the index at the
  length, -1, i64 max and min, the empty string, pool strings, substring
  views (in range and one past the view inside the parent), string ops after
  an in-line read, arena-scope rollback and fuel exhaustion inside a string
  loop; the pair programs take handles 0, past the end and negative.

## What was checked locally

Host: Linux x86_64 (4 vCPU, shared). AArch64 runs used qemu-user 8.2.2 built
locally with two test-only patches (`seccomp(2)` accepted without installing a
filter, `openat2(2)` passed through); this is measurement tooling outside the
build closure and does not qualify anything.

* Fixed points: x86_64 F1 = F2 = F3 = `bin/amu-linux-x86_64` (`92b3078e…`, 8,647,168
  bytes; round 1 `f8332459…`, 8,593,920; base 9,458,176); aarch64 packed root
  F1 = F2 (`2238db15…`, 3,580,416 bytes; round 1 `172f588b…`, base 3,625,472)
  with container `20fb958c…`, derived under qemu from a round 2 candidate
  root (itself derived from the round 1 root) after main's #1666, #1559 and
  #1672 were merged;
  the x86_64 compiler that root emits is byte-identical to `bin/amu-linux-x86_64`, and so
  are its x86 images of the 24 pinned cases.
* Re-derived after main's #1662 (the AIUEOS object route's extern functions
  in `seed/74`, a FULL-MANIFEST module): x86_64 F1 = F2 = F3 = `9c8cd664…`
  (8,663,552 bytes); aarch64 root F1 = F2 = `867ba03c…` (3,588,608 bytes),
  container `f89c8f3a…`, derived under qemu from the `2238db15…` root. The
  x86_64 compiler that root emits is again byte-identical. The new compiler
  emits the same 19 x86_64 kx64 payloads and aarch64 containers as
  `92b3078e…`, and the same three CDCI role images, so the measurements below
  stand. Its kernel-object output for #1662's extern cases is byte-identical to
  main's compiler.
* Re-derived again after main's #1674 through #1691. Those changes touched
  `seed/74` (data cells, MMIO intrinsics, record windows) and `seed/75` (the
  static runtime calls only runtime functions, JUN-336).
  * x86_64: F1 = F2 = F3 = `a0148782…` (8,663,552 → 8,704,512 bytes).
  * aarch64 root: F1 = F2 = `de33395b…` (3,604,992 bytes), container
    `f7d32abf…`, derived under qemu from the `867ba03c…` root. The x86_64
    compiler it emits is byte-identical to the native fixed point.
  * Unchanged: the 19 x86_64 kx64 payloads, the aarch64 containers and the
    three CDCI role images.
  * The kernel-object sources of the cells, globals, MMIO, records, externs and
    exports gates give results identical to main's compiler (7 objects, 7
    refusals).
  * `check-runtime-boundary` passes, including JUN-336's shadow refusals, so the
    flat runtime helpers call only runtime functions.
* Re-derived again after main's #1671 and #1693.
  * #1671 (JUN-578): the adopted core's SHA-256 crypto-hardware option. It
    changes `seed/41-a64gen`, the core source/container pins (`5b12da97…` /
    `74de9bf3…`) and the controller's core words.
  * #1693: `seed/74` cell addresses.
  * x86_64: F1 = F2 = F3 = `c2635f7b…` (8,704,512 bytes).
  * aarch64 root: F1 = F2 = `ba40652f…` (3,604,992 bytes), container
    `37441725…`, derived under qemu from the `de33395b…` root. The x86_64
    compiler it emits is byte-identical to the native fixed point.
  * CDCI:
    * The amu-selfhost gate rebuilt from the merged
      `seed/CORE-STATIC-MANIFEST` is `9d49b122…`, and it rebuilds
      `seed/MANIFEST` to main's `74de9bf3…`.
    * The kotoba-native gate (`06ddfe88…`) is unchanged.
    * The controller (`da225b80…`) carries the new pins.
    * A local `check-native-cdci` full run passes (24 cases, 18 refusals,
      parent-death cleanup), as do `check-complete-x86` and
      `check-public-native-product`.
  * The 19 x86_64 kx64 payloads are unchanged. 18 of the 19 aarch64
    containers are unchanged. `nettle-sha256` now uses the SHA-256 crypto
    instructions by default; with `--no-crypto-hw` (the C-equivalent benchmark
    setting) its container is byte-identical to the measured one.
* Re-derived again after main's #1695 (JUN-556 E, extern calls with up to
  eight arguments). It changed `seed/74` and lifted the profile-0 call-arity
  limit in `seed/70` from 5 to 8. This change's runtime-profile paths leave
  profile 0 unchanged.
  * x86_64: F1 = F2 = F3 = `e3e019fe…` (8,708,608 bytes).
  * aarch64 root: F1 = F2 = `9914c0ea…` (3,604,992 bytes), container
    `65b31b85…`, derived under qemu from the `ba40652f…` root. The x86_64
    compiler it emits is byte-identical.
  * Unchanged: the CDCI role images; the 19 x86_64 payloads; the 19 aarch64
    containers built with `--no-crypto-hw`; and all 60 kernel-object gate
    sources, identical to main's compiler.
  * `check-complete-x86`, the full `check-native-cdci` and
    `check-public-native-product` pass again.
* Re-derived again after main's #1697 (JUN-595), a core change in
  `seed/41-a64gen`. Its core pins are `1a80ca12…` / `7ec9181f…`.
  * x86_64: F1 = F2 = F3 = `74cd256f…` (8,708,608 bytes).
  * aarch64 root: F1 = F2 = `6722a5bc…` (3,604,992 bytes), container
    `8c46912d…`, derived under qemu from the `9914c0ea…` root. The x86_64
    compiler it emits is byte-identical.
  * CDCI:
    * The amu-selfhost gate rebuilt from the merged core is `cf3cd7d5…`, and
      it rebuilds `seed/MANIFEST` to main's `7ec9181f…`.
    * The kotoba-native gate is unchanged.
    * The controller image is `99d41c35…`.
  * Unchanged: the 19 x86_64 payloads and the 19 aarch64 containers built
    with `--no-crypto-hw`.
  * The local `check-complete-x86`, the full `check-native-cdci` and
    `check-public-native-product` pass.
* Re-derived again after main's #1700 (JUN-556, exports take up to eight
  parameters), a core change in `seed/21-check`, `seed/41-a64gen` and
  `seed/90-drv` (core pins `ee282502…` / `b73d1961…`), and #1702, #1704 and
  #1706 (`.bss` arrays and window accesses on the object route, `seed/74`).
  * x86_64: F1 = F2 = F3 = `8e1530e7…` (8,729,088 bytes).
  * aarch64 root: F1 = F2 = `87996f7e…` (3,613,184 bytes), container
    `3a8ea308…`, derived under qemu from the `6722a5bc…` root. The x86_64
    compiler it emits is byte-identical.
  * CDCI:
    * The amu-selfhost gate rebuilt from the merged core is `e24347fe…`, and
      it rebuilds `seed/MANIFEST` to main's `b73d1961…`.
    * The kotoba-native gate is unchanged.
    * The controller image is `b1e21d6c…`.
  * Unchanged: the 19 x86_64 payloads, the 19 aarch64 containers built with
    `--no-crypto-hw`, and all 91 kernel-object gate sources (11 gates),
    identical to main's compiler.
  * The local `check-complete-x86`, the full `check-native-cdci` and
    `check-public-native-product` pass.
* Re-derived again after main's #1699, #1712, #1714 and #1716 (aiueos boot,
  object route and desktop sources: `seed/74`, `78`, `84`, `86`, `91`, `95`,
  `97`).
  Following ADR 0388 (#1709), the merge restored main's pin files and every
  Linux pin was regenerated from the merged source; `sourceRevision` stays
  `null`.
  * x86_64: F1 = F2 = F3 = `5e6484f1…` (8,774,144 bytes).
  * aarch64 root: F1 = F2 = `7f88b254…` (3,641,856 bytes), container
    `4a6895ba…`, derived under qemu from the `eccf892f…` root (itself the
    fixed point before #1712). The x86_64 compiler it emits is
    byte-identical.
  * Unchanged: the CDCI images (amu-selfhost `e24347fe…`, controller
    `b1e21d6c…`, kotoba-native `06ddfe88…`), the 19 x86_64 payloads, the 19
    aarch64 containers built with `--no-crypto-hw`, and all 99 kernel-object
    gate sources (13 gates), identical to main's compiler.
  * The local `check-complete-x86`, the full `check-native-cdci` and
    `check-public-native-product` pass.
* Re-derived again after main's #1718 (JUN-633, scalar SSE floats on the
  aiueos object route, ADR 0391), which changed `seed/70` itself. Its float
  dispatch in `xg-bin` / `xg-cmp` conflicted with this change's `xg-pair`; the
  merge keeps both (floats first, then the integer path through `xg-pair`).
  The float paths respect the rax cache: their operand reads are emitted
  bytes, which clear it, and every result reaches its slot through `xg-save`
  with rax equal to the stored value. Floats are admitted only on the object
  route, never in the runtime profile.
  * x86_64: F1 = F2 = F3 = `2750d271…` (8,786,432 bytes).
  * aarch64 root: F1 = F2 = `e3d6c64e…` (3,645,952 bytes), container
    `d9e238a2…`, derived under qemu from the `7f88b254…` root. The x86_64
    compiler it emits is byte-identical.
  * Unchanged: the CDCI images, the 19 x86_64 payloads, the 19 aarch64
    containers built with `--no-crypto-hw`, and all 107 kernel-object gate
    sources (14 gates, including the 8 f32 sources), identical to main's
    compiler.
  * The local `check-complete-x86`, the full `check-native-cdci`,
    `check-public-native-product` and the x86 inline-access corpus pass.
* Re-derived again after main's #1726 and #1727 (JUN-633 slices 4 and 5:
  halt-until-interrupt and the spin-wait hint on the object route,
  `seed/74`).
  * x86_64: F1 = F2 = F3 = `0bc6fcd3…` (8,790,528 bytes).
  * aarch64 root: F1 = F2 = `25d9b0e5…`, container `01e9eef7…`, derived
    under qemu from the `de5d67d0…` root (the fixed point after #1726). The
    x86_64 compiler it emits is byte-identical.
  * Unchanged: the CDCI images, the 19 x86_64 payloads, the 19 aarch64
    containers built with `--no-crypto-hw`, and all 111 kernel-object gate
    sources (16 gates, including the halt and spin-wait gates), identical to
    main's compiler.
  * The local `check-complete-x86`, the full `check-native-cdci`,
    `check-public-native-product` and the x86 inline-access corpus pass.
* Re-derived again after main's #1711 (KOTOBA-173, capability declaration
  names: a core change in `seed/60-proj` and `seed/90-drv`, core pins
  `ec6b3422…` / `62fe99b8…`), #1728 (JUN-584: the native definition-identity
  layer, `seed/04`-`09` and `05-definition-report`, joins FULL-MANIFEST, now
  59 modules), #1729 and #1731 (wasm32-browser) and #1730 (JUN-633 slice 6:
  fused f32 reductions on the object route, `seed/74`).
  * x86_64: F1 = F2 = F3 = `1efce79b…` (9,220,608 bytes), from the
    3,811,672-byte unity `89fd4fe0…`.
  * aarch64 root: F1 = F2 = `702760f7…` (3,846,656 bytes), container
    `f4b6cd0b…`, derived under qemu from the `25d9b0e5…` root. The x86_64
    compiler it emits is byte-identical.
  * CDCI:
    * The amu-selfhost gate rebuilt from the merged core is `1b34f224…`; the
      previous and the new compiler build it identically, and it rebuilds
      `seed/MANIFEST` to main's `62fe99b8…`.
    * The kotoba-native gate is unchanged (`06ddfe88…`).
    * The controller image is `44fe9af0…`.
  * Unchanged: the 19 x86_64 payloads and the 19 aarch64 containers built
    with `--no-crypto-hw`. All 133 kernel-object sources (the 17
    `check-aiueos-object-*` gates including fused-dot, its evidence sources
    and the 12 `seed/tests/kernel-memory` dot cases) compile identically to
    main's compiler.
  * The local `check-complete-x86`, the full `check-native-cdci`,
    `check-public-native-product`, the identity-resource gate and the x86
    inline-access corpus pass.
* Re-derived again after main's #1735 (JUN-633, ADR 0398: aarch64 f32 -> i64
  traps as on x86, a core change in `seed/41-a64gen`, core pins `7ebbac8b…` /
  `d18d5eda…`), #1732 (JUN-633 slice 7: f32 -> i64 truncation, `seed/70` op 37
  and `seed/74`) and #1733 (KOTOBA-174, ADR 0396: `--format host-entry` in
  `seed/75`/`76` and the new derived pin `bin/x86_64-linux/amu`).
  * `seed/70` and `seed/76` merge without conflict. Op 37 keeps the rax cache
    invariant: its operand read is emitted bytes, which clear the cache, and
    its result reaches the slot through `xg-save` with rax equal to the stored
    value. The host start finds the standard start's argument-vector line
    exactly once in this change's `seed/76`.
  * x86_64: F1 = F2 = F3 = `7695a1d9…` (9,228,800 bytes), from the
    3,816,887-byte unity `abba47b5…`. Its `--format host-entry` image
    `bin/x86_64-linux/amu` is `b42c01e1…` (9,228,800 bytes).
  * aarch64 root: F1 = F2 = `8198e87c…` (3,850,752 bytes), container
    `fecf5924…`, derived under qemu from the `702760f7…` root. The x86_64
    compiler and host entry it emits are byte-identical.
  * CDCI:
    * The amu-selfhost gate rebuilt from the merged core is `6d610126…`; the
      previous and the new compiler build it identically, and it rebuilds
      `seed/MANIFEST` to main's `d18d5eda…`.
    * The kotoba-native gate is unchanged (`06ddfe88…`).
    * The controller image is `f6e86336…`.
  * Unchanged: the 19 x86_64 payloads and the 19 aarch64 containers built
    with `--no-crypto-hw`. All 139 kernel-object sources (the 18
    `check-aiueos-object-*` gates including f2i, their evidence sources and
    the 12 `seed/tests/kernel-memory` dot cases) compile identically to
    main's compiler.
  * The local `check-complete-x86`, the full `check-native-cdci`,
    `check-public-native-product`, `check-host-default-target --isa x86_64
    --reproduce`, the identity-resource gate and the x86 inline-access corpus
    pass.
* Re-derived again after main's #1738 (JUN-600, ADR 0399: bounded MSR
  read/write and PCI data-port input on the object route, `seed/74`).
  * x86_64: F1 = F2 = F3 = `d0238a74…` (9,232,896 bytes), from the
    3,822,974-byte unity `9de4a952…`. Its `--format host-entry` image is
    `02d1ae3b…` (9,236,992 bytes).
  * aarch64 root: F1 = F2 = `6e62d382…` (3,854,848 bytes), container
    `6bc8ae13…`, derived under qemu from the `8198e87c…` root. The x86_64
    compiler and host entry it emits are byte-identical.
  * Unchanged: the CDCI images (amu-selfhost `6d610126…`, controller
    `f6e86336…`, kotoba-native `06ddfe88…`), the 19 x86_64 payloads and the
    19 aarch64 containers built with `--no-crypto-hw`. All 154 kernel-object
    sources (the 19 `check-aiueos-object-*` gates including msr, their
    evidence sources and the 12 kernel-memory dot cases) compile identically
    to main's compiler.
  * The local `check-complete-x86`, the full `check-native-cdci`,
    `check-public-native-product`, `check-host-default-target --isa x86_64
    --reproduce` and the x86 inline-access corpus pass.
* Re-derived again after main's #1734 (JUN-701: route B2 on aarch64-linux,
  `--format b2` in `seed/80` and `xa-rt-b2` in `seed/77`), which changes the
  two aarch64 modules this change rewrites.
  * Both merge without conflict. The new code keeps the x9 cache invariant:
    the E2 loads and stores load through `xa-lt` and emit through `xa-w`
    (which ends the cache), store x10 (which never claims it), and the ccall
    loads x16 through the cache-aware loader. The b2 start sets the v11
    context words 288..328 the inline vector and pair access read.
  * `check-b2-image.py` passes with this branch's compiler: x86_64 build and
    run (8 runs); aarch64-linux build, and the run phase under qemu-user, where
    only the misaligned-caller control cannot fault (qemu does not emulate
    SCTLR_EL1.SA0) and the other 7 runs, including both fuel checks, pass.
    The inline-access corpus passes on aarch64-linux (39 cases, 78 runs).
  * x86_64: F1 = F2 = F3 = `02ad3dbd…` (9,249,280 bytes), from the
    3,833,354-byte unity `6cff518f…`. Its `--format host-entry` image is
    `d92a906b…` (9,253,376 bytes).
  * aarch64 root: F1 = F2 = `30bcee14…` (3,863,040 bytes), container
    `2c79a263…`, derived under qemu from the `6e62d382…` root. The x86_64
    compiler and host entry it emits are byte-identical.
  * Unchanged: the CDCI images, the 19 x86_64 payloads, the 19 aarch64
    containers built with `--no-crypto-hw`, and all 154 kernel-object sources
    (19 gates), identical to main's compiler.
  * The local `check-complete-x86`, the full `check-native-cdci`,
    `check-public-native-product`, `check-host-default-target --isa x86_64
    --reproduce` and the x86 inline-access corpus pass.
* Native x86_64 rehearsal of the CI tail (the arm64 proof was a local
  stand-in): `check-complete-x86` F1=F2=F3, `check-native-cdci`
  PASS_NATIVE_KOTOBA_CDCI (24 cases, 18 refusals, parent-death cleanup),
  `check-public-native-product`, `check-native-kotoba-early`,
  `check-native-identities`, `check-static-profile-native`, the four
  source-identity gates (checked-source, source-vectors, identity-resource,
  definition-effects; identity-resource also with the aarch64 root under
  qemu), the io-read/durable-sleep/spawn/private-store/sleep-resume runtime
  checks and all 17 x86 gate-plan groups (including the zero-watermark and
  runtime-profile mutation gates, whose source anchors name the flat
  allocator text).
* All 24 pinned runtime cases (`seed/static-cases.json`) pass as static images
  on both targets, with the x86_64 static compiler and with the new aarch64 root.
* `check-inline-vectors.py`: PASS on both targets (156 runs), with the x86_64 static compiler
  and with the new aarch64 root.
* The 19 Embench-derived ports (`bench/embench/reproduce-20261015/ports`,
  `bench-verify` through the native runner): result 1 with **identical total
  fuel and all 17 arena counters** to the base compiler on both routes, in
  both rounds. The aarch64 payload bytes (a64gen) are unchanged for all 19.
* The CDCI roles rebuilt by the new compiler: the `amu-selfhost` gate still
  compiles `seed/MANIFEST` to the pinned core container `0efb5556…`.

## Measurements (diagnostic only)

`measurements.json` holds every row (result, fuel, arena counters, metric for
base, round 1 and round 2).

| series | metric | round 1 / base | round 2 / base | round 2 / round 1 | exact |
| --- | --- | --- | --- | --- | --- |
| x86_64 route, native, n/128 | runner CPU seconds | 0.167 | **0.149** (6.7x faster) | 0.892 | 19/19 |
| x86_64 route, n/1024 | instructions executed | 0.219 | **0.195** | 0.890 | 19/19 |
| aarch64 route (a64gen payloads), n/16 | instructions executed | 0.982 | 0.982 | 1.000 | 19/19 |

Geomeans over the 19 ports. "exact" = result 1 with the same total fuel and
all 17 arena counters as the base compiler. The CPU column is one serial
process with the three builds interleaved per workload (round 1 and round 2
the minimum of three runs, base one run); on this shared host a single run
can be off by tens of percent, and only the instruction counts are
deterministic.

* x86_64, round 1: the largest gains are on the vector-heavy ports (CPU
  nsichneu 0.043, huffbench 0.076, matmult-int 0.082, xgboost 0.085 of base;
  instructions nsichneu 0.078, huffbench 0.104, matmult-int 0.124); crc32 is
  scalar table code (CPU 0.86) and slre stayed in the string helpers (CPU
  0.68, instructions 0.870).
* x86_64, round 2: **slre** goes from 2.46 G to 0.35 G instructions (0.141 of
  round 1, 0.122 of base) and from 2.83 s to 0.31 s CPU (0.110 of round 1,
  0.075 of base); xgboost 0.772 and qrduino 0.998 of round 1 in
  instructions; the other 16 ports execute exactly the same instruction count
  as in round 1 (their CPU times move within noise).
* aarch64: only the runner's runtime changes on this route, and the a64gen
  payloads already read pairs and code-relative strings in line, so none of
  the 19 ports calls the flattened string helpers: round 2 leaves every count
  unchanged to the instruction. Round 1's allocator path moved
  allocation-heavy aha-mont64 (0.712; the runtime part per two-item
  allocation went from about 800 to about 440 instructions); slre 0.989.

Compiler work on x86_64 (wall clock, same host):

| work | base | round 1 | round 2 |
| --- | --- | --- | --- |
| the x86_64 static compiler compiles `seed/FULL-MANIFEST` to x86_64 static (self-compile) | 37.9 s, 36.6 s | 11.8 s, 11.9 s (11.6 s, 11.7 s on the round 2 source) | 8.6 s, 8.5 s |
| the `amu-selfhost` CDCI gate compiles `seed/MANIFEST` (same container `0efb5556…`) | 429.0 s | 65.8 s, 63.5 s | 60.1 s |
| compile the 19 Embench ports (x86_64, sum) | 10.2 s | 2.4 s | 2.0 s |

The `amu-selfhost` gate is the adopted core compiled by this emitter; CI
recorded 1,036.4 s for the same step on the base image
(`docs/evidence/x86_64-core-static-20261023`).

Since KOTOBA-170 (#1669) `bin/amu` is the macOS ARM64 entry and the x86_64 static
compiler is `bin/amu-linux-x86_64`; "bin/amu" in `measurements.json` names the
x86_64 static compiler of its time.

## Not claimed

* Not an Embench score, official or translated: no C arm, one shared host, and
  the AArch64 numbers are emulated instruction counts.
* The adopted core and its measured M104 lineage (`seed/MANIFEST`,
  `seed/41-a64gen`) are unchanged. On macOS (the M104 host) neither the
  payloads nor the Mac packager runtimes change; on aarch64-linux the payloads
  are byte-identical and only the runtime's allocator and string helper paths
  change.
* The R4 fast path relies on the R4 rule (string literals are valid UTF-8 by
  construction, and `(pair a b)` yields an `i`, never a `:string`), as
  41-a64gen already does. A pool string, or any string that is not
  code-relative, always takes the helper.
* Stack use per helper call drops; a program that overflowed the stack still
  traps the same way, but a recursion close to the limit can now go deeper.
