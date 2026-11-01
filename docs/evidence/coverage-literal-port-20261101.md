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
main and `trust_cli` remain unqualified. Report calculation, verified-evidence
matching, dataset file IO/hash, and runtime migration remain open. No test suite
or legacy oracle was run.
