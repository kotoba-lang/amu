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

The closure qualification completed with 42 tests / 536 assertions for the
aggregate ISA boundary, 54 / 683 for aggregate machine IR, 48 / 269 in the
independent verifier, and 965 / 7,633 in Amu. The shared real-process suite ran
14 tests / 639 assertions across x86-64 and AArch64. Its combined held-operation
artifact returned `54`.

External linkage was also exercised, not only inspected: a two-module
`native.lib/add` -> `native.app/main` project was compiled for AArch64, loaded
through the W^X loader, and returned `42`. The admitted evidence had entry
offset `100`, module-graph digest
`4d7bf9d7d1553c6511de7867a3c463c9173d4d0e1b73c88cce9230609e5e846f`, an
empty unresolved-symbol set, and no ambient symbols.

The implementation closure landed as kotoba-native PR 54, kotoba-verifier PRs
26 and 27, and Amu PR 590. The Murakumo admission gate passed the complete
fixture and rejected a copy missing that fixture with exit 90.

Arbitrary code addresses, open-ended variadic parameters, ambient lookup, and
unresolved dynamic linkage remain structural rejections, not native fallbacks.
