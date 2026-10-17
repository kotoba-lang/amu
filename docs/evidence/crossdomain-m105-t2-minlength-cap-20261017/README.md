# T2 minimum-vector-length iteration-cap falsification (2026-10-17)

## Question

Would increasing `t2-ml-init`'s alternating interprocedural analysis limit from
64 to 512 passes prove the registered Statemate vector's 169-element shape and
remove the repeated runtime length guard?

## Method and result

The 512-pass candidate and a 64-pass control use the same seed source except
for that single loop cutoff literal. Both were rebuilt from a local native
compiler and each reached a selfhost fixed point at G1=G2=G3.

- 512-pass candidate source SHA-256: `99c418845543c59e4aeeb158ca8aed2c4b3c835edecb7bc4398a22ff68739510`
- 512-pass fixed-point compiler SHA-256: `ee68dad55af866a23ccc1fdcd35197e7e69a2838f04757936bfa1e6246d45b13`
- 64-pass control source SHA-256: `79c91e352296237547c0e6b801b690bc7384f828699135833954b20a245d35c4`
- 64-pass fixed-point compiler SHA-256: `1544a204b003bd3b5ec9831be008fcbd5ffa5a91c44f922a4ca13a1dca539588`
- Both compilers rebuilt all 19 pinned M104 Kotoba ports successfully.
- Candidate and control produced identical native images, kseeds, and export
tables for all 19 workloads (19/19 each).
- Statemate's image is unchanged, so the extra iteration budget did not remove
its registered vector-shape checks.

The compiler binaries differ, but this source-level change did not reach the
registered benchmark application code. No additional exactness or timing run
was needed. This is a falsified optimization hypothesis, not evidence of a
speedup. The per-workload image hashes are in `comparison.json`.

## Limits

This only closes the proposed iteration-cap change for these 19 pinned port
sources and this compiler candidate. It does not show that interprocedural
minimum-length analysis is useless in other programs, nor explain the separate
M104 Kotoba/C timing result. Local build and compile receipts remain in the
local task `workspaces/` tree; this evidence file contains no absolute
machine paths or measurements from a loaded-host timing run.
