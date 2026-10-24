# Full32 native integration evidence (2026-10-24)

The candidate includes Amu main `6deb9969392a7fc06319fbedf97cd356128f3c7d`
(PR #1548). `seed/FULL-MANIFEST` has 32 canonical source modules. The adopted
18-module core remains the one semantic compiler; no hosted or C-loader
compiler is part of this qualification.

| Evidence | Native result |
| --- | --- |
| `full32-arm-fixed-point.json` | ARM F4 = F5 = F6 after the reviewed gate pin refresh; compiler image SHA-256 `523544cc0d1b78323660e58c6e687d84c69d8eba5bff0c96caa2cd8a54aba466` |
| `core-cold-locked.json`, `core-warm-locked.json` | Independent adopted-core cold, warm, locked, and self-rebuild identities; the core source is unchanged by #1548 |
| `full32-corpus.json` | 19 Embench workloads; MIR main, six individual large entries and whole-large; GMIR main and seven other entries; resource controls and 18 pin refusals. All 146 recorded calls have the expected exits. MIR whole-large ended with zero tracked pairs, vectors, items, heap bytes and regions and 155,688,217 scope releases. No performance result is claimed. |
| `fs2-current-native-matrix.json` | ARM FS2 fixture: eight positive groups, 13 framing/range/shape refusals, 11 observed kernel boundaries, eight actual kernel errno cases, plus cleanup/retention assertions |
| `full32-aot-arm.json` | 122 bounded Kototama i64 AOT cases; Kotoba-native ordered verdict exit 0, corrupted-observation control exit 1. The gate reads observations through FS2. |
| `module-lock-full32-real-resolver.json` | 37 native calls: generic source resolution, CID block write, KSL2 replay through the adopted compiler, ASCII/Unicode execution and negative cases without stray block-store creation |
| `defcid-full32.json`, `defgraph-full32.json` | Native frozen ten-vector Definition CID and dependency-graph fixture execution/refusals |
| `full32-native-inputs.json`, `full32-artifact-candidate.json` | Source and emitted ARM/x86 product/controller input pins; candidate, not an x86 execution verdict |
| `complete24-gate-pin-audit.json`, `complete24-image-stability.json` | All 24 gate source/image/result/exit/fuel constants match the first x86 CI compilation, and the refreshed full32 compiler independently re-emits the same 24 x86 case images. The first CI run refused stale image pins as `CDCI:E4002`; current controller execution awaits the new CI run. |
| `fs2-current-full32-build.json`, `fs2-current-full32-basic.json`, `fs2-current-full32-extended.json`, `fs2-current-full32-observed.json`, `fs2-current-full32-errno.json` | Refreshed compiler `523544cc…` built the FS2 image. Native ARM execution passed 21 basic forms, 39 extended abnormal/cleanup cases, 11 observed partial-I/O/signal boundaries, and eight child-only kernel errno injections. Complete path-race/fault parity is still open. |
| `fs2-current-full32-errno-details.json` | Per-case kernel syscall/errno, guest exit/diagnostic and remaining-file observations for all eight injections, with each filter hash and one current FS2 image identity. |
| `module-lock-current-full32.json` | Refreshed compiler passed 37 native CID/block writer, KSL2 replay, Unicode namespace, actual compiler execution and refusal calls; `actualCompilerIntegration` and `writerReplayQualified` are true. Whole CLI caller integration remains open. |
| `defcid-current-full32.json`, `defgraph-current-full32.json` | Refreshed compiler executed the frozen ten Definition CID vectors and graph fixture, including the bounded refusal cases. Checked-KIR caller-wide qualification remains open. |
| `full32-corpus-before-gate-pin.json`, `full32-corpus.json` | The earlier corpus is retained separately. The refreshed compiler `523544cc…` passed all 146 calls: 19 Embench, MIR main, six individual large entries and whole-large, GMIR, resource controls and pin refusals. Whole-large ended with zero tracked pairs, vectors, items, heap bytes and regions and 155,688,217 scope releases. |

The full32 ARM checks ran without network access in a native arm64 Linux VM.
Python staged inputs, verified hashes, and observed process exits; Kotoba
artifacts performed semantic checks. GitHub PR #1557 native ARM/x86 CI and its
post-merge main run determine current CI qualification.

The original corpus, FS2, AOT, CID and Definition receipts above were produced
before the gate factory pin refresh. The current corpus, FS2, CID and Definition
receipts are listed separately for compiler image `523544cc…`. CI must still
establish the current x86, AOT and controller verdicts. The old receipts remain
historical evidence for the earlier compiler.

**Open qualification:** The public Kotoba CLI's 12 commands have request
parsing, but their complete native executions and product dispatch are not
qualified. Definition CID has not been exercised through every checked-KIR
caller, and the FS2 matrix does not prove every path race or fault. The native
product descriptor deliberately keeps broader public compatibility false.
Those boundaries cannot be filled by the earlier full31 receipt, legacy
CLJK/CLJC/Node/NBB/KBB/JVM paths, or a C loader.
