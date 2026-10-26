# Native measurement-host candidate observations — 2026-10-26

Tracking: KOTOBA-145 (parent KOTOBA-140; related full19 gate KOTOBA-144).
Source/API: [closed host candidate](../../native-benchmark-host.md).
This packet is not a qualified performance result or an external rerun.

## Preserved first attempts

`measurement-arm-records-r1.tar.gz` SHA-256:
`1bfe8f3ed958ff3fb564db2ac62bfc8435c55533aefcb919069209655dededbb`.
It retains source/lock/observer copies, observations and raw stdout/stderr
for compiler derivations r1/r2, all19 original-library staging, the failed
host parse, successful diagnostic host r2, full-count host r1 and the later
failed refusal campaign controls-r1. Generated ELF/KSEED/payload binaries
are omitted from this compact Git archive; their exact hashes are recorded.
The complete archive including generated binaries remains in task scratch
as `measurement-arm-records-r1.tar.gz` (40 MiB), SHA-256
`0739a65d93fb5dc949878fa04f6ce749c9f865f7aee7c91afc624ce67c656760`.

Amu alone built every compiler, host and workload. Python staged exact
bytes, observed processes and cross-checked records. Execution was native
Linux ARM under the already configured network-disabled Podman environment,
through the shared two-slot admission queue. No quiet-host assertion, C
comparison, official Embench score or independent third-party run occurred.

The original19 source hashes and all declared exports were preserved.
Twelve original-library payloads match the historical M104 image bytes;
seven differ, retaining their newly observed hashes/offsets instead of using
historical metadata. The original xgboost verifier has arity2; that interface
was retained, not changed to match the other18 verifiers.

The first factory/compiler had native F1=F2=F3 and24 native cases, but its
pinned host source contained a stray top-level `+`; actual host compilation
refused. Native source checking identified byte0. The failed source/output
is retained. The corrected compiler r2 again achieved F1=F2=F3, packed-image
equality, unchanged adopted core and24 cases; the two CDCI role images also
retained their original hashes.

## Full-count accounting observation r1

Compiler image:
`72f5c712fee54ace0e0f695b9e74c2e6abd9da5c1da608e1ae7dfc64355fa640`.
Host image:
`92880b9ad61b72f8602ecf3cf557b608332b5fc6b5ac92b8b2c3b1a1a9007d39`.
Observation:
`69093931a67d0c14d9c66164ae99d4a6c57d4ac1bac24850187bf4114631140f`.
Pinned original reference:
`6368bd343086a6c88e0645e31dde82bcdf64742c7b4727cdd56103ef72e9b4cc`.

All19 unchanged original libraries ran at their original registered counts.
All original verifiers returned1. Benchmark fuel, verification fuel and
all17 final arena fields matched the reference exactly19/19. The companion
`arm-full-reference-observation-r1.json` is explicitly an observer-only
cross-check, not a native ordered qualification verdict. tarfind's native
warm seed615896958 produced benchmarkFuel15682841411 and verifyFuel1 exactly.
Offset760 remained nondecreasing across warm/reset/benchmark/verification.

## Refusal failure is not hidden by accounting success

controls-r1 repeated the full19 reference match and passed all8 factory
refusals, but only16/17 runtime refusals: the symlink case was incorrectly
admitted. The native observer therefore exited2, status
`native-candidate-incomplete`. Actual ARM Linux reports O_NOFOLLOW32768;
the candidate had used x86's131072. The host-only fix reuses the existing
ISA-specific `kxrt-f2-flags(0)` (no shared runtime change), and also makes
the read-only open nonblocking before its regular-file/size/hash checks.

The revised host source hash is
`14d71453c7b81c097382782d73833f11199ff0fcc6584470c594bac5298f4c83`.
Fresh compiler derivation, all19 provenance, all refusal controls and full
accounting must be rerun for that hash. Earlier success is not inherited
by the changed byte graph. Built semantic mutants, native ordered
qualification, both ISA full native gates, refreshed root/product pins and
exact-head CI remain mandatory; every performance/qualification flag stays
false until its own evidence closes.

## Corrected ARM slice r2 — terminal success, still not adoption

`measurement-arm-records-r2.tar.gz` SHA-256:
`c03f62f40fcc6b3377aa45331fb841bc1e5a05af00dcd7b3f5f6eb27776a8a58`.
The same generated-binary exclusions apply to this compact record archive.

Fresh compiler derivation r3 completed native F1=F2=F3, packed equality,
unchanged adopted core,24 cases and unchanged CDCI role image hashes. Its
compiler image is
`e86ad0565510de457993e0f256f298ff40672bccdba021c9a75cb50fab23e03e`.
All19 original libraries/exports were regenerated with this same compiler.
Its exact host image is
`96190f2c4a265f883664301aba14a6e44bcae29eb2c8ad813117bcf2655cdec3`.

Actual corrected execution passed8/8 factory refusals and17/17 runtime
refusals, including symlink, wrong payload hash/size/type, malformed args,
changed counts and unmetered/zero/insufficient fuel. It then passed all19
original-count verifiers and matched all19 benchmark fuel, verification fuel
and all17 final-arena reference fields again. The observer terminated0.
Observation SHA-256:
`e76ea01bdc831c15da217daa219c70fac4942d7588ac56e0902ac091982b023c`.
`arm-full-reference-observation-r2.json` records that cross-check without
promoting it to native qualification or displaying candidate timing values.

The current compiler separately passed175 guest/private-runtime refusals
with no output image across all7 formats, plus24 native runtime cases.
Boundary observation SHA-256:
`c6911812d9f3cfd651875382a8d08940c4630f78b9fbb3b0a495254e4a1372b5`.
These diagnostics shared build slots; they were not a quiet-host campaign.

Built semantic timing/reset/accounting/highwater mutants, native ordered
qualification, native x86/full gates, current root/product pin regeneration
and exact-head CI are still open. The candidate is not merged, deployed or
promoted; fullQualification/nativeVerdictAuthority/performanceQualified
remain false.
