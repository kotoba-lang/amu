# Current native selfhost: all19 original workloads versus C

All19 current original-active-profile bodies completed30 accepted native/C pairs
on authorized zebulun Apple M4:570 accepted pairs. Independent source, guest,
offset, original C/runner receipt, exact fuel, raw samples and statistic audits pass.
No workload qualifies as C-or-better. Matmult alone exceeds the10% RSD threshold;
its new ratio is reference-only and does not overwrite the preceding qualified
paired-copy decision. These are aligned body times, not official Embench scores.
There is no product implementation change in this refresh.

Source snapshot: `af5e55b788487eb71bcc4a21cfef08974b87bbfc`.
Qualified implementation: `5869e7ee14002a520aa77d5a5cdc41e76e7f03ea`.
Current831000-byte native compiler SHA256:
`4c36b9893d7efc6f527d262dfd6c9b957988e5d6b4a759eed5d37339b6a96755`.
Every measured guest is emitted by committed-source integrated generation3 and
matches qualified native generation4 exactly, including offset and original fuel.
The [preceding copy qualification](coscientist-copy-forward-20261006.md) records
the four-generation native fixed point, three integrated generations and gates.

## Fresh same-host comparison

Lower native/C is better. Values are nanoseconds per original aligned body.

| Workload | Native ns | C ns | Native/C | Admission |
| --- | ---: | ---: | ---: | --- |
| statemate | 762.971 | 31.313 | 24.365667x | stable |
| picojpeg | 213133.445 | 11094.382 | 19.210934x | stable |
| nettle-aes | 25790.248 | 1395.766 | 18.477487x | stable |
| edn | 11496.715 | 743.286 | 15.467422x | stable |
| tarfind | 14374.186 | 1003.938 | 14.317809x | stable |
| qrduino | 283303.080 | 21935.568 | 12.915238x | stable |
| nettle-sha256 | 2791.518 | 217.356 | 12.843093x | stable |
| wikisort | 186268.034 | 15187.000 | 12.264966x | stable |
| ud | 532.121 | 53.683 | 9.912226x | stable |
| nsichneu | 723.612 | 78.019 | 9.274787x | stable |
| xgboost | 1361513.095 | 180841.118 | 7.528781x | stable |
| slre | 7841.218 | 1045.199 | 7.502131x | stable |
| huffbench | 53615.269 | 7212.068 | 7.434104x | stable |
| sglib-combined | 41171.781 | 5790.243 | 7.110545x | stable |
| md5sum | 11004.036 | 2494.816 | 4.410760x | stable |
| matmult-int | 3393.438 | 936.103 | 3.625069x | UNSTABLE; reference only |
| depthconv | 121.133 | 34.132 | 3.548940x | stable |
| crc32 | 3935.464 | 1705.576 | 2.307411x | stable |
| aha-mont64 | 1069.221 | 544.266 | 1.964521x | stable |

All19 raw geometric mean is8.276942x native/C, **unqualified** because one entry
is unstable. It is reference-only and is not an official score. This refresh is
not a comparison against historical suite means or a multiplication of earlier
speedups. Previous qualified copy measurements remain historical paired evidence.

Protocol is unchanged: alternating Kotoba/C order,30 accepted pairs per workload,
300ms target/50ms minimum intervals, load at most4, estimated background idle at
least90%, series RSD at most10%. C-or-better qualification requires at least1.05x
C/native speedup and a mean gap exceeding summed standard deviations. Rejected
pairs and unstable outcomes are preserved. Native fuel is checked on every call.
The historical matrix controls original sources, unchanged C and pinned runner;
its old native byte pins are explicitly replaced by current qualified artifacts.

## Evidence-driven next experiment

The largest stable gap is statemate24.365667x. Its current native code has539
functions,499 nonleaf and40 leaf. Frame counts are384 at96 bytes,101 at64,
40 at0,11 at48, and one each at80/160/32. These static counts are not runtime
time shares or a dynamic profile.

A read-only actual SIR/emission diagnostic finds201 returning BL sites in
statemate whose result follows only owned labels, unconditional joins and exact
uncharged identity wrappers to scalar return. It also finds64 such sites in
picojpeg and131 in nsichneu. These are candidate sites, not optimization proofs.
The current compiler recognizes a direct CALL/RET but can miss those terminal
continuations. The first proposed experiment extends terminal recognition while
keeping original register/frame assignment and the existing tail-call emitter.
It avoids reclassifying published nonleaf fuel as private leaf fuel. Full
frameless-tail allocation needs a separate argument-permutation/context proof.

[Prospective hypothesis](evidence/coscientist-current19-refresh-20261006/next-hypothesis.json)
requires a bounded16-step same-function continuation, unique owned labels, no
cycles, exact unchanged scalar result, closed typed uncharged identities and no
effects/fuel/ABI changes. Unknown cases retain the original call. Independent
fullstate/partial-fuel/trap/resource/argument/label mutation proofs, all19
regressions, native fixed point and integrated gates precede fresh rotating
product/candidate/C timing. **This optimizer is not implemented or measured.**
The earlier pair-copy hypothesis remains unimplemented; the new stable measured
ranking gives this continuation experiment priority.

## Content and computation identities

`kotoba.compiler.definition-identity` content addresses alpha-normalized checked
typed KIR, semantic/desugar versions, effect row, interface and direct definition
dependencies. This identifies implementations, not all mathematically equivalent
programs. Unison uses normalized definition/dependency hashes too:
[official explanation](https://www.unison-lang.org/docs/the-big-idea/).

A computation recipe additionally seals canonical arguments and observable
handler/state/resource inputs; that recipe can itself be content addressed.
Definition identity alone is insufficient for reusing effectful results or
bypassing fuel/traps. Reusable specialization/proof artifacts must also seal the
compiler, target, ABI and optimization contract. The native DefCID/artifact/result
cache bridge remains unconnected. This refresh freshly executes every body.
See the [identity contract](coscientist-content-address-20261005.md).

## Replay and boundaries

[Summary](evidence/coscientist-current19-refresh-20261006/summary.json),
[independent audit](evidence/coscientist-current19-refresh-20261006/audit.json),
[checksums](evidence/coscientist-current19-refresh-20261006/checksums.sha256),
[raw evidence](evidence/coscientist-current19-refresh-20261006/timing-proof.tgz).
The archive contains every raw accepted/rejected row, current guests, exact C
dylibs and prior build/environment receipt, pinned runner and load sampler,
prospective registration, orchestration and independent audit scripts, all19
unchanged source inputs and complete current SIR/emission censuses. The preceding
integrated archive is cross-pinned by SHA256 in summary.json.

One-off bootstrap diagnostic/packaging authoring is an exception for new research
tools; no product refactor, host fallback or changed benchmark workload is used.
Recorded orchestration scripts retain their absolute roots. The additional
`replay-audit.py` and `replay-tail-census.py` use the extracted source snapshot and
censuses directly; both passed independently after extracting the final archive
into a new directory. Original C build
commands and upstream archive/file hashes are retained in the C receipt.
C-or-better across all19 and100% own-source product qualification remain open.
Rung records, product selection and wire20 grants are unchanged. The PR is draft.
