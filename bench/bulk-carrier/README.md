# bulk-carrier — what an element access costs, and what it is paid to

Evidence for ADR 0285. The question is whether the shared value model should
gain a bulk carrier, and the answer turns on **crossings per element**, not on
capacity.

## Read the counts first

A count does not drift with host load. This workstation carries concurrent
sessions and was measured at load1 12–700; a timing run at load1 394–613 read
3x the same arm's load1 12–23 figure and produced negative slopes in the
sub-nanosecond arms. So the structural claims rest on `crossings.cljs`, and
every timing here is diagnostic.

```sh
amu compile wasmvec.kotoba  --target wasm32 --fuel 4000000000000
amu compile wasmloop.kotoba --target wasm32 --fuel 4000000000000
nbb crossings.cljs wasmvec.kotoba.wasm      # self-recursion spelling
nbb crossings.cljs wasmloop.kotoba.wasm     # loop/recur spelling
```

`wasmvec` and `wasmloop` compute the same function by two admitted spellings —
both verified against `kotoba.kir/execute`, both returning 133120 / 129024 /
129024 at outer = 1. Each has three arms: `run-touch` reads one element per
iteration, `run-base` **carries** the vector and never reads it, `run-noref`
carries nothing. `run-base` and `run-noref` return the same value, so they are
the same computation and their difference is the carrier alone.

The default fuel budget is 512 **operations per instance**, which by itself
forbids any bulk loop; `--fuel` is a policy parameter and capacity is not.

## Then the timings, and their refusals

```sh
nbb slope.cljs wasmvec.kotoba.wasm 200 9 > wasm.edn
cc -O3 -o native_model native_model.c && ./native_model 200000 9 > c.json
nbb gen_slice_wasm.cljs                       # hand-encoded slice-at stand-in
nbb --classpath <perfgate>/src:<machine>/src gate.cljs \
    wasm.edn c.edn inline:indirect plain:inline h-slice:h-noref
```

`slope.cljs` measures a **slope** between outer counts A and 2A, so module
compile, JIT warmup, the export call and the vector construction all cancel;
no warmup round is needed and no constant can inflate the result. Every arm's
return value is checked against the KIR reference interpreter before it is
timed.

`gate.cljs` is the verdict — `perfgate.core/qualify`, no JVM. It prints
refusals rather than working around them, and says `MISSING ARM` rather than
silently skipping a pair it was asked for. Three comparisons in ADR 0285 are
refusals, including the hand-encoded `slice-at` experiment, which measured
**`:not-separated-from-noise`**: under this loop's rules that is the absence of
a result, and it is why no compiler change follows it.

`native_model.c` models three lowerings over the arena layout `kexe_loader.c`
already has. Every arm carries the same compiler barrier on the accumulator —
without it clang folds the plain arm to 0.0013 ns/element, a measurement of
nothing.

`gen_slice_wasm.cljs` hand-encodes the instruction sequence a `slice-at` would
compile to. Its control arm returns 129024 and its load arm 133120 — the KIR
values for the Kotoba arms — which is how we know it is the same loop computing
the same function. It is a stand-in for a lowering that does not exist, and is
not evidence that the compiler can emit it.

## The loop spelling is a capability limit too

```sh
nbb depth.cljs wasmvec.kotoba.wasm  run-noref 6000 12000   # self-recursion
nbb depth.cljs wasmloop.kotoba.wasm run-noref 12000 40000  # loop/recur
```

Self-recursion stops between 6,128 and 12,128 iterations with a host
`RangeError`, not a Kotoba diagnostic, so it does not present as a language
limit. `loop`/`recur` is O(1) in depth and did not trap at 163M element visits.
A fresh instance per probe is not optional: a trap leaves the scratch bump
global unrestored, so a reused instance reports a ceiling of 1 whatever the real
one is.

## Quiet-host samples

`samples-levi-wasm.edn` and `samples-levi-c.edn` are the run ADR 0285's
correction rests on: levi (`Mac16,10`, M4) at load1 1.78-2.14, n=15, per-arm
outer counts sized so every sample integrates at least 3 ms of CPU, explicit
warmup for every arm before any sampling.

```sh
nbb --classpath <perfgate>/src:<machine>/src gate.cljs \
    samples-levi-wasm.edn samples-levi-c.edn \
    k-loop-touch:k-rec-touch k-loop-base:k-rec-base k-loop-noref:k-rec-noref \
    h-noref:h-slice c-inline:c-indirect c-plain:c-inline
```

Five qualify. `h-noref:h-slice` refuses with `:not-separated-from-noise`, and
that refusal is the point: the bounds test plus `i64.load` cannot be told apart
from the loop it sits in, while the `vector-at` it would replace costs 381.72
ns/element.

Do not compare the wasm arms to the C arms as equals: the C arms carry a
compiler barrier on the accumulator (without it clang folds the plain arm to
0.0013 ns) and the wasm arms have no equivalent.
