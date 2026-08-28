# ADR 0278: AArch64 logical-seeded constant selection

## Decision

Pin kotoba-native `704d02ed`. An AArch64 integer constant may use one
logical-immediate ORR seed followed by one MOVK when that two-word sequence is
strictly shorter than its MOVZ/MOVN wide-move sequence. Exact logical
immediates remain one word, and MOVZ/MOVN wins every equal-length tie.

The selector is closed and local. For each of four 16-bit lanes it asks whether
replacing that lane with zero or `0xffff` produces an architectural logical
immediate, for a maximum of eight recognizer probes. It owns no global table or
index of the 5,334 logical-immediate encodings. Fixed-width branch materializers
remain fixed-width, and x86-64 and every non-AArch64 target are unchanged.

## Structural and semantic evidence

The qualified modular-mix reciprocal `0x8000000100000003` changes from three
wide-move words to one ORR-immediate plus one MOVK. In the fresh core benchmark
bundle, the two occurrences remove eight bytes total: the raw artifact is 724
bytes instead of 732 bytes. The pinned selector test checks the exact two-word
encoding, absence of the former global index, and the eight-probe structural
ceiling.

The merged kotoba-native component passed 192 JVM tests / 2,336 assertions and
6 NBB tests / 12 assertions. Cold selector diagnostics were 5.96 ms on JVM and
8.07 ms on NBB for the supplied corpus; these are diagnostic observations, not
CI thresholds or general compile-speed claims.

The Amu closure passes its focused aggregate boundary suite (5 tests / 49
assertions), full JVM suite (151 namespaces, 1,151 tests / 8,519 assertions),
and the NBB project, locked-classpath, and JDK-free native suites. A fresh W^X
prepare/measure run executes the 724-byte artifact (SHA-256
`9f89d5ab9fdf9f941cd87d20028d8717370dc15a37dce116d56e0ba4e6fc22ea`)
with known result `1830338420` on the available AArch64 host. Its timing is
discarded because host load exceeded the qualification limit.

## Claim boundary

This decision establishes exact instruction-count reduction, bounded selector
work, dependency closure, and semantic execution. It does not establish a
statistically qualified runtime speedup, Rust/LLVM parity, or a “world fastest”
claim. It also does not by itself mint ADR 0277's separately content-addressed,
freshness-bounded fastest claim; that remains the perfgate's decision. Rust and
LLVM remain optional external comparators, not runtime or build dependencies.
