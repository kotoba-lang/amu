# ADR-0404 -- f32 locals live in FP registers in aarch64 leaves (JUN-804 S1)

- Status: **implemented; Mac core adoption candidate** (seed/41 `fh-*`, `gn-range-wrapper`, `gn-call-range`;
  evidence `docs/evidence/s1-fp-homes-20261103/`; receipt `seed/adoption-jun804-s1-fp-homes-20261103.json`).
  The signed Mac F builds G1 = G2 = G3 from the new core (`PASS_MAC_CORE_ADOPTION_FIXED_POINT`); native ARM/x86 CI
  and the Linux controller qualification are pending.
- Date: 2026-11-03
- Owner direction: 2026-11-03, JUN-804: plan and build an inference-first Kotoba and Amu, with Kotoba and Amu
  selfhost on this Mac's architecture, compiled by Amu selfhost directly. This is that plan's stage S1.
- Relates to: ADR 0398 (aarch64 f32 -> i64), the r6j FLOAT rung (seed/21-check `ck-fl-*`, seed/41 FLOAT section).

## Context

Surface f32 arithmetic already exists: 21-check admits the 36 fixed-signature float operations (`f32-add`,
`f32-mul`, `f32-lt`, `f32-sqrt`, `i64-to-f32-rounded`, ...) and lowers each to one SIR instruction. What was slow is
the code seed/41 emits for them. A float temp is its bit pattern in a general register (an f32 sign-extended from
32 bits), and every operation moves both operands into s0/s1 with `fmov`, applies one instruction and moves the
result back with `fmov` + `sxtw`. In a loop, an f32 accumulator crosses the general/FP boundary twice per
iteration, on its dependency chain.

Measured on a MacBook Pro M1 Max (2026-11-03, loaded host, CPU time; `docs/evidence/s1-fp-homes-20261103/`):

- a 4,864 x 896 f32 matvec in Kotoba took 32.2 ms against 6.2 ms for the same algorithm in C
  (`cc -O2 -ffp-contract=off`);
- earlier the same day, the same loop with integer operations over the same vector reads took about a tenth of the
  float loop's time, so the float handling, not the vector access, cost most of the difference;
- an inline-assembly replay of the per-element float sequence (`fmovcost.c`): Kotoba's sequence 27.3 ms; keeping
  only the product in an FP register 26.6 ms; keeping the accumulator in an FP register 5.9 ms.

Separately, `f32-from-bits` is a library function (a 32-bit range assert, then a retyping). Every call is a real
`bl`, which also makes any kernel that reads f32 values from a vector a non-leaf function.

## Decision

1. **The 32-bit range identity is an inline wrapper.** `gn-range-wrapper` recognizes, by SIR shape and never by
   name, a one-parameter function whose body is `(assert (and (>= b -2^31) (<= b 2^31-1)))` followed by `b`, the
   body of `f32-from-bits`. Token 1280 (+512 with entry fuel) is disjoint from the sign wrapper's `1024 + width`
   (width <= 32). `gn-call-range` checks a constant at compile time, and anything else with
   `sxtw x17, wX ; cmp x17, xX ; b.eq +2 ; brk #0`, the same trap the callee's assert raises. The argument temp is
   the result. Like the identity wrapper, the call keeps the caller a leaf.
2. **FP homes.** `fh-admit` runs before register assignment in an ordinary leaf (`gn-f-leaf` 1) whose SIR uses only
   plain operations (CONST, LGET, LSET, BIN, CMP, UN, branches, labels, FUEL, RET, TRAP, inlined runtime operations,
   identity or range wrapper calls) and contains a float operation. A local slot past the parameters whose every
   `LSET` takes a value whose latest straight-line producer is an f32 operation (f32 BIN, f32 neg/abs/sqrt,
   i64 -> f32, f64 -> f32, a range identity call) gets s16 .. s31 in slot order (at most 16). The slot gets no
   general register, so `gn-memslot` does not force a frame for it.
3. **Every existing path stays correct.** A homed slot is reached through the frame-slot path, which moves it with
   `fmov sH, wX` (store) and `fmov wX, sH ; sxtw xX, wX` (load) instead of `str` / `ldr`. Readers that are not f32
   operations (returns, integer compares, calls, label materialization) therefore see the usual sign-extended
   carrier.
4. **f32 operations use homes in place.** In a function with homes, an f32 BIN, compare or neg/abs/sqrt reads a
   homed operand directly, and an f32 result is written straight into the home of the local it is stored to, when
   that `LSET` is at most 32 straight-line instructions away, nothing in between reads or writes the slot or
   writes the result temp, and the temp is dead after the `LSET` (`fh-co`, `fh-gap?`). Loop updates such as
   `(recur (+ k 1) (f32-add acc ..))`, where the counter's `LSET` comes first, qualify. Temps below the result
   that hold the slot's old value are materialized first (`gn-protect`). The result temp then records "local s",
   and the later `LSET` finds its value in place.

Functions without float locals, and every function outside an ordinary leaf, are generated exactly as before.

## Why these limits

- **Leaves only.** v16 .. v31 are caller-saved, and a leaf makes no call that could clobber them. Several certified
  NEON peepholes in seed/41 use v0 .. v9 and v16 .. v31. They admit exact integer shapes (int32 tables, zero fills,
  matrix rows, SHA rounds), so none admits a body with a float operation. The plain-operation scan is the guard.
- **Straight-line producers.** The admission proves a slot's values are f32 carriers without trusting slot types,
  because a slot number may be reused by bindings of other types. A binding whose value comes from an `if`, or that
  follows another binding with control flow in a multi-binding `recur`, stays in a general register (correct, not
  homed).
- **No contraction.** Results are bit-identical to separate `fmul` and `fadd`. A fused `f32-fma` is a language
  decision, not a code-generation one.

## Consequences

- f32 kernels on this Mac: the matvec takes 19.9 ms with one accumulator (from 32.2) and 14.6 ms with four (from
  26.1), against 6.2 and 2.1 ms in C. The rest of the gap is in vector access and the `f32-from-bits` range checks
  (JUN-804 S2), not in float code.
- Payloads of programs with f32 locals in leaves change. Integer-only programs produce identical bytes (checked
  for a set of programs; the full 19-workload corpus is integer-only). `check-a64-f2i.py` passes unchanged.
- The adopted core changes. Re-pinned here: core unity `fc894801…` (only seed/41 changes among the 19 modules),
  G1 = G2 = G3 container `fc713b1c…` and native `ceb20d88…`, CDCI policy and controller literals (core source, core
  container, amu-selfhost gate `67c4e4fc…`; the kotoba-native gate rebuilds unchanged, `ab782746…`), and the seed/79
  controller pin. The Linux controller and native ARM/x86 qualification run in CI.
