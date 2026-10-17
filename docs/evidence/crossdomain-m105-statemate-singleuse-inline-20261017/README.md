# T2 single-use private callee inline probe

Status: exactness passed for all changed images; not promoted. The experiment
did not change statemate and has no paired timing evidence.

## Hypothesis

Allow T2 to move a private, non-exported, non-address-taken callee into its
only direct call site when that site is inside a repeated or recursive caller,
even when the callee exceeds the usual inline-size limit. The call is moved,
not duplicated. This was intended to remove the repeated `body` call and entry
checks in statemate.

The selfhost compiler reached a three-generation fixed point at SHA-256
`1544a204b003bd3b5ec9831be008fcbd5ffa5a91c44f922a4ca13a1dca539588`. It
compiled all 19 pinned ports. Compared with the preceding recursive-inliner
candidate, only three native payloads changed:

| Workload | Previous bytes | Candidate bytes | Delta |
|---|---:|---:|---:|
| picojpeg | 113,416 | 113,576 | +160 |
| sglib-combined | 50,968 | 51,968 | +1,000 |
| xgboost | 66,052 | 66,732 | +680 |

The three changed images grew by 1,840 bytes total. The other 16 images were
byte-identical to the previous candidate. Statemate stayed at the pinned
264,184-byte image, SHA-256
`6cb09af5443a9e2ce159f2853b92db2e74b887e73a108349c4cde2b65d5e6636`; the
repeated call was therefore not transformed. The precise admission gate that
excluded it has not been isolated.

## Exactness and disposition

The official exactness harness passed all three changed images at their
registered iteration counts: result, fuel accounting, and arena report all
matched. The full receipt is
[`exactness-report.json`](exactness-report.json).

No paired elapsed-time comparison was run. The report's
`localElapsedNsNotAResult` values are diagnostic only. Image growth and
exactness do not establish a speedup. Keep this rule unpromoted until a paired
measurement shows a repeatable benefit; for statemate, return to the repeated
vector-shape guard hypothesis and prove the descriptor invariant and exact
fuel behavior before changing code generation.

Build and image outputs are under
`workspaces/codex/amu-statemate-singleuse-inline-20261017/attempt-3/`.
