# ADR 0277: Self-recur producer home coalescing

## Decision

Pin kotoba-mir `1677cb0d` and kotoba-native `62aaadcd`. On AArch64, the
allocator may assign a unique-use, non-trapping integer producer directly to
its exact self-recur parameter home. The proof is deliberately local: exactly
one self-recur site, equal argument/home arity, one argument occurrence, one
whole-function use at that site, and a straight-line suffix with no call or
control boundary. The home must be free or occupied by an operand whose final
CFG use is that producer; integer instructions read their operands before
writing the destination.

Duplicate and multi-use arguments, `(b, a+b)`, swap cycles, interference,
multiple recur sites, backed values, and any call/control boundary retain the
existing simultaneous parallel-copy path. Non-self calls, fuel charging,
frames, x86-64, and every non-AArch64 target are unchanged.

## Rejected expansion

The KIR-level loop fixture computes its next counter before an intervening
call. Its public parameter home is caller-saved, so pinning that producer to
the home would lose the value. That edge keeps one `x20 -> x0` copy. Moving the
producer across the call or changing entry preservation requires a separate
scheduling proof and is not part of this decision. No allocated-machine-code
peephole is admitted because SSA identity and whole-function use evidence are
no longer available there.

## Evidence boundary

The real source compiler fixture computes both next values after its call, so
both remaining hot-edge moves disappear: each producer writes `x19` or `x20`
and the recur immediately consumes those homes. Its AArch64 artifact is 184
bytes, down from the original 208-byte baseline and from ADR 0276's 192 bytes.
Fuel boundary execution still passes on both available macOS ISA loaders. The
x86-64 artifact remains byte-identical at 256 bytes with SHA-256
`b6da0619229eaf96a8edef7f25443a9565e57c7761b79fa466775f186bab79f2`.

A clean-tree competitive measurement passed the host-load gate (`load1` 6.754
before and 6.854 after, limit 7.5). On that broader modular-mix fixture,
Amu-native's median was 10.46 ns versus Rust's 10.12708 ns (1.03287x Rust) and
Go's 10.86333 ns. This measurement is qualified but is not an old/new paired
measurement of this loop transform: it therefore does not establish transform
speedup, Rust/LLVM parity, or a “world fastest” claim.
