# ADR 0178: T7.1 zero-charge loop/recur dual-backend

- Status: Accepted
- Date: 2026-07-29
- WBS: T7.1 / T7.4

## Decision

Desugared `loop`/`recur` (`__kotoba_loop_N`) is **zero-charge after first
helper entry** on both backends:

| Backend | Mechanism |
|---|---|
| KIR | Trampoline re-entry skips `charge!` (kir#24 / ADR 0023) |
| wasm | Loop-helper function bodies omit fuel prologue (wasm#35 / ADR 0035) |

`:loop-deep-kit` now runs 10k iterations with **`:fuel 16`** (was 12000).

### Not claimed

- Zero-charge for arbitrary mutual recursion / non-helper tails
- Host wall-clock is still required against `(loop [] (recur))`

## Evidence

- pilot dual-green; goldens refreshed for loop kits
- pins: kotoba-kir `fa2fbb5`, kotoba-wasm `8ef2caf`
