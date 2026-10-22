# Native document runtime candidate

`seed/21-check.kotoba` now appends implementations for `document-f64`,
`document-f64-value`, `document-print` and `document-read` to modules using
documents. The readable runtime fragments are in `seed/runtime/`; the compiler
embeds their literal bytes and does not read those files or run a generator.
`seed/runtime/document-runtime.json` binds the fragments, formatter and corpus.

The finite formatter is alpha-renamed from `compiler/f64_text.kotoba`. Its
parser adapter calls the seed's existing exact integer decimal parser. The
document group includes that parser and the existing UTF-8 helper group;
its keyword table includes the formatter's two refusal keywords, including
in project keyword-table unions. No JVM, CLJS/Node, hosted numeric conversion,
new C runtime or hosted build dependency is introduced by these sources.

The codec uses the existing `n/b/i/f/s/k/y/v/l/e/m` identity encoding and
`K/D` map-key markers. It preserves f64 bits and normalizes signed zero only
at the identity boundary. Equality, map lookup and set membership compare
identity bytes, so zero aliases do not depend on EDN decimal spelling.
The reader rejects trailing or malformed input, non-finite values, unordered
or duplicate sets/maps, overflow, and depth/node/item/text budget violations.
`document-sha256` remains absent. Existing native string-pool limits and its
EDN token restrictions remain open qualification boundaries.

The positive corpus has thirteen independent wire anchors covering all eleven
existing kinds, round trips, scalar f64 boundaries, zero identity across
equality/map/set operations, Unicode/escaping and i64 extrema. `main` must
return 31. Each of the eighteen `refuse-*` exports must trap; normal return
is failure. The complete formatter exponent-boundary corpus also remains
required, as does the full Kami input-map component.

**Not compiled or executed through a qualified loaderless Amu selfhost route.**
Delimiter, private-call closure, literal byte parity, formatter alpha-equivalence
and whitespace reviews are source checks only. They do not establish compiler
admission, a type check, runtime success, self-reconstruction or product closure.
The adopted bootstrap/fixed-point pins are intentionally unchanged: this source
candidate cannot inherit the old receipt. No C-loader/hosted fallback is used
to obtain a passing result. Keep the PR a draft until the complete qualified
build/link/package/launch and positive/refusal/fuel gates actually run.
