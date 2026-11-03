# Exact decimal literal candidate

The checker now asks the canonical integer decimal parser for raw binary64
bits and emits an `__r6-as :f64` constant. It does not generate floating
division, rounded integer conversions or a guest text-parser call. The finite
reader subset supports decimal point/exponent spellings, at most64 bytes and
three exponent digits. Signed zero is preserved. Malformed, oversized or
non-finite tokens stay refused; operators and ordinary symbols stay symbols.

`seed/19-decimal.kotoba` is an alpha-renamed copy of
`src/kotoba/compiler/decimal_bits.kotoba`, plus a token-shape gate matching the
canonical native Form reader. It contains no host conversion or generator.
The module precedes `20-names`/`21-check` in all three current compiler source
manifests. Preserved historical compiler manifests and adopted artifact pins
are unchanged. The candidate cannot inherit their qualification receipts.

The positive native entry `main` must return31 across five groups and26
independent literal anchors: the complete Kami fixture's16-digit fraction,
ordinary values, decimal/exponent spelling, halfway ties, normal/subnormal and
overflow boundaries, integral rounding and signed zero/underflow. Refusal
files must fail compilation for overflow, four-digit exponents, more than64
bytes, malformed exponents and unsupported BigDecimal suffixes. The original
Kami fixture remains unchanged, including all three occurrences of
`0.4117647058823529` and its complete five-API/eight-group coverage.

**This candidate has not been compiled or run through a qualified loaderless
Amu selfhost route.** Source parity, call/arity/delimiter review and manifest
ordering are not native type checking or execution. Require actual native
compile/link/run of this corpus, the full document/formatter corpus and Kami
component, refusal/fuel/authority controls, compiler generations and the
complete C-free build/package/launch closure before merging. No hosted or
C-loader fallback is introduced. Other seed gaps, including top-level float
constants, non-finite reader dispatch and x86 runtime float support, are not
implicitly cleared by expression-literal lowering.
