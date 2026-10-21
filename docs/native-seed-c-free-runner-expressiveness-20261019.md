# C-free runner: seed-route expressiveness probes for runner constructs (JUN-29 / JUN-19 vehicle (a), 2026-10-19)

Closes open measurement #2 of `native-seed-c-free-runner-surface.md` ("whether the
seed compiler subset can express the runner at all") by execution, and measures
JUN-19 bootstrap vehicle (a) ("emit the runner as x86_64-linux ELF from Kotoba
source with the Amu-produced compiler"). Measurement record; no runner
implementation is claimed.

## Method and bootstrap provenance

Producer = G2 of `scripts/seed/build-x86_64-linux.py`, rebuilt this run from the
worktree's pinned `seed/X86_64-LINUX-MANIFEST` unity (G1=G2 fixed point
`PASS_NATIVE_X86_64_LINUX_CROSS_COMPILER_BUILD`):

* producer (G1==G2) sha256 `101995a7fbf9e6a93400d7a178ed7c66e1c8dec6be515702d734c829c565d2e2`
* loader (`host/kexe-loader`, clang build of `seed/bootstrap/adopted-loader-20261012.c`) sha256 `05798f17613db2936cf8fe29c16590c8c2b7513fc80e5b2334e89d16b482f7aa`
* source unity sha256 `8e3ea20185ad2703ae2ddd0b33c3195a44dcdece6116d7e02e37a7916c34dc81`

The trusted C loader appears only as one-time bootstrap/measurement provenance
(exactly as `native-seed-c-free-runner-surface.md` §4(a) prescribes); it is not
an accepted run path. Harness = Python orchestration only (`run_probes.py`,
copied verbatim to `docs/evidence/` receipts via Linear comment). Each probe
(source sha256 in the harness receipt) was compiled on both x86 output routes of
`seed/70-x86_64-linux.kotoba` + `seed/71-x86_64-runtime.kotoba`:

* **elf64** (profile 0, `xg-build`, standalone scalar ELF64): `compile SRC --target x86_64-linux --output NEW`
* **kx64-v1** (profile 1, `xr-build`, context-v11 runtime payload): `compile SRC --target x86_64-linux --output NEW --format kx64-v1`

## Results (admission matrix)

| probe | construct (SIR ops) | elf64 (profile 0) | kx64-v1 (profile 1) |
|---|---|---|---|
| p1-scalar | direct call, i64 scalars | OK, 8208 B ELF | OK, 215 B payload |
| p2-trap | `(assert ...)` -> TRAP (OP-TRAP/ud2) | OK, 8208 B | OK, 177 B |
| p3-fuel | loop/recur (OP-FUEL charge) | OK, 8208 B | OK, 292 B |
| p8-str | string literal (OP-STR 16) | **REFUSED E7101 detail 16** | OK, 154 B |
| p4-cap | `typed-cap-call` (OP-CAP) + literal | **REFUSED E7101 detail 16** | OK, 240 B |
| p6-fnref | `fn-ref` + call through it (OP-FADDR 22 / OP-CALLI 23) | **REFUSED E7101 detail 22** | OK, 390 B |
| p5-indirect | call through data `((vector-at v 0) 41)` | **REFUSED E2104** (frontend) | **REFUSED E2104** (frontend) |
| p7-float | f64 (i64->f64 conversion UOP 33) | **REFUSED E7101 detail 33** | **REFUSED E7101** |

Refusal attribution is exact (`seed/SIR` op numbering): detail 16 = OP-STR,
22 = OP-FADDR, 33 = the float conversion UOP. p4's first fired gate is the
string literal (OP-STR); the capability gate is the separate
`xg-build` check `(not= (vector-at M MM-CAPS) 0) -> E7101 OP-CAP` and also
refuses. p5 is refused before codegen by the checker (E2104: the head of a call
must be a known function; the language has no call-through-value typing).

## Static byte scans of admitted outputs

* elf64: `e_entry 0x401000`, 8208 bytes each, RX+RW segments as specified.
  Inline fuel contract holds: `mov rax,[r9+8]` / `mov [r9+8],rax` present iff an
  OP-FUEL site is emitted (p1 callee-entry charge and p3 loop charge = 1+1;
  p2 = 0+0). `ud2` present in all (fixed exit-path site plus the trap path).
* kx64-v1 p6 payload (350 B): `jmp rax` x1 (tail OP-CALLI) and
  `call [rdi+disp32]` x3 at displacements **0x38/0x40/0x48 = slots 56/64/72**
  (`pair_new`/`pair_first`/`pair_second`) — the fn-ref value is a runtime pair,
  so the guest directly exercises runner vtable entries at the exact offsets
  enumerated in `native-seed-c-free-runner-data-slots-20261019.md`.
* kx64-v1 p4 (cap) shows `call [rdi+disp32]` x3 (cap/`string-*` helper slots),
  p8 x2.

## Conclusion (what this bounds)

1. **The only route that emits a freestanding ELF (profile 0) cannot express the
   runner.** The runner's mandatory surface — capability I/O (wires 35/37/38/39),
   string literals, function addresses / indirect dispatch — is refused by that
   profile's admission (E7101), and data-driven calls are refused even by the
   frontend (E2104). Vehicle (a) therefore **cannot** produce the runner from the
   current seed subset: the kernel-profile runner slice
   (`:aiueos-c-free-bare-metal-v1`, ADR 0271; Linear JUN-30/JUN-102 admission and
   receipt binding of `native-seed-c-free-runner-data-slots-20261019.md` §4) is a
   **measured dependency**, not an assumption. Alternative remains vehicle (b)
   (raw-ELF byte emitter, hand-audited).
2. The runtime profile (kx64-v1) admits caps and fn-ref/indirect dispatch, but it
   emits an in-process guest payload (KX64V1 container) that runs *against* the
   vtable the runner must provide — it cannot be the runner's own artifact.
3. Trap and fuel obligations (ud2 refusal paths, `fuel`@8 inline read/write) are
   expressible in both current routes, matching the layout contract.
