# Original statemate fuel census: select a closed-chain register hypothesis

The [local constant-index candidate](coscientist-local-constant-index-20261006.md) passed native proof but failed the pre-registered performance rule. This diagnostic changes target selection using actual completed fuel charges on the unchanged original statemate body. It does not measure exclusive cost or produce a new speed/Embench score. The product remains unchanged; C-or-better remains unachieved.

The current native fixed-point product builds both a diagnostic compiler and an instrumentation-disabled compiler directly from Kotoba. Disabled instrumentation produces exactly the product statemate binary SHA256 `5500419beb37f71f0c2ee09c64233170bc853378b082b694025b45ccbe32152d`, 87,716 B, entry offset 85,576. The diagnostic binary differs and is never used for comparable performance timing. No Node/JVM/nbb compiler fallback is used.

A separate supervisor arena contains 65,536 counters, referenced from appended context offset400. Existing ABI fields remain at their original offsets. Generator scratch15 records the current SIR site. Each successful original plain fuel lowering or masked inline charge increments site*2+kind **after** its original charge succeeds. Failed charges do not increment. All original charge instructions and branch/trap/return order remain. The wrapper preserves x16/x17, NZCV and balanced stack; it does not touch x8. Actual statemate SIR has9,739 sites, within the audited limit. This bounded fixed-input diagnostic is not a general instrumentation compiler for arbitrary larger graphs.

Independent Clang assembler encodings match all954 actual statemate counter blocks and651 calibration-image blocks. Every actual counter index lies inside the arena (maximum19,446 and43,830 respectively), with no branch/call inside the twelve-word blocks. The diagnostic adds exactly48 bytes per statemate block. Counts attribute optional inline-wrapper fuel to its emitting call site rather than to a source callee; they are not necessarily function-entry counts.

## Native observations and controls

Thirty conditions (n0/1/2/17/32 × fuel1/2/64/805/806/16,777,216) compare product, disabled, diagnostic and original supervisor:120 executions. Result, trap/exit, remaining fuel, resource counts and all partial vector items agree. On successful runs, completed-charge totals equal published consumption exactly.

| Original bodies | Consumed fuel | Closed mode2 charges | Other leaf charges | Other nonleaf charges |
| --- | ---: | ---: | ---: | ---: |
| 0 | 1 | 0 | 0 | 1 |
| 1 | 806 | 555 | 196 | 55 |
| 2 | 1,545 | 1,110 | 327 | 108 |
| 17 | 12,630 | 9,435 | 2,292 | 903 |
| 32 | 23,715 | 17,760 | 4,257 | 1,698 |

All observed original statemate charges use the plain lowering; no masked inline charge executes in these conditions. Closed mode2 accounts for68.86% of one-body charges and555/739=75.10% of each subsequent body's charges. Those percentages are **charge counts, not CPU-time shares**. The first body contains setup and cannot represent every subsequent body by division.

Forty-two independent handwritten-SIR calibration groups add84 native executions. Known zero/one/multiple loop charges, two leaf calls and a composed clamp with two masked charges match hand-derived result/fuel/count expectations. An independent source-site oracle checks every counter's exact site and plain/masked kind. Four synthetic lost/duplicate/wrong-site/wrong-kind mutations are rejected.

Twenty-two further transaction groups add44 native executions. Clamp-leaf return followed by caller bounds trap has already published the leaf charges. A different masked-write wrapper completes a first write and then fails bounds inside its second write: with initial fuel>=4 it records4 successful internal charges but publishes consumption2, preserving the first partial mutation. This is intentional original leaf transaction semantics. Thus successful internal charge count must not be equated to published consumption on every failure. Exhaustion publishes zero in both cases.

Two oracle authoring mistakes were caught and corrected from the original handwritten SIR: a signed32 clamp example was initially assigned the wrong result, and a caller bounds trap was initially mistaken for a trap inside the leaf. Both native paths agreed and the independent oracles refused the mistakes. Corrected source arithmetic and return/trap order, original failures and native receipts are retained; no admission threshold or semantic outcome was loosened.

There are94 distinct groups and248 native supervisor executions total. Extracted offline replay verifies archive/input hashes, exact disabled product binary/offset, independent source-site counts, mutations and retained transaction states. Replay is not fresh native execution or timing.

## Next registered optimizer

Carry fuel in a reserved register across proved closed mode2 private chains, retaining every original charge and publication point. This differs from rejected sufficient-fuel duplicate regions, cold-failure layout and constant-index lowering. The count evidence gives it a larger dynamic target, not a speed guarantee.

Admission must prove x8 is free across every admitted operation. Public entry loads fuel; private entry skips reload only with a proved carry predecessor and independently verified target offset. Exhaustion publishes zero. Every bounds/handle/other trap and escaping return/tail must expose the same current fuel as the original **closed mode2** route. Existing masked/leaf transaction semantics must not be imported accidentally. Unknown, returning, capability, allocation and incompatible wrapper shapes retain the old route.

Before timing: abstract arithmetic laws, exact source/machine audits, state and adversarial mutation oracles, current593 fixtures/25,658 runs, native three-generation fixed point, and all19 unchanged-workload comparisons. Adoption additionally needs one fresh unchanged-rule quiet-host product/candidate/C campaign. No register optimizer, performance gain or product promotion is claimed here.

Evidence: [summary](evidence/coscientist-statemate-fuel-census-20261006/summary.json), [native build parity](evidence/coscientist-statemate-fuel-census-20261006/build-proof.json), [next hypothesis](evidence/coscientist-statemate-fuel-census-20261006/next-hypothesis.json), [full native source/binaries/counters/states/corrections](evidence/coscientist-statemate-fuel-census-20261006/native-diagnostic.tgz), [extracted replay](evidence/coscientist-statemate-fuel-census-20261006/replay.json), [archive hashes](evidence/coscientist-statemate-fuel-census-20261006/archive-manifest.json).
