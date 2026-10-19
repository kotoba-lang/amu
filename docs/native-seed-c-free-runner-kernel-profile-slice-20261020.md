# kernel-profile runner slice — admission delta, pinned to the measured gate (JUN-29/JUN-30/JUN-102)

Date: 2026-10-20. Worktree `/Users/junkawasaki/github/wt/codex/jun29-runner-bookkeeping-20261019`
at `97bf461a`. This is a DESIGN record of the admission extension the C-free
runner needs from the seed x86-64 emit path. No code changed this tick; every
number below is measured from the checkout or from the prior evidence docs
(`native-seed-c-free-runner-{surface,slot-hits-20261019,call-abi-20261019,data-slots-20261019,expressiveness-20261019,raw-elf-emitter-20261019,seed-sequence-20261020}.md`).

## 1. What refuses today (measured: `seed/70-x86_64-linux.kotoba` @ `97bf461a`)

The profile key is `(xg-get M 4)`: **0** = standalone `x86_64-linux` scalar ELF,
**1** = `kx64-v1` runtime guest payload. Two admission layers walk ALL SIR,
including unreachable functions:

* `xg-check-sir` (op admission):
  * profile 0 admits **`OP-FN(1)..OP-CALL(13)` + `OP-FUEL(18)` + `OP-RET(19)` +
    `OP-TRAP(20)` only**. Anything else — `OP-RT(14)`, `OP-CAP(15)`, `OP-STR(16)`,
    `OP-VEC(17)`, `OP-TAB(21)`, `OP-FADDR(22)`, `OP-CALLI(23)`, `OP-VECP(24)`,
    `OP-RES2(25)`, `OP-RET2(26)` — is `xg-err 7101 <op>`.
  * profile 1 admits `OP-FN(1)..OP-COUNT(26)` (the whole table).
  * operand checks on both profiles: `OP-BIN` bop 1..10, `OP-CMP` cc 1..5,
    `OP-UN` only `UOP-NOT`/`UOP-BITNOT`, `OP-CALL` target a real FN with
    `n == nparams`, `n ≤ 5` (profile 1: ≤ 16).
* `xg-check-fns` (function admission) + `xg-type`:
  * profile 0: kind ∈ {`FK-DEFN`, `FK-PRIV`}, `nparams ≤ 5`, every param and the
    return type **scalar (`TY-I64` / `TY-BOOL`)**, `frame ≤ 4096`, and the sole
    export is `main(): () → i64`.
  * profile 1 adds `FK-LAMBDA`/`FK-ADAPTER` (adapter ≤ 5 params, immediately
    after its lambda), `nparams ≤ 16`, types `> 0` and not `TY-F64`/`TY-F32`.

Measured consequence (expressiveness 20261019, 8 probes through the
G2=G1 fixed-point cross compiler): profile 0 refused p8-str (E7101 detail 16),
p4-cap (15), p6-fnref (22), p5-indirect (E2104 frontend), p7-float (33);
profile 1 admitted all of those as **kx64-v1 guest payloads**, never as a host
ELF. **The refusal is admission, not codegen** — `xg-one` already emits every
op 1..26 (`xr-rt`/`xr-cap`/`xr-str`/`xr-vec`/`xr-tab`/`FADDR`/`CALLI`/`xr-vecp`).

## 2. What the runner needs (measured surface, unchanged)

1. **cap I/O wires `#{35 37 38 39}`** → `OP-CAP(15)` + `typed_cap_call` vtable
   slot 128. Brokers 20/42/43-47 stay refused (out of slice).
2. **String literals** → `OP-STR(16)` (`lea rsi,[rip+disp32]` pool reads).
3. **Indirect dispatch** → `OP-FADDR(22)` + `OP-CALLI(23)` and host vtable
   `call [rdi+disp32]` over the measured 18-of-36 slot union (10 compile-path
   slots; displacements ⊆ 23 admitted `xr-slot` entries).
4. **Pair/vector runtime** → `OP-RT(14)` (`RT-PAIR-NEW` etc.; kx64-v1 guest hits
   slots 56/64/72 = pair_new/first/second).
5. `OP-FUEL(18)` fuel@8 inline and `OP-TRAP(20)` `js→ud2` — already admitted in
   profile 0.
6. **Call-site discipline** (call-abi 20261019, 25 payloads, anomaly 0):
   entry-by-call (`rsp ≡ 8 mod 16`), frame 16, `mov rdi,[rbp-8]` reloaded before
   every host dispatch, `mov r9,[rbp-8]` before every guest call and restored
   after. The runner contract binds this as `:sysv-ctx-v11`.

## 3. The pinned design delta (kernel-profile slice, `:aiueos-c-free-bare-metal-v1`, ADR 0271)

Introduce a **third admission profile (value 2) — do not widen profile 0.**
Profile 0's refusals are load-bearing: the G1→G3 fixed-point chain is admitted
under exactly that subset, and widening it silently would retire the scalar
route's proof. The kernel profile admits, at minimum:

* ops: `OP-RT(14)`, `OP-CAP(15)`, `OP-STR(16)`, `OP-VEC(17)`, `OP-TAB(21)`,
  `OP-FADDR(22)`, `OP-CALLI(23)`, `OP-VECP(24)` in the **standalone ELF** route
  (profile 1's set minus `OP-RES2(25)`/`OP-RET2(26)` unless a measured runner
  construct needs two-register results — none does today).
* functions: `FK-LAMBDA`/`FK-ADAPTER`, `nparams ≤ 16` (profile 1 bound),
  types = profile 1 bound (`> 0`, not f64/f32 — handles are opaque i64).
* capability wires: exactly `#{35 37 38 39}` at admission; anything else fails
  closed before any hook runs (as `runner-seed-test` already holds).

### Open design points (measured unknowns — not guessed)

* **Entry sequence**: profile 0's `xg-start` is a FIXED stub (context
  RIP-relative → `call main` → `write(1, …, 8)` → `exit`). The runner's entry
  must instead pre-map arenas, install the sandbox, then enter the guest —
  and the runner process itself needs `mmap`/`openat2`/`seccomp`/`rlimit`
  syscalls that the fixed stub has no path for. Either the kernel profile
  carries its own entry stub (a third `xg-start` variant) or the runner's
  syscall surface is served through `OP-CAP` wires from a supervisor. The
  surface doc §2 pins the syscall LIST (base 11 / fs 11 / scope-35 extras 6);
  which route emits it is this slice's central unresolved question.
* **Arena envelopes at entry** (`KEXE_VECTORS=4194304`, `VECTOR_ITEMS=134217728`,
  `STRING_POOL=268435456`, `PAIRS=16777216`, stack ≥ 1 MiB / 512 KiB reserved)
  are runner obligations before guest entry; where they live in emitted code
  follows from the entry decision above.
* **`xg-type` for the kernel profile**: the runner's ctx-driven dispatch may
  want handle-typed params beyond profile 1's `> 0 ∧ ¬f64 ∧ ¬f32` rule; keep
  profile 1's bound until a measured construct demands otherwise.

## 4. Non-goals of this slice (unchanged)

seccomp BPF emission, `openat2` `RESOLVE_BENEATH` containment, `RLIMIT_AS`,
and any Linux process semantics: NOT in this slice. The slice pins the
**admission surface and the phase order**
(`map-arenas → install-sandbox → pre-entry → call-guest → post-run`), not the
syscalls' emission. Vehicle (b) (raw-ELF byte emitter, 55/55 static + 6/6
execution probes) remains the fallback route with its own harness.
