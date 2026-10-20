# gpu-workgroup-unaliased-shape2-m1max-20261019 — unaliased-slot protocol, kernel shape 2, Apple M1 Max

Verbatim stdout of `KGPU_SLOT_OFFSET=<o> kbb --backend sci scripts/test-gpu-workgroup-unaliased-shape2.cljk`
(six fresh processes, o = 0..5), 2026-10-19 JST, on the amu-gpu bot host.
`EXIT=0` lines are the script's own process exit. The logs in this directory
are run-1.log .. run-6.log (run-N is slot-offset N-1).

This is a REPLICATION measurement: it re-runs the PR #1340 unaliased-slot
protocol with a second kernel shape to test whether that protocol's two
conclusions are kernel-shape-conditional. It is not a tuning result and not a
vendor dispatch row.

## Provenance

- Command per run: `KGPU_SLOT_OFFSET=<o> kbb --backend sci scripts/test-gpu-workgroup-unaliased-shape2.cljk`
- Code: branch `bot/amu-gpu-20261019-0337`, base `origin/main` =
  `bea7b9b24a44ebd3d5108e8e356a39c6bed5912d`, plus exactly
  `scripts/test-gpu-workgroup-unaliased-shape2.cljk`,
  `tools/kexe_gpu_vulkan.c` (one constant: KGPU_MAX_KEPT 4 -> 8, needed for 6
  simultaneously kept command buffers; byte-identical to the hunk the
  sweep/ratio/compute/unaliased branches make for the same reason, so those
  branches merge cleanly), and this directory.
- Host: Apple M1 Max, macOS 26.4, aarch64-macos. MoltenVK, Vulkan device
  apiVersion 1.3.357, INFO `Apple M1 Max|1.3.357|1024|1` (run logs).
- The PROTOCOL is identical to the shape-1 unaliased protocol
  (gpu-workgroup-unaliased-m1max-20261019, branch bot/amu-gpu-20261019-0204,
  PR #1340): one kernel per local size W in {32,64,128,256,512,1024}, 24
  rounds of 6 REPLAYs in alternating forward/reverse slot order, within-round
  RATIO t(r,w)/median-of-round, and the SLOT <-> SIZE cyclic Latin square over
  six fresh processes (slot-offset 0..5) so additive size, slot and process
  effects are mutually identifiable. WHAT CHANGES IS ONLY THE KERNEL SHAPE --
  the second shape the shape-1 README named as the flip bar ("Flipping
  :measured? still needs more than six runs of one kernel shape"). Shape 2:
  2^24 u32 per buffer (64 MiB, 384 MiB live), 2D dispatch (256, 65536/W) --
  a narrow-x grid instead of shape 1's wide-x (32768, 1024/W) -- and n-mix =
  32 serial xorshift rounds per element (4x less ALU per element than shape
  1's 128, 16x more than the bandwidth-bound sweep kernels). Same one u32
  write per element, same read-back verification.
- The script self-tests before touching the GPU (every self-test passed at
  every invocation; all six runs reached the measurement): parser (INFO
  answer carrying its own '|', refusal of a short T field, a malformed read
  field and out-of-order reads), the sample->size mapping (offset 0 keeps the
  parity rule; 24 samples per size at every offset 0..5; explicit offset-2
  facts: size 0 -> slot 2, slot 0 -> size 4), Latin-square balance (all 36
  (size, slot) cells covered exactly once over offsets 0..5), median/quartile
  arithmetic, `analyze` on synthetic streams (a 10% size effect under 2x
  round-baseline variation comes out as gap 0.1, noise 0, fastest W=256; a
  no-effect stream gives gap 0, noise 0), `analyze-slots` on a synthetic
  stream whose slot-0 samples are 10% slower (slot 0 -> ratio 1.1, every
  other slot -> 1.0), and n-mix pinning (the GLSL loop and the JS read-back
  mirror both carry exactly 32 mixing rounds).
- Read-back verification: words 0..3 of every output buffer checked against
  the host's own mixing (generated from the same n-mix the GLSL loop uses);
  `verify=ok` per size in all six runs (36/36; `grep -c verify=ok run-*.log`
  = 6 in each log), and `EXIT=0` in all six logs.

## Cross-run aggregation (computed over the six logs)

Aggregator source (run as `node aggregate-unaliased.js <this dir>`; it is the
shape-1 aggregator unchanged and parses only the printed lines of the run
logs -- it contains no measurement of its own):

```javascript
// Cross-run aggregator over the six unaliased-slot run logs. Derives every
// number from the printed lines; contains no measurement of its own.
// Usage: node aggregate-unaliased.js <evidence-dir>
const fs = require("fs");
const path = require("path");
const dir = process.argv[2];
const sizes = [32, 64, 128, 256, 512, 1024];
const runs = [];
for (let i = 1; i <= 6; i++) {
  const text = fs.readFileSync(path.join(dir, `run-${i}.log`), "utf8");
  const lines = text.split("\n");
  const run = { n: i, offset: null, slotmap: null, size: {}, slot: {}, fastest: null, gap: null, noise: null, gapGt: null, exit: null };
  for (const l of lines) {
    let m;
    if ((m = l.match(/PROTOCOL\t.*slot-offset=(\d+)\tslotmap=(\S+)/))) { run.offset = +m[1]; run.slotmap = m[2]; }
    else if ((m = l.match(/RATIOMED\t(\d+)\tratio=([\d.]+)/))) run.size[+m[1]] = +m[2];
    else if ((m = l.match(/SLOTMED\t(\d+)\tratio=([\d.]+)/))) run.slot[+m[1]] = +m[2];
    else if ((m = l.match(/RATIOFASTEST\t(\d+)/))) run.fastest = +m[1];
    else if ((m = l.match(/RATIOSEPARATION\tgap=([\d.]+)\tnoise=([\d.]+)\tgap>noise=(\w+)/))) {
      run.gap = +m[1]; run.noise = +m[2]; run.gapGt = m[3] === "true";
    }
    else if ((m = l.match(/^EXIT=(\d+)/))) run.exit = +m[1];
  }
  if (run.exit !== 0 || Object.keys(run.size).length !== 6 || Object.keys(run.slot).length !== 6)
    throw new Error(`run-${i} incomplete: exit=${run.exit}`);
  runs.push(run);
}
const median = (xs) => { const s = [...xs].sort((a, b) => a - b); const n = s.length;
  return n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2; };
const f4 = (x) => x.toFixed(4);

console.log("per-run ratio medians (rows = W, cols = run slot-offset 0..5):");
for (const w of sizes)
  console.log(`W=${w}  ` + runs.map(r => f4(r.size[w])).join(" "));
console.log("");
console.log("per-run slots (which slot each W occupied; cols = run offset 0..5):");
for (const w of sizes)
  console.log(`W=${w}  ` + runs.map(r => {
    // slot of w in this run = the slot whose slotmap entry names w
    const pairs = r.slotmap.split(",").map(p => p.split(">"));
    return pairs.find(p => +p[0] === w)[1];
  }).join(" "));
console.log("");
console.log("grand per-size (UNADJUSTED marginal median over the 6 runs):");
const grandSize = {};
for (const w of sizes) { grandSize[w] = median(runs.map(r => r.size[w]));
  console.log(`W=${w}  grand=${f4(grandSize[w])}  per-run=${runs.map(r => f4(r.size[w])).join(" ")}`); }
console.log("");
console.log("grand per-slot (UNADJUSTED marginal median over the 6 runs):");
const grandSlot = {};
for (const s of [0, 1, 2, 3, 4, 5]) { grandSlot[s] = median(runs.map(r => r.slot[s]));
  console.log(`slot ${s}  grand=${f4(grandSlot[s])}  per-run=${runs.map(r => f4(r.slot[s])).join(" ")}`); }
console.log("");
const sizeVals = sizes.map(w => grandSize[w]), slotVals = [0, 1, 2, 3, 4, 5].map(s => grandSlot[s]);
console.log(`grand per-size spread (max-min): ${f4(Math.max(...sizeVals) - Math.min(...sizeVals))}   max=${f4(Math.max(...sizeVals))} min=${f4(Math.min(...sizeVals))}`);
console.log(`grand per-slot spread (max-min): ${f4(Math.max(...slotVals) - Math.min(...slotVals))}   max=${f4(Math.max(...slotVals))} min=${f4(Math.min(...slotVals))}`);
console.log("");
console.log("per-run summary (fastest / gap / noise / slowest row / slowest slot):");
for (const r of runs) {
  const slowRow = sizes.reduce((a, w) => (r.size[w] > r.size[a] ? w : a), sizes[0]);
  const slowSlot = [0, 1, 2, 3, 4, 5].reduce((a, s) => (r.slot[s] > r.slot[a] ? s : a), 0);
  r.slowRow = slowRow; r.slowSlot = slowSlot;
  console.log(`run-${r.n} offset=${r.offset} fastest=${r.fastest} gap=${f4(r.gap)} noise=${f4(r.noise)} gap>noise=${r.gapGt} slowest-row=${slowRow} slowest-slot=${slowSlot}`);
}
console.log("");
console.log("W=32 attribution (does the penalty follow the size or the slot?):");
for (const r of runs) {
  const slotOf32 = +r.slotmap.split(",").map(p => p.split(">")).find(p => +p[0] === 32)[1];
  console.log(`run-${r.n} offset=${r.offset} W=32-in-slot=${slotOf32} W=32-ratio=${f4(r.size[32])} slowest-row=${r.slowRow} slowest-slot=${r.slowSlot}`);
}
const rowCounts = {}, slotCounts = {};
for (const r of runs) { rowCounts[r.slowRow] = (rowCounts[r.slowRow] || 0) + 1; slotCounts[r.slowSlot] = (slotCounts[r.slowSlot] || 0) + 1; }
console.log(`slowest-row counts: ${JSON.stringify(rowCounts)}`);
console.log(`slowest-slot counts: ${JSON.stringify(slotCounts)}`);
console.log(`fastest-size set across runs: ${JSON.stringify([...new Set(runs.map(r => r.fastest))])}`);
console.log(`gap>noise runs: ${runs.filter(r => r.gapGt).length}/6`);
console.log(`W=32 grand=${f4(grandSize[32])} vs field-grand(median of the other five)=${f4(median(sizes.filter(w => w !== 32).map(w => grandSize[w])))}`);
```

Output, verbatim (run 2026-10-19 on this directory):

```
per-run ratio medians (rows = W, cols = run slot-offset 0..5):
W=32  0.9950 1.0004 1.0034 1.0002 0.9978 0.9977
W=64  0.9979 1.0030 1.0092 1.0000 1.0004 1.0032
W=128  0.9980 0.9971 0.9936 0.9957 1.0014 0.9986
W=256  1.0027 0.9966 1.0034 0.9971 0.9996 0.9989
W=512  0.9989 0.9993 0.9919 1.0021 1.0035 1.0014
W=1024  1.0023 1.0016 1.0014 1.0025 1.0004 1.0000

per-run slots (which slot each W occupied; cols = run offset 0..5):
W=32  0 1 2 3 4 5
W=64  1 2 3 4 5 0
W=128  2 3 4 5 0 1
W=256  3 4 5 0 1 2
W=512  4 5 0 1 2 3
W=1024  5 0 1 2 3 4

grand per-size (median over the 6 runs; each size seen once in every slot):
W=32  grand=0.9990  per-run=0.9950 1.0004 1.0034 1.0002 0.9978 0.9977
W=64  grand=1.0017  per-run=0.9979 1.0030 1.0092 1.0000 1.0004 1.0032
W=128  grand=0.9975  per-run=0.9980 0.9971 0.9936 0.9957 1.0014 0.9986
W=256  grand=0.9992  per-run=1.0027 0.9966 1.0034 0.9971 0.9996 0.9989
W=512  grand=1.0004  per-run=0.9989 0.9993 0.9919 1.0021 1.0035 1.0014
W=1024  grand=1.0015  per-run=1.0023 1.0016 1.0014 1.0025 1.0004 1.0000

grand per-slot (median over the 6 runs; each slot seen once with every size):
slot 0  grand=0.9992  per-run=0.9950 1.0016 0.9919 0.9971 1.0014 1.0032
slot 1  grand=1.0000  per-run=0.9979 1.0004 1.0014 1.0021 0.9996 0.9986
slot 2  grand=1.0027  per-run=0.9980 1.0030 1.0034 1.0025 1.0035 0.9989
slot 3  grand=1.0009  per-run=1.0027 0.9971 1.0092 1.0002 1.0004 1.0014
slot 4  grand=0.9984  per-run=0.9989 0.9966 0.9936 1.0000 0.9978 1.0000
slot 5  grand=0.9998  per-run=1.0023 0.9993 1.0034 0.9957 1.0004 0.9977

grand per-size spread (max-min): 0.0042   max=1.0017 min=0.9975
grand per-slot spread (max-min): 0.0044   max=1.0027 min=0.9984

per-run summary (fastest / gap / noise / slowest row / slowest slot):
run-1 offset=0 fastest=32 gap=0.0029 noise=0.0143 gap>noise=false slowest-row=256 slowest-slot=3
run-2 offset=1 fastest=256 gap=0.0006 noise=0.0308 gap>noise=false slowest-row=64 slowest-slot=2
run-3 offset=2 fastest=512 gap=0.0017 noise=0.0434 gap>noise=false slowest-row=64 slowest-slot=3
run-4 offset=3 fastest=128 gap=0.0015 noise=0.0082 gap>noise=false slowest-row=1024 slowest-slot=2
run-5 offset=4 fastest=32 gap=0.0018 noise=0.0094 gap>noise=false slowest-row=512 slowest-slot=2
run-6 offset=5 fastest=32 gap=0.0009 noise=0.0124 gap>noise=false slowest-row=64 slowest-slot=0

W=32 attribution (does the penalty follow the size or the slot?):
run-1 offset=0 W=32-in-slot=0 W=32-ratio=0.9950 slowest-row=256 slowest-slot=3
run-2 offset=1 W=32-in-slot=1 W=32-ratio=1.0004 slowest-row=64 slowest-slot=2
run-3 offset=2 W=32-in-slot=2 W=32-ratio=1.0034 slowest-row=64 slowest-slot=3
run-4 offset=3 W=32-in-slot=3 W=32-ratio=1.0002 slowest-row=1024 slowest-slot=2
run-5 offset=4 W=32-in-slot=4 W=32-ratio=0.9978 slowest-row=512 slowest-slot=2
run-6 offset=5 W=32-in-slot=5 W=32-ratio=0.9977 slowest-row=64 slowest-slot=0
slowest-row counts: {"64":3,"256":1,"512":1,"1024":1}
slowest-slot counts: {"0":1,"2":3,"3":2}
fastest-size set across runs: [32,256,512,128]
gap>noise runs: 0/6
W=32 grand=0.9990 vs field-grand(median of the other five)=1.0004
```

## What the six runs say (measured)

- THE SHAPE-1 W=32 PENALTY DOES NOT REPRODUCE UNDER SHAPE 2. W=32 is the
  slowest row in 0/6 runs (shape 1: 6/6); the slowest row scatters over
  {64: 3, 256: 1, 512: 1, 1024: 1} with no repetition pattern. W=32's grand
  ratio is 0.9990 against a field-grand of 1.0004 -- if anything nominally
  faster, well inside noise -- and it is the fastest row in 3/6 runs. The
  shape-1 conclusion "the W=32 penalty follows the size, not the slot" was
  measured on one kernel shape and is KERNEL-SHAPE-CONDITIONAL: it did not
  replicate when the working set (2^25 -> 2^24 u32), grid geometry
  ((32768, 1024/W) -> (256, 65536/W)) and mix depth (128 -> 32) all changed.
- "No stable size effect above noise" DOES REPRODUCE: the fastest-by-ratio
  size flips 32/256/512/128/32/32 and gap>noise holds in 0/6 runs (gaps
  0.0006-0.0029 against noise 0.0082-0.0434). The pre-registered rule (same
  fastest size in every run AND gap > noise) fails exactly as in the five
  earlier protocols.
- Shape 2 is 3-10x noisier than shape 1: per-run noise 0.0082-0.0434 here vs
  0.0019-0.0035 on shape 1. At this noise NEITHER the size dimension (grand
  per-size spread 0.0042) nor the slot dimension (grand per-slot spread
  0.0044) separates; on shape 1 the slot spread (0.0003) was an order of
  magnitude below the size spread (0.0028). This shape cannot resolve a 0.2%
  effect in either direction -- which is exactly the magnitude of the shape-1
  W=32 penalty, so its absence here is non-replication, not refutation.

## What this evidence is NOT

- Not a tuning result and not a vendor dispatch row. NO dispatch row is
  replaced: the apple workgroup row in `kotoba.compiler.accelerator-targets`
  stays provisional `:measured? false` -- neither confirmed nor overturned.
- The non-replication does NOT show the shape-1 W=32 penalty was an artifact:
  shape 1's unaliased protocol had already ruled out the slot confound. What
  shape 2 shows is that the penalty is conditional on the kernel shape
  (working set / grid geometry / mix depth), so it cannot be promoted to a
  device fact about W=32. Any dispatch decision keyed on a "W=32 penalty"
  must say which kernel shape it was measured on.
- Neither shape resolves an effect at the 0.2% level (shape-2 noise is worse,
  shape-1's only stable signal was the W=32 row). A :measured? flip for the
  apple workgroup row still needs a protocol whose noise floor is below the
  effect it claims, on more than six runs of one shape.

## Suite state at this commit

`kbb --backend sci --classpath "src:test:$(kbb -Spath -M:test)" run-tests.cljk`
re-run on the branch at this commit (2026-10-19): 304 tests / 4939 assertions
(4908 passed), 16 failures + 15 errors, exit 1. NOT a green suite and not
claimed as one. Base `bea7b9b2` (gate-base-bea7b9b2.log, same gate command at
the merge base): 304 tests / 4908 passed, 16 failures + 15 errors -- and the
NAME-LEVEL RED SET IS IDENTICAL (31 FAIL/ERROR lines on each side, empty diff
after normalizing the run-tests.cljk path prefix). Red names at this commit:
numbered-grants-at-any-count (9),
packages-macos-with-a-macos-profile-and-platform-load-command (1),
every-source-namespace-is-reachable-from-the-tests (1),
malformed-policy-still-refused-by-name (3),
native-constructors-charge-fuel-test (1),
same-policy-read-twice-is-equal (1 fail + 1 error),
row-tuple-element-argument-test (9 errors),
text-edit-rebound-state-is-a-row-test (1 error),
refuses-macos-static-host-typed-list-operations (1 error),
refuses-macos-static-host-capability-calls-without-providers (1 error),
named-grants-at-any-count (1 error),
min-max-qualified-on-typed-wasm-test (1 error). These map to the families
recorded as red at base bea7b9b2 (policy-grant-count, row-tuple-element-argument,
ios-aot, typed-wasm-min-max, namespace-reachability, native-allocation-budget,
rebound-row). This diff touches no suite namespace (a script run-tests does
not load, one C constant, and this evidence directory).
Flake note: one earlier run of this same tree (recorded in commit 228d0e6a's
message) saw 16 failures + 18 errors -- the extra 3 errors were
native-rebound-row-update-test (host/stack-exhausted), a known host-stack
flake; that test is green in both the base run and the branch re-run recorded
here. The name-identity claim above is for THIS base/branch run pair.

NOTE (review): these grand figures are UNADJUSTED marginal medians. The six
offsets make size, slot and run effects identifiable, but a median over runs
does not separate additive effects (a fixed size's run effect is paired with
a different slot effect in each run). A Latin-square additive fit (size +
slot + run) is the method that separates them; until such a fit is recorded,
the grand values are descriptive marginal summaries, not effect estimates.
