# ADR 0215: Canonical ability wire adapter

Status: accepted

Superseded for aggregate values by ADR 0216. The scalar/document v1 decision
and source-level boundary remain valid.

## Context

The legacy `data-host-arg` surface prepared `bytes-ptr` and `bytes-len` in
guest source. Porting that spelling into the canonical compiler would expose a
physical ABI, duplicate the type information already carried by abilities,
and make application code choose a codec boundary.

The compiler already elaborates qualified operations such as `http/post` into
sealed typed ability calls. The org-owned `kotoba.value.v1` codec already
provides the shared value representation used by actor and I/O libraries, but
generated hosts lacked one exact adapter from those typed providers to bytes.

## Decision

`kotoba.compiler.value-codec/ability-provider` builds the exact provider map
accepted by the portable reference runtime and generated CLJS runtime. Its
closed specification contains only request type, result type, an ability-owned
byte limit, and a host `invoke-wire` function:

```clojure
(ability-provider
 {:request-type :document
  :result-type :document
  :max-bytes 65536
  :invoke-wire host-call})
```

The adapter encodes the typed request with `kotoba.value.v1`, invokes the
physical byte transport, checks the same limit before decoding the result, and
returns a normal typed provider value. Existing runtime checks validate the
request before the adapter and the result after it.

The first adapter profile admits scalar values and `:document`. Document
nodes are translated to and from ordinary canonical values at the boundary,
so hosts see maps, vectors, sets, lists, and scalars rather than the compiler's
tagged document representation. Record, variant, option, result, and other
parametric descriptors are rejected until their schema-directed wire shapes
are standardized; encoding compiler-internal vectors would only hide that gap.
Document sets or map keys that are distinct in the document comparator but
equal in the host value model are also rejected instead of being collapsed.

Kotoba source continues to say `(http/post request)` or another qualified
ability operation. `bytes-ptr`, `bytes-len`, codec selection, and transport
layout remain generated-host responsibilities. Unknown adapter fields are
rejected, so transport construction cannot smuggle ambient authority into the
provider registry.

## Consequences

- Actor, I/O, and compiler hosts share the org-owned canonical value codec.
- No raw legacy kgraph operation or pointer/length form is added to the
  canonical language.
- The adapter is synchronous because the currently admitted typed-provider
  contract is synchronous. An asynchronous host contract requires a separate
  runtime decision rather than returning an unchecked promise as a value.
- Aggregate descriptors beyond `:document` remain the next explicit adapter
  gap; they are not serialized as compiler-internal constructor vectors.
- Ability-specific schema and authorization remain outside the codec. The
  namespace declaration, compile policy, provider allow set, and host all keep
  their existing fail-closed checks.

## Evidence

`value-codec-test` compiles a friendly `http/post` document program, executes
it through the portable KIR runtime, observes canonical bytes at the wire
function, and receives the decoded typed result. Negative cases prove exact
adapter specifications and the shared request/result byte bound.
