# ADR 0216: Schema-directed ability wire values

Status: accepted

## Context

ADR 0215 introduced one bounded `kotoba.value.v1` adapter for JVM and CLJS
typed-ability providers. Its first profile deliberately stopped at scalars and
documents: transmitting KIR record or variant constructor vectors would have
made a compiler representation into a public protocol. That left nominal
records, variants, structural options and results, and typed collections
without a common host-library boundary.

JavaScript numbers also cannot represent every signed 64-bit integer. A bare
number therefore cannot be both interoperable and exact across JVM and CLJS.

Wasm Components already carry these types through the WIT Canonical ABI. They
need the same descriptor authority, not a byte tunnel layered over that ABI.

## Decision

The ability adapter v2 accepts recursively admitted descriptors for records,
variants, options, results, heterogeneous vectors, bounded lists, sets, maps,
and schema references. A provider may add an exact `:schemas` map to resolve
`[:ref :namespace/name]` descriptors. The typed ability descriptor remains
out-of-band authority; full compiler descriptors are never serialized.

The canonical semantic envelopes are:

```clojure
;; record
{:kotoba.record/type :app/request
 :kotoba.record/fields {:id int64-value}}

;; variant
{:kotoba.variant/type :app/choice
 :kotoba.variant/case :count
 :kotoba.variant/value int64-value}

;; option
{:kotoba.option/present false}
{:kotoba.option/present true :kotoba.option/value value}

;; result
{:kotoba.result/status :ok :kotoba.result/value value}
{:kotoba.result/status :error :kotoba.result/value value}
```

Every envelope and record field map is exact. Records and variants retain
their nominal identifier. Lists remain lists, vectors remain vectors, sets
remain sets, and maps remain maps on `kotoba.value.v1`; recursive payloads are
converted according to their descriptor.

Every `i64`, including one nested inside a document or aggregate, uses the
org codec's exact signed-int64 wrapper. Every `f32` or `f64` uses its explicit
float wrapper. This prevents a JVM integer and a lossy JavaScript number from
becoming alternate encodings of the same declared value. The compiler pins
the org codec revisions that implement exact int64 and the shared bounded
encode/decode facade.

For JVM and CLJS providers the physical representation is bounded
`kotoba.value.v1` bytes. For Wasm Components it remains the native WIT
Canonical ABI. Both use the typed ability descriptor as schema authority;
Component calls do not tunnel canonical-value bytes through WIT.

## Consequences

- Actor, I/O, and generated host libraries can share one schema-directed
  semantic value contract without exposing bytes or compiler constructors in
  Kotoba source.
- Malformed envelopes, wrong nominal identities, undeclared variant cases,
  unresolved references, lossy integers, and values beyond the per-ability
  byte bound fail closed.
- This is a versioned expansion from adapter v1 to v2. Hosts must opt into the
  v2 envelope contract when using aggregates.
- Streams, tasks, callables, async results, string indexes, and disjoint-set
  compact profiles remain outside this adapter. They need lifecycle or
  profile-specific decisions rather than generic value serialization.

## Evidence

`value-codec-test` crosses the real byte boundary with a referenced nominal
record containing exact minimum/maximum int64 values, a nested option and
variant, and a list of results. Negative cases prove exact envelopes, nominal
identity, schema resolution, and rejected unsupported types. The NBB test
executes the same schema-directed adapter with JavaScript BigInts.

The Component WIT type renderer maps the corresponding result and nominal
references to native WIT types. Existing Component composition and Wasmtime
tests cover structural option/result payloads through the Canonical ABI, so
the byte adapter is not duplicated inside Components.
