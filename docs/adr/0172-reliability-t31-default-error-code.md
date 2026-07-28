# ADR 0172: T3.1 — every reject! carries a stable error code

- Status: Accepted
- Date: 2026-07-28
- WBS: T3.1

## Decision

1. `reject!` 2-arity defaults to `:kotoba.error/subset-reject`.  
2. 3-arity still preferred for specific codes (namespace, pure-product, ambient, …).  
3. Diagnostics always prefer `:kotoba.error/code` over coarse phase codes.  
4. Burn-down of specific codes continues opportunistically; zero code-less rejects.

## Related

- ADR 0170 human diagnostics, ambient 0166, capability 0171
