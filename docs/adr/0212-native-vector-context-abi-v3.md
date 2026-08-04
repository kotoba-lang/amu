# ADR 0212: bounded native vectors and context ABI v3

- Status: Accepted
- Date: 2026-08-04
- WBS: T1.4 native maturity; closes the homogeneous-vector native host gap

## Context

The native backends could emit the homogeneous vector operations, but the
signed-kexe host context ended at the string callbacks. A valid native artifact
using `vector-i64` or `vector-f64` therefore had no executable host table. KIR,
Wasm, JavaScript, and ClojureScript coverage did not prove native execution.

The source-language surface should not expose this boundary. Authors keep the
data-shaped vector literal and the existing closed collection operations;
handles, arena offsets, and callback slots are an implementation detail.

## Decision

Context ABI v3 appends six callbacks at offsets 152 through 192:

1. empty vector allocation;
2. append;
3. count;
4. trapping indexed read;
5. immutable indexed replacement;
6. suffix view.

A vector value is a positive handle into a 4,096-entry table. Each entry is an
`(offset, length)` slice of a 65,536-word arena. One vector remains bounded to
16,384 items, matching KIR admission. The element words are untyped at this
layer: an f64 is already carried by its exact IEEE-754 i64 bit pattern.

`conj` may append without copying only when the source slice ends at the arena
top. Existing handles retain their old length, so the appended word is outside
every earlier value. `assoc` always copies. `drop` allocates a new handle over a
contiguous suffix and copies no elements. Invalid handles, negative or
out-of-range indices, excessive lengths, and either arena's exhaustion trap.

The POSIX and Windows loaders implement the same offsets and bounds. Compiler
JVM and nbb paths emit the same v3 metadata, while the independently pinned KIR,
artifact, native, and verifier repositories provide the corresponding lowering
and validation.

## Syntax quality

The host ABI adds no source syntax. A normal integer vector literal such as
`[1 2 3]` still infers `:vector-i64`; `nth` and destructuring remain
type-directed. The explicit `vector-*` and `vector-f64-*` names remain the
bounded primitive vocabulary when an operation or floating representation must
be stated directly. This is a clean separation: common data stays Clojure-shaped,
while representation-specific choices stay visible only at genuinely typed
boundaries.

## Evidence

- `clojure -M:native-conformance`: 16/16 through a signed kexe and the real
  host-ISA loader.
- Integer cases cover construction, count, indexed access, total fallback,
  append, replacement immutability, and suffix views.
- The f64 composed case covers construction, append, suffix view, indexed
  access, and exact bit preservation.
- The ordinary compiler suite asserts the complete context ABI v3 map for both
  x86-64 and AArch64 artifacts.
