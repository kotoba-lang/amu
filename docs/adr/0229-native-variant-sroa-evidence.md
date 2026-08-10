# ADR 0229: native scalar variant SROA evidence follows the pinned closure

- Status: accepted
- Date: 2026-08-11
- Machine-readable companion:
  [`0229-native-variant-sroa-evidence.edn`](0229-native-variant-sroa-evidence.edn)

## Context

ADR 0063 gave sealed native variants a safe legacy representation: a stack
region containing a discriminant and the widest payload, followed by defensive
runtime dispatch. That representation remains useful for wider payloads, but a
non-escaping variant whose cases carry only `:i64` or `:bool` does not require a
stack aggregate.

`kotoba-native` now scalar-replaces that bounded family before GMIR.
Construction creates an internal tag-and-payload SSA bundle. A variant-valued
`if` joins the bundle with two phis, and `variant-match` becomes ordinary
target-neutral tag comparison control flow. The payload expression still
evaluates exactly once and only the selected branch body executes.

## Decision

Amu pins `kotoba-native` `d2e68785092229fef85e0e18e23534563cd80a82`
and the independently matching `kotoba-verifier`
`71c680f0c465f12e3d330d31056c413e00d65468`. The generated dependency lock
binds those exact revisions.

The shared ISA gate lowers a source-level variant-valued branch and match. Its
GMIR has four phis: tag, payload, match result, and the scalar result inside the
boolean case. Both x86-64 and AArch64 allocation plans have zero frame slots
and no spill traffic.

Both production loaders execute both cases as real processes. Argument one
selects the integer case and returns 42; argument zero selects the false boolean
case and returns 7. A zero division in the unselected integer branch does not
execute when the boolean case is selected, while the same division traps when
that branch is selected. A constructor payload that divides by zero also traps
even when its selected branch ignores the payload, proving construction did not
drop or delay payload evaluation.

The verifier independently admits only the all-`:i64`/`:bool` local family: a
direct construction, one local binding, or one same-schema variant-valued
`if`, followed by an exhaustive declaration-order match. It continues to
reject symbol forwarding, schema drift, non-scalar local payloads, and variant
boundary values. The older directly nested legacy match retains its established
wider payload support.

## Consequences

Eligible local variants need neither heap allocation, a variant stack region,
nor a serialized aggregate GMIR operation. The existing scalar GMIR/MIR and
parallel-copy contracts transport the two-word logical bundle.

This does not define variant parameters or results, nested/record payload
scalarization, a general aggregate calling convention, global register
allocation, or Rust-wide performance parity. Those remain separate maturity
increments.
