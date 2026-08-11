# ADR 0245: Thread CLI fuel to the native image

## Finding

The public `compile --fuel N` option reached component compilation but the
single-source core/native branch called `compile-source` without build
metadata. The command succeeded and reported an artifact while silently using
512. Independently, the pinned native ELF packager also wrote literal 512 into
kernel contexts. Metadata, seal, and executing machine could therefore name
different budgets.

## Decision

The CLI passes `--fuel` as `compile-source` build metadata. Amu pins
`kotoba-native` at `15b4a0e24ba2492d741d2f4b40aa7637598d8f84`, whose kernel
packager copies the sealed fuel value and rejects disagreement with the fuel
ABI. `deps-lock.edn` is regenerated in the same change.

The regression gate invokes the public CLI, parses the emitted ELF64 program
headers, and reads the RW context's fuel word. This tests the production chain,
not merely the intermediate artifact map.
