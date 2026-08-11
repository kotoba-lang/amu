# ADR 0248: Pin the native held-operation closure

## Decision

Pin kotoba-native aggregate ABI v7 and the verifier that independently accepts
record-payload variant boundaries and boxed locals. Source-level function
references and `invoke` lower to a closed ordinal dispatcher. `apply` consumes
a bounded pair chain and accepts at most four total arguments. No callable
value contains an arbitrary machine address.

`compile-project` now records explicit linkage evidence. Native compilation
submits the SHA-256 module-graph digest, an explicitly empty unresolved-symbol
set, and `ambient-symbols false` to the producer's closed-linkage admission
before emission. Missing, private, and cyclic imports already fail while the
closed graph is linked.

## Evidence

The shared real-process ISA table executes aggregate record payload dispatch,
sealed indirect invocation, and bounded `apply` on x86-64 and AArch64. The
JDK-free CLI compiles, extracts, and runs one artifact combining all three under
the W^X loader. The Windows profiles compile and verify the same source. Project
tests compile a two-module native graph for both target encoders and bind its
linkage evidence to the artifact's project digest.

Arbitrary code addresses, open-ended variadic parameters, ambient lookup, and
unresolved dynamic linkage remain structural rejections, not native fallbacks.
