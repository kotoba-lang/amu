# ADR 0285: A bulk carrier must be guest-addressable memory, not a bigger vector — and the ceilings do not move

- Status: accepted
- Date: 2026-08-30

## Decision

1. **Add a distinct carrier, `[:slice T]`** — bounded, host-owned, contiguous,
   whose element access lowers to a **load** on wasm32 and native. Do not widen
   `:vector-i64` to be it; the two have genuinely different representations and
   only one of them can be indexed without a crossing.
2. **Do not raise `vector-item-limit` (16384), `:vector-item-capacity` (65536),
   or `:vector-capacity` (4096).** Authorization to raise them was given and is
   **not needed**: the architecture the measurements support is per-block, and
   the largest per-block working set is ~576 samples against a per-vector bound
   of 16384. Leaving them still means the loader memory image, the verifier's
   derived limits and the pinned runtime identity SHA do not move together —
   which is the cheapest possible way to avoid a second instance of the
   co-movement defect ADR 0284 found.
3. **Frame-scale pixel data does not enter the guest**, on the evidence
   available. Two independent measurements refuse it, and neither is about
   capacity. **Corrected 2026-08-30 on a quiet host: that refusal rests on
   native measurements, and wasm32 does not share the premise** — see "What a
   quiet host changed" below. The wasm32 half of this decision is now open.

The ordering matters and is the ranking: the two front-door blockers gate every
other claim, `loop`/`recur` is a **counted 2x** available today with no compiler
change, and the carrier is third.

## Evidence boundary

### The cost is crossings, not capacity — counted

A count does not drift with host load, and this workstation ran at load1 12–700
from concurrent sessions throughout. The structural claims rest on counts; the
timings below are diagnostic.

Every `kotoba:typed` import was wrapped before instantiation
(`bench/bulk-carrier/crossings.cljs`) and the calls counted over one outer step
= 4096 element visits. Three arms: `touch` reads one element per iteration,
`base` is the identical loop that **carries** the vector and never reads it, and
`noref` is the identical loop carrying no vector at all. `base` and `noref`
return the same value (129024), so they are the same computation.

| source spelling | arm | `assert-ref` | `vector-at-i64` | crossings/element |
|---|---|---|---|---|
| self-recursion | touch | 4227 | 4096 | **2.032** |
| self-recursion | carry only | 4227 | 0 | **1.032** |
| self-recursion | no vector | 0 | 0 | 0 |
| `loop`/`recur` | touch | 129 | 4096 | **1.032** |
| `loop`/`recur` | carry only | 65 | 0 | **0.016** |
| `loop`/`recur` | no vector | 0 | 0 | 0 |

Two findings, both exact:

**A loop that merely carries a `:vector-i64` pays a host crossing per
iteration.** `kotoba.wasm.core` emits a `typed-assert-ref` prologue for every
reference-typed parameter, so a recursive function re-proves the type of an
externref its own caller already asserted. The vector is never read in that arm.

**Half of that cost is paid for the source author's choice of loop spelling.**
`structured-loop?` requires `loop-helper-name?`, so a frontend `loop`/`recur`
helper becomes a real wasm loop whose prologue runs once, while self-recursion
becomes real recursion whose prologue runs per iteration: 4227 → 129, and 2.032
→ 1.032 crossings per element. **Both spellings are admitted guest grammar and
nothing tells the author which one costs twice as much.** Both were verified
against `kotoba.kir/execute` and return identical values at outer = 1 and 2.

The residue after `loop`/`recur` is **1.032 crossings per element**, which is
`vector-at` itself. That is the number a carrier has to remove, and it cannot be
removed by making the carrier bigger.

### Timings — diagnostic, with three refusals recorded

Slope between outer counts A and 2A, so module compile, JIT warmup, the export
call and the 64-element construction all cancel. `process.cpuUsage` for wasm,
`CLOCK_THREAD_CPUTIME_ID` for C; arms interleaved; every arm's value checked
against `kotoba.kir/execute` before timing. Qualified with `perfgate.core/qualify`
under the default policy against a `:measured` `machine.core` descriptor probed
by `sysctl`.

wasm32, self-recursion spelling, load1 12–23, n=9:

| arm | ns/element | rel-stdev | vs C `-O3` |
|---|---|---|---|
| `vector-at` per element | 1033.53 | 0.018 | 2720x |
| carries the vector, never reads it | 488.22 | 0.046 | 1285x |
| identical loop, no vector | 6.72 | 0.116 | 17.7x |

The `loop`/`recur` fixture was timed too, at load1 ~490, n=7: `vector-at`
1608 ns/element, carry-only **22.9**, loop-only **1.2**. Those cannot be
divided into the table above -- different run, different load, and per
iteration 49 even ratios drift day over day -- but the direction matches the
counts on the two arms the counts govern (2x on touch, 64x on carry-only), and
the third is a codegen difference the counts do not govern at all: both `noref`
arms make **zero** crossings, so the ~14x between them is a chain of wasm calls
against a real wasm loop. `loop`/`recur` therefore buys two separate things --
one crossing per iteration, and the loop itself.

C `-O3`, same arena layout the loader already has
(`kexe_vector_v1{offset,length}` indexing a flat `int64_t vector_items[]`),
load1 12–15, n=9, compiler barrier on the accumulator in every arm:

| arm | ns/element | rel-stdev | vs plain |
|---|---|---|---|
| `acc += a[i]` | 0.3800 | 0.058 | 1.0x |
| the loader's `checked_vector_at` body, **inlined** | 0.7268 | 0.057 | **1.9x** |
| the same body through a function pointer | 1.6174 | 0.024 | 4.3x |

The plain arm reproduces ADR 0284's 0.329 within noise, which is how we know the
method matches. Without the barrier clang folded it to 0.0013 ns — a measurement
of nothing — and all three arms carry the barrier so none is vectorised while
another is.

**`c-indirect` here reads 1.617 where ADR 0284 read 4.547.** This one is a
same-translation-unit call through a `volatile` function pointer, which the
branch predictor handles; ADR 0284's crossed a real boundary. Ours therefore
**understates** the call, which makes the inlining result below conservative
rather than flattering.

Qualified: inlined vs indirect **55.1%** (gap 0.891, summed stdev 0.080);
plain vs inlined **47.7%** (gap 0.347, summed stdev 0.063); wasm carry-only vs
touch **52.8%**.

**Refused, and recorded as the absence of a result:**

- `wasm noref vs touch` and `wasm noref vs base` — improvement 99.35% and
  98.62%, gaps 55x and 21x their summed stdev, **refused `:too-noisy`** because
  the candidate arm's rel-stdev is 0.116 against a policy of 0.10.
- **The hand-written `slice-at` experiment did not separate.** Two hand-encoded
  wasm arms with byte-identical loop shape — one summing `i`, one summing an
  unsigned-bounds-tested `i64.load` — read 1.576 and 1.872 ns/element at load1
  506–554, n=21. Gap 0.296, summed stdev 0.489: **`:not-separated-from-noise`,
  plus `:too-noisy` on both arms.** At this host's load the cost of the load
  cannot be shown to differ from zero. That is consistent with the load being
  nearly free and is **not evidence that it is**; it needs a quiet-window
  re-run, and no fleet host reaches that threshold today (ADR 0281).

The hand-written control is what makes the experiment interpretable at all: its
no-load arm returns 129024 and its load arm returns 133120 — the values
`kotoba.kir/execute` gives for the Kotoba `noref` and `touch` arms — so the
hand-written loop is the same loop and the load arm computes the same function
as `vector-at`.

### What a quiet host changed, and what it corrected

Everything above was measured on this workstation at load1 12-700. Re-measured
on **levi** (`Mac16,10`, Apple M4, 10 cores) at **load1 1.78-2.14**, all arms
interleaved in one process, per-arm outer counts chosen so every sample
integrates at least 3 ms of CPU, explicit warmup for every arm before any
sampling, values checked against `kotoba.kir/execute` first, n=15:

| arm | ns/element | rel-stdev | vs C `-O3` |
|---|---|---|---|
| `vector-at`, self-recursion | 753.41 | 0.011 | 3153x |
| carries the vector, self-recursion | 362.96 | 0.016 | 1519x |
| loop only, self-recursion | 5.026 | 0.009 | 21.0x |
| `vector-at`, `loop`/`recur` | 387.43 | 0.029 | 1621x |
| carries the vector, `loop`/`recur` | 5.704 | 0.016 | 23.9x |
| **loop only, `loop`/`recur`** | **0.2371** | 0.010 | **0.99x** |
| hand-written loop | 0.3935 | 0.050 | 1.65x |
| hand-written loop + bounds + `i64.load` | 0.4249 | 0.057 | 1.78x |
| C `-O3` `acc += a[i]` | 0.2390 | 0.003 | 1.00x |
| C, inlined arena access | 0.4938 | 0.015 | 2.07x |
| C, indirect call | 1.0815 | 0.012 | 4.53x |

Qualified by `perfgate.core/qualify`, default policy, `reasons []`:
`loop`/`recur` over self-recursion — **48.6%** on the touch arm, **98.4%** on
the carry arm, **95.3%** on the loop arm; C inlined over indirect 54.3%; C plain
over inlined 51.6%.

**The correction.** This ADR said the loop alone reads 17.7x C and concluded
that removing the crossing is "necessary and not sufficient". That 17.7x was the
**self-recursion spelling on a loaded host**, and it was not a property of the
backend. On a quiet host the same loop written `loop`/`recur` costs **0.2371
ns/element** — about one cycle, against 0.2390 for the C arm. For wasm32 the
loop is not the bottleneck and the carrier is very nearly the whole cost.
ADR 0284's 11.2x is a **native** measurement and stands; the two backends differ here,
and this ADR previously generalised one to the other.

**Do not read 0.99x as "amu equals C".** The C arm carries a compiler barrier on
its accumulator — without it clang folds the loop to 0.0013 ns, a measurement of
nothing — and the wasm arm has no equivalent, so the C arm is serialised on a
dependency chain the wasm arm may not be. The defensible statements are the two
that need no cross-language comparison: `loop`/`recur` beats self-recursion on
the pure loop by **21x, qualified**, and the loop costs about one cycle per
element.

**The two numbers the design rests on, from the same run:**

- marginal cost of today's `vector-at`, best spelling: **381.72 ns/element**
  (387.43 − 5.70), separated from noise by four orders of magnitude.
- marginal cost of the proposed bounds-tested `i64.load`: **0.0314
  ns/element** — and `perfgate` **refuses** it, `:not-separated-from-noise`,
  gap 0.031 against summed stdev 0.044. Both arms are individually clean
  (rel-stdev 0.050 and 0.057, inside the 0.10 policy); the arms are simply
  closer together than their own spread.

**That refusal is the result, not a failure to get one.** The claim the design
needs is not a ratio between those two numbers. It is that today's element
access costs 381.72 ns and is comfortably separated, while the proposed one
cannot be told apart from doing nothing at all.

**What this does not settle.** A composite figure of 0.237 + 0.031 ≈ 0.27
ns/element for a `loop`/`recur` guest reading through a load is **inferred by
adding a marginal measured in one loop shape to a cost measured in another** —
no arm measured it. Building it is what would measure it. And the native side is
untouched: ADR 0284's 11.2x loop-only figure is why the frame-scale conclusion
above still holds there.

### Why the type should exist, and why not for frames

**There is no carrier to extend.** `:vector-i64` costs a crossing per element on
wasm and a context call per element on native; `:bytes` is capped at 65536 and
**opaque** — no guest operation indexes a byte; `:document` caps at 255 i64
leaves; and on native a vector cannot cross the **export** boundary at all, so
bulk data cannot enter a guest by any route today. Whatever is built is new.

**Removing the crossing is necessary and not sufficient.** ADR 0284 measured the
native loop *alone*, performing no element access, at 11.2x C; the wasm loop
alone reads 17.7x here. An independent attribution (utsushi
`bench/decode-cost-attribution`, merge 42bd12d) reaches the same wall from the
other side: with an *unlimited* `vector-i64`, residual addition at one guest call
per macroblock is 345,600 element crossings per frame, 2.39 ms/frame at ADR
0284's 6.920 ns — **1.9x worse than doing it in host arrays**, and still 1.0x,
bare parity, even at the 3.678 ns loop-only figure with the call removed
entirely. **Frame-scale pixel data in the guest is refused by measurement from
two directions, and capacity is not what refuses it.**

**Where that attribution and this ADR disagree, stated rather than glossed.**
Its measurements and mine agree on everything that was measured: the carrier
must be guest-addressable memory the guest indexes with its own loads, capacity
alone does not clear the bar, plane assembly (~21% of decode CPU) **must stay in
the host**, and a per-block guest is not viable at today's per-element cost. We
differ on the *recommendation*. It concludes "capacity still has to move", with
the target a decoder's minimum working set — the current picture plus one
reference picture, 230,400 samples at 320x240, against a present cap of 16,384
(7.1%). This ADR concludes the cap should not move.

The reason is that document's own eligibility table. Every operation it marks
**eligible** already fits: residual addition (~49%) at 256 samples in and 256
out is, in its words, "64x under the cap"; the inverse transforms (~2%) are 16.
The operation that needs 230,400 is plane assembly — the one the same table
marks "must stay in the host". A reference *picture* is only a guest working set
if motion compensation reads it in the guest; under a per-block split the guest
derives the motion vector and the host extracts the (16+5)² = 441-sample patch,
so the guest addresses the patch and never the picture.

Its 10.6x figure is what settles it: with an **unlimited** carrier, touching
each sample of one frame exactly once already costs 10.6x ffmpeg's entire frame
decode. A cap sized for an architecture that measurement rejects buys nothing,
and buying it means moving the loader memory image, the verifier's derived
limits and the pinned runtime identity SHA together. Both readings rest on the
same numbers; this one declines to pay for the architecture those numbers refuse.

So the capacity must not be derived from a frame. The 230,400-sample figure
(current plus reference picture at 320x240) is the working set of an
architecture these measurements reject.

**Derived from the per-block architecture instead**, so it can be re-derived
rather than quoted: the bound is the largest working set one guest kernel
invocation must address. For H.264 that is the deblocking window across a
macroblock edge, (16+8)² = **576** samples, and the quarter-pel motion-compensation
reference patch, (16+5)² = **441**. A 16x16 luma macroblock is 256, a 4x4
residual block 16. Round to **4096** for headroom over larger transform sizes and
chroma formats. 4096 < 16384, so **today's per-vector bound already covers it and
does not move.**

### Records already cover part of this, which narrows the claim

The native backends accept a sealed `:i64` record where they reject
`:vector-i64`, and a record reaches a native **export** where a vector cannot.
So some per-block data can enter a native guest today with no new type — and
that is not hypothetical: a parallel agent ran H.264 §8.5.12's inverse residual
transform and §8.5.9's dequant chain on three paths, including aarch64 machine
code through the kexe loader, with `java`/`javac`/`clojure`/`clj` shadowed by
exit-127 stubs, against an oracle of 317 coefficient blocks from real libx264
bitstreams. A 4x4 block is 16 values, and the transform is naturally unrolled.

**Two limits decide how far that reaches, and both are in KIR, not the loader.**

1. **`record-field-limit` is 32** (`kotoba.kir.value`). The loader's 128-field
   argument bound is looser and therefore not the binding one.
2. **`record-get` takes a literal keyword, never a runtime index.** The native
   admission gate requires `(keyword? field)` and that the field be declared in
   the record type. **There is no indexed record accessor at all**, so a record
   cannot be traversed by a loop — every access must be written out.

So records cover exactly: **working sets of at most 32 elements, accessed at
statically known positions.** That is the 4x4 transform, and it is roughly the
2% of decode CPU the utsushi attribution puts in transforms.

**The slice's justification is therefore narrower than this ADR first implied,
and worth stating rather than leaving implied.** It is needed for, and only for:

- working sets above 32 — a 16x16 macroblock is 256, a quarter-pel MC reference
  patch 441, a deblocking window across an edge 576;
- **access at a runtime index, at any size** — motion compensation indexes by a
  motion vector, intra prediction selects neighbours by mode. Neither is a
  literal keyword, so no record expresses them however small the block;
- anything written as a loop rather than unrolled.

Between them those are residual addition (~49% of decode CPU), motion
compensation and deblocking — every operation the attribution marks eligible
**except** the transforms records already carry. The carrier is not needed to
start; it is needed to get past 2%.

### What the carrier must not be

Each restriction is what buys the load:

- **Not nestable** in records, variants, options, results, maps or sets — nesting
  requires a host-owned boxed value, which is the crossing.
- **Not constructible in the guest** — construction is allocation. The host
  supplies a read-only in-slice and a write-only out-slice.
- **Not aliasable** — the host has proven the two disjoint before the call, so
  the guest cannot form the question.
- **Does not escape the call.**

Bounds remain exact-checked, the guest cannot influence them, and the loader's
`_Static_assert`ed image is untouched because no number changes.

### The loop spelling is also a capability limit, not only a cost

wasm32 does not turn guest self-tail-recursion into a loop, so a self-recursive
traversal is bounded by the **host** call stack. Measured with a fresh instance
per probe (a trap leaves the scratch bump global unrestored, so a reused
instance reports a ceiling of 1 regardless of the real one):

| spelling | outer=1000 | 3000 | 6000 | 12000 | 40000 |
|---|---|---|---|---|---|
| self-recursion | ok | ok | ok | **`RangeError: Maximum call stack size exceeded`** | — |
| `loop`/`recur` | ok | — | — | ok | ok (163M element visits) |

So a guest traversal spelled as self-recursion stops somewhere between 6,128 and
12,128 iterations, and **what stops it is a host `RangeError`, not a Kotoba
diagnostic** — it does not present as a language limit at all. One 1920-sample
row survives; anything frame-shaped does not. `loop`/`recur` is O(1) in depth
and did not trap.

### Why the lowering is not simply widened, which is the next iteration's work

`structured-loop?` is `(and (loop-helper-name? …) (structured-loop-body? …)
(not (reference-type? result)))`. **`structured-loop-body?` — the tail-position
analysis, which is the hard part — is already general**: it takes the function
name, parameter count and body, is written for any self-call, and fails closed
to the historical call lowering on anything it does not recognise. Only the
**name check** confines the lowering to frontend `__kotoba_loop_N` helpers.

Two things stop that name check simply being dropped, and both are why this
wants its own iteration rather than a one-line change:

1. **Fuel is charged in the prologue.** `charge` is emitted once per function
   entry and skipped for loop helpers, so today a self-recursive call costs one
   fuel per call and a `recur` costs none — matching KIR trampoline re-entry.
   Turning a self-recursive function into a loop without moving the charge would
   make its iterations free, weakening a resource bound. Preserving the count
   exactly means emitting the charge at the top of the loop body instead, where
   one iteration charges one unit, exactly as one call does now.
2. **`assert-ref` coverage narrows.** The prologue would run once instead of per
   call, so recursive arguments that are themselves references would no longer
   be re-asserted. `loop`/`recur` already has exactly this exposure and is
   accepted, so the change is consistent with landed behaviour — but it is a
   reduction in checking, and inferring that a security check is redundant is
   not something to do as a side effect of a codegen win.

### What was NOT done, and why

**The carrier is designed and measured, not implemented.** Implementing it spans
kotoba-kir admission, both backends' lowering, `kexe_loader.c` and the verifier's
independent derivation. Landing any proper subset would create exactly the defect
ADR 0284 named — an admission gate admitting what nothing can lower — and that
ADR's whole point is not to add a second one. The Reflect stage was done first
and its verdict is above: **not separated**, which under this loop's rules is the
absence of a result and not a licence to proceed to compiler work.

**The `assert-ref` prologue was not removed.** The counted 2x from `loop`/`recur`
suggests the prologue is unnecessary on internal calls — the argument came from
the caller's own already-asserted local — but that is an inference about a
security check, and export boundaries genuinely need it. It wants its own
iteration with its own falsification.

### Limits of this evidence

- wasm32 under V8 (Node 26) with `runtime/browser-host.mjs`. Not wasmtime, not
  the browser. Counts are engine-independent; timings are not.
- The C arms model native lowering; they are not the native backend. No Kotoba
  native binary was built here — ADR 0284's native numbers are quoted, not
  re-measured.
- One access pattern: sequential reads over a 64-element L1-resident vector.
- **No run here is claim-grade.** load1 was 12–700; a run at 394–613 read 3x the
  same arm's load1 12–23 figure and produced negative slopes in the
  sub-nanosecond arms. Cross-run absolutes are not comparable, and per iteration
  49 even ratios drift day over day. Every timing above is diagnostic.
- The wasm arms' recursion depth is bounded by the host call stack, because
  wasm32 does not turn guest self-tail-recursion into a loop; the fixtures nest
  two levels to keep depth off the slope.
- Separately observed and not pursued: **a trap leaves the scratch bump global
  unrestored**, so every later call on that instance also traps. It is why an
  early depth probe reported a ceiling of 1.
