# Native CLI/CID/FS candidate evidence (2026-10-24)

## Current full33 candidate

Amu main `47f41d0b23f93d2966ed5ae9c1ef128f4941f5a0` (including PRs
#1548 and #1547) is merged into PR #1557. The current manifest has 33
canonical modules. The full source SHA-256 is
`084d18d062c2a62e17fe4486b20f46228b2cb7cdd461218278102eb293f44bb8`.
The native ARM F4, F5 and F6 compiler images match byte for byte at
`d90a65b7db344d6a4ba0448d98f311fabf5386bbbb0c27f8cf9e94a0eb239603`.
The emitted x86 product candidate is `8c6dd949c4abebefd3b3b803c1e57d72341bd21a631300e262854078cddaa9f5`.

| Evidence | Current native result |
| --- | --- |
| `full33-arm-fixed-point.json`, `full33-native-inputs.json`, `full33-artifact-candidate.json` | Exact full33 ARM fixed point and freshly emitted x86/controller candidate bytes; x86 execution is a separate CI gate. |
| `full33-corpus.json` | 146 native calls passed on the current compiler: all 19 Embench, MIR normal and all individual large plus whole-large, GMIR, resource controls and 18 source-pin refusals. Whole-large exited 0 with tracked use 0 and 155,688,217 scope releases. No performance score is claimed. |
| `full33-fs2-arm.json` | 47 native calls, including eight positive FS groups, 13 refusals, 11 observed kernel boundaries, eight child-only kernel errno cases and stage cleanup. |
| `full33-module-lock.json` | 37 native calls, CID block write, KSL2 emission, adopted compiler replay and executable ASCII/Unicode graphs with missing/mismatched/path refusals. |
| `full33-cid.json`, `full33-sha256.json`, `full33-defcid.json`, `full33-defgraph.json` | Native CID structural and SHA-256 vectors, all ten frozen Definition CID vectors, and bounded dependency graph/refusal cases. |
| `full33-project-paths.json` | Generic source graph normalization/discovery, CID lock replay through native compile/execute, Unicode and symlink refusal, and 256-module admission with 257th refusal. |

The exact-head [PR native CI run 40094268227](https://github.com/kotoba-lang/amu/actions/runs/40094268227)
is still running. The local corpus and FS/CID results above are native ARM
execution, distinct from exact-head x86/public/controller CI. Public CLI command execution, caller-wide Definition CID,
complete generic FS race/fault parity and post-merge main CI are open. The
full32 receipts below remain immutable historical comparisons.

## Historical full32 candidate

The candidate includes Amu main `6deb9969392a7fc06319fbedf97cd356128f3c7d`
(PR #1548). `seed/FULL-MANIFEST` has 32 canonical source modules. The adopted
18-module core remains the one semantic compiler; no hosted or C-loader
compiler is part of this qualification.

| Evidence | Native result |
| --- | --- |
| `full32-arm-fixed-point.json` | ARM F4 = F5 = F6 after the controller pin refresh; compiler image SHA-256 `4b06ad3fe4ed8e053e3d28ecfea0ed2d8730ec8e4c465285b89a524af3374718` |
| `core-cold-locked.json`, `core-warm-locked.json` | Independent adopted-core cold, warm, locked, and self-rebuild identities; the core source is unchanged by #1548 |
| `full32-corpus.json` | Historical controller-pin compiler `4b06ad3f…` passed all 146 native calls: 19 Embench, MIR all large and whole-large, GMIR, resource controls and pin refusals. MIR whole-large ended with zero tracked use and 155688217 scope releases. No performance result is claimed. |
| `fs2-current-native-matrix.json` | ARM FS2 fixture: eight positive groups, 13 framing/range/shape refusals, 11 observed kernel boundaries, eight actual kernel errno cases, plus cleanup/retention assertions |
| `full32-aot-arm.json` | 122 bounded Kototama i64 AOT cases; Kotoba-native ordered verdict exit 0, corrupted-observation control exit 1. The gate reads observations through FS2. |
| `module-lock-full32-real-resolver.json` | 37 native calls: generic source resolution, CID block write, KSL2 replay through the adopted compiler, ASCII/Unicode execution and negative cases without stray block-store creation |
| `defcid-full32.json`, `defgraph-full32.json` | Native frozen ten-vector Definition CID and dependency-graph fixture execution/refusals |
| `full32-native-inputs.json`, `full32-artifact-candidate.json` | Source and emitted ARM/x86 product/controller input pins; candidate, not an x86 execution verdict |
| `complete24-gate-pin-audit.json`, `complete24-image-stability.json` | All 24 gate source/image/result/exit/fuel constants match the first x86 CI compilation. The final full32 compiler re-emits the same 24 x86 case images. The first CI run refused stale image pins as `CDCI:E4002`; a later independent preflight found stale controller h3/h4 bindings, now corrected and checked against all five policy hashes. Current controller execution awaits the new CI run. |
| `fs2-current-full32-build.json`, `fs2-current-full32-basic.json`, `fs2-current-full32-extended.json`, `fs2-current-full32-observed.json`, `fs2-current-full32-errno.json` | Historical full32 compiler `4b06ad3f…` built the FS2 image. Native ARM execution passed 21 basic forms, 39 extended abnormal/cleanup cases, 11 observed partial-I/O/signal boundaries, and eight child-only kernel errno injections. Complete path-race/fault parity is still open. |
| `fs2-current-full32-errno-details.json` | Per-case kernel syscall/errno, guest exit/diagnostic and remaining-file observations for all eight injections, with each filter hash and one current FS2 image identity. |
| `module-lock-current-full32.json` | Historical full32 compiler passed 37 native CID/block writer, KSL2 replay, Unicode namespace, actual compiler execution and refusal calls; `actualCompilerIntegration` and `writerReplayQualified` are true. Whole CLI caller integration remains open. |
| `defcid-current-full32.json`, `defgraph-current-full32.json` | Historical full32 compiler executed the frozen ten Definition CID vectors and graph fixture, including the bounded refusal cases. Checked-KIR caller-wide qualification remains open. |
| `*-before-controller-pin.json` | Previous `523544cc…` receipts, including the 146-call corpus, are retained before the controller pin correction. |

The full32 ARM checks ran without network access in a native arm64 Linux VM.
Python staged inputs, verified hashes, and observed process exits; Kotoba
artifacts performed semantic checks. GitHub PR #1557 native ARM/x86 CI and its
post-merge main run determine current CI qualification.

The original FS2, AOT, CID and Definition receipts above were produced before
the gate factory and controller pin refreshes. Current corpus, FS2, CID and
Definition receipts use compiler image `4b06ad3f…`. CI must still establish
current x86, AOT and controller verdicts. Earlier receipts remain historical
evidence.

**Open qualification:** The public Kotoba CLI's 12 commands have request
parsing, but their complete native executions and product dispatch are not
qualified. Definition CID has not been exercised through every checked-KIR
caller, and the FS2 matrix does not prove every path race or fault. The native
product descriptor deliberately keeps broader public compatibility false.
Those boundaries cannot be filled by the earlier full31 receipt, legacy
CLJK/CLJC/Node/NBB/KBB/JVM paths, or a C loader.
