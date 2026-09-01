# ADR 0289: The collections residual is out-of-line division, not callback crossings

- Status: accepted
- Date: 2026-08-31
- Stage: Reflect (diagnostic; one workstation at load1 47, ratios only)

## Decision

Iterations 52–54 name the same cause for both open residuals — collections
1.93 and strings 2.17 — and point them at one lever:

> what remains is almost purely the ~170 indirect callback crossings per call
> against gcc's direct array code

**That is not supported.** Two controls say the crossing is a small term and a
hardware division is a large one. The `guest-visible bounds-checked load`
lever is not refuted as a *win*, but it is no longer the largest remaining
lever, and it should not be justified by call-elimination.

## Control 1 — the crossing, in isolation, is ~free

Two C arms compute the same kernel over the same data and differ in exactly
one variable: whether each element read crosses an indirect function pointer
mirroring `checked_vector_at` (context/version check, handle resolve, bounds
check, arena load).

| arm | median | |
|---|---|---|
| A direct (`v[i]`) | 667.1 ns/call | |
| B crossing | 668.7 ns/call | **ratio 1.002, 1.6 ns/call** |

**The first version of this control was wrong, and the arithmetic is what
caught it.** Both arms initially lived in one translation unit, so LLVM could
see the callee body, knew its clobber set, and scheduled around it. That
version reported 5.9 ns for 108 crossings — 0.055 ns each, below the cost of a
single indirect call, which is impossible. Rebuilt with the callback in a
separate TU and `-fno-lto`, the answer did not move (1.002).

The crossings are real and were counted, not assumed: a counter in the
callback reported `XCALLS = 17,255,040` against a predicted
`512×107.5 + 4×2×20000×107.5 = 17,255,040`. Exact.

They are ~free because the loop is latency-bound on a serial dependency chain
(`acc = imod(acc*31 + v[i], 1000003)`) and the calls retire in its shadow.

## Control 2 — where the 1.93 actually lives

`kernel_collections.kotoba` compiled to `aarch64-kotoba-v1` (872 code bytes,
218 instructions, `:fuel-abi {:mode :hidden-context-x7 :initial 512}`). The
`walk` loop spans `0x13c..0x1ac` — **29 instructions per element**:

| what | instrs |
|---|---|
| `vector-at` crossing (incl. spilling `x7` to stack around the call) | 9 |
| fuel accounting — `ldr`/`cbnz`/`brk`/`sub`/`str`, a read-modify-write in memory | 5 |
| `imod` constant rebuild, argument moves, `bl`, result move | 6 |
| loop condition and hash arithmetic | 9 |

Plus the callee. `bl` at `0x18c` is word `0x97ffff9d`, displacement −99,
target `0x0` — decoded, not taken from symbolization — which is `imod`: **18
instructions containing a hardware `sdiv`**, of which 8 rebuild `INT64_MIN`
and `-1` from immediates every call for the overflow guard.

**~47 instructions per element, including a real division on the
loop-carried chain**, against the C twin's ~6–8 strength-reduced ones.

## The discriminator is dynamic, not static

Both binaries contain exactly **one** `sdiv`. That is not the difference.

- **C twin**: every constant divisor (`1000003`, `16`, `65521`, `8`) is
  strength-reduced to `smulh`+`asr`. The single `sdiv` is `imod(s1, len)`,
  whose divisor is a runtime value — **~1 execution per call**.
- **amu**: `imod` is a user function, not inlined, and its divisor is not
  constant at the call site, so the shared body's `sdiv` runs once per element
  from `fill` and from both `walk`s — **~165 executions per call**.

## Consequence — lever re-ranking

Ranked above `guest-visible bounds-checked load`, which removes 9 of 47
instructions and measured ~1% in isolation:

1. inlining small user functions
2. constant-divisor strength reduction
3. bulk fuel in loop bodies (the per-element `ldr`/`str` on `x7`)

## What this does not claim

- Absolute numbers. One machine, one day, load1 47. No quiet-host run.
- No amu-vs-gcc same-run A/B; the controls are C-vs-C plus static counts.
- **strings**: `kernel_strings.kotoba` was not disassembled. Whether its 2.17
  shares this cause is **unmeasured**, not assumed to be the same.

## Aside: the lever is a backend gap, not a security constraint

`kexe_loader.c` says twice that a whole-operation callback exists "because the
guest cannot load a byte". Checked against `lang/surface-status.edn`'s
shielding axes on `origin/main`: a bounds-checked element load manufactures no
code (`:code-identity`), bypasses no dispatch (`:dispatch-bypass`), mutates
nothing (`:authority`), spawns nothing (`:resource-bounds`). It is covered by
no shielded surface, so it is an implementation gap and may be built.

The bounds check is already expressible in guest KIR — `vector-region`'s
literal path emits `(if (>= i 0) (if (< i n) sel (quot 1 0)) (quot 1 0))`,
trapping via divide-by-zero. Only the load is missing.

**Hazard worth recording**: the local `kotoba-lang` checkout was 14 commits
behind and contained no `:shielding-axis` key at all. Reading it would have
produced the opposite conclusion with no sign anything was wrong.
