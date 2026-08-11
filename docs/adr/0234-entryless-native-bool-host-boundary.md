# ADR 0234: Exercise the entryless native boolean host boundary

## Status

Accepted.

## Context

Native compilation of entryless libraries was qualified, but execution only
accepted integer argument words. The executor also boxed a boolean result from
the optional `main` signature, which is absent for an entryless library. Thus a
compiled export could exist without a truthful typed host call boundary.

## Decision

Preserve declared boolean parameter types through sema and KIR. At execution,
derive the contract from the selected sealed export, accept a host boolean only
for `:bool`, lower it to a native 0/1 word, and box a selected `:bool` result
back to a host boolean. Reject raw 0/1 in boolean slots and booleans in `:i64`
slots.

Require an Amu integration test that compiles an entryless two-export Kotoba
library, signs it, admits it, and invokes both exports through the real native
loader process. The same test owns the two negative type cases.

## Evidence

The native executor namespace passes 48 tests and 140 assertions with the
local sema and tender changes. Inverting boolean word marshalling makes the new
integration test fail twice (integer result 0 instead of 41, boolean false
instead of true). Removing boolean parameters from typed-HIR selection makes
the sema test fail twice because HIR falls to v2 and loses `:param-types`.

## Consequences

This closes one production-shaped scalar slice: source signature through
checked HIR, sealed native artifact, signed admission, real process execution,
and typed host values. It does not qualify aggregate or string values at the
native host boundary, nor does it make native the default application target.
