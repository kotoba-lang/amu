# 0347 — J-C priced: the per-iteration assert-ref crossing is ~47% of the element, qualified on benjamin

- date: 2026-09-09 11:54 JST
- status: evidence record (no compiler change, no sealed claim)
- axis: JIT/tiering (docs/jit-cosientist.md, J-C) — first measured verdict of the J-C line
- machine: darwin-arm64-benjamin (fleet node, 10 cores, 0 users, load1 2.0–3.0 across the
  run window; node v26.5.0, nbb 1.5.211). Workstation quiet gate failed again this tick
  (load1 13.5–37 on 10 CPUs, idle ≤54%); per ADR 0341 the measurement ran on benjamin.

## Question

J-C: can JIT-side inlining remove the wasm host-crossing cost H-Y1 counted (2.032
crossings/element for self-recursion vs 1.032 for `loop`/`recur`)? Before any inlining
hypothesis can be priced, the crossing's wall-share must be measured on a quiet host —
the ADR 0285 timings were diagnostic-only, taken at load1 12–23 (workstation).

## Fixtures

`bench/bulk-carrier/wasmvec.kotoba.wasm` (self-recursion spelling)
sha256 66c78038...fef515 and `wasmloop.kotoba.wasm` (`loop`/`recur` spelling)
sha256 ef5261de...61edc5, both compiled this tick on the workstation with
`bin/amu compile --target wasm32 --fuel 4000000000000` and sha-verified on-node
after scp. Crossings recounted on-node first (load-independent, wrapping every
import before instantiation): wasmvec touch 2.032 / base 1.032 / noref 0;
wasmloop touch 1.032 / base 0.016 / noref 0 crossings/element — exact
reproduction of ADR 0285's counts.

## Method

`nbb slope.cljs <artifact> 200 9` twice per spelling (2 process-cold runs, 18
samples per arm): CPU-time slope between outer=200 and outer=400 so module
compile, JIT warmup, export call and vector construction cancel; arms interleaved
in-round; every arm's return verified against the kotoba.kir expectations inside
slope.cljs (exit 0 every run). Verdicts from `perfgate.core/qualify` (default-v1
policy) run ON benjamin against the gitlibs perfgate+machine sources — route:
`bench/bulk-carrier/jc_qualify.clj`, raw samples sealed at
`bench/bulk-carrier/jc_crossing_benjamin_t32.edn`.

## Verdicts (perfgate.core/qualify, machine darwin-arm64-benjamin, n=18)

| pair | improvement | separated? | qualified? |
|---|---|---|---|
| loop/recur touch vs self-rec touch | **+47.49%** | yes (gap 313.23 vs summed-stdev 13.57) | **QUALIFIED** |
| loop/recur carry-only vs self-rec carry-only | **+98.42%** | yes (gap 314.69 vs 5.99) | **QUALIFIED** |
| loop/recur noref vs self-rec noref (CONTROL) | +95.82% | yes | NOT qualified (:too-noisy — both arms are the loop-only residue, 4.9/0.2 ns/elem, rel-stdev 1.21) |

rel-stdevs on the priced arms 0.011–0.030, far inside the 0.10 ceiling. The
control behaving as expected (sub-5 ns residue, too noisy to price, exactly the
arms where the counts say zero crossings and the difference is a codegen shape
the counts do not govern) supports the method, not a claim.

## Reading

1. The per-iteration `typed-assert-ref` host crossing costs **~47.5% of the
   touched element** (659.6 → 346.3 ns/elem) at qualified separation — H-Y1's
   2x count is now a priced 2x, not just a counted one. The carry-only arm puts
   the crossing at ~315 ns of a ~320 ns carry loop (+98.4%): carried references
   pay almost entirely for the re-proof.
2. J-C's original framing ("JIT-side inlining removes the crossing") is
   **mispriced as stated**: the measured mechanism that removes the crossing is
   the loop-spelling's prologue-once structure (a wasm loop, prologue hoisted
   out) — i.e. a **frontend/codegen change**, not a host-JIT change. On V8
   (already tiered) the residual 1.032 crossing/element on `loop`/`recur` touch
   is `vector-at` itself, and the loop-base arm shows the carrier can be driven
   to ~5 ns/elem once nothing crosses.
3. Ladder consequence (for amu-rank): J-C should be re-scoped from "JIT-side
   inlining of crossings" to "prologue hoisting / structured-loop widening for
   self-recursion with ref-typed params" (the open follow-up ADR 0285 already
   names). The measured ceiling for that lever on this fixture is ~47% of
   element cost — an order above the ≥5% bar. The ~170 indirect-callback
   crossings per call seen elsewhere in the codegen ledger are a different,
   un-priced population.

## Discipline notes

- No compiler change, no sealed claim; J-C remains un-promoted until amu-rank
  re-scopes it. The JIT warmup/steady-state perfgate policy note stands
  unchanged (the slope method needs no warmup boundary decision because the
  warmup cancels between outer=A and outer=2A terms).
- Artifacts: jc_qualify.clj + jc_crossing_benjamin_t32.edn (raw 18 samples x 6
  arms + gate + fixture hashes) sealed under bench/bulk-carrier/. Node-side
  scratch at benjamin:~/jc_t32 (kept, like jb4_t28, for the next tick).
