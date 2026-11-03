# Native binary64 text corpus

The component is `src/kotoba/compiler/f64_text.kotoba` and the existing exact
integer parser `decimal_bits.kotoba`. It has no hosted numeric printer/parser
or C runtime call. Decimal candidates are checked against the original bits
using the integer parser, not a float intermediate.

The corpus imports that complete two-module source closure. It includes ten
independent text anchors, signed zero, both infinities and NaN refusals, and
four round trips around every finite binary exponent boundary. `main` returns
7 only when all three groups pass. Boundary work is intentionally not replaced
with a smaller scalar subset.

This corpus has not run through a qualified loaderless Amu selfhost route.
No native success, fixed point or compiler primitive admission is claimed.
The existing C-loader receipts are historical evidence and cannot qualify
this replacement under the current owner contract. Do not add a hosted or
C-loader runner to obtain a pass.

The seed now embeds an alpha-renamed, schema-free formatter and connects it
to all four document operations; see `../document/README.md` and
`seed/runtime/document-runtime.json`. Embedding adds no source reads or hosted
generator to the product closure. Next gates are actual native type checking,
compile/link/run, denied-host/refusal controls, canonical-byte conformance and
the full Kami input-map component through qualified selfhost-produced artifacts.
All four primitives remain unqualified until those gates pass.
