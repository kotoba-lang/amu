# C-free x86-64 seed runner: bounded surface (JUN-29)

Measured against the pinned bootstrap loader source
`seed/bootstrap/adopted-loader-20261012.c` (13,055 lines) at worktree HEAD
`f56efdd7`, 2026-10-19. This document is a measurement record for the
C-free replacement of the trusted C loader on the x86-64 Linux compiler run
path (Linear JUN-29). It claims no implementation.

## 1. What the guest actually touches

The KX64V1 payload runs **in process** against a `kexe_context_v11` struct;
host services are C function pointers in that struct, not syscalls first.

* 36 function-pointer slots in the context region (loader lines 4320-4700).
* Static-asserted offsets: `fuel` @8, `allow` @16, `cap_call` @48,
  `pair_new` @56, `pair_first` @64, `pair_second` @72,
  `kgraph_assert` @80, `kgraph_get` @88, `kgraph_count` @96,
  `kgraph_entity_at` @104, `string_equal` @112, `string_concat` @120,
  `typed_cap_call` @128, `string_substring` @136 (loader lines 4674-4683+).
* ABI v9 adds data slots written once before the guest starts
  (`pair_used_pointer`, `pairs_base`, `pair_validated_base`,
  `vector_used_pointer`, `vectors_base`, `vector_items_base`); v10 adds
  range operations. A C-free runner must lay out the same struct.
* Capability wires for the compiler command path are exactly
  **35,37,38,39** (every `scripts/seed/*.py` invocation):
  `:fs/app-data` (35), `:io/write` (37), `:cli/args` (38),
  `:io/write-error` (39) (loader lines 6939, 6993, 7818).
* Fuel exhaustion and v9 handle-range failures execute `ud2`/`udf`
  (SIGILL); x86-64 restores the fuel decrement before `ud2` (line 11844).

## 2. Bounded syscall surface (Linux seccomp, `install_syscall_sandbox`,
line 12202)

Unconditional base (11): `write`, `exit`, `exit_group`, `rt_sigreturn`,
`rt_sigprocmask`, `getpid`, `gettid`, `tgkill`, `munmap`, `brk`,
`clock_gettime`.

With any fs scope (34 or 35) (11): `read`, `open`, `openat`,
`openat2` (437), `close`, `lseek`, `pread64`, `fstat`, `newfstatat`,
`access`, `faccessat2` (439).

With a `:fs/app-data` (35) scope only (6): `mkdirat`, `unlinkat`,
`renameat` (x86_64 264; `renameat2` deliberately denied), `fchmod`,
`fsync`, `getrandom`.

Brokers (gpu 42 / spawn 20 / net 43-47) add `read` only, and the compiler
command path grants none of them. Capability-dependent admissions outside
the listed sets (review finding): `install_syscall_sandbox` admits
`getdents64` when the `:fs/browse` (wire 34) scope is present (loader
lines 12235-12240) and admits `getrandom` when the entropy grant is
present even without scope 35 (lines 12353-12358). Everything else
returns `SECCOMP_RET_TRAP`; a wrong `arch` field returns
`SECCOMP_RET_KILL_PROCESS`.
**`mmap` and `mprotect` are never admitted** (line 4807): every arena is
mapped by the runner before the sandbox is installed.

Path containment is not seccomp's job: `:fs/app-data` opens go through
`openat2` with `RESOLVE_BENEATH` relative to the scope root
(`kexe_scope_open`, line 8193), so the runner must keep that enforcement.

## 3. Resource envelopes (docs/native-seed-x86_64-linux.md)

`KEXE_VECTORS=4194304`, `KEXE_VECTOR_ITEMS=134217728`,
`KEXE_STRING_POOL=268435456`, `KEXE_PAIRS=16777216`; fuel via
`KEXE_FUEL` / `context.fuel`. Launch stack >= 1 MiB;
`tools/seed-x86_64-linux-loader.c` pre-reserves 512 KiB of stack before the
loader lowers `RLIMIT_AS` below its fixed arenas.

## 4. C-free build vehicles (toolchain inventory, this host, 2026-10-19)

Measured missing: `zig`, `rustc`, `cargo`, `nasm`, `yasm`, `ld.lld`.
Present: Apple clang 21 (`as`/`ld` emit Mach-O, not Linux ELF64).

So a Linux ELF runner cannot be linked with the host toolchain, and the
host C toolchain is a rejected production surface anyway (ADR 0271:
hosted kexe C is rejected; production `:native-aot` is
`:aiueos-c-free-bare-metal-v1`). Candidate vehicles:

* (a) Emit the runner as x86_64-linux ELF from Kotoba source with the
  Amu-produced compiler (the route that already produces guest ELF64,
  `docs/native-seed-x86_64-linux.md`). The runner artifact then contains
  no C source/object; the one-time bootstrap that builds it goes through
  the current loader and must be recorded as explicit bootstrap provenance.
* (b) A raw-ELF byte emitter (machine code written directly). No external
  toolchain, but every instruction is hand-audited.

(a) matches the selfhost direction of JUN-19/JUN-30/JUN-31.

## 5. Open measurements (next tick)

1. Which of the 36 context slots the compiler payload actually calls on the
   `compile --target x86_64-linux` path — bound the runner's vtable by
   instrumenting the trusted loader for one bootstrap run (measurement use
   of the C loader only; not an accepted run path).
2. Whether the seed compiler subset can express the runner at all: the
   standalone profile refuses indirect calls / capabilities / floats
   (E7101-E7102), while the runner must dispatch vtable calls and named
   traps. If the subset cannot, the runner needs a kernel-profile slice
   (aiueos side, ADR 0271 production order) and that becomes an explicit
   dependency to record, not to silently work around.
3. Where admission verification (pinned source graph / container hash) must
   run in a runner that has no C: the receipt must bind runner, compiler,
   source graph and output hashes (JUN-29 acceptance).

Status, 2026-10-19 (same day's later ticks):

* **1 is measured** — `native-seed-c-free-runner-slot-hits-20261019.md`,
  `native-seed-c-free-runner-data-slots-20261019.md`, and the call-site
  discipline in `native-seed-c-free-runner-call-abi-20261019.md` (25
  payloads, anomaly 0).
* **2 is measured but open** —
  `native-seed-c-free-runner-expressiveness-20261019.md` (seed routes vs
  runner constructs) and `native-seed-c-free-runner-raw-elf-emitter-20261019.md`
  (vehicle (b) verified as a probe). The kernel-profile slice remains the
  recorded dependency; the raw-ELF probe also showed the rdi-clobber defect
  class that compiler-produced code cannot exhibit (same call-abi record).
* **3 is implemented** —
  `native-seed-c-free-runner-admission-receipt-20261019.md`:
  `kotoba.compiler.runner-slice` (admission + `:kotoba.runner-receipt/v1`
  binding runner/compiler/source-graph/output hashes with the measured
  call-site contract) plus one measured receipt over the 2026-10-19
  G1→G2 chain, `verify`d and `admit!`ed.

Status, 2026-10-20:

* The run sequence is now wired end to end —
  `kotoba.compiler.runner-seed`
  (`native-seed-c-free-runner-seed-sequence-20261020.md`): map-arenas →
  install-sandbox → pre-entry → call-guest → post-run, with the guest
  call gated on admission and the 2026-10-19 chain's admission
  `73c7761f…e95c` / receipt `b16d1d53…3965` reproduced through the full
  sequence. 2's kernel-profile dependency is unchanged and still open.
