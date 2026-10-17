# Self-recursive nested-callee inline admission

Status: **fixed point reproduced; no official port image changed**.

The compiler candidate adds a direct-self-call exemption to T2's nested-callee
speculative-inline admission check. It was rebuilt from the previous native
selfhost compiler on macOS arm64. The three generated compiler payloads were
byte-identical:

| Generation | SHA-256 |
| --- | --- |
| G1 | `ef2ceb749edfa8a3aeae3845612d377d9fcfcb498e4775f926f7ccaff8e6b541` |
| G2 | `ef2ceb749edfa8a3aeae3845612d377d9fcfcb498e4775f926f7ccaff8e6b541` |
| G3 | `ef2ceb749edfa8a3aeae3845612d377d9fcfcb498e4775f926f7ccaff8e6b541` |

The native compiler successfully regenerated all 19 pinned Embench translated
ports. Each image SHA-256 matched the immediately preceding candidate at
`workspaces/codex/amu-statemate-loop-call-inline-20261017/attempt-2/all19-candidate-2/images.json`.
The compilation receipt is
`workspaces/codex/amu-statemate-recursive-inliner-20261017/attempt-3/all19-candidate/report.json`;
the new image table is beside it as `images.json`.

Because no image changed, this attempt has no new runtime or exactness claim.
The preceding candidate's 12 changed images passed the official exactness
harness in
`workspaces/codex/amu-statemate-loop-call-inline-20261017/attempt-2/exactness-12-escalated/report.json`.
The current host is heavily loaded, so no performance timings were collected.
