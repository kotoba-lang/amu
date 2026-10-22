# Resident fuel: frozen timing proof

Copy these three files into an otherwise empty directory and run:

```sh
python3 replay-resident-fuel-timing.py
```

The standard-library-only reader executes no guest or network operation. It verifies the archive envelope and every selected member, immutable source/header/native/C/offset/runner identity, all 57 fresh semantic results and fuel values, all 145 calibration samples and 2,061 attempted arm samples, CPU tick admission, rotations, bounds, means, SDs, and the qualification decision. The independent audit and all rejected trials and preparation/parser failures are retained in the archive. The original separately frozen 484/525 owner inventories remain exact.

The one fresh campaign accepted 570 triples from 687 attempts. AES alone has a qualified 1.095869621× gain against experimental AESv2 (16,529.964 → 15,083.878 ns/body). Its C reference is 1,510.128 ns/body, so the candidate remains 9.988475174× slower than C. No benchmark has a qualified regression or beats C. All 19 are stable; the full-suite geometric relative time is +0.0122123533%, with 18 byte-identical native controls. This is no overall compiler gain claim or official Embench score.

The source-adopted product remains 44bfaa28c/native761856bb. This experiment requires the scoped timing-host mask6 contract; it is neither product adoption nor a general mutable embedding ABI guarantee. Original C binaries are pinned, while absent compiler/flag metadata stays unknown. Earlier actual ISA132 evidence is retained and bound, not a new 132-case run. Semantic preflight elapsed values are never used as timing statistics.

Trust boundary: offline replay checks the retained trusted producer/runner/OS receipts and their arithmetic; it does not re-execute native code, re-measure CPU time, prove a universal host-ownership property, or replace the separately published native semantic proof. Child CPU time is reconstructed from recorded receipt fields. The reader rejects four tested corruptions: altered archive bytes, wrong member hash, missing member, and an invalid uncompressed-size envelope. Manifest and reader integrity ultimately rely on this versioned repository record.

A separate root review copied only the three files into an unrelated directory and replayed them successfully: [offline root receipt](root-replay.json). This receipt records zero native runs and zero measurements.
