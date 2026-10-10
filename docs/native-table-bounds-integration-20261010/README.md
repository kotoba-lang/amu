# Direct def/use table-bounds adoption evidence (draft)

This SOURCE integration extends local SX commit `d8c766013c2458012f4bb876cbc423878ba2574c`. Root owns repository edits and adoption. The draft adds no independent qualification, guest execution or repository mutation.

Only `seed/41-a64gen.kotoba` changes relative to that commit; the other 15 full16 modules, including the encoder, are byte-identical. Generator: 230,928 bytes, SHA256 `dca3ba1e25a1e12d0ccc7b311060ac05d56d859f4b151dc914ea0a1a54c52d4e`. Reconstructed full16 unity: 1,162,525 bytes, SHA256 `88358abfa2350993ce5176405290cb755b88817f5a938cdcbd9d65f7e59dc798`. Reconstruction uses registered ordered module bytes separated by a newline, with a final newline. Root should repeat this identity check after import.

The semantic change certifies an immediate same-owner two-argument shift/low-mask call followed by a unary immutable split-table reader using the same result temporary. The positive low mask is strictly below total table length. Exact checked helper shape, owner/header walk and original table admission remain required. Only tautological unsigned bounds tests are omitted; original fuel, literal fixups, addresses and loads remain. Unsafe masks, broken def/use, unknown types/owner/shape and nonadmitted calls use original code. The factored SX helper body and inverse records bind the parent exactly.

One-off hand-edit exception: no existing AST refactor rule implements this new semantic admission/emission contract. This is a backend feature, not a repeated mechanical rename or port. Record this reason in the commit message under AGENTS.md; no AST plan/apply/verify execution is claimed. The remaining modules are preserved verbatim.

Saved evidence:

- Native fixedpoint6 closed exit 0: G2/G3/G4 whole native payload and container equality is recorded. Native: 964,656 bytes, `d915fae6ebad27d467054eea8a7663d0fc51d69a9f7ecb706b03352fa77ea1c3`; container: 964,682 bytes, `df197acfa723877c83caeaf4434e2641b12981e5fbfa0a49faf0a918e884b1b4`.
- Selected95 mixed composition `91189c8f93936d1d1358e21c0b9f5b5ae72d570bc0c1435b862e5e7270a6469c` records 90 exact-image reused profiles plus five fresh AES profiles. It is selected functional evidence through composition, not 95 fresh runs, timing or physical-memory qualification.
- Saved AES activation records 16 static impossible guards removed, 288 bytes less code and exact 26,960 literal bytes. It does not observe typed SIR directly.
- Fixture V2 build4 closed exit 0 and saved whole-word comparison removes precisely four CMP/B.LO/BRK triplets (48 bytes) from two adjacent positive sites. Unsafe-mask and let-bound broken-adjacency sites retain checks. All other words are exact except mapped branch and literal-address relocations; ownexports match the shifted payload. V1 succeeded without activation and remains preserved, without calibrating it as a positive witness.
- Calibration2 closed exit 0: result MIN, consumed fuel 3, complete OFF/ON reports equal, arenas zero. Boundary18 closed exit 0 (`00adb9`, session 65793): nine whole pairs equal, including initial fuel 2/3/4, both table halves, signed input -1, unsafe mask15 success/out-of-range SIGTRAP120 and broken-adjacency fallback. This fixture does not supply separate shift-extreme inputs.
- AES short comparison closed exit 0 with three whole observable pairs equal and ON/OFF about 0.96293 (~3.7% shorter exploratory). It includes reset/ABI/validation and provides no calibrated official C score, pure-kernel timing or C≥ claim. No timing rerun is proposed.

`evidence-index.json` stores exact paths, byte lengths, SHA256 identities and the module comparison. Root closures and referenced completion hashes were checked during draft preparation. Adoption remains root-owned; no performance claim or publication follows automatically from this evidence.

Root integration: destination full16 unity is byte-identical (88358abf,1162525B);15 other modules preserved. Bootstrap inventory is byte-identical to the parent; git diff --check passes. Native evidence is reused by exact source content, not a freshly executed repository build. No product binary release or official C score is claimed.
