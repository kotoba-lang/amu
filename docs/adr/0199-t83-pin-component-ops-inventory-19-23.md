# ADR 0199: Pin kotoba-component ops inventory wire ids 19–23

- Status: Accepted
- Date: 2026-08-01
- Depends: kotoba-component ADR 0120; compiler ADR 0198 catalog 19–23

## Context

Capability catalog and guest host surfaces use ops wire ids 19–23. Component
ADR 0120 registered those ids in `component-model-v1.edn`. Compiler still
pinned component at pre-inventory SHA and backend-qualification expected set
stopped at id 18.

## Decision

1. Pin `io.github.kotoba-lang/kotoba-component` to the ADR 0120 merge tip.
2. Extend `component-capability-inventory-and-provider-authority-are-closed`
   expected inventory with ids 19–23.

## Evidence

- backend-qualification inventory equality green

## Related

- Closes compiler residual after named catalog + component inventory
