# ADR 0185: T1.3/T4.5 named HOF + thread + option/result pilots (43→46)

- Status: Accepted
- Date: 2026-07-29
- WBS: T1.3 / T4.5 / T4.3

## Decision

1. **Named HOF (T4.5 residual):** `map` / `filter` admit a **simple module
   symbol** as unary callback (arity-1 `defn`), in addition to inline `fn` and
   `inc`/`dec`. Unbound or wrong-arity names fail closed at typecheck.
2. **Threading dual-backend (T1.3):** pilot `->` / `->>` / `as->` / `cond->`.
3. **Option/result dual-backend (T1.3/T4.3):** pilot `nil?` / `some?` / `some` /
   `option-value` / `result-ok?` / `result-value` / `result-error` / `not`.

Pilot **43 → 46** (`named-hof-kit` 21, `thread-kit` 36, `option-result-kit` 18).

## Not claimed

- Multi-source `map`, first-class closures stored in locals
- `some->` / parametric option sugar beyond existing if-some path
- Full string-split→collection (T4.2 residual)

## Evidence

- Unit tests + dual-backend conformance goldens
