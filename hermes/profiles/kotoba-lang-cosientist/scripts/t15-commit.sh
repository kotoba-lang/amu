#!/bin/bash
set -e
cd /tmp/langcos/sema-t15
git add src/kotoba/compiler/frontend.cljc
git commit -m "some->/some->> desugar: single canonical temp name (iter 15)

Iter 14 falsified the branch-3f847f9 desugar as non-deterministic:
equivalent spellings produced different KIR. Root cause (measured this
tick, before the edit): the temp name came from *loop-counter* inside
analyze (some-thread__N, renumbered by unrelated loops / collision
avoidance) and gensym outside, so the same source desugared to different
binder names and hence different definition CIDs.

Fix: one deterministic synthetic temp (synthetic \"some-thread\") for
every spelling, same shape as binding-some. No lowering change.

Measured parity matrix (amu --jvm-free, definition CIDs):
- some->  0-let == some->  1-let == nested-let hand twin
  (t bafyreiac7b4vxobujx6ainywyo7xkjtbejd6ygbv2uv3j4aubqb3t4nbqe)
- some->  1-let typed-param == typed-param hand twin
  (t bafyreia2bhjmxm2ljwe7o3urxte2hszr6h2px4wvd6snnvrhid3a7led74)
- some->> 0-let == some->> 1-let == nested-let hand twins
  ((- 100 (option-value ...)) bafyreifh37gjockkt...,
   (- 100 5 (option-value ...)) bafyreieipf6przxla...)
- values: some-> 42, some->> 59 (ALL-OK)
- fail-closed: 0-step some-> / some->> REJECT exit 65 (own diagnostic)
- regression: sema suite 237 tests / 1145 assertions / 0 failures" 2>&1
git log --oneline -1
