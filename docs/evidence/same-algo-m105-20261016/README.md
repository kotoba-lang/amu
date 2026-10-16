# m105 same-algorithm compiler adoption evidence

This record covers the m105 compiler source integration. It does not report a
new Embench score.

## Source and fixed point

The adopted source is the 16-module `seed/MANIFEST` unity at source commit
`2ee6d9b5b94e64b6fc1e353ab14130f3f660fd78`, SHA-256
`5cdd9f8725201c10d19936ced5d1f8c9a199d645f280b6144c49779381303419`
(2,772,145 bytes). It adds A r7 and B decision-tree lowering with the four
validated step-4 patches. The C LICM experiment is excluded because it failed
fuel and official workload checks.

The three-generation self-build produced the same native image in G1, G2 and
G3: SHA-256
`888b38cea457f4dafc933af70a02403e3e87b59aec58469d6772d7bf7ee3a23f`
(2,547,320 bytes). Its kseed container SHA-256 is
`9d5d594784814ecc550d073073c97a1018f74f9dffae43584dd05f9b27df080b`.
The source and fixed-point record is in [selfbuild.json](selfbuild.json).

The adopted image passed 483/483 result, fuel and state observations and
19/19 official workload functional checks. The four differential-test shards
covered 30,888 cases with zero mismatches. The records are in
[observations.json](observations.json), [official-images.json](official-images.json),
and [difftest-shard1.log](difftest-shard1.log) through
[difftest-shard4.log](difftest-shard4.log).

The policy-native golden was regenerated from the archived original 19 sources
with the adopted image. Its JSON SHA-256 is
`97440b6e3fecf0e3f6c9695698663cadeeb182c3598dfad49790da0471daa1e2`; the
deterministic archive SHA-256 is
`26b2d89aaafa62368ea1772fd2e086d62cab87ba6851af9808556e202c7cab16`.
The regeneration command is:

```sh
python3 docs/evidence/same-algo-m105-20261016/native19-golden.py \
  --output /Users/junkawasaki/github/workspaces/codex/m105-native19-golden
```

The pinned results are [main-same-algo-m105-native19.json](../../../seed/main-same-algo-m105-native19.json)
and [main-same-algo-m105-native19.tgz](main-same-algo-m105-native19.tgz).

## Measurement boundary

The `verify-preserved-integration.py --main` check also passed: it rebuilt the fixed point, verified policy refusals and the policy-free smoke case, and reproduced all 19 pinned original images. Its report is in [preserved-integration.json](preserved-integration.json).

No official m105 Embench round was run. The published 0.8213 ratio remains
specific to m104's pinned compiler source and fixed-point image. Local m105
screening estimates are not an official round and are not substituted for one.
The m104 reproduction package and its measurement pins remain historical.
