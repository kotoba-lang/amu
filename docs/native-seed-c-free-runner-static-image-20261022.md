# C-free x86-64 runner: the `x86_64-linux-static` image (JUN-29, 2026-10-22)

Design and milestone record for the runner body that JUN-29's acceptance
needs: the pinned Amu-produced x86-64 compiler runs on Linux without the
trusted C loader and rebuilds itself (G1=G2=G3). Earlier records
(`native-seed-c-free-runner-*.md`) measured the surface and modelled the
sequence; none of them emits a runner. This one does.

## 1. Decision: the runner is linked into the image, written in Kotoba

The main contract (`seed/README.md`, `docs/selfhost-priority.md`) asks for a
loaderless `x86_64-linux-static` ELF. So the runner is not a separate
program that loads a KX64V1 payload; it is a runtime linked into the same
ELF as the guest:

```
ELF64 ET_EXEC, EM_X86_64, no interpreter, no libc
  RX  [ELF header + phdrs][entry stub][guest + runtime functions][literal pool]
  RW  [kexe_context_v11 image: fuel, allow, 36 fn slots, v9/v10 data slots]
      [runtime globals]
  arenas: mapped by the runtime at start (anonymous mmap)
```

The runtime functions (one per used context slot, plus the start sequence
and the capability providers) are **Kotoba source** compiled by the same
x86 backend in the same unit as the guest. The backend gains a small set of
intrinsics, recognized by reserved `kxrt-` names, that Kotoba cannot express:

| intrinsic | emitted code |
|---|---|
| `(kxrt-load64 a)` / `(kxrt-store64 a v)` | `mov rax,[rax]` / `mov [rax],rcx` |
| `(kxrt-load8 a)` / `(kxrt-store8 a v)` | `movzx eax,byte [rax]` / `mov [rax],cl` |
| `(kxrt-syscall n a b c d e f)` | Linux `syscall` (rax, rdi, rsi, rdx, r10, r8, r9) |
| `(kxrt-ctx)` | `lea rax,[rip+context]` |
| `(kxrt-call-main ctx)` | call guest `main` under the guest context ABI |
| `(kxrt-trap)` | `ud2` |

Everything else (UTF-8, pair/vector arenas, path checks, argument and file
providers) is ordinary checked Kotoba code that can be read and tested like
the rest of the seed. This avoids two rejected alternatives:

* a hand-assembled byte runtime (vehicle (b)): every instruction hand-audited
  and outside the checker;
* widening the shared frontend/SIR with memory ops: changes the adopted
  closure that the AArch64 route and the bootstrap pins depend on.

Runtime functions do not charge fuel (`OP-FUEL` is not emitted for them), so
the guest-visible fuel accounting is unchanged. They may use only scalar SIR
plus intrinsics; any `OP-RT`/`OP-CAP`/`OP-STR`/`OP-VEC`/closure op inside a
runtime function is refused at admission, which prevents the runtime from
calling itself through the context.

Context slots are filled at link time: the RW image holds the absolute
addresses of the runtime slot functions (fixed `ET_EXEC` base), so no
function-address op is needed at run time.

## 2. Bootstrap provenance

The first static compiler (S1) is produced by the existing kx64-v1 compiler
running under the trusted loader; that is the one recorded bootstrap step.
From S1 on, the chain is `S1 --compile--> S2 --compile--> S3` on Linux
x86-64 with no loader, and acceptance is S1=S2=S3 byte equality plus the
runtime case suite matching the reference results.

## 3. Milestones

* **M0** — intrinsics + static image format + start sequence; a guest that
  needs no helper (`main` returns a scalar) runs on Linux x86-64 and reports
  through the same stdout/exit contract.
* **M1** — pair/string/vector helpers used by the compile path and the 24
  runtime cases (18 slots measured in
  `native-seed-c-free-runner-slot-hits-20261019.md`).
* **M2** — capability providers for wires 35/37/38/39 with containment
  under the declared root; refusal of every other wire.
* **M3** — the compiler itself as a static image: S1=S2=S3 on Linux x86-64,
  plus a receipt binding runner, compiler, source graph and output hashes.
* **M4** — hardening that the C loader provides beyond observable
  equivalence (seccomp filter, rlimits).

Status lines are appended below as milestones land.

### Status 2026-10-22

* **M0-M3 measured.** `seed/75-x86_64-static.kotoba` implements the format and
  the intrinsics; `seed/76-x86_64-static-rt.kotoba` holds the runtime (23 context slots, wires 35/37/38/39, traps,
  structured report). `scripts/seed/check-x86_64-static.py` records:
  * prepare (macOS arm64, the one bootstrap step through the pinned loader):
    S1 sha256 `22b63172…0028` (1,409,536 bytes; re-measured after the runner mode landed — the first landing measured `a897af61…95da`);
  * execute-linux, no loader: **S1 = S2 = S3** byte for byte; S3's
    `--format kx64-v1` output for the same source graph equals the
    loader-run compiler's (`2faa0899…48d8`); the 24 runtime cases, rebuilt by
    S3 as static images, match the AArch64 loader reference in result, trap
    status/exit 120 and remaining fuel; refusals: float, guest call into the
    runtime, unknown format, existing output preserved, source outside
    `KEXE_CAP_RESOURCES_35`.
  * receipts: `docs/evidence/native-x86_64-static-20261022/`.
* **Execution host caveat.** The Linux run was x86-64 user space under
  qemu-user on an aarch64 Linux kernel (podman machine). A run on a native
  x86-64 kernel is still to be recorded.
* **Cross closure.** `X86_64-LINUX-MANIFEST` (AArch64 closure + x86 backend,
  built by the adopted producer) links the empty
  `76-x86_64-static-rt-none.kotoba`: the runtime text does not fit the adopted
  producer's LITB region next to the AArch64 closure (measured E101 region 3),
  so that closure refuses `--format static` with E7102.
* **Still open.** M4 hardening (seccomp, rlimits); wire-35 forms beyond
  READ/EXISTS/WRITE/APPEND; multiple scope roots; the S1 bootstrap still uses
  the pinned loader once and is labelled as such in the receipt.

### Status 2026-10-22 (later): the KX64V1 runner

JUN-29's acceptance names a C-free runner for KX64V1 payloads, separate from
the static image. The runtime already implements the v11 context and the
command-path wires, so the runner is the same image in mode 1
(`--format kx64-runner`, source `seed/x86_64-kx64-runner.kotoba`): it maps
the payload named on the loader-compatible command line and enters it
through the ninth intrinsic `kxrt-call-at`. `scripts/seed/check-x86_64-static.py`
bootstraps R1 with the bridge and checks that S3 rebuilds it byte for byte on
Linux; `scripts/seed/check-x86_64-selfhost.py --execute-linux --runner R.elf`
runs the existing G1/G2/G3, 24-case and refusal suite with the runner in
place of the C loader.

Measured on Linux (same qemu-user caveat): R1 = R rebuilt by S3
(`62e3a193…c585`, 102,912 bytes); through R, the pinned-chain G1 payload
(`08318b77…a6e6`) rebuilds itself **G1=G2=G3**, the 24 runtime cases match the
AArch64 loader reference (result, trap/exit 120, remaining fuel), and the six
refusals hold; the receipt records `trustedCLoader: false`. Receipts: `docs/evidence/native-x86_64-kx64-runner-20261022/`.
