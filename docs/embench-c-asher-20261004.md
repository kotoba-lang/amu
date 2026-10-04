# C and Kotoba compiled by Amu: Embench comparison

Measured on 2026-10-04 JST on Tailscale host asher (Apple M4, 10 cores, 16 GiB RAM, macOS 26.2). C uses Apple Clang 17.0.0, -O2, without LTO. Kotoba uses the r6m unified Amu image abcc1318957af7d3a09cfd66c06d17821b5cf47f4c47d02b5620e9e92a24f02e. Amu is the compiler of the measured Kotoba programs, not another independent language entry.

Current comparison coverage: [the canonical-path audit](coscientist-comparison-matrix-20261004.md)
rebuilds and runs all 19 paths through native selfhost Amu. Thirteen have matched
original active-profile alternatives after the CRC32/Montgomery follow-ups; six still need initialization/repetition/
timing alignment. The measurements below are historical and are unchanged.
No full-suite Kotoba score or C-or-better result is established.

## C reference and score

The C sources, upstream main and verification functions are unchanged at upstream commit 09c2ed8c3b7008c95d08b038de4a3f6dc103ed70 (Embench 2.0rc2 workload sources). Each measured interval begins at start_trigger and ends at stop_trigger. Cache warmup and output verification are outside that interval. Five samples per workload are measured; the global scale value is calibrated separately for each program to approximately four seconds and each value is disclosed in comparison.csv/json. This is a custom platform runner, not an execution of the official benchmark_speed.py driver or a result published by the Embench organization.

Using the upstream speed formula `baseline_ms / measured_ms * gsf` across all 19 workloads gives:

| C metric | Measured value |
|---|---:|
| Speed, geometric mean | 38387.81 |
| Geometric standard deviation | 1.910 |
| One geometric standard deviation range | 20101.99–73307.35 |
| Maximum recorded load | 3.28 |

No speed/MHz value is estimated because the effective M4 clock during these runs is not measured. No official code-size score is inferred from raw extraction bytes.

Published official C results for context:

| Embench version | Platform and C toolchain | MHz | Speed | Speed/MHz | Size |
|---|---|---:|---:|---:|---:|
| 0.5 | Cortex-M4, GCC 9.2, -O2 | 16 | 16.00 | 1.00 | 1.15 |
| 1.0 | SweRV-EH2, GCC 10.2, -O2 | 50 | 66.50 | 1.33 | 1.26 |

These published scores use older workload sets and baselines. They are not divided into the current M4 score to claim a speedup. The repository README says it holds only 0.5 results, but the SweRV record itself declares 1.0; the per-result version is retained here.

Sources: [official result repository](https://github.com/embench/embench-iot-results), [upstream scoring method](https://github.com/embench/embench-iot/blob/09c2ed8c3b7008c95d08b038de4a3f6dc103ed70/doc/README.md).

## Paired nine-workload reference comparison

C time below is its timed benchmark body divided by LOCAL_SCALE_FACTOR × GLOBAL_SCALE_FACTOR. Kotoba time is a warmed repeated correctness export, including verification inside that export and per-call ABI arena/fuel reset. Both sides use the complete input/output of these nine translations. Their timing boundaries and data representations are not identical, so this is a port-level reference comparison, not a pure compiler/language efficiency estimate or an official Kotoba Embench score. The ten adapted ports are excluded.

| Workload | C body (µs/iteration) | Kotoba with Amu r6m (µs/correctness call) | Kotoba time / C time |
|---|---:|---:|---:|
| aha-mont64 | 0.670 | 1.062 | 1.58x |
| crc32 | 2.735 | 4.552 | 1.66x |
| depthconv | 0.035 | 2.684 | 75.99x |
| matmult-int | 0.906 | 18.641 | 20.58x |
| md5sum | 2.593 | 12.148 | 4.69x |
| nettle-sha256 | 0.225 | 4.301 | 19.15x |
| tarfind | 2.042 | 14.518 | 7.11x |
| ud | 0.054 | 2.986 | 55.17x |
| xgboost | 167.868 | 16393.463 | 97.66x |

Geometric mean of these nine time ratios: **13.43x** (smaller is better; C = 1). This is not the full Embench suite score. The base64 decoding used for static byte data in several Kotoba ports, runtime representations, output verification, and generated machine code all contribute to the gap.

An official-equivalent Kotoba/Amu full-suite score remains unavailable: ten full upstream bodies, exact initialization/repetition/timing boundaries and a dummy-subtracted size metric remain to be implemented and audited. Reusing the prior single-call stage-0 ratios or scaling them by a published C score would not produce that score.

Evidence: docs/evidence/embench-c-asher-20261004/raw-results.tgz contains unchanged-source hashes, build commands, executable hashes, all timing samples and load checks. The C measurements were calibrated a second time using the warmed initial data; initial-rows.json retains that first run. The nine native batches are retained from the initial run.

Subsequent research, separately measured: [depthconv](coscientist-depthconv-20261004.md)
has a matched batch alternative 24.597x faster than its Base64 reference but
2.901x slower than C. [EDN](coscientist-edn-20261004.md) now has a complete
eight-operation alternative with 5,427 state-cell matches, measuring 14.357x
slower than C. Nine adapted workloads remain without complete alternatives.
These additions do not revise the historical table, its geometric mean, or
produce an official full-suite score.

[Huffbench](coscientist-huffbench-20261004.md) now has a complete selfhost
500-byte codec alternative with 3,309 matching C state cells and a separate
matched-batch comparison: 60,339.107 ns/body versus C 8,278.511 ns (7.289x
slower). Eight adapted workloads remain without complete alternatives. The
historical table and geometric mean remain unchanged; no official full-suite
score or C-or-better claim follows. Two rejected prototype raw reports await
recovery from offline asher; the baseline report is archived locally.

[NSichneu](coscientist-nsichneu-20261004.md) now has a complete sequential
alternative for all 126 upstream transitions, with 17,272 stage-state matches
and 136 production-chain final-state matches. It is unmeasured while asher is
offline, so there is no new performance ratio. Seven adapted workloads remain
without complete alternatives; historical timings and full-suite score claims
remain unchanged. C volatile globals and owned Kotoba vectors differ in access
semantics; the evidence establishes the recorded sequential state comparisons.

[Nettle-AES](coscientist-aes-20261004.md) now has a complete AES-256 alternative
including both schedules, inversion, and 256-byte encryption/decryption.
12,680 phase-state values and 634 production-body final values match C.
It is unmeasured while asher is offline. Six adapted workloads still lack
complete alternatives; no historical timing or geometric mean is changed
and no official full-suite score or C-or-better claim follows.

[Statemate](coscientist-statemate-20261004.md) now has a complete selfhost
window-controller alternative. All 2,028 staged state values, 169 actual-body
values and 676 repeated-body values match unchanged C. Native check/compile,
batches and bounds/fuel checks pass. It remains unmeasured while asher is
offline; five adapted workloads still lack complete alternatives. The
historical timing table and geometric mean remain unchanged.

[SLRE](coscientist-slre-20261004.md) now has a complete regex-engine
alternative, preserving parsing, branches, quantifiers, captures and
backtracking. Native selfhost check/compile pass. All 33,810 fixture state/
result values and 15 production-body values agree with C, including a replay
with padded short regex buffers and sanitizer-checked oracle accesses.
Batches and bounds/fuel guards pass. asher remains offline, so this adds no
performance ratio or official score. Four adapted workloads still lack
complete alternatives; the historical timing table remains unchanged.

[SGLIB combined](coscientist-sglib-20261004.md) now has a complete alternative
for quicksort, linked-list sort, hash, queue, heap and red/black tree/iterator.
Native selfhost check/compile pass; 9,445 structural and repeated-body values
match C, with batches, bounds/fuel and oracle sanitizer checks. asher is still
unreachable, so no timing ratio or official score is added. Three adapted
workloads still lack complete alternatives; historical timings are unchanged.

[QR codewords](coscientist-qr-codewords-20261004.md) now has a selfhost fragment
for the original input's byte-mode and Reed–Solomon pipeline, with four-input
C differential, unchanged-function selfchecks, table and guard checks.
Framing/placement/mask selection/format remain open. QR is still counted
among the three incomplete alternatives, and no performance ratio or
historical timing is changed while asher is unreachable.

[QR frame construction](coscientist-qr-frame-20261004.md) now also has a
selfhost fragment: all 1,269 base/reservation byte comparisons across nine
boundaries match unchanged C behavior for the original v2 profile. Placement,
mask scoring/selection and final format are still open. Three full alternatives
remain incomplete; this untimed evidence changes no historical performance
ratio or official-score claim.

[QR data placement](coscientist-qr-placement-20261004.md) now connects the
selfhost codewords and frame fragments. All 7,144 image/cursor/component
observations match C, with four unchanged-fillframe final-image selfchecks
and guards/sanitizers. Masks, scoring/selection and final format remain open.
Three full alternatives remain incomplete. asher is offline: this untimed
fragment changes no historical timing ratio or official-score claim.

[Full selfhost qrduino](coscientist-qr-full-20261004.md) now supplies the
complete original v2/L path through eight masks, penalties/selection and
format bits. Native check/compile and 10,048 staged/repeated value matches
pass, including original C verifier and full final images, with guards and
sanitizers. Only picojpeg/wikisort still lack complete alternatives. asher
is offline; no timing ratio or official score is added to the historical
table. The complete comparator's fresh replay is saved for quiet-host runs.

[Full active-profile selfhost WikiSort](coscientist-wikisort-full-20261004.md)
now retains all nine original 400-item inputs and the executed cache-512
algorithm. All 17,710 staged/repeated values agree with C, with full verifier,
guards and resource checks. Original C signed-multiply overflow is recorded;
explicit-wrap sanitizers pass and both C variants have identical observed
states. Only picojpeg still lacks a complete alternative. asher is offline;
no ratio or official score is added and historical timings are untouched.

[Selfhost picojpeg reader](coscientist-picojpeg-reader-20261004.md) now has
9,504 matching C buffer/bit-reservoir observations on the original fixture,
with native guards and original C decoder/verifier/sanitizers. The native
full decoder is still missing; picojpeg remains the last incomplete alternative.
asher is offline, so this untimed fragment changes no historical timing or
official-score claim. The actual C profile is 51×64 YH1V1 with 56 MCUs.

[Selfhost picojpeg headers/tables](coscientist-picojpeg-headers-20261004.md)
now match 4,712 C reader/quant/Huffman/header state values through scan setup,
including the original full-init API comparison and guards/sanitizers.
Native coefficient/IDCT/color decoding remains open, so picojpeg is still
incomplete. asher remains offline; this untimed fragment changes no historical
ratio, ranking or official-score claim. Raw artifacts and fresh replay are saved.


Picojpeg DC/AC coefficients (2026-10-04): native selfhost Kotoba now decodes
all 168 original blocks; 14,740 coefficient/reader/terminal fields match C.
The original C transforms and verifier are retained in the observation
adapter, independently checked with ASan/UBSan (1..32 iterations). A draft
adapter pointer-initialization failure is retained and corrected. IDCT/color
and full reused native bodies remain open; no timing, score or performance
ranking changed. See `coscientist-picojpeg-coefficients-20261004.md`.


Picojpeg complete original active profile (2026-10-04): native selfhost Kotoba
now performs all IDCT/color work for all 56 MCUs, with 33,356 staged and 4,400
reused-body values matching C. Full 1/2/17/32 bodies and original verifier
pass; 32 bodies fit one reused 4,096-cell workspace and minimum passing fuel
7,102,019 without changing bounds/fuel/ABI. Original C ASan/UBSan checks pass
1..32 bodies and all initialized observations. The prior picojpeg coefficient/
IDCT/color/reuse gap is closed for this original input; alternate JPEG APIs
are unqualified. asher is offline, so timing/ranking/official-score claims
remain unchanged. See `coscientist-picojpeg-full-20261004.md`.


CRC32 matched repeated body (2026-10-04): both chunked/scalar table paths
match 2,306 table/prefix/RNG observations each and unchanged C body/verifier
through 32 bodies. Verification occurs once after all bodies; RNG resets
exactly as C at each body. Chunked remains canonical; scalar is an unmeasured
candidate, despite lower fuel. Original C sanitizer checks 1..32 pass. Matrix
coverage becomes 12 matched profiles / seven pending alignments. asher offline;
no new timing, score, ranking or performance promotion. See
`coscientist-crc32-full-20261004.md`.


Aha-mont64 matched full repeated body (2026-10-04): unchanged unsigned helper
AST, ordinary/Montgomery result, partial inverse check and errors agree with
original C at 1/2/17/32 bodies. Original verifier and C ASan/UBSan pass 1..32.
A draft constant-vector bounds exit-code expectation was corrected against
generated comparison/BRK instructions, with failed evidence retained and no
guard change. Matrix coverage becomes 13 matched profiles / six pending
alignments. asher offline; no new timing/score/promotion. See
`coscientist-mont64-full-20261004.md`.
