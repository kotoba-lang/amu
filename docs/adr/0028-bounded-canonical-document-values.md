# ADR 0028: Bounded canonical document values

Status: accepted

## Context

The fleet pilot `kotoba-lang/annotation` exposes a real gap between scalar
maps and nominal schemas. Its public value is an extensible EDN/JSON-LD
document: keys are known in part, extension keys are permitted, and values can
be strings, booleans, integers, nested documents, or vectors. The existing
`:map` remains deliberately limited to keyword-to-i64 data. Weakening that
type, admitting arbitrary JavaScript objects, or silently dropping extension
properties would violate the safety and compatibility goals.

## Decision

Introduce a distinct immutable `:document` value in typed ABI v11. A document
is a canonical tagged tree, never a host object. Its admitted nodes are:

- null;
- boolean, signed i64, finite f64, bounded string, bounded keyword, or bounded
  symbol;
- a vector, list, or set of document nodes;
- a map from document nodes to document nodes. Source keyword keys remain a
  shorthand and are normalized to document keyword nodes.

Every value is validated as a whole with all of these fixed limits:

- maximum depth 8;
- maximum 256 nodes;
- maximum 32 entries in any map;
- maximum 32 items in any vector, list, or set;
- maximum 65,536 aggregate UTF-8 bytes across strings, keywords, symbols, and
  keys;
- unique map keys in canonical document order; keyword-keyword pairs retain
  textual keyword order for compatibility with the original profile;
- unique set items in the unsigned lexicographic order of their canonical
  document bytes;
- no NaN, infinity, functions, host references, prototypes, getters,
  cycles, or shared mutable containers.

Construction and update operations return newly frozen/canonical values.
Map association, dissociation, and merge are deterministic; later maps win,
and exceeding any limit traps instead of truncating. Lookup returns
`[:option :document]`. Scalar accessors also return typed options so a caller
must handle a kind mismatch explicitly. Runtime operations are pure and grant
no capability.

The constructor surface is `document-null`, scalar constructors for
bool/i64/f64/string/keyword/symbol, `document-vector`, `document-list`,
`document-set`, and `document-map`. Container operations are count, set
membership, map contains/get/assoc/dissoc, and right-biased map merge. String,
bool, i64, and f64 accessors return typed options. Container-kind or
scalar-kind mismatches trap; no coercion or truthiness conversion occurs.

Canonical binary encoding and bounded EDN reading/printing cover every
admitted node. The binary encoding defines document identity and the total
order used by sets and non-keyword map keys. Existing keyword map entries keep
their `K <keyword>` encoding, preserving their canonical bytes and digests;
other keys use `D <document-key>`. This gives one map representation rather
than splitting portable documents into keyword-keyed and general-map profiles.

Typed Wasm ABI v11 assigns descriptor tag 18 to `:document`. The browser host
admits older ABIs unchanged and exposes document imports only when the sealed
module uses them. Host-created values are validated and registered; copied or
forged externrefs are rejected at the Wasm boundary. Restricted JavaScript
implements the same representation and limits independently.

## Consequences

Portable document libraries can migrate without pretending heterogeneous data
is an i64 map or exposing ambient JavaScript objects. Nominal records remain
preferred when a schema is closed. `:document` is the bounded extension seam,
not a replacement for application schemas.

Qualification covers the reference evaluator, restricted JavaScript, real
typed Wasm instantiation, hostile host values, limits, canonicalization,
bounded EDN round trips, set and map duplicate rejection, general document-key
lookup and construction, and persistent updates. The
browser host regression suite also proves continued admission of ABI versions
5 through 10, while modules using `:document` select ABI v11.
`kotoba-lang/annotation` is the first fleet consumer and remains a separate
migration so compiler publication is its immutable dependency boundary.
