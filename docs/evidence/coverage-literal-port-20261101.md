# Coverage digest and month validators — 2026-11-01

This is an intermediate W2 source port for AWAI-47. Current Amu `origin/main`
`9d244200e66d3c38557fe710037045da3c757b86` contains
`src/kotoba/compiler/coverage.cljk`, whose `sha256?` and `month?` use regex
reader literals. No canonical `.kotoba` module for this namespace existed at
that source revision.

The new `src/kotoba/compiler/coverage.kotoba` provides pure, byte-oriented
`sha256?` and `month?` validators in canonical Kotoba. It preserves the
`[0-9a-f]{64}` and `YYYY-(01..12)` shape constraints without regex sugar.
Source SHA-256: `9b58e2366c46ddf3c2f18db07340e5f91351a919cccf968335e003933d826190`.

Command: `bin/amu check src/kotoba/compiler/coverage.kotoba` — output `ok`.
The native CLI image SHA-256 is
`14df059566c27d6deaf5ff5915a1f2b8d5717db87926944bd6869639114829b6`;
`cli.json` pins full compiler SHA-256
`0df05effcc0624e94403e8aaf1780feab564de1b44b322680f5535582adb6c04`.
The root descriptor calls that full compiler a diagnostic candidate. No test
suite or legacy oracle was run for this port.

This does not yet port manifest schema validation, report calculation,
dataset file/digest verification, or `trust_cli` wiring. No old runtime path
has been removed or qualified by this module alone.

## Manifest schema validation source slice — 2026-11-01

`coverage.kotoba` now also contains an internal `manifest-valid?` over Amu's
native `:document` values. It checks exact map keys and types; dataset identity
lengths, timestamp and SHA-256; interactive-web population; ordered month
range; threshold bounds; observation count, platform uniqueness, exactly one
unknown share and a 10000-bps total; and support status/path/evidence rules,
including support-platform membership in observations.

Command: `bin/amu check src/kotoba/compiler/coverage.kotoba` — output `ok`.
At this point in the work, this proved source admission only. The validator
was not yet exported or wired into `trust_cli`; the single-file checker had
rejected the attempted public `:document`-argument export with E2104, so the
callable module boundary still needed a qualified multi-module route. Report
calculation, verified-evidence matching, dataset file IO/hash, native execution
parity and runtime qualification remain open. No tests or legacy oracle were
run for this slice.

## Locked public validator admission — 2026-11-01

Made `manifest-valid?` a declared public function. A two-module KSL2 project
lock imports it from a Kotoba caller. The check passed with the open Amu
KOTOBA-13 candidate at commit
`d673111b66f43a8569e545c772a70e51737e1707` (local native bootstrap CLI SHA-256
`ae94dc99ffe489ef77cb5eb0044bea1d2500a4273d45c55bcf57b887994f390a`). The
locked source set was exactly `coverage.kotoba` SHA-256
`f7cf8b400a1cbca7cb11d05f35a5a333aa44f53487bbb60778d5336839a2bf90` and the
small Kotoba caller SHA-256
`cf2900407f6ffb621f0455790e7dbf7265f9aed2a52d6877810756d14b20a59d`; KSL2
lock SHA-256
`7a78de350ed6b588db5a637438eff872c8f2f454e269ce3e083f2d4cc4a03914`.

Command: candidate `bin/amu check <entry.kotoba> --source-lock <project.ksl>`
— output `ok`. This confirms locked project source admission and public
signature resolution only. It does not execute the validator or establish
manifest semantic parity. The Amu candidate is open/unmerged; production Amu
main and `trust_cli` remain unqualified. Report calculation, verification of
the evidence-matching predicate, dataset file IO/hash, and runtime migration
remain open. No test suite or legacy oracle was run.

## Verified release evidence matching source admission — 2026-11-01

Added the public pure `release-evidence-valid?` predicate. It validates the
verified-evidence vector shape, finds each release digest by digest key,
requires the verified platform to match, and checks that verified paths cover
the release paths. Duplicate verified digests keep the final matching entry,
matching the CLJK report's digest-index behavior. Support paths are already
restricted by `manifest-valid?` to `:wasm` and `:native`; the check tests those
members explicitly because the current Amu project candidate refuses
`document-set-at`.

A locked two-module Kotoba caller importing `release-evidence-valid?` passed
candidate Amu `check` at `d673111b66f43a8569e545c772a70e51737e1707` (CLI image
SHA-256 `ae94dc99ffe489ef77cb5eb0044bea1d2500a4273d45c55bcf57b887994f390a`).
Exact source SHA-256:
`86f70173e58a5cc21652f0c810f8d6c5a6cf42240b8f11969cc5d541fb7137b8`; caller
SHA-256:
`2fcaefa4803b13f526fc63ada0156af99054d35666ba00daea4a53095307759a`; KSL2
lock SHA-256:
`7e35f4e77319be5b69f1b09cfa4855a4e565d6af31fc5ee9d54bd6e1345f8747`.

This is locked source admission and signature resolution only. It does not
execute this predicate or establish CLJK semantic parity. Report calculation,
dataset file IO/hash, `trust_cli` wiring, and production Amu qualification
remain open. No test suite or legacy oracle was run.

## Report calculation locked source admission — 2026-11-01

Added public `report`, returning a typed Kotoba `Result`. It validates the
manifest and verified-evidence vector, rejects release evidence with a missing
or mismatched digest/platform/path set, then computes unknown and identifiable
share, released supported share, floored coverage bps, threshold outcome and
release platform set. The release set is formed by reading a serialized set of
validated keywords through the native document reader; this avoids introducing
a host or legacy EDN runtime.

A locked two-module Kotoba caller importing `report` passed the candidate Amu
`check --source-lock` at commit
`d673111b66f43a8569e545c772a70e51737e1707`; bootstrap CLI image SHA-256
`ae94dc99ffe489ef77cb5eb0044bea1d2500a4273d45c55bcf57b887994f390a`.
Source SHA-256: `088f256c735e65577c2c5ca52de806435de81f8b2ff963861329aaa0a8a6f2a8`;
caller SHA-256: `d60465940aad335b8c8681db0edb2d3c855483dbe939e26355a04796abf536c3`;
KSL2 lock SHA-256: `8b38992d11b96bea99fa0a2ed4e8232c9aeabac665a801f4b24be74f1adca9f5`.

This verifies locked source admission and public signature/dependency
resolution only. The function was not executed; report parity, dataset file IO
and digest verification, `trust_cli` wiring, and production Amu qualification
remain open. No test suite or legacy oracle was run.
