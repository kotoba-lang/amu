# Native raw FS2 decision source

This changes the canonical decision sources paired with native #205. It
does not build/admit either decision artifact, activate a profile or qualify
runtime behavior. No tests, compiler, decision generator or implementation
were executed or added.

## C1 provider selector

All 26 functions, public names/parameters, operation IDs, grants and existing
provider routes remain. Only `cap-provider` gains two explicit contracts:

- kind 8 (`bytes-v1`, bytes/bytes) and kind 9 (`string-bytes-v1`, string/bytes)
  route to existing provider 5 only for fs/app-data wire 35;
- every other wire with those kinds refuses with -1;
- both ABI metadata words name the same whole contract. Equal discriminators
  do not imply that request/result primitive types must be equal.

Current GMIR main has not admitted these kinds. Its complete canonical
validator and native compiler lowering/encoding remain upstream work.

## C3 typed form decision

All previous 53 function parameter lists and dispatch operations 0–48 remain.
`typed-fs-form-admitted` and op 49 are added:

| Contract | Allowed forms |
| --- | --- |
| 1, string/string | all sixteen original forms |
| 8, bytes/bytes | write 1, append 2 |
| 9, string/bytes | read 0, range 4 |
| unknown kind or form outside 0–15 | refusal |

The native mechanism calls op 49 before path access, requires FS2 for raw
contracts, validates only the framed path as UTF8, and preserves arbitrary
payload bytes. Existing scope-absence op 48 and all refusal/resource rules
remain. These decisions do not grant filesystem authority.

Both exact ISA-matched Amu-produced sealed C1 and handler artifacts need to
be rebuilt/admitted together with the native source. Old cached artifacts
without op 49 or the provider selector cannot qualify this revision. No
C-loader/header-generator equality, hosted oracle, CLJK sugar or KBB-first
condition is introduced.

Complete raw codec/caller integration, native runtime/lowering/admission,
positive/refusal/resource evidence, owning mains/immutable locks and the real
self-rebuild remain open. Source preparation does not complete the whole
byte I/O, hash, compiler or CDCI route.
