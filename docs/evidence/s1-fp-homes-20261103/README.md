# S1: f32 locals in FP registers (JUN-804, ADR 0404), 2026-11-03

Author-run, diagnostic. MacBook Pro M1 Max, 32 GB, macOS 26.4, on a shared host (load average 19–55 during the
day, two unrelated VMs running). Not a quiet-host measurement and not a published benchmark. Native ARM/x86 CI and the
core adoption round are pending.

- Old compiler: `bin/amu` of main `1abb17f30` (sha256 `916f3237…6a`).
- New compiler: `bin/amu` of this branch after `scripts/seed/repin-derived-pins.py` (sha256 `2065be26…2a`). The new
  root reaches F1 = F2, and the public product check passes (`PASS_PUBLIC_MACOS_PRODUCT`).

## Gate

`gate/gate.py --old <main>/bin/amu --new <branch>/bin/amu --work <dir> --out result.json --q8 gate`
builds every program with both compilers. The C twin `gate/twin.c` is built with `cc -O2 -ffp-contract=off`. Python
only builds, runs and compares. [`result.json`](result.json): 24 of 24 checks pass.

| Check | Old | New |
| --- | --- | --- |
| f32 matvec, 1 accumulator, 64 x 896 (`mv.kotoba.in` + `rowdot1`) = C | pass | pass |
| f32 matvec, 4 accumulators (`rowdot4`) = C | pass | pass |
| RMSNorm row x3 (`rms.kotoba.in`, sqrt and divide) = C | pass | pass |
| FP-home paths (`homes.kotoba`: returned home, compares, neg/abs/sqrt, f64 -> f32, two homes, aliased copy) = C | pass | pass |
| 1- and 4-accumulator checksums differ (values round, so order is observable) | | pass |
| mutants (`f32-sub` for one add) differ from C, both shapes | pass | pass |
| `f32-from-bits` of 1.5f, -3.0f bits, 2^31-1 return the same values; 2^31 and -2^31-1 trap | pass | pass |
| integer programs (Q8_0 kernel 64 and 4,864 rows, a vector loop, hello) produce identical `__TEXT` | — | pass |

`scripts/seed/check-a64-f2i.py --compiler seed/bootstrap/aarch64-macos/amu-full-root.macho` (new root): `PASS_A64_F2I`.
The f32 -> i64 guards hold, and the thirteen trap operands trap. Its float probes that do not name the conversion keep the
SHA-256 values pinned from the main `26833b16` root.

## Speed

CPU time per 4,864 x 896 f32 matvec, `(t[10] - t[0]) / 10`, median of 5 interleaved rounds (range):

| Kernel | Old compiler | New compiler | C `-O2 -ffp-contract=off` |
| --- | ---: | ---: | ---: |
| 1 accumulator, strict order | 32.2 ms [29.8–38.8] | **19.9 ms** [15.3–22.6] | 6.2 ms |
| 4 accumulators (products bound in a `let`) | 26.1 ms [23.3–27.3] | **14.6 ms** [14.1–16.4] | 2.1 ms |

The 1.6–1.8x gain comes from the loop code shown below. The roadmap target (within 2x of C) is not met. In an
inline-assembly replay of the new per-element float sequence (`fmovcost.c`, variant 4), the float part costs about
6.7 ms against 27 ms for the old one. What remains is each element's two `vector-at` descriptor lookups and bounds
checks and its two `f32-from-bits` range checks. Measured on the 1-accumulator loop, removing the range checks takes
20.8 ms to 15.5 ms. Those are the roadmap's S2 (typed f32 buffers that need no range check and load into FP
registers; hoisted descriptor and bounds checks), not this change.

### What changed in the loop

Old, 1 accumulator ([`old-acc1-loop-tail.txt`](old-acc1-loop-tail.txt)): two `bl` calls to `f32-from-bits`, a frame,
fuel through memory, and the accumulator in a general register:
`fmov s0,wA ; fmov s1,wP ; fadd s0,s0,s1 ; fmov wA,s0 ; sxtw xA,wA` every iteration.

New ([`new-acc1-loop-tail.txt`](new-acc1-loop-tail.txt)): a leaf with fuel in x8, the range check inline
(`sxtw x17,wX ; cmp x17,xX ; b.eq ; brk #0`), and the accumulator in s16: `fadd s16, s16, s1`.

New, 4 accumulators ([`new-acc4-loop-tail.txt`](new-acc4-loop-tail.txt)): the products land in s20..s23 and the
accumulators in s16..s19, and the loop has no general-register round trip for any f32 value:
`fadd s16,s16,s20 ; fadd s17,s17,s21 ; fadd s18,s18,s22 ; fadd s19,s19,s23`.

## Limits found on the way

- With five `recur` bindings whose expressions read vectors, a later binding's `vector-at` sits at temp index > 5.
  The existing generator inlines `vector-at` only for temps 0..5 (`gn-inl`), so it becomes a runtime call and the
  function stops being a leaf, under both compilers. Binding the products in a `let` keeps the reads shallow. This is
  the 4-accumulator shape measured above.
- A binding whose value comes through control flow (`if`), or that follows a binding with control flow in a
  multi-binding `recur`, is not homed. That keeps it correct, just not faster.

## Files

- `gate/`: the programs, the C twin and the driver. `gate/q8_matvec.kotoba.in` is murakumo's Q8_0 kernel.
- `fmovcost.c`: the inline-assembly replay. Variants: 0 the old sequence, 1 product in FP, 2 accumulator in FP,
  3 loads into FP, 4 this change, 5 this change with the product fused.
- `result.json`: the gate output.
