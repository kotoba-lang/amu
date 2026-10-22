# Retired seed scripts (C loader removed, 2026-10-22)

The trusted C loader sources were removed from the seed path:
`seed/bootstrap/adopted-loader-20261012.c`,
`seed/bootstrap/adopted-parser-fuzz-20261012.c` and
`tools/seed-x86_64-linux-loader.c`. Building and rebuilding the compiler now
goes only through Amu selfhost: `selfhost-bootstrap.py` starts from the
pinned Amu-produced root `seed/bootstrap/aarch64-linux-static-root.elf` and
runs on arm64 Linux with no C compiler or loader
(receipt `docs/evidence/selfhost-bootstrap-aarch64-20261022/`).

Every script below built that loader with clang or ran payloads through it.
They are refused or replaced by a C-free port — the table says which. Their
receipts stay in `docs/evidence/` as
historical evidence, and each one names what a selfhost replacement has to
cover before its property counts as qualified again.

| script | what it qualified | status |
|---|---|---|
| build-adopted.py | adopted closure G1..G3 through the C loader (macOS) | replaced: `selfhost-bootstrap.py` step 3 runs the pinned adopted compiler through the C-free aarch64 runner to the same fixed point |
| build-x86_64-linux.py | AArch64-hosted x86 cross compiler (X86_64-LINUX-MANIFEST) | refused: the cross closure has no static runtime; the Linux selfhost closure covers x86_64 output |
| check-x86_64-selfhost.py | x86 G1..G3 and runtime cases through the C loader | replaced: `selfhost-bootstrap.py` steps 1, 2, 4 (static compiler, runners, cases against `seed/static-cases.json`) |
| check-x86_64-static.py | static x86 image bootstrapped through the C loader | replaced: `selfhost-bootstrap.py` (root is Amu-produced, no bootstrap loader step) |
| check-x86_64-linux.py | scalar standalone x86 ELF suite | refused: port the 55 standalone regressions onto the static compiler |
| check-x86_64-aiueos-object.py | x86_64-aiueos-kernel-v1 object ABI | ported: `check-x86_64-aiueos-object-cfree.py` re-qualifies the same ABI and refusal suite on the static compiler (`--target x86_64-aiueos-kernel-v1`) through two C-free producers; receipt `docs/evidence/aiueos-kernel-object-cfree-20261022/` |
| check-adjacent-fuel-reload.py, check-bounded-lookup.py, check-certified-scalar-calls.py, check-mask-direct-source.py, check-nonzero-guard-charge.py, check-positive-quotient-proof.py, check-positive-quotient.py, check-prepaid-fuel-reuse.py, check-sequential-scan.py, check-twoarg-comparisons.py | adopted 41-a64gen optimizations (oracles, fuel, arena counters) through the C loader | refused: re-run the paired controls through the aarch64 runner |
| verify-loader-fuzz.py | fuzz coverage of the C loader's parser | retired with the loader |
| verify-preserved-integration.py, test-preserved-verification.py | frozen-source integration through the C loader | refused: re-run through the aarch64 runner |
| test-x86_64-build-pins.py | orchestration fault injection of build-x86_64-linux.py | retired with that script |
| check-native-source-recovery.sh | native source recovery through the loader | refused: re-run through the aarch64 runner |

The embench reproduction under `bench/embench/reproduce-20261015/` also built
the removed loader; it remains a historical record and is not runnable.
