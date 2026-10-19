# kernel-profile entry route — entry-stub vs OP-CAP supervisor, measured comparison (JUN-29, 2026-10-20)

Resolves the central open design point of
`native-seed-c-free-runner-kernel-profile-slice-20261020.md` §3 ("either the
kernel profile carries its own entry stub (a third `xg-start` variant) or the
runner's syscall surface is served through `OP-CAP` wires from a supervisor")
by measurement. Every byte number below is from an artifact decode this tick
(xcrun llvm-objdump as independent instrument); computed products are labelled
`computed`. Method follows `native-seed-c-free-runner-raw-elf-emitter-20261019.md`:
hand-audited byte strings, independent decode; Python is orchestration only.

Artifacts (this tick):
* `p1-scalar.elf64` — profile 0 standalone ELF from the expressiveness probes
  (probe-work, G2 producer sha256 `101995a7…5d2e2`, expressiveness doc).
* `p4-cap.kx64-v1` — profile 1 payload, `(typed-cap-call :fs/app-data :string
  :string "p1-scalar.kotoba")`, wrapped for decode via `wrap_elf.py`
  (call-abi 20261019 instrument).
* `entry_route_encoding_probe.py` → `/tmp/entry_route_setup_sites.elf`, blob
  sha256 `e419f130221463631ceb79dbfc05fba2246e639ba263238dec3b32eaebb428c2`
  (setup-syscall site encodings; addresses in the blob are placeholders —
  what is measured is the encoding shape and byte cost per site).

## 1. Measured: today's fixed `xg-start` stub (Route A's extension point)

Disassembly of `p1-scalar.elf64` at `e_entry 0x401000`:

```
401000: leaq 0xff9(%rip), %r9        7B   context pointer (ctx-v11)
401007: callq main                   5B
40100c: pushq %rax                   1B
40100d: movl $1,%eax; movl $1,%edi;  10B
        movq %rsp,%rsi; movl $8,%edx 8B   write(1,&result,8) site = 20B
40101f: syscall                      2B
401021: cmpq $8,%rax; movl $0,%edi;  11B
        je; movl $0x4a,%edi          7B   short-write → exit code 74
401031: movl $0x3c,%eax; syscall     7B   exit site = 12B
401038: ud2                          2B
```

* Stub total **58 B** (0x401000–0x401039), **2 syscall sites** (write 20 B,
  exit 12 B), 1 `ud2`. The stub is FIXED — SIR admission (`xg-check-sir`) never
  sees it. A third `xg-start` variant (Route A) grows exactly this region.

## 2. Measured: OP-CAP dispatch cost (Route B's guest surface)

`p4-cap.kx64-v1` (240 B payload), cap-call site for wire **35** (`:fs/app-data`
— `movl $0x23,%esi`):

```
4000c1: movl $0x23, %esi         5B  wire id
4000c6: movl $0x1, %edx          5B  arg1
4000cb: movl $0x1, %ecx          5B  arg2
4000d0: movq -0x8(%rbp), %rdi    4B  ctx reload (call-abi :sysv-ctx-v11 discipline)
4000d4: callq *0x80(%rdi)        6B  vtable slot 128 = typed_cap_call
4000da: movq -0x8(%rbp), %r9     4B  r9 restore (discipline)
```

* **29 B per 2-arg cap call**, discipline reloads included. Same shape for
  pair vtable slots 56/64/72 (`callq *0x38/0x40/0x48(%rdi)`, measured in
  p6 payload and raw-elf probe) and for `OP-CALLI` (`jmp rax`). Fuel charge
  site 18 B (`mov rax,[r9+8]; test; jg; ud2; dec; mov [r9+8],rax`).
* The entire measured guest service surface for the compiler command path is
  wires `#{35 37 38 39}` — the slice's pinned set.

## 3. Measured: what Route A's stub must grow by (setup syscalls, inline)

Independent decode verified each hand-audited site (syscall numbers confirmed:
437 openat2, 302 prlimit64, 157 prctl, 317 seccomp, 60 exit):

| site (shape) | measured bytes |
|---|---|
| mmap 6-arg (`MAP_PRIVATE\|ANON`) — 1 arena | **35** |
| openat2 4-arg (fd from ctx, `&how`, 24) | **27** |
| prlimit64 4-arg (`RLIMIT_AS=9`) | **25** |
| prctl 5-arg (`PR_SET_NO_NEW_PRIVS=38`) | **28** |
| seccomp 3-arg (`SET_MODE_FILTER=1`) | **22** |
| control: exit 1-arg (as in today's stub) | 12 (cross-checks §1) |

* Arenas are runner obligations (surface doc §3: 4 × `KEXE_*` + stack ≥1 MiB /
  512 KiB reserved) ⇒ 5 mmap sites = **175 B** (`computed` 5×35).
* Inline setup code = 175 + 27 + 25 + 28 + 22 = **277 B** (`computed` sum of
  measured sites), before any argument materialization beyond the shapes above.
* The seccomp filter is DATA, not code: the measured allow-list (surface doc
  §2) is 28 syscalls (11 base + 11 fs + 6 scope-35 extras) ⇒ ≥2 `sock_filter`
  insns per entry + arch check + default `KILL_PROCESS` ≈ **≥59 insns /
  ≥472 B** (`computed` lower bound; real filters grow with jump patching).
* **Path containment cannot be a site**: `openat2 RESOLVE_BENEATH` enforcement
  (`kexe_scope_open`, loader line 8193) is logic, not an instruction sequence —
  its inline stub cost is unmeasured and, under the slice's non-goals
  ("seccomp BPF emission, `openat2` `RESOLVE_BENEATH` containment, `RLIMIT_AS`
  … NOT in this slice"), unmeasurable *in this slice*.

**Route A inline delta ≈ ≥749 B (277 code + ≥472 filter) + containment logic,
emitted into every kernel-profile ELF**, in a region admission never sees
(fixed stub) — the same property that keeps today's `write`/`exit` simple is
exactly what would hide mmap/seccomp/containment from `xg-check-sir`.

## 4. Comparison and pinned entry decision

| dimension | Route A: third `xg-start` variant | Route B: supervisor + `OP-CAP` |
|---|---|---|
| guest emission delta | +≥749 B stub/filter per ELF (`computed`) | **0 new constructs** — 29 B/service-site (measured), wires `#{35 37 38 39}` |
| admission impact | stub is ungated emission (SIR checks don't reach it) | exactly the pinned profile-2 slice; no widening |
| seccomp BPF emission | required **in emitted code** (= declared non-goal) | stays in the runner artifact |
| `openat2` containment | must be re-implemented per emitted ELF | `kexe_scope_open` (line 8193) lives once in the runner |
| verification burden | vehicle (b) hand-audit × ~12 more instruction sites + filter blob | runner audited once; guest surface is vtable calls already measured (call-abi 25 payloads, anomaly 0) |
| boot route (JUN-30/31) | stub must also cover bare-metal entry | runner **is** the boot entry (vehicle (a) or (b)); guest entered via ctx-v11 |

**Decision (pinned): Route B.** The kernel profile's entry is the runner's call
into guest `main` under the measured `:sysv-ctx-v11` discipline (kx64-v1's
contract: ctx in `r9`, `mov rdi,[rbp-8]` reload before every host dispatch).
No third `xg-start` variant is introduced; if a standalone entry is later
needed for the JUN-31 QEMU boot, it lives in the runner artifact (vehicle (a)
emission with bootstrap provenance, or vehicle (b) hand-audited bytes), **not**
in per-ELF guest emission. This also matches the slice's phase order
(`map-arenas → install-sandbox → pre-entry → call-guest → post-run`): every
phase before `call-guest` is runner-side by construction.

Route A remains the documented fallback if a measured runner construct ever
needs a wire outside `#{35 37 38 39}` — that measurement does not exist today
(wires 20/42/43–47 stay refused, surface doc §2).

## 5. What this does NOT settle (unchanged, measured unknowns)

* seccomp BPF emission, `openat2` containment, `RLIMIT_AS`, Linux process
  semantics — still outside the slice; they now have a *location* (runner
  artifact), not an implementation.
* Arena envelope placement at entry is runner-side under Route B; the runner's
  own map phase is the vehicle (a)/(b) work, unmeasured here.
* The +1 error in the repo test suite (15→16, row/wasm region) is unrelated to
  this slice (runner namespaces FAIL/ERROR 0) — attribution run in flight.
