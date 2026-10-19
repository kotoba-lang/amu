# m105 same-algorithm compiler adoption evidence

This record preserves the initial m105 candidate and its exported-tree review
correction. It does not report a new Embench score.

## Initial m105 candidate

The original 16-module `seed/MANIFEST` unity at source commit
`2f17a378527d07aebb948857b980d6ff0bf53095` had SHA-256
`5cdd9f8725201c10d19936ced5d1f8c9a199d645f280b6144c49779381303419`
(2,772,145 bytes). It added A r7 and B decision-tree lowering with the four
validated step-4 patches. The C LICM experiment is excluded because it failed
fuel and official workload checks.

That initial candidate self-built to `888b38cea457f4dafc933af70a02403e3e87b59aec58469d6772d7bf7ee3a23f`
(2,547,320 bytes), with container SHA-256
`9d5d594784814ecc550d073073c97a1018f74f9dffae43584dd05f9b27df080b`. Its
original reports and golden are preserved under the `*-pre-guard` filenames.

The original candidate passed 483/483 result, fuel and state observations,
19/19 workload checks, and 30,888 differential cases. The observations remain
byte-identical after the review correction. See [observations.json](observations.json),
[official-images-pre-guard.json](official-images-pre-guard.json), and
[difftest-pre-guard-shard1.log](difftest-pre-guard-shard1.log) through
[difftest-pre-guard-shard4.log](difftest-pre-guard-shard4.log).

## Exported-tree review correction (2026-10-16)

The PR's expanded decision-tree bounds also rewrote exported function trees,
which violated the existing bounded-lookup refusal control. The source rewrite
is now gated to private functions by `FF-EXPORT`; exported definitions keep
their reviewed native bodies.

The reviewed source commit is `9892fc06a5f40cf392e02750f5d6a7fa0731a585`.
Its unity SHA-256 is
`4d941a063ca8098aee861ed0ddc3ef59db2e2bd44e9e93189e7b15438849f256`
(2,772,276 bytes). G1, G2 and G3 all produce image
`6b158aa8654706743462b8a730f189072ba05f364b00af28a3f6d23045add2eb`
(2,547,352 bytes); the container SHA-256 is
`e419658b76bce0e30febd9bd22270e23209ec03770b474ebc51bd25f8e36cd02`.
The current self-build records are in [selfbuild.json](selfbuild.json) and
[adopted-selfbuild.json](adopted-selfbuild.json).

The full bounded-lookup acceptance and refusal check passed unchanged, as did
all ten adopted-native regression checks. The current image compiled all 39
sources, matched all 483 result/fuel/state observations, and passed all 19
workload fuel/arena checks. Four fresh differential shards against the
pre-guard m105 image (`888b38…`) covered 30,888 cases with zero mismatches;
the logs are [difftest-shard1.log](difftest-shard1.log) through
[difftest-shard4.log](difftest-shard4.log). The current timer diagnostics are
in [official-images.json](official-images.json); their single-run counters are
validation output, not an Embench measurement.

The policy-native golden was regenerated from the archived original 19 sources.
Its JSON SHA-256 is
`f49615b573ec36f6873ec32bcf0f92b62c1c824bbcadbcc0a6a0e2a283009fea`; the
deterministic archive SHA-256 is
`5bba13726b77a4ac1d056e3eaa48bbde2c05acfdf4ff98d4e419fff683ed0c05`.
The current results are [main-same-algo-m105-native19.json](../../../seed/main-same-algo-m105-native19.json)
and [main-same-algo-m105-native19.tgz](main-same-algo-m105-native19.tgz). The
pre-guard versions are retained in this directory.

The main policy-safety integration also passed: three fixed-point generations,
34 explicit policy refusals, policy-free result 42, and all 19 pinned original
images reproduced exactly. See [preserved-integration.json](preserved-integration.json)
and the compact [guard review record](guard-review.json).

No official m105 Embench round was run. The published 0.8213 ratio remains
specific to m104's pinned compiler source and fixed-point image. Local m105
screening estimates are not an official round and are not substituted for one.
The m104 reproduction package and its measurement pins remain historical.
