# gpu-workgroup-compute-m1max-20261019 — compute-bound kernel, within-round ratio protocol, Apple M1 Max

Verbatim stdout of `kbb --backend sci scripts/test-gpu-workgroup-compute.cljk`
(five consecutive runs, each a fresh process), 2026-10-19 JST, on the amu-gpu
bot host. `EXIT=0` lines are the script's own process exit. The logs in this
directory are run-1.log .. run-5.log.

## Provenance

- Command: `kbb --backend sci scripts/test-gpu-workgroup-compute.cljk`
- Code: branch `bot/amu-gpu-20261019-0105`, base `origin/main` =
  `bea7b9b24a44ebd3d5108e8e356a39c6bed5912d`, plus exactly
  `scripts/test-gpu-workgroup-compute.cljk`,
  `tools/kexe_gpu_vulkan.c` (one constant: KGPU_MAX_KEPT 4 -> 8, needed for 6
  simultaneously kept command buffers; byte-identical to the hunk the
  sweep/ratio branches make for the same reason, so those branches merge
  cleanly), and this directory.
- Host: Apple M1 Max, macOS 26.4, aarch64-macos. MoltenVK, Vulkan device
  apiVersion 1.3.357, INFO `Apple M1 Max|1.3.357|1024|1` (run logs).
- Workload: same buffer and dispatch shape as the three earlier protocols
  (docs/evidence/gpu-workgroup-sweep-m1max-20261018/,
  gpu-workgroup-sweep-m1max-interleaved-20261018/ on branches
  `bot/amu-gpu-20261018-2102` / `bot/amu-gpu-20261018-2307`, and
  gpu-workgroup-ratios-m1max-20261019/ on `bot/amu-gpu-20261019-0035`): one
  kernel per local size W in {32,64,128,256,512,1024}, 2^25 u32 elements per
  size (128 MiB), 2D dispatch (32768, 1024/W), read-back words 0..3 verified
  against the host's own mixing (`verify=ok` in all runs, per size).
  WHAT CHANGES IS ONLY THE KERNEL BODY: the sweep kernels do 2 rounds of
  xorshift mixing (6 shift-xor steps) per element before one u32 write and
  measured bandwidth-bound; this kernel runs n-mix = 128 serial,
  register-resident xorshift rounds per element before the same one write --
  64x the ALU per element, identical memory traffic -- so it is
  compute/latency-bound. This is the "compute-bound kernel variant" the
  interleaved sweep README named as the next slice.
- Timing loop and analysis: IDENTICAL to the ratio protocol
  (scripts/test-gpu-workgroup-ratios.cljk, PR #1337): 24 rounds of 6 REPLAYs,
  alternating within-round order (32..1024 on even rounds, 1024..32 on odd),
  144 timed samples per run, and the statistic is the within-round RATIO
  t(r,w) / median_w'(t(r,w')) (round-common baseline divides out). Timings
  are the loader's submit->fence host clock (REPLAY nanoseconds).
- The script self-tests before touching the GPU: parser (INFO answer carrying
  its own '|', refusal of short/malformed/out-of-order answers), the parity
  sample->size mapping (24 samples per size), median/quartile arithmetic,
  `analyze` on synthetic streams (a 10% size effect under 2x round-baseline
  variation must come out as gap 0.1, noise 0, fastest W=256; a no-effect
  stream must give gap 0, noise 0), and -- new in this script -- n-mix
  pinning: the generated GLSL loop and the host read-back JS mirror must both
  carry exactly n-mix mixing rounds, so guest and verifier cannot drift apart
  silently.
- Development-time failures: none for this slice. All five invocations ran to
  EXIT=0 with every read-back verified.

## Cross-run aggregation (computed over the five logs)

Command (run from the worktree root; output verbatim below):

```
node -e '
const fs = require("fs");
const path = require("path");
const dir = "docs/evidence/gpu-workgroup-compute-m1max-20261019";
const ws = [32, 64, 128, 256, 512, 1024];
const bySize = {}; const winners = []; const seps = [];
for (let i = 1; i <= 5; i++) {
  const txt = fs.readFileSync(path.join(dir, `run-${i}.log`), "utf8");
  const run = {};
  for (const line of txt.split("\n")) {
    let m = line.match(/^GPU-WORKGROUP-COMPUTE\tRATIOMED\t(\d+)\tratio=([\d.]+)/);
    if (m) run[m[1]] = parseFloat(m[2]);
    m = line.match(/^GPU-WORKGROUP-COMPUTE\tRATIOFASTEST\t(\d+)/);
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
const slowest = [];
for (let i = 1; i <= 5; i++) {
  const txt = fs.readFileSync(path.join(dir, `run-${i}.log`), "utf8");
  const run = {};
  for (const line of txt.split("\n")) {
    const m = line.match(/^GPU-WORKGROUP-COMPUTE\tRATIOMED\t(\d+)\tratio=([\d.]+)/);
    if (m) run[m[1]] = parseFloat(m[2]);
  }
  let maxw = ws[0];
  for (const w of ws) if (run[String(w)] > run[String(maxw)]) maxw = w;
  slowest.push(`${maxw}(${run[String(maxw)].toFixed(4)})`);
}
console.log(`per-run slowest row: ${slowest.join(" / ")}`);
'
```

Output:

```
per-size ratio medians, runs 1..5, then grand median and across-run range:
W=32  1.0017 1.0008 1.0022 1.0017 1.0025  grand=1.0017  range=0.0017
W=64  1.0001 0.9993 0.9998 0.9992 0.9989  grand=0.9993  range=0.0012
W=128  0.9994 0.9987 0.9995 0.9990 0.9994  grand=0.9994  range=0.0008
W=256  1.0000 0.9990 0.9985 0.9995 0.9989  grand=0.9990  range=0.0015
W=512  1.0000 1.0008 0.9998 0.9998 1.0003  grand=1.0000  range=0.0010
W=1024  1.0001 1.0005 1.0005 1.0005 1.0008  grand=1.0005  range=0.0007
grand ranking: 256(0.9990) < 64(0.9993) < 128(0.9994) < 512(1.0000) < 1024(1.0005) < 32(1.0017)
grand gap (runner-up minus best): 0.0003
per-run winners: 128 / 128 / 256 / 128 / 64
per-run gap: 0.0005 0.0004 0.0010 0.0002 0.0000   per-run noise: 0.0028 0.0020 0.0029 0.0021 0.0020
per-run gap>noise: false false false false false
per-run slowest row: 32(1.0017) / 32(1.0008) / 32(1.0022) / 32(1.0017) / 32(1.0025)
```

The aggregator reads the five logs, re-derives per-run ratio medians,
winners and gap/noise pairs from the printed lines, and computes the grand
medians over the per-run medians (median of five). It contains no measurement
of its own; every number above traces to a run log line.

## What the five runs say (measured)

- The compute-bound kernel does what this slice was built for in ONE respect:
  the ratio statistic TIGHTENS by 10-30x against the bandwidth-bound ratio
  protocol. Per-run noise (median per-size IQR) is 0.0020-0.0029 here vs
  0.0293-0.0659 for the sweep kernel; per-size ratio medians are stable
  across five processes to 0.0007-0.0017 (vs 0.0036-0.5632). The
  compute-bound kernels run long enough that the round-common baseline and
  launch jitter stop dominating.
- EVEN AT THAT RESOLUTION, NO STABLE SIZE EFFECT ABOVE NOISE. Pre-registered
  rule (same as every prior protocol): a stable effect needs the same
  fastest-by-ratio size in every run AND gap > noise. Observed: the fastest
  size flips 128 / 128 / 256 / 128 / 64, and in every run the best-vs-
  runner-up gap (0.0000-0.0010) is below that run's noise floor
  (0.0020-0.0029). All six sizes sit within 0.3% of each other (grand
  ranking spread 0.0027 from W=256 to W=32).
- The one signal that IS stable across all five runs is at the same extreme
  as every earlier protocol: W=32 is the slowest row in four of five runs
  (ratio medians 1.0008-1.0025, above 1.0 in every run, across-run range
  0.0017). In run 2 the printed precision ties W=32 with W=512 at 1.0008
  (the aggregator's strict `>` keeps the W=32 row for a rounded tie, and
  the logs carry no further digits or raw samples to break it), so run 2
  is recorded as tied, not as a W=32 win. At this resolution it is a
  0.1-0.25% penalty -- real as a within-round ratio difference, far below
  anything that would pick a dispatch size, and with 5 runs of one kernel
  shape it stays descriptive, not decisive.
- Residual biases carry over unchanged from the ratio protocol: slot and
  size are still aliased (slot k is always the same two sizes across the
  alternating rounds), so nothing here separates a workgroup-size effect
  from a per-slot effect.

## What this evidence is NOT

It is not a tuning result and not a vendor dispatch row. For this
compute-bound kernel shape on M1 Max there is NO stable workgroup-size
effect above the 0.2-0.3% per-run noise floor, and the fastest row still
flips under a protocol that cancels baseline and order bias. Therefore NO
dispatch row is replaced and the apple workgroup row in
`kotoba.compiler.accelerator-targets` stays provisional (`:measured? false`)
-- neither confirmed nor overturned. The32-vs-field margin is a measured
number scoped to THIS kernel shape on THIS device; flipping `:measured?`
needs more than five runs of one kernel shape per bound (the unaliased-slot
protocol named in the ratio README is still open), and this slice
deliberately does not upgrade the row.

## Suite state at this commit

Gate result pasted in the PR at this commit. This diff touches no suite
namespace (one script the suite does not load, one C constant outside the
suite, and this evidence directory).
