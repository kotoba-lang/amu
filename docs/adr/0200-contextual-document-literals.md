# ADR 0200: Contextual document literals

Status: accepted

## Decision

Admit `(document literal)` as a frontend-only elaboration form. Its single
argument is inert, closed EDN-shaped data: nil, booleans, i64/f64 values,
strings, keywords, symbols, vectors, lists, sets, and maps with arbitrary
document keys. Nested forms are data and are never invoked as Kotoba code.

The frontend lowers the tree before HIR/KIR validation to the existing
`document-null`, scalar, vector, list, set, and map constructors. Keyword map
keys retain the historical shorthand and node accounting; other keys lower to
document nodes. Deterministic reader/elaboration ordering makes JVM and NBB
output identical, while the document runtime remains the authority for
canonical EDN ordering and aggregate UTF-8 bounds.

## Bounds and authority

Elaboration rejects arity errors and enforces the existing document depth,
node, and per-container item limits. Generated forms inherit available reader
locations, so collection and symbol failures point inside the authored
literal. No capability, host import, runtime tag, codec, or backend operation is
added.

## Evidence

`document-edn-test` compares the contextual form's elaborated HIR directly with
the explicit constructor tree, then exercises the same value on KIR,
restricted ESM, and browser Wasm. The public NBB wasm32 fixture uses a general
vector document key and proves JVM-free reader parity.
