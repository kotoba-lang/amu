# gpu-workgroup-unaliased-m1max-20261019 — unaliased-slot protocol, Apple M1 Max

Verbatim stdout of `KGPU_SLOT_OFFSET=<o> kbb --backend sci scripts/test-gpu-workgroup-unaliased.cljk`
(six fresh processes, o = 0..5), 2026-10-19 JST, on the amu-gpu bot host.
`EXIT=0` lines are the script's own process exit. The logs in this directory
are run-1.log .. run-6.log (run-N is slot-offset N-1).

## Provenance

- Command per run: `KGPU_SLOT_OFFSET=<o> kbb --backend sci scripts/test-gpu-workgroup-unaliased.cljk`
- Code: branch `bot/amu-gpu-20261019-0204`, base `origin/main` =
  `bea7b9b24a44ebd3d5108e8e356a39c6bed5912d`, plus exactly
  `scripts/test-gpu-workgroup-unaliased.cljk`,
  `tools/kexe_gpu_vulkan.c` (one constant: KGPU_MAX_KEPT 4 -> 8, needed for 6
  simultaneously kept command buffers; byte-identical to the hunk the
  sweep/ratio/compute branches make for the same reason, so those branches
  merge cleanly), and this directory.
- Host: Apple M1 Max, macOS 26.4, aarch64-macos. MoltenVK, Vulkan device
  apiVersion 1.3.357, INFO `Apple M1 Max|1.3.357|1024|1` (run logs).
- Kernel body, buffers, dispatch shape, timing loop and ratio statistic are
  IDENTICAL to the compute protocol (gpu-workgroup-compute-m1max-20261019,
  branch bot/amu-gpu-20261019-0105): one kernel per local size
  W in {32,64,128,256,512,1024}, 2^25 u32 elements per size, n-mix = 128
  serial xorshift rounds per element, 24 rounds of 6 REPLAYs, alternating
  within-round order, within-round RATIO t(r,w)/median-of-round. WHAT
  CHANGES IS ONLY THE SLOT <-> SIZE ASSIGNMENT -- the residual bias every
  earlier protocol README named and none removed: slot k (the kept command
  buffer index) always carried the same size, so a per-slot effect and a
  per-workgroup-size effect were perfectly aliased. Here size i's dispatch is
  recorded into slot (i + offset) mod 6; six processes (offset 0..5) form a
  CYCLIC LATIN SQUARE: every (size, slot) cell is observed exactly once, so
  additive size, slot and process effects are mutually identifiable across
  the run set. Mid-run re-recording is deliberately NOT used: freshly
  re-recorded command buffers would confound slot with buffer
  age/freshness.
- The script self-tests before touching the GPU (all passed at every
  invocation): parser (INFO answer carrying its own '|', refusal of
  short/malformed/out-of-order answers), the sample->size mapping (offset 0
  keeps the old parity rule; 24 samples per size at every offset 0..5;
  explicit offset-2 facts: size 0 -> slot 2, slot 0 -> size 4), Latin-square
  balance (all 36 (size, slot) cells covered exactly once over offsets 0..5),
  median/quartile arithmetic, `analyze` on synthetic streams (a 10% size
  effect under 2x round-baseline variation comes out as gap 0.1, noise 0,
  fastest W=256; a no-effect stream gives gap 0, noise 0), `analyze-slots`
  on a synthetic stream whose slot-0 samples are 10% slower (slot 0 -> ratio
  1.1, every other slot -> 1.0), and n-mix pinning (the GLSL loop and the JS
  read-back mirror both carry exactly 128 mixing rounds).
- Read-back verification: words 0..3 of every output buffer checked against
  the host's own mixing; `verify=ok` per size in all six runs (36/36).
- Development-time failures: one -- the very first invocation refused with
  exit 3 because the fresh worktree had no node_modules (nbb cli.js
  missing); resolved by copying node_modules from the previous tick's
  worktree (shasum-verified identical). All six measurement runs exited 0.

## Cross-run aggregation (computed over the six logs)

Aggregator source (run as `node aggregate-unaliased.js <this dir>`; it parses
only the printed lines of the run logs and contains no measurement of its
own):

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
console.log("grand per-size (median over the 6 runs; each size seen once in every slot):");
const grandSize = {};
for (const w of sizes) { grandSize[w] = median(runs.map(r => r.size[w]));
  console.log(`W=${w}  grand=${f4(grandSize[w])}  per-run=${runs.map(r => f4(r.size[w])).join(" ")}`); }
console.log("");
console.log("grand per-slot (median over the 6 runs; each slot seen once with every size):");
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

Output, verbatim:

```
per-run ratio medians (rows = W, cols = run slot-offset 0..5):
W=32  1.0020 1.0017 1.0024 1.0015 1.0025 1.0019
W=64  0.9997 0.9999 0.9999 0.9991 0.9990 0.9999
W=128  0.9991 0.9999 0.9996 0.9989 0.9990 0.9991
W=256  1.0000 0.9998 0.9996 1.0000 0.9976 0.9998
W=512  1.0003 1.0001 0.9989 1.0003 1.0002 1.0000
W=1024  1.0004 0.9996 0.9999 1.0004 1.0009 1.0002

per-run slots (which slot each W occupied; cols = run offset 0..5):
W=32  0 1 2 3 4 5
W=64  1 2 3 4 5 0
W=128  2 3 4 5 0 1
W=256  3 4 5 0 1 2
W=512  4 5 0 1 2 3
W=1024  5 0 1 2 3 4

grand per-size (median over the 6 runs; each size seen once in every slot):
W=32  grand=1.0019  per-run=1.0020 1.0017 1.0024 1.0015 1.0025 1.0019
W=64  grand=0.9998  per-run=0.9997 0.9999 0.9999 0.9991 0.9990 0.9999
W=128  grand=0.9991  per-run=0.9991 0.9999 0.9996 0.9989 0.9990 0.9991
W=256  grand=0.9998  per-run=1.0000 0.9998 0.9996 1.0000 0.9976 0.9998
W=512  grand=1.0002  per-run=1.0003 1.0001 0.9989 1.0003 1.0002 1.0000
W=1024  grand=1.0003  per-run=1.0004 0.9996 0.9999 1.0004 1.0009 1.0002

grand per-slot (median over the 6 runs; each slot seen once with every size):
slot 0  grand=0.9998  per-run=1.0020 0.9996 0.9989 1.0000 0.9990 0.9999
slot 1  grand=0.9998  per-run=0.9997 1.0017 0.9999 1.0003 0.9976 0.9991
slot 2  grand=1.0000  per-run=0.9991 0.9999 1.0024 1.0004 1.0002 0.9998
slot 3  grand=1.0000  per-run=1.0000 0.9999 0.9999 1.0015 1.0009 1.0000
slot 4  grand=1.0000  per-run=1.0003 0.9998 0.9996 0.9991 1.0025 1.0002
slot 5  grand=0.9999  per-run=1.0004 1.0001 0.9996 0.9989 0.9990 1.0019

grand per-size spread (max-min): 0.0028   max=1.0019 min=0.9991
grand per-slot spread (max-min): 0.0003   max=1.0000 min=0.9998

per-run summary (fastest / gap / noise / slowest row / slowest slot):
run-1 offset=0 fastest=128 gap=0.0005 noise=0.0024 gap>noise=false slowest-row=32 slowest-slot=0
run-2 offset=1 fastest=1024 gap=0.0001 noise=0.0019 gap>noise=false slowest-row=32 slowest-slot=1
run-3 offset=2 fastest=512 gap=0.0006 noise=0.0026 gap>noise=false slowest-row=32 slowest-slot=2
run-4 offset=3 fastest=128 gap=0.0001 noise=0.0024 gap>noise=false slowest-row=32 slowest-slot=3
run-5 offset=4 fastest=256 gap=0.0013 noise=0.0035 gap>noise=false slowest-row=32 slowest-slot=4
run-6 offset=5 fastest=128 gap=0.0007 noise=0.0029 gap>noise=false slowest-row=32 slowest-slot=5

W=32 attribution (does the penalty follow the size or the slot?):
run-1 offset=0 W=32-in-slot=0 W=32-ratio=1.0020 slowest-row=32 slowest-slot=0
run-2 offset=1 W=32-in-slot=1 W=32-ratio=1.0017 slowest-row=32 slowest-slot=1
run-3 offset=2 W=32-in-slot=2 W=32-ratio=1.0024 slowest-row=32 slowest-slot=2
run-4 offset=3 W=32-in-slot=3 W=32-ratio=1.0015 slowest-row=32 slowest-slot=3
run-5 offset=4 W=32-in-slot=4 W=32-ratio=1.0025 slowest-row=32 slowest-slot=4
run-6 offset=5 W=32-in-slot=5 W=32-ratio=1.0019 slowest-row=32 slowest-slot=5
slowest-row counts: {"32":6}
slowest-slot counts: {"0":1,"1":1,"2":1,"3":1,"4":1,"5":1}
fastest-size set across runs: [128,1024,512,256]
gap>noise runs: 0/6
W=32 grand=1.0019 vs field-grand(median of the other five)=0.9998
```

## What the six runs say (measured)

- THE W=32 PENALTY FOLLOWS THE SIZE, NOT THE SLOT. W=32 is the slowest row
  in all six runs while occupying every slot 0..5 exactly once (ratio median
  1.0015-1.0025, across-run range 0.0010). The slowest slot rotates with the
  offset -- it is always the slot hosting W=32 (one count per slot) -- so
  the signal is not a per-slot artifact. The unaliasing question this
  protocol was built to answer has an answer: the earlier protocols' one
  stable signal was a real W=32 effect, not a buffer-slot confound.
- The slot confound is measured as ABSENT at this resolution: grand
  per-slot spread 0.0003 (0.9998..1.0000) vs grand per-size spread 0.0028,
  which is driven by W=32 (grand 1.0019 vs field grand 0.9998 -- a measured
  0.2% penalty for W=32 on this kernel shape, this device).
- STILL NO STABLE SIZE EFFECT ABOVE NOISE for picking a dispatch size: the
  fastest-by-ratio size flips 128/1024/512/128/256/128 and gap>noise holds
  in 0/6 runs (gaps 0.0001-0.0013 against noise 0.0019-0.0035). The
  pre-registered rule (same fastest size in every run AND gap > noise) fails
  exactly as in the four earlier protocols.

## What this evidence is NOT

- Not a tuning result and not a vendor dispatch row. NO dispatch row is
  replaced: the apple workgroup row in `kotoba.compiler.accelerator-targets`
  stays provisional `:measured? false` -- neither confirmed nor overturned.
  Flipping `:measured?` still needs more than six runs of one kernel shape.
- The W=32 penalty (0.2%) is a MEASURED device fact for THIS kernel shape on
  THIS device, now unaliased from slot. It is descriptive, not decisive: it
  does not choose a dispatch size (W=32 was never the fastest row; nothing
  here recommends any size).
- "Slot effect absent" is scoped to additive separation at this resolution
  (per-slot grand spread 0.0003): a slot effect below that, or non-additive
  with size, is not excluded. Slot and process effects are separated only
  across the six processes (each cell observed once), so per-cell noise is
  one run's worth.

## Suite state at this commit

`kbb --backend sci --classpath "src:test:$(kbb -Spath -M:test)" run-tests.cljk`
-> 304 tests / 4908 assertions, 16 failures + 15 errors, exit 1. NOT a green
suite and not claimed as one. Red test names at this commit:
packages-macos-with-a-macos-profile-and-platform-load-command (1),
every-source-namespace-is-reachable-from-the-tests (1),
malformed-policy-still-refused-by-name (3),
native-constructors-charge-fuel-test (1), numbered-grants-at-any-count (9),
same-policy-read-twice-is-equal (2), row-tuple-element-argument-test (9
errors), min-max-qualified-on-typed-wasm-test (1 error),
named-grants-at-any-count (1 error),
refuses-macos-static-host-capability-calls-without-providers (1 error),
refuses-macos-static-host-typed-list-operations (1 error),
text-edit-rebound-state-is-a-row-test (1 error). These map to the same
families PRs #1333/#1335/#1338/#1339 recorded as red at base bea7b9b2
(policy-grant-count, row-tuple-element-argument, ios-aot, typed-wasm-min-max,
namespace-reachability, native-allocation-budget, rebound-row). This diff
touches no suite namespace (a script run-tests does not load, one C
constant, and this evidence directory). The base-vs-branch name-level diff
was NOT run this tick (tick budget exhausted) -- I do not claim
diff-identical red sets; I claim only the counts (16+15) match the recorded
base-red counts and the families match the recorded base-red inventory.
