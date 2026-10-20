# gpu-workgroup-ratios-m1max-20261019 — within-round ratio protocol, Apple M1 Max

Verbatim stdout of `kbb --backend sci scripts/test-gpu-workgroup-ratios.cljk`
(five consecutive runs, each a fresh process), 2026-10-19 JST, on the amu-gpu
bot host. `EXIT=0` lines are the script's own process exit. The logs in this
directory are run-1.log .. run-5.log.

## Provenance

- Command: `kbb --backend sci scripts/test-gpu-workgroup-ratios.cljk`
- Code: branch `bot/amu-gpu-20261019-0035`, base `origin/main` =
  `bea7b9b24a44ebd3d5108e8e356a39c6bed5912d`, plus exactly
  `scripts/test-gpu-workgroup-ratios.cljk`, `tools/kexe_gpu_vulkan.c` (one
  constant: KGPU_MAX_KEPT 4 -> 8, needed for 6 simultaneously kept command
  buffers; byte-identical to the hunk PR #1332 makes for the same reason, so
  the two branches merge cleanly), and this directory.
- Host: Apple M1 Max, macOS 26.4, aarch64-macos. MoltenVK, Vulkan device
  apiVersion 1.3.357, INFO `Apple M1 Max|1.3.357|1024|1` (run logs).
- Workload: identical to the two sweep protocols
  (docs/evidence/gpu-workgroup-sweep-m1max-20261018/ and
  docs/evidence/gpu-workgroup-sweep-m1max-interleaved-20261018/ on branches
  `bot/amu-gpu-20261018-2102` / `bot/amu-gpu-20261018-2307`): one kernel per
  local size W in {32,64,128,256,512,1024}, 2^25 u32 elements per size, 2
  rounds of xorshift mixing; timings are the loader's submit->fence host
  clock (REPLAY nanoseconds). Read-back words 0..3 verified against the
  host's own mixing (`verify=ok` in all runs, per size). All five runs
  exited 0.
- Protocol (what changes against the interleaved sweep):
  1. RATIOS instead of raw times: per round r, ratio t(r,w) /
     median_w'(t(r,w')). Round-common factors (baseline, clock drift,
     thermal state) divide out; the interleaved sweep showed the run-to-run
     baseline shift leaves a residue in raw per-size medians that swamps the
     per-size differences.
  2. MORE ROUNDS: 24 (vs 8), 144 timed samples per run.
  3. ALTERNATING WITHIN-ROUND ORDER: round r replays slots 32..1024 when r
     is even, 1024..32 when r is odd. The interleaved sweep's documented
     residual bias (fixed within-round order favoring one end under a
     monotonic ~3.6 ms within-round drift) is cancelled by construction; the
     script's self-test pins the parity sample->size mapping every median
     depends on.
- The script self-tests before touching the GPU: parser (INFO answer
  carrying its own '|', refusal of short/malformed/out-of-order answers),
  the parity mapping (24 samples per size), median/quartile arithmetic, and
  `analyze` on synthetic streams (a 10% size effect under 2x round-baseline
  variation must come out as exactly gap 0.1, noise 0, fastest W=256; a
  no-effect stream must give gap 0, noise 0).
- Development-time failures that are NOT part of this evidence and produced
  no measurement used anywhere: an earlier attempt glued REPLAY answers
  without separators (the guest accumulator lost its `" "` interleave) and
  was refused by the parser (exit 1); a paren imbalance introduced while
  fixing that refused at parse. Both were fixed before run-1.

## Cross-run aggregation (computed over the five logs)

Command (run from the worktree root; output verbatim below):

```
node -e '
const fs = require("fs");
const dir = "docs/evidence/gpu-workgroup-ratios-m1max-20261019";
const ws = [32,64,128,256,512,1024];
const bySize = {}; const winners = []; const seps = [];
for (let i = 1; i <= 5; i++) {
  const txt = fs.readFileSync(`${dir}/run-${i}.log`, "utf8");
  const run = {};
  for (const line of txt.split("\n")) {
    let m = line.match(/^GPU-WORKGROUP-RATIOS\tRATIOMED\t(\d+)\tratio=([\d.]+)/);
    if (m) run[m[1]] = parseFloat(m[2]);
    m = line.match(/^GPU-WORKGROUP-RATIOS\tRATIOFASTEST\t(\d+)/);
    if (m) winners.push(m[1]);
    m = line.match(/gap=([\d.]+)\tnoise=([\d.]+)/);
    if (m) seps.push([parseFloat(m[1]), parseFloat(m[2])]);
  }
  for (const w of ws) (bySize[w] ||= []).push(run[String(w)]);
}
const med = a => { const s = [...a].sort((x,y)=>x-y); const n = s.length;
  return n % 2 ? s[(n-1)/2] : (s[n/2-1]+s[n/2])/2; };
console.log("per-size ratio medians, runs 1..5, then grand median and across-run range:");
const grand = {};
for (const w of ws) {
  const v = bySize[w]; grand[w] = med(v);
  console.log(`W=${w}  ${v.map(x=>x.toFixed(4)).join(" ")}  grand=${grand[w].toFixed(4)}  range=${(Math.max(...v)-Math.min(...v)).toFixed(4)}`);
}
const order = [...ws].sort((a,b)=>grand[a]-grand[b]);
console.log(`grand ranking: ${order.map(w=>`${w}(${grand[w].toFixed(4)})`).join(" < ")}`);
console.log(`grand gap (runner-up minus best): ${(grand[order[1]]-grand[order[0]]).toFixed(4)}`);
console.log(`per-run winners: ${winners.join(" / ")}`);
console.log(`per-run gap: ${seps.map(s=>s[0].toFixed(4)).join(" ")}   per-run noise: ${seps.map(s=>s[1].toFixed(4)).join(" ")}`);
console.log(`per-run gap>noise: ${seps.map(s=>s[0]>s[1]).join(" ")}`);
const sameWinner = winners.every(w => w === winners[0]);
const allGap = seps.every(s => s[0] > s[1]);
console.log(`PRE-REGISTERED RULE (encoded): same fastest in every run = ${sameWinner}; gap>noise in every run = ${allGap}; STABLE EFFECT = ${sameWinner && allGap}`);
'
```

Output:

```
per-size ratio medians, runs 1..5, then grand median and across-run range:
W=32  1.0133 1.0071 1.0396 1.5703 1.1035  grand=1.0396  range=0.5632
W=64  0.9911 0.9909 0.9945 0.9910 0.9927  grand=0.9911  range=0.0036
W=128  0.9994 0.9677 0.9864 0.9802 0.9859  grand=0.9859  range=0.0317
W=256  0.9811 0.9949 0.9847 0.9957 0.9805  grand=0.9847  range=0.0152
W=512  1.0172 1.0163 1.0081 0.9953 1.0124  grand=1.0124  range=0.0219
W=1024  1.0101 1.0148 1.0136 1.0051 1.0149  grand=1.0136  range=0.0098
grand ranking: 256(0.9847) < 128(0.9859) < 64(0.9911) < 512(1.0124) < 1024(1.0136) < 32(1.0396)
grand gap (runner-up minus best): 0.0012
per-run winners: 256 / 128 / 256 / 128 / 256
per-run gap: 0.0100 0.0231 0.0017 0.0109 0.0054   per-run noise: 0.0659 0.0387 0.0307 0.0293 0.0401
per-run gap>noise: false false false false false
```

## What the five runs say (measured)

- The ratio protocol does what it was built for: the round-common baseline
  divides out (W=64's ratio median is stable to 0.0036 across five
  processes), so what remains is per-size behavior plus within-run noise.
- NO STABLE SIZE EFFECT ABOVE NOISE for this kernel shape. Pre-registered
  rule (script output): a stable effect needs the same fastest-by-ratio size
  in every run AND gap > noise in the runs. Observed: the fastest size flips
  256 / 128 / 256 / 128 / 256, and in every run the best-vs-runner-up gap
  (0.0017-0.0231) is BELOW that run's noise floor (0.0293-0.0659).
- What IS stable across all five runs is small and at the extremes: W=64's
  ratio median is below 1.0 in all five runs (0.9909-0.9945) and W=1024's is
  above 1.0 in all five (1.0051-1.0149), ranges disjoint -- a consistent
  1.4-2.4% relative difference between those two sizes. That is a real
  within-round ratio difference at this resolution, but it is far below what
  would pick a dispatch size (neither 64 nor 1024 is the fastest row in any
  run's ratio medians) and with 5 runs it stays descriptive, not decisive.
- W=32 is the noisiest row by far (across-run range 0.5632, including one
  run where its ratio median was 1.5703). Consistent with the two earlier
  protocols finding W=32 slowest or most erratic in every run.
- Residual bias NOT removed: nothing here separates a workgroup-size effect
  from a per-slot effect (slot k is always the same size). Slot and size are
  aliased in all three protocols. Second-order at this noise level, but a
  future protocol can rotate the slot->size assignment to unalias them.

## What this evidence is NOT

It is not a tuning result and not a vendor dispatch row. At this workload
(memory-bound mixing) there is NO stable workgroup-size effect on M1 Max
above the 2.9-6.6% per-run noise floor, and the fastest row still flips
under a protocol that cancels baseline and order bias. Therefore NO dispatch
row is replaced and the apple workgroup row in
`kotoba.compiler.accelerator-targets` stays provisional (`:measured? false`)
-- neither confirmed nor overturned. Every number here is scoped to THIS
kernel shape on THIS device; flipping `:measured?` needs more than five runs
of one kernel shape (e.g. the compute-bound kernel variant the interleaved
README named as a next slice, and the unaliased-slot protocol noted above).

## Suite state at this commit

`kbb --backend sci --classpath "src:test:$(kbb -Spath -M:test)" run-tests.cljk`
result pasted in the PR at this commit. This diff touches no suite namespace
(one script the suite does not load, one C constant outside the suite, and
this evidence directory).