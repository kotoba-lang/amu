# ADR 0174: T7.4 deep loop / fuel envelope dual-backend

- Status: Accepted
- Date: 2026-07-29
- WBS: T7.4 (depends T7.1 partial / T7.2)

## Decision

Add pure-product pilot case `loop-deep-kit`: **10_000** `loop`/`recur`
iterations on KIR + wasm32-kotoba-v1, completing with expected result `42`.

### Fuel

- Charge model remains **1 unit per function entry** (T7.2 / `fuel-model.md`).
- `loop`/`recur` still desugars to a named self-calling helper (T7.1); each
  iteration is a helper entry, so 10k iters need ≫ default 512.
- Case declares `:fuel 12000` (margin over ~10_002 entries: `main` + helper).
- `compile-source` now accepts `:fuel` in emit-metadata (or policy
  `:budgets :fuel`) and bakes it into the wasm fuel global.
- Lang-conformance runner threads case `:fuel` to both backends + goldens.

### KIR pin (kotoba-kir#21 / ADR 0021)

- Compile-time oracle uses raised `oracle-fuel` (fail-open to nil).
- Self-tail trampoline on `__kotoba_loop_N` stack tip so 10k does not blow
  host JVM stack (fuel still charged).

### Not claimed

- Zero-charge `recur` / machine TCO for arbitrary functions.
- Changing the historical default of 512 for unparameterized compiles.

## Evidence

- pilot 22→23 dual-green + goldens (`:loop-deep-kit`)
- `clojure -M:conformance` / `--check-golden`
- ADR 0173 (small loop pilot) remains the unit-scale dual-green
