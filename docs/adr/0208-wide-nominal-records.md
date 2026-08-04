# ADR 0208: wide nominal records and generated schema references

Status: accepted

## Context

The canonical `defrecord` surface inherited the five-parameter callable ABI
limit even though the owned record value profile already admits 32 fields.
Provider schemas such as an HTTP request have six fields, so otherwise ordinary
Kotoba code had to retain `record-new`, `record-get`, and a hand-written
namespace `:schemas` table.

## Decision

`defrecord` admits one through 32 unique fields, matching the record value
profile. Direct `->Type` calls lower to `record-new` at widths above five;
`map->Type` continues to require one literal map with exactly the declared
keys. Constructors of at most five fields remain first-class functions. A wider
constructor does not become a callable value because doing so would exceed the
truthful bounded function ABI.

A defrecord whose field graph already uses closed `[:ref ...]` edges registers
its descriptor in the namespace schema table under `:namespace/Type`. This
makes the generated nominal identity available to parameter types and nested
collection descriptors without duplicating `(:schemas ...)`. An explicit
namespace schema with the same identity is rejected rather than silently
shadowed. Legacy defrecords containing nested inline nominal descriptors remain
valid but do not receive an automatic schema reference; authors can replace the
inline edge with the generated `[:ref ...]` form.

## Consequences

Wide records are data, not a back door to wider functions. Source can use
ordinary constructors, keyword projection, `get`, and destructuring while KIR
and Wasm retain the existing bounded record representation. The schema table
continues to be closed and validated before type compatibility is admitted.

## Evidence

`record-protocol-static-dispatch-test` covers a six-field HTTP-shaped record,
generated references inside a typed set, direct and map construction, ordinary
field projection, exact execution results, and schema collision rejection.
