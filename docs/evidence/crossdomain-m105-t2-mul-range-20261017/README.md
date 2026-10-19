# T2 multiplication interval analysis

Status: selfhost fixed point and port build passed; no native image changed; no runtime claim.

## Hypothesis and counter-hypothesis

T2 already tracks bounded signed ranges for constants, parameters, addition, subtraction, non-negative AND, and bounded phis. A vector index such as `base + stride * i` can remain unknown when `i` has a finite tracked range. This candidate added a conservative multiplication transfer using the four endpoint products. Because tracked endpoints are signed i32, each endpoint product fits signed i64; the existing range constructor keeps only products inside its signed i32 domain and returns unknown otherwise. Unknown or empty inputs also remain unknown.

The counter-hypothesis was that no pinned access relies on such a proof, or that T2's bounded recursive analysis cannot carry the product range to a useful access.

## Build and disposition

The candidate reached a G1=G2=G3 selfhost fixed point at `6641a18dd0d9d33b4afa14fc7fad4e08805358b325b2945e4c7b3ed8e1a33465`. It compiled all 19 pinned ports. Every native image SHA-256 matched the exact-source control, so this transfer has no current Embench image reach. No exactness rerun or timing comparison was needed; no runtime benefit is claimed. Keep the rule unpromoted.

## Provenance

- Candidate source SHA-256: `61a427fd10f713154fc40fdc25ca66c9b156170f189c07e67e79d8d019660307`
- Control source SHA-256: `79c91e352296237547c0e6b801b690bc7384f828699135833954b20a245d35c4`
- Fixed-point build: `workspaces/codex/amu-t2-mul-range-20261017/attempt-2/build/build-report.json`
- Port build and image table: `workspaces/codex/amu-t2-mul-range-20261017/attempt-2/all19-candidate/`
- Candidate patch: `workspaces/codex/amu-t2-mul-range-20261017/attempt-2/source.patch`
