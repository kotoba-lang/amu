# ADR 0371: Static images reach the GPU through a separate provider process

Date: 2026-10-22
Status: Decision 1 (the platform boundary) accepted by the owner on 2026-10-22.
The rest is Proposed. Wire 42 is not admitted until security integration signs
off (Decision 7). Steps 1 (the protocol table) and 2 (the runtime transport)
are implemented; nothing else is.
Tracking: JUN-285 (this ADR), JUN-291 (step 1), JUN-294 (step 2). Related: JUN-109 (wire 42 admission), JUN-282
(`amu run` on static images), JUN-283, AWAI-12 (murakumo inference on Amu
selfhost).

## Context

### What the loader removal left

PRs #1458, #1459 and #1460 removed the C loader and its GPU brokers
(`tools/kexe_gpu_vulkan.c`, `tools/kexe_gpu_metal.m`). Programs now run as
loaderless static images (`--format static`, runtime `seed/76` for x86_64 and
`seed/77` for aarch64). As a result, `:gpu/compute` (wire 42) has no route at
any layer:

* **Checker.** The seed admits wires 3 20 23 33 34 35 37 38 39 41
  (`seed/21-check.kotoba`, `ck-wire-ok`). Wire 42 is named
  (`seed/21-check.kotoba:5294`) but refused with E2115.
* **Runtime.** The static runtime serves wires 35, 37, 38 and 39 only. Any
  other id reaches `kxrt-fail` (`seed/76-x86_64-static-rt.kotoba`,
  `kxrt-typed-cap-call`).
* **Sandbox.** The seccomp filter has no `ioctl`, `futex` or `clone`, and no
  `mmap` after start. RLIMIT_AS is 64 MiB once the arenas are mapped.
* **Processes.** The image is one process. It has no IPC and no knob for
  inherited file descriptors.

`docs/c-loader-removal.md` listed the brokers as removed. It did not list
`:gpu/compute` as refused. This ADR adds that entry.

### What the removed broker did

The broker ran in the loader's supervisor process, never in the sandboxed
guest. The reason, from its header: a Mesa or NVIDIA driver needs `ioctl`,
`mmap`, `futex`, threads and other syscalls the guest is not admitted.

* **Transport.** Two pipes, made before the fork and only when the grant named
  wire 42. Each message was a u32 little-endian length followed by the bytes.
* **Protocol.** One ASCII request line per call:
  * `INFO`, `DEVCLASS`
  * `ALLOC`, `MAP <path> <offset> <length>`, `WRITE`, `WRITEDEC`, `READ`
  * `PIPELINE <spv-path> <bindings>`
  * `BEGIN`, `BEGINK`, `DISPATCH`, `DISPATCHC`, `SUBMIT`, `REPLAY`
  * `DROP`, `ZERO`, `FREE`
* **Handles.** Each one is the lowest free slot, counting from 1. Generated
  guests hard-code these numbers.
* **Refusals.** An answer starting with `!` is a refusal. The guest turned it
  into an unnamed SIGILL.
* **Timing.** `SUBMIT`, `REPLAY` and a lone `DISPATCH` answer host
  `CLOCK_MONOTONIC` nanoseconds from submit to fence. The evidence of
  kotoba-lang/inference and murakumo `bench` is built on this number.

The broker also had defects that must not be carried forward:

* **Any readable file was reachable.** `MAP` and `PIPELINE` accepted any path
  the unsandboxed supervisor could read. Together with `READ`, a guest could
  read any such file back. This contradicts the capability catalog's own
  rationale, "nor this grant open files for the guest to read".
* **No byte cap.** `ALLOC` and `MAP` had no limit. Driver time in the
  supervisor was bounded only by wall time.
* **Unnamed refusals.** Every refusal became a bare SIGILL.
* **SIGPIPE.** A guest killed mid-request could raise SIGPIPE in the
  supervisor.
* **`INFO` field count.** `INFO` answered 4 fields. ADR 0355 says 5.

### Constraints

* `docs/selfhost-priority.md`:
  * Rule 2: only a selfhost-built compiler is selfhost evidence.
  * Rule 3: "Do not pin a C loader as the solution".
  * Rule 5: fail closed.
  * CDCI uses only `x86_64-linux-static`.
* ADR 0001, Phase 5: "Treat model parsing and vendor drivers as hostile
  boundaries isolated from the verifier and supervisor."
* ADR 0240: `:aiueos-c-free-bare-metal-v1` requires an empty receipt for
  dynamic dependencies.
* AIUEOS ADR 0222 keeps GPUs on the Linux boxes and refuses porting Vulkan.
* **No platform boundary is defined.** Nothing in this repo says whether the
  host's GPU driver is a platform or a legacy dependency. On every fleet host
  the userspace driver is C, C++ or Objective-C, and it needs libc and threads:
  * Mesa ANV and RADV
  * NVIDIA nvgpu on L4T
  * Metal.framework

  No Kotoba program can reach these GPUs without executing that driver, short
  of writing a new driver per vendor.

### Hosts to serve

| Host | OS / ISA | GPU / driver |
| --- | --- | --- |
| aiueos-6600hs-1 (B70) | Ubuntu 24.04, x86_64 | Intel Arc Pro B70, xe + Mesa ANV |
| gad | Linux, x86_64 | Radeon 8060S, RADV |
| aiueos-k16, aiueos-6600hs-2 | Linux, x86_64 | Radeon 680M, RADV |
| xavier | L4T R35.4.1, aarch64 | Jetson AGX Xavier, NVIDIA Vulkan 1.3 |
| main-2 (M1 Max), 10 Mac minis (M4) | macOS, aarch64 | Metal (MoltenVK also measured) |

## Decision

### 1. The vendor GPU driver is a platform boundary, reached only from a provider process

Two parts of the declared host are platform, in the same class as the kernel:

* the kernel GPU driver;
* the vendor's userspace driver stack, which is the Vulkan loader with its
  ICD, or Metal.framework.

Neither is a C loader, C runtime or build dependency of Amu. Exactly one
artifact class may load them: the GPU provider (Decision 3). The provider:

* is never part of the compiler or selfhost closure;
* never runs in CDCI;
* is never accepted for `:aiueos-c-free-bare-metal-v1`.

**Accepted by the owner on 2026-10-22.** Before this, `docs/selfhost-priority.md`
had no platform boundary, and without one no GPU route existed on any fleet
host. That document now states the boundary and points here.

### 2. Three processes, one direction of authority

```text
launcher (static, C-free)          reads the grant, owns wall time, writes the receipt
 ├─ guest (static image)           decides everything; sealed by seccomp
 │     fd A ──request──▶ ┐
 │     fd B ◀──answer─── ┤
 └─ provider (platform-linked)     owns the device; decides nothing
```

* **Guest.** The existing static image. It never maps a device, never loads a
  library, and gains no `ioctl`, `mmap`, `futex` or `clone`. For it, wire 42 is
  a transport: write one framed request to fd A, read one framed answer from
  fd B.
* **Provider.** A Kotoba program compiled by Amu selfhost into a
  platform-linked executable (Decision 5). It executes verbs. Every decision
  stays in the guest, as the capability catalog already requires: which kernel,
  which shape, what to sample.
* **Launcher.** The C-free static runner that replaces `amu run` (JUN-282). It:
  1. creates the two pipes;
  2. spawns the provider and the guest;
  3. passes each one its fds;
  4. kills both when wall time expires;
  5. joins their reports into one run receipt.

  Neither child spawns anything.

The provider runs once per run, not as a shared node daemon. One provider per
run keeps GPU memory private to one guest. It also keeps `socket` and `connect`
out of the guest's filter.

### 3. Wire-42 protocol v1 stays byte-compatible for guests

The framing, verb set, handle numbering, `!` refusal prefix and the meaning of
`SUBMIT` do not change. Existing generated guests (inference
`gen_decode_tokens_guest`, murakumo's `:kotoba-native` engine) need no change,
and the evidence stays comparable.

The protocol's reference moves from C into Kotoba: one `.kotoba` decision table,
`tools/gpu_compute_protocol.kotoba`, holds the grammar, bounds and refusal
names. Both the provider and the runtime tests use it.

Only the broker's defects change:

* **Artifact table.** `MAP` and `PIPELINE` keep their path argument, but the
  provider resolves it only against an artifact table that the launcher passes
  in. Each entry has a path, a SHA-256 and a kind (`:model`, `:spirv` or
  `:msl`). The provider checks the digest before first use. Any other path is
  refused by name. Guests that pass the same paths keep working; the grant
  decides which files.
* **Named refusals.** An answer is `!<code> <text>`. The guest runtime still
  traps (exit 120). Before the trap it writes one stderr line that names the
  refusal: `KEXE_TRAP {:kind :capability :wire 42 :refusal :<code>}`. Codes
  live in the decision table.
* **Byte cap.** The grant bounds the total device bytes (`ALLOC` plus `MAP`).
  A request over the cap is refused, not attempted.
* **Answer bound.** An answer never exceeds the runtime's value bound
  (`KXRT-VALUE-MAX`, 8 MiB). The provider refuses a `READ` that would exceed
  it, instead of sending a frame the guest cannot hold.
* **Timeouts.** The fence timeout per submit comes from the grant (default
  60 s). `VK_ERROR_DEVICE_LOST` or a timeout gives a named refusal, and then
  the provider exits. There is no device recovery.
* **SIGPIPE.** The provider ignores SIGPIPE. End of file on fd A means the
  guest is gone, and the provider tears down.
* **`INFO`.** `INFO` keeps its 4 fields and device class stays in `DEVCLASS`.
  ADR 0355 is corrected to match.

### 4. Guest runtime changes (`seed/76`, `seed/77`)

* **New knob.** `KEXE_CAP_RESOURCES_42=<request-fd>,<answer-fd>`, named like
  `KEXE_CAP_RESOURCES_35`. Before the sandbox, `fstat` checks both:
  * each must be a FIFO or a socket;
  * each must be fd 3..1023, and the two must differ.

  If wire 42 is in `KEXE_ALLOW` and the knob is missing or invalid, the image
  exits 2. It fails closed.
* **Dispatch.** `kxrt-typed-cap-call` gains `42` for the string kind only.
* **Seccomp.** The filter stays derived from the grant, as the fs set is today.
  When wire 42 is granted and both fds are valid, it adds one rule: `read`,
  allowed only when `args[0]` is the answer fd. `write` is already in the base
  set. Nothing else is added.
* **Memory.** Answers are interned into the string pool, which is already
  mapped. RLIMIT_AS does not change.
* **SIGPIPE.** When wire 42 is granted, the runtime ignores SIGPIPE. A provider
  that is gone then gives EPIPE, and the call traps (exit 120) instead of the
  process dying of a signal.

### 5. The provider

* **Source.** Canonical Kotoba, compiled by the selfhost compiler. No C source,
  no C compiler and no C runtime object (`crt1.o`) is involved.
* **Entry.** Amu emits `_start`, which calls the host libc's
  `__libc_start_main`. The driver therefore runs with libc initialized, the
  same way it would under any program. The import is resolved by the host's
  dynamic linker at run time.
* **New compiler output.** A `--format platform-linked` ELF writer, first for
  x86_64 SysV:
  * `PT_INTERP` and `PT_DYNAMIC`;
  * `DT_NEEDED` entries;
  * GOT relocations, bound now (`BIND_NOW`, RELRO).

  It also needs a typed C-ABI import declaration. Pointers are `:i64`, and
  Vulkan structs are laid out byte by byte in Kotoba.
* **Import allowlist.** The compiler checks it:
  * `libc.so.6`: `__libc_start_main` only. The provider's own I/O uses raw
    syscalls.
  * `libvulkan.so.1`: `vkGetInstanceProcAddr` only. Every other Vulkan entry
    point is resolved through it.

  The dynamic-dependency receipt is therefore two libraries and two symbols.
* **Confinement.** The guest's filter does not apply to the provider, so the
  provider confines itself after device creation:
  * a Landlock ruleset limits reads to the artifact table plus the files the
    driver has already opened;
  * a seccomp filter denies `execve`, `fork` and non-AF_UNIX `socket`, and
    admits `clone` only with `CLONE_THREAD`;
  * the driver's shader cache is disabled, or pointed at a per-run scratch
    directory.

  Whether each driver tolerates this (Mesa's threads, L4T) is measured per
  host, not assumed.
* **Receipt.** The provider records:
  * its own image hash;
  * its `DT_NEEDED` names;
  * after device creation: the resolved paths and SHA-256 of `libvulkan` and
    the ICD (from `/proc/self/maps`);
  * the driver name and version (`VkPhysicalDeviceDriverProperties`);
  * the device and the kernel release.

### 6. The launcher and the grant

The launcher reads a structured GPU grant. The grant contains:

* wire 42;
* the artifact table;
* the device-byte cap;
* the submit timeout;
* the device index.

The launcher pins the grant's digest in the run receipt. It is a run-time grant
and is separate from the compiler's `--policy`. Admitting wire 42 at compile
time therefore does not wait for E2170. Whether GPU guests also need
compile-time policy narrowing is an open question (below).

The launcher's own filter admits `pipe2`, `clone`, `execve`, `wait4` and
`kill`. The guest's filter admits none of them.

### 7. Seed admission (JUN-109, proposal 4a)

Wire 42 is admitted by a measured adoption round, the same way R4B and R6B
admitted earlier wires. It changes:

* `seed/HEADS`: `:caps`, `:cap-shapes` and the keyword codes;
* `seed/00-ns` and `seed/20-names`, through their generators;
* `seed/21-check`: `ck-wire-kw`, `ck-wire-ok`, the shapes and `ck-r6b-capkw`;
* `seed/30-lower`: `lw-wire`;
* `seed/90-drv`: the policy names.

These files are hash-pinned. The round needs:

* the fixed point (G1 = G2 = G3);
* the paired cases;
* a new adoption receipt;
* a new static root receipt;
* the security-integration sign-off.

**Which pin each step moves.** Two closures pin the seed, and they share the
frontend (`00-ns`, `20-names`, `21-check`, `30-lower`):

| closure | pinned by | holds |
| --- | --- | --- |
| `seed/MANIFEST` (adopted) | `seed/adoption-20261017.json`, `seed/compiler-core.json` | the frontend, `90-drv` and the adopted backend; not `76`/`77` |
| `seed/X86_64-LINUX-SELFHOST-MANIFEST` | `seed/bootstrap/aarch64-linux-static-root.json` | the frontend, the static backends and the runtimes `76`/`77` |

`scripts/seed/selfhost-bootstrap.py` fails on "adopted source drift" when the
`seed/MANIFEST` unity changes, and only records `rootReproduces` for the
static root.

* **Step 2 changes only `seed/76` and `seed/77`.** They are the runtime text
  embedded in every static image, and only the Linux selfhost closure holds
  them. So step 2 needs a C-free root re-pin and no adoption round:
  1. The old root builds S1.
  2. S2 = S3.
  3. S3 becomes the root.
  4. A second run shows root = S1 = S2 = S3.
* **Step 3 changes the shared frontend.** It moves both pins: a new adoption
  receipt with the conformance evidence of ADR 0370, and another root re-pin.

### 8. Platforms, in order

1. **x86_64-linux.** First qualification on B70 (ANV) or gad (RADV). CDCI is
   unaffected: it has no GPU and never runs a provider.
2. **aarch64-linux.** Xavier. This adds AAPCS64 imports to the writer.
3. **macOS.** Blocked, and out of scope here:
   * macOS has no static image: it has no stable syscall ABI, and executables
     must link libSystem and be signed.
   * Amu's Mach-O writer emits `MH_OBJECT` only (kotoba-object #8).
   * The guest itself therefore has no route on macOS.

   macOS needs its own ADR for platform-linked Mach-O executables. The provider
   there would be native Metal: amu #1404 measured a cold command buffer at
   92 µs on Metal against 2.5 ms on MoltenVK. Until then, M1 Max and M4 numbers
   stay historical bootstrap references.

### 9. Shader artifacts are pinned data

SPIR-V still comes from `glslangValidator`. MSL text comes from the kernel DSL,
which runs on kbb. Under this ADR, shaders are data inputs, identified by
SHA-256 in the artifact table. They are not part of a selfhost claim, and a
receipt records each digest and its producer.

Emitting SPIR-V from Kotoba, and moving the kernel DSL into Amu, is a separate
follow-up.

### 10. What may be called a selfhost result

A GPU number is a selfhost result only when all of these hold:

* the selfhost compiler built the guest, the provider and the launcher, and
  each hash is recorded;
* the receipt records the platform stack (kernel, driver, loader and ICD
  digests) and the shader digests.

Every other GPU number is a bootstrap reference.

## Rejected alternatives

* **Restore or pin a C broker.** `docs/selfhost-priority.md` rule 3 forbids it.
* **Load the driver inside the static image.** The guest would need a dynamic
  linker, libc, threads, `ioctl`, `mmap` and `futex`. That erases the sandbox,
  and it puts the driver next to the program, against ADR 0001's isolation
  rule.
* **A Kotoba userspace driver over kernel DRM ioctls** (xe, amdgpu, nvgpu).
  * Each vendor needs its own command streams and an ISA compiler, which is the
    role of Mesa's NIR/ACO.
  * AIUEOS ADR 0222 sizes ANV/RADV at about 10^5 lines.
  * Apple has no public kernel interface.
  * `com-intel-xe-driver` does not yet submit a command buffer.

  This stays research. It could later replace the provider for one vendor
  without changing the guest protocol.
* **A provider in another language** (Rust/wgpu, Python, Deno/WebGPU). That puts
  a non-Kotoba runtime in the product route, and `docs/selfhost-priority.md`
  excludes Node-class hosts.
* **A shared node daemon over a Unix socket.** The guest would need `socket` and
  `connect`, and GPU memory would be shared across tenants. Pooling can be
  reconsidered if measurements call for it.
* **Keep wire 42 refused.** Acceptable only as the interim. It blocks selfhost
  GPU results (JUN-109, AWAI-12) and murakumo's `:kotoba-native` engine.

## Consequences

* **First dynamic-dependency receipt.** Amu gains its first output with
  dynamic dependencies. It is confined to the provider class, and the
  ADR 0240 surface never accepts it.
* **Comparable evidence.** The old guest also talked to the broker over pipes,
  and the protocol keeps `SUBMIT`'s meaning, so per-step overheads stay
  comparable. Everything is re-measured all the same.
* **Docs that still describe the deleted broker as current** get a dated note
  pointing here:
  * ADR 0355, ADR 0356, both ADR 0357s, ADR 0358;
  * `docs/native-aot-baseline.md`;
  * the `:gpu/compute` comment in `resources/kotoba/lang/capability-catalog.edn`
    (done: JUN-293, rewritten rather than given a dated note);
  * the `accelerator*` source comments.

  This is a follow-up; this change only adds the refused entry in
  `docs/c-loader-removal.md`.

## Open questions for the owner

1. ~~Is the platform boundary in Decision 1 accepted?~~ Accepted 2026-10-22.
2. Will security integration sign off on admitting wire 42, and on the
   artifact table replacing guest-named paths?
3. Does provider confinement (Landlock plus seccomp after device creation) hold
   on Mesa and L4T?
4. Do GPU guests need compile-time policy narrowing (E2170), on top of the
   run-time grant?
5. Who owns the macOS ADR (Decision 8), and when?

## Implementation steps

Each step is its own PR, in this order:

1. **Protocol table.** Done (JUN-291).
   * **Table.** `tools/gpu_compute_protocol.kotoba` holds the grammar, the
     bounds, the order rule and 34 named refusals. Its header lists where it
     is stricter than the C broker.
   * **Tests.** `tools/gpu_compute_protocol_test.kotoba` has 107 cases and
     needs no GPU.
   * **Check.** `scripts/seed/check-gpu-compute-protocol.py` builds the unit,
     compiles it with the pinned root and runs it as a static image. A control
     build with one wrong expectation must fail exactly one case.
   * **Receipts.** `docs/evidence/gpu-compute-protocol-20261022/`: aarch64-linux
     native, and x86_64-linux under qemu-user.
   * **The `:gpu/compute` comment in the capability catalog** follows this
     ADR since JUN-293 (2026-10-22):
     * kotoba-lang/kotoba-lang#808 changed the authority's comment.
     * amu's `resources/kotoba/lang/capability-catalog.edn` was then resynced
       to the authority's bytes, which also closed its earlier drift (the
       `:fs/app-data :confinement` entry).
     * The string in `src/kotoba/compiler/embedded_resources.cljk` was
       rewritten to equal that file byte-for-byte, without running the CLJK
       generator.
2. **Guest runtime.** Done (JUN-294).
   * **Runtime.** `seed/76` and `seed/77` have `KEXE_CAP_RESOURCES_42`, the fd
     checks, the framed transport, named refusal lines, ignored SIGPIPE and
     the seccomp read rule. Nothing in them is active unless wire 42 is in
     `KEXE_ALLOW`.
   * **Contract.** `seed/X86_64-LINUX-ABI` states all of it.
   * **Root.** Re-pinned C-free to `7597850a…`. The previous root `f4a2a53e…`
     is kept in the receipt's history.
   * **Check.** `scripts/seed/check-gpu-runtime-transport.py` covers 10
     start-up cases with the product compiler, which still refuses wire 42
     (E2115). It then builds a test-only compiler, with wire 42 admitted in
     memory and never adopted, and runs 8 transport cases against a scripted
     provider.
   * **Seccomp control.** One case uses a compiler whose read rule names
     another fd; its guest must die of SIGSYS. It runs where the kernel
     enforces seccomp.
   * **Receipts.** `docs/evidence/gpu-runtime-transport-20261022/`.
3. **Seed adoption round** admitting wire 42, with its receipts (JUN-109).
4. **Launcher** (JUN-282): spawn, pipes, wall time, the GPU grant and the
   joined receipt.
5. **Platform-linked ELF writer** and C-ABI imports, x86_64 SysV, with the
   import allowlist.
6. **Vulkan provider** in Kotoba on x86_64-linux. Qualify it on B70 or gad
   with:
   * `INFO` and `DEVCLASS`;
   * the dot and kdot fixtures;
   * the decode guest's argmax chain against the f64 oracle.
7. **aarch64-linux** imports, then Xavier.
8. **macOS ADR.**
9. **Dated notes** in the stale docs listed under Consequences.
