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
