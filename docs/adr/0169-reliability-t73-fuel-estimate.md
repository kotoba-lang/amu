# ADR 0169: T7.3 crude fuel-estimate

- Status: Accepted
- Date: 2026-07-28
- WBS: T7.3

## Decision

Best-effort compile-time estimate:

- `function-count` + static simple call-sites  
- Charge model aligns with T7.2 (1 unit / function entry)  
- CLI: `clojure -M:fuel-estimate <file>`  

Not a WCET proof; recursion/loops not unrolled.

## Related

- `docs/lang/fuel-model.md` (kotoba-lang T7.2)
