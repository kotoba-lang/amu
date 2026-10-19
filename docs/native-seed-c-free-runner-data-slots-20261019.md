# C-free seed runner: static data-slot reference enumeration (JUN-29, 2026-10-19)

Closes the open measurement of `native-seed-c-free-runner-slot-hits-20261019.md`
("which emitters read which data slots"): a static enumeration of inline
context **data**-slot references in the seed emitters, so the runner's required
layout is bounded by measurement instead of assumption. Measurement record; no
runner implementation is claimed. Emitters measured at the same worktree state
as the slot-hit record (docs commits `adbb9876` + `4ac06d08` on
`codex/aiueos-amu-bridge-20261017`).

## Method (two independent scans, cross-checked)

Context ABI (loader `seed/bootstrap/adopted-loader-20261012.c`, `_Static_assert`s
lines 4643-4725): `version` @0, `fuel` @8, `allow` @16, function slots
48..376, and the v9/v10 data slots `pair_used_pointer` @288, `pairs_base`
@296, `pair_validated_base` @304, `vector_used_pointer` @312, `vectors_base`
@320, `vector_items_base` @328, `code_base` @384, `code_length` @392.

1. **enc- call scan**: every `enc-ldr/str/ldp/stp` site in `seed/*.kotoba`
   whose base register is `x7` (the aarch64 context register), offset resolved
   through `CTX-FUEL` (8) / `CTX-CODE-BASE` (384) / `(+ CTX-CODE-BASE 8)`.
2. **instruction-word scan**: every numeric literal in `seed/41-a64gen.kotoba`
   decoded as an AArch64 LDR/STR/LDP/STP (32/64-bit, unsigned/signed offset);
   base-`x7` memory ops kept. This covers emission paths that bypass `enc-*`
   (raw word tables such as `wm-entry`) and `kpat-match` pattern words.
3. **x86-64 side**: full read of `seed/70-x86_64-linux.kotoba`,
   `71-x86_64-runtime.kotoba`, `72-x86-cross-entry.kotoba`,
   `73-x86-linux-entry.kotoba` (485 lines total) with byte-level decoding of
   every context access.

## 1. aarch64 emit path (`seed/41-a64gen.kotoba`) — inline base-x7 reads

| offset | slot | sites (scan 1) | scan 2 | representative emitters |
|---|---|---|---|---|
| 0 | `version` | 1 | — | `qrow-preflight` (reads, compares == 11) |
| 8 | `fuel` | 257 (read+write) | 9 (wm-entry word table) | every charge/republish site |
| 288 | `pair_used_pointer` | 8 | — | `se-entry`, `gn-rt-cpa`, `ac-string`, `sls-emit`×2, `trg-guards`, `trg-se-entry`, `t2-e-sdesc-from` (ldp 288/296) |
| 296 | `pairs_base` | 7 + t2 ldp | — | same string-handle paths |
| 304 | `pair_validated_base` | **0** | **0** | — |
| 312 | `vector_used_pointer` | 74 | 1 | `gn-hchk` (9 callers pass 312/320), `ve-read`, `vl-entry`, `pi-call`, ~60 embench kernel entries, `qrow-preflight`, `t2-e-desc-from` |
| 320 | `vectors_base` | 77 | 1 | same set + `gn-op-vec`/`gn-op-vecp` |
| 328 | `vector_items_base` | 78 | 1 | same set + `gn-vidx`, `gn-chain-base`, `sl-read`, `gn-vread`, `gp-read` |
| 384 | `code_base` | 24 | — | `gn-rt-lit-at`, `gn-rt-cpa`, `gn-op-vecp`, `gn-op-tab`, `ti-emit`, `ac-string`, `t2-e-sdesc-from`, `t2-e-tabs` |
| 392 | `code_length` | 6 + t2 ldp | — | `se-entry`, `gn-rt-cpa`, `ac-string`, `sls-emit`, `trg-se-entry`, `t2-e-sdesc-from` |

Notes:

* `gn-hchk` (the shared handle-check inline) takes its offsets as parameters;
  all 9 call sites pass `(312 320)` (vector table). The pair-side check
  (288/296) is inlined directly at its 8 sites.
* `wm-entry` (word-table emitter) reads 312/320/328 + fuel only — the two
  scans agree, no hidden slot.
* `kpat-match` pattern words (lines 6863/7271/12680) and `ncv-body-words`
  (4950/4958) contain no base-x7 memory op.
* **`pair_validated_base` (304) has zero inline readers in every emitter.**
  Consistent with the string-handle paths validating via
  `pair_used_pointer`/`pairs_base` + `code_base`/`code_length` instead. The
  offset stays reserved (host-side helpers may use it; a later emitter could
  start reading it) but no current seed output binds the runner to it.

## 2. x86-64 emit path (`seed/7x`) — inline context reads

| slot | x86-64 inline reads | evidence |
|---|---|---|
| `version` @0 | 0 | scalar ELF writes its own page as `{0, fuel}`; no check |
| `fuel` @8 | read+write | `xg-fuel` (OP-FUEL): `mov rax,[r9+8]` / `dec rax` / `mov [r9+8],rax` (words `0x08418b49`, `0x08418949`), `ud2` on exhaustion |
| all v9/v10 data slots (288-328, 384-392) | **0** | string/table literals are RIP-relative (`lea rax/rcx,[rip+pool]` in `xr-str`/`xr-vec-items`/`xr-tab`); handle checks live in host helpers |

Everything else in the x86 kx64-v1 payload goes through **function** slots:
`xr-call` = `mov rdi,[rbp-8]` + `call [rdi+disp32]` with disp = the slot
offset. `xr-slot` admits exactly 23 slots: 48, 56, 64, 72, 112, 120, 128,
136, 144, 152, 160, 168, 176, 184, 192, 200, 208, 216, 240, 352, 360, 368,
376 (kgraph 80-104, arena 224/232, text 248-280, v10 range 336/344 are
refused at admission). The measured 18-slot runtime union ⊆ these 23.

## 3. Runner-required layout (what this bounds)

* The struct offsets are hard ABI for both paths: x86 dispatches
  `call [rdi+disp32]`, aarch64 dispatches `[x7,#slot]` — a C-free runner must
  place function pointers at the identical offsets and pre-write the data
  slots before the guest starts (loader lines 12802-12809 fill site).
* **For the JUN-29 x86-64 Linux run path (G1=G2=G3 all x86 kx64-v1, emitted
  by `seed/7x`): inline data-slot obligations collapse to `fuel` @8 (read and
  write).** The v9/v10 data slots must exist at their offsets but are not
  read inline by any x86 seed output; the runner needs their content only for
  its own helper implementations (the semantics `checked_pair_*` /
  `checked_vector_*` provide today).
* For aarch64 guests the inline set is: `version` @0 (= 11), `fuel` @8,
  288, 296, 312, 320, 328, 384, 392 — all written pre-start.
  `pair_validated_base` @304: reserve, no guest reader.
* Function-slot obligation stands as measured before: 10 (compile path) /
  18 (measured union); the x86 emitter admits 23; the remaining 13 of 36 may
  stay denied unless a later workload proves them reachable.

## 4. Receipt binding for the kernel-profile runner slice (connects JUN-30 / JUN-102)

Admission for the runner slice (`:aiueos-c-free-bare-metal-v1`, ADR 0271
production order — the seed scalar subset cannot express it, measured in
`native-seed-c-free-runner-slot-hits-20261019.md` §3) must bind one receipt
record, verified before the guest starts:

```
{:runner        <runner artifact sha256>
 :compiler      <compiler payload sha256>          ; G1/G2/G3 chain recorded per hop
 :source-graph  <unity source sha256>              ; seed/X86_64-LINUX-SELFHOST-MANIFEST concat
 :output        <emitted payload sha256>
 :wires         [35 37 38 39]                      ; :fs/app-data :io/write :cli/args :io/write-error
 :envelope      {:vectors 4194304 :vector-items 134217728 :string-pool 268435456 :pairs 16777216 :fuel <budget>}
 :layout        :sysv-ctx-v11                      ; offset map of §1-§2, incl. fuel@8 inline contract
 :refusals      <recorded refusal behavior>}       ; ud2/SIGILL paths kept identical to the loader
```

Any kernel-profile runner slice work (aiueos side, JUN-30/JUN-102) is
admitted against this binding; a run without a matching receipt is not a
JUN-29 acceptance run.
