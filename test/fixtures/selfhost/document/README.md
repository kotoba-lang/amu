# Native document runtime candidate

`seed/21-check.kotoba` now appends implementations for `document-f64`,
`document-f64-value`, `document-print`, `document-read` and `document-sha256` to modules using
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
`document-sha256` validates the same canonical encoding and hashes its raw
bytes, not the hex print or EDN text. The eight-function integer core in
`compiler/sha256_bits.kotoba` follows [FIPS 180-4](https://csrc.nist.gov/pubs/fips/180-4/upd1/final)
and is alpha-renamed into a third literal runtime fragment. It has virtual
padding and one reusable schedule; the input is read-only and mutable vectors
are fresh private state. It calls no hash capability or host crypto. It does
not impose the hex printer's 32768-byte restriction on digest input. Existing
native string-pool limits and EDN representation restrictions remain open
qualification boundaries; this source change does not qualify the whole
document domain or the SHA2 library.

The positive corpus has thirteen independent wire anchors covering all eleven
existing kinds, round trips, scalar f64 boundaries, zero identity across
equality/map/set operations, Unicode/escaping and i64 extrema. `main` must
return 31. Each of the eighteen `refuse-*` exports must trap; normal return
is failure. The complete formatter exponent-boundary corpus also remains
required, as does the full Kami input-map component.

Additional required native corpora:

- `native/document_sha256_test.kotoba`, main=15: all original thirteen digest
  and thirteen wire anchor bodies, signed-zero/type identity, canonical byte
  lengths 55/56/63/64/119/120/127/128, the print boundary and the full existing
  65536-byte document payload. Existing representation/resource gaps may still
  refuse the full gate; do not skip its large cases to obtain a pass.
- `native/sha256_bits_test.kotoba`, main=31: complete core module import,
  standard message shapes, padding boundaries, arbitrary/non-UTF8/zero bytes,
  65536-byte inputs, repeat calls and input immutability. This requires real
  native project/module resolution, not a flattened hosted substitute.

Digest constants are independent Python hashlib authoring data, including
the preexisting owning language anchors. No Kotoba source was evaluated to
produce an expected digest. These are unexecuted tests, not passing results.

**Not compiled or executed through a qualified loaderless Amu selfhost route.**
Delimiter, private-call closure, literal byte parity, formatter alpha-equivalence
and whitespace reviews are source checks only. They do not establish compiler
admission, a type check, runtime success, self-reconstruction or product closure.
The adopted bootstrap/fixed-point pins are intentionally unchanged: this source
candidate cannot inherit the old receipt. No C-loader/hosted fallback is used
to obtain a passing result. Keep the PR a draft until the complete qualified
build/link/package/launch and positive/refusal/fuel gates actually run.
