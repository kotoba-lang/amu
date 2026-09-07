# Build-scaling co-scientist — tournament state

The research goal is the sentence kotoba-lang.org cannot say today: *at every
source size the harness measures, the Kotoba toolchain produces an artifact
that answers correctly and has the lowest process-cold build wall time of
every available lane.* The fitness function is
[`buildbench`](https://github.com/kotoba-lang/buildbench) plus
[`perfgate`](https://github.com/kotoba-lang/perfgate) at its unrelaxed
default policy — a ≥5% win separated from the arms' own spread — evaluated
independently at every size. Nothing weaker counts, and a size where the
Kotoba lane produces no valid artifact does not score at all: it is not a
slow result, it is the absence of one.

This is the sibling of `docs/codegen-coscientist.md`. That loop asks how fast
the *emitted code* runs; this one asks how fast the *compiler* runs, and it
is the one the published site currently reports as `CEILING FOUND`.

## The loop

| stage | what it means here |
|---|---|
| **Generate** | hypotheses come from the published run's own JSON and from re-measurement, never from reading the compiler and guessing |
| **Reflect** | before compiler work, falsify cheaply: change the *shape* of the workload so that a wrong hypothesis predicts a different curve, and measure. A hypothesis that survives no discriminator does not get a compiler change |
| **Rank** | a barrier that makes a size unmeasurable outranks any speed win at a size that already measures; among speed hypotheses, expected share of the growth term |
| **Evolve** | a confirmed-but-partial mechanism is combined with the next one until the summed effect changes the qualified verdict |
| **Meta-review** | the verdict is `perfgate.core/qualify` on a host-qualified buildbench run, recorded here. A busy-host measurement can move a hypothesis, never close one |

The published run this loop starts from is
`bench/public-build-scaling/latest.json` in `kotoba-lang/kotoba-lang`,
generated 2026-08-31 on `judahnoMac-mini.local` (Apple M4, 10 cores),
`load1 2.73`, 7 samples per lane.

## Scoreboard — published run, 2026-08-31, Apple M4

Median process-cold build wall time, milliseconds. `invalid` = the artifact was
produced and does not load; `refused` = the compiler declined and said why.

| K | source lines | Kotoba CLI | Amu (nbb) | best comparator | verdict |
|---:|---:|---:|---:|---|---|
| 1 | 9 | **11.8** | 733 | clang-native 29.1 | Kotoba fastest |
| 32 | 226 | 35.8 | 825 | clang-native 30.4 | lost |
| 128 | 898 | 111.5 | 1123 | clang-native 35.8 | lost |
| 129 | 905 | *invalid* | 1124 | clang-native 36.6 | no Kotoba answer |
| 512 | 3586 | *invalid* | 3381 | clang-native 60.6 | no Kotoba answer |
| 1023 | 7163 | *invalid* | 9242 | clang-native 105.0 | no Kotoba answer |
| 1024 | 7170 | *refused* | *refused* | clang-native 101.7 | no Kotoba answer |
| 2048 | 14338 | *refused* | *refused* | clang-native 223.2 | no Kotoba answer |

**1 of 8 sizes is won.** The goal sentence is false, and the site says so
(`BUILD SCALING · CEILING FOUND`). Three different *kinds* of thing have to
change — a release that was never cut, a language bound that needs deciding,
and a genuine performance defect — which is why they are separate hypotheses
and not one project.

## Hypothesis population

| id | hypothesis | status | evidence |
|---|---|---|---|
| **H-1** | The `invalid` cells at K≥129 are one already-fixed defect that is not in anyone's hands yet: 0.7.3 truncates a Wasm `call` operand to one byte, so every function index ≥128 gets a LEB128 continuation bit with no continuation byte | **confirmed — no compiler work left** | `kotoba-lang/kotoba` CHANGELOG *Unreleased*, carried in via kotoba-wasm `2cec282`; issue #526 open; `v0.7.3` (2026-08-29) is still the newest release. Re-verified independently 2026-09-07: current Amu at K=768 emits a module that instantiates and answers `main() = 768` |
| **H-2** | The `refused` cells at K≥1024 are a defect in `max-functions` | **rejected on reflection — do not raise the bound** | `max-functions 1024` is one of ~20 declared per-module admission bounds in `kotoba-sema` `frontend.cljc:1213`. Loosening a declared bound so a benchmark passes is the benchmark measuring its own thresholds. Whether the bound is *right* is a separate, owner-level question — see H-2′, which is where the published justification for it turned out to be wrong |
| **H-2′** | K≥1024 has no Kotoba number because the harness is single-file by construction, not because the language stops. A project lane (`--source-path`) gives those sizes an answer without touching a bound | **refused — iteration 1** | `max-project-functions` is **also 1024** and is checked against the *linked* program (`kotoba/compiler/project.cljc:9`). A 4-module, 800-function project links and checks; a 4-module, 2048-function project is refused with `linked project exceeds function limit`. The premise both the README and the site state is false as measured |
| **H-3** | Amu's build time is not linear in function count. A quadratic term, not the constant factor, is what makes large sizes hopeless | **confirmed — iteration 1** | two independent hosts; see below |
| **H-3a** | the quadratic is in the backend (lowering + Wasm emission) | **refused — iteration 1** | `check` is 93% of `compile` at K=1023 (16777 / 18069 ms). The whole backend is ~7% of the time and cannot hold a term that is 76% of the growth |
| **H-3b** | the quadratic is in *body size* — one function whose body has K bindings costs O(K²) | **partial — iteration 1** | splitting `main`'s K bindings across M chunk functions at fixed K=768 removes ~30% of the superlinear term and then plateaus: 11541 → 10539 → 9942 → 9830 → 9926 ms for M = 1, 2, 4, 12, 48 |
| **H-3c** | the rest is per-*module*: a pass whose cost is (functions × functions) | **refused — iteration 1** | 1000 one-operation functions check in 3427 ms on a straight line (fitted quadratic coefficient 0.00026, 13% of the growth). Function count is not the quantity |
| **H-3d** | the quantity is **total expression nodes in the module**, not functions, bodies or calls separately | **confirmed — iteration 1** | one two-parameter model, `1419 + 0.535·N + 0.0000447·N²` ms, predicts five points across four differently-shaped workload families within the host's own spread |

## Iteration 1 — 2026-09-07: the growth term is quadratic, and it is in the front end

Re-measured on a **second** machine (Apple M1 Max, 10 cores, 32 GiB) against
Amu `origin/main` `715138d0`, 3 process-cold samples per point, the same
generated workload and the same declared fuel budget as the published run.

**This host was busy (`load1` 10–23), so no absolute millisecond here is
portable and none of it qualifies under perfgate.** What is being claimed from
it is the *shape* of the curve, which is what a busy host still supports: the
load fell on every point.

### The curve

| K | `amu check` | `amu compile --target wasm32` | check share |
|---:|---:|---:|---:|
| 1 | 1504 | 1540 | 98% |
| 64 | 1886 | 2100 | 90% |
| 128 | 2293 | 2517 | 91% |
| 256 | 4035 | 3727 | — |
| 512 | 6619 | 7377 | 90% |
| 768 | 11242 | 12077 | 93% |
| 1023 | 16777 | 18069 | 93% |

Marginal cost per added function, `compile`: **8.9 ms at K=64, 23.5 ms at
K=768→1023.** A linear compiler has a flat marginal cost. This one's grows by
2.6× over a 16× range in K.

Least squares on both hosts:

| host | fit (ms) | quadratic dominates above |
|---|---|---:|
| Apple M4, published run | `733 + 2.02·K + 0.00616·K²` | K ≈ 328 |
| Apple M1 Max, this run | `1540 + 6.63·K + 0.00931·K²` | K ≈ 712 |

On the **published** run the quadratic term is `0.00616 × 1023² = 6.4 s` of the
8.5 s that K=1023 costs above its own intercept — **76% of the growth**. The
constant factor is not the problem at large sizes. The exponent is.

### Where it is not

`amu check` is 93% of `amu compile` at K=1023. Whatever is quadratic, the
backend does not contain it: lowering, register allocation and Wasm emission
together are ~7% of the time.

### The discriminators

The workload has three dimensions that a naive reading conflates: how many
functions the module has, how big one function's body is, and how many call
sites there are. Four shapes separate them. All at fixed effort, `amu check`,
median of 3, same host and hour.

| shape | what it holds fixed | result |
|---|---|---|
| **split `main`** — K=768 leaves, `main`'s 768 bindings dealt across M chunk functions | function count and call count roughly fixed, one body shrinks by M | 11541 → 10539 → 9942 → 9830 → 9926 → 10949 ms for M = 1, 2, 4, 12, 48, 192. Recovers ~15% and then plateaus — and *rises* again at M=192, where the split has added 192 more functions |
| **cut the calls** — 768 leaves, `main` calls only the first C | function count fixed at 768 | C = 768 → 10543, 384 → 8491, 96 → 7661, 1 → 7256 ms |
| **shrink the bodies** — K one-operation leaves, `main` calls one | call count fixed at 1, bodies minimal | 1419 (K=1), 1646 (128), 2128 (384), 2985 (768), 3427 (1000) ms — **essentially linear**, fitted quadratic coefficient 0.00026 |
| **keep the bodies, cut the calls** — K four-operation leaves, `main` calls one | call count fixed at 1, bodies full | 1447 (K=1), 2102 (128), 3554 (384), 7420 (768) ms |

**Function count alone is not the quadratic.** A thousand one-operation
functions check in 3.4 s and the curve through them is a straight line. The
same thousand functions with four-operation bodies is where the term appears.

That points at one quantity rather than three, and it fits: **total expression
nodes in the module.** Writing `N` for the node count each shape produces
(≈ 3 per minimal leaf, ≈ 9 per four-operation leaf, ≈ 4 per `main` binding),
a single two-parameter model fits all four families on this host:

```
check(N) ≈ 1419 + 0.535·N + 0.0000447·N²   ms
```

| shape | N | predicted | measured |
|---|---:|---:|---:|
| minimal bodies, K=384 | 1152 | 2094 | 2128 |
| minimal bodies, K=1000 | 3000 | 3427 (fitted) | 3427 |
| four-op bodies, 1 call, K=128 | 1152 | 2094 | 2102 |
| four-op bodies, 1 call, K=768 | 6912 | 7239 | 7420 |
| full workload, K=128 | 1664 | 2433 | 2293 |
| full workload, K=768 | 9984 | 11242 (fitted) | 11242 |
| full workload, K=1023 | 13299 | 16442 | 16777 |

The residuals are within the spread of a host at `load1` 10–23. The two points
marked *(fitted)* are the ones the coefficients were solved from; the other
five are predictions.

### What that costs at the declared bound

`max-expression-nodes` is **50,000** (`kotoba-sema` `frontend.cljc:1216`). The
model says a module at that bound takes `0.0000447 × 50000² ≈ 112 s` in the
quadratic term alone — on this host, hosted on nbb. **The admission bound
currently admits modules the front end cannot check in reasonable time.** That
is a stronger statement than the benchmark's, and it does not depend on any
comparator.

## Iteration 1 — the K≥1024 story is not the one that was published

`H-2′` said: the harness is single-file by construction, so give large sizes a
**project** (`--source-path`) lane and they get an answer without touching a
bound. Both `buildbench`'s README and kotoba-lang.org state the premise it
rests on — *"The limit is per module: a larger program is a multi-module
project."*

**Measured 2026-09-07 against Amu `715138d0`, that premise is false.**

```
$ amu check main.kotoba --source-path proj800     #  4 modules, 800 leaves
{:format :kotoba.check/v1, :definitions {...}}    #  links and checks

$ amu check main.kotoba --source-path proj2048    #  4 modules, 2048 leaves
{:ok false, :error :project-link,
 :message "linked project exceeds function limit"}
```

`kotoba/compiler/project.cljc:9` — `(def max-project-functions 1024)`, checked
against the **linked** program, not per module. The per-module
`sema/max-functions` bound has a whole-program twin with the same value, so
there is no arrangement of modules today that compiles a 2048-function Kotoba
program.

That is a correction to a published claim, and it changes this loop's goal
rather than merely adding work to it: at K=1024 and K=2048 the Kotoba lane has
no answer for a reason no amount of compiler speed will remove. Either the
whole-program bound moves — an owner-level language decision with a real
justification behind it, not a benchmark's convenience — or the goal sentence
is restated as *fastest at every size the language admits*, and the site says
which sizes those are.

Both texts should stop saying the multi-module sentence in the meantime.

## Ranking after iteration 1

| rank | action | why it ranks here |
|---:|---|---|
| 1 | **Find the node-quadratic pass in the front end** and remove it | it is 76% of the growth at K=1023 on the published host, it is in the 93% of the time that `check` owns, and every size above ~300 is hostage to it. Nothing else moves the curve's *shape* |
| 2 | **Cut `v0.7.4`** | 0.7.3 silently mis-compiles any single file above 128 functions. The fix landed upstream and has been sitting unreleased since; the benchmark is the least of it. No research is required — the blocker is that packaging needs a JDK, GraalVM `native-image` and three platform targets |
| 3 | **Correct the multi-module sentence** in `buildbench/README.md` and in the site's build-scaling table | it is a published claim that measurement refutes |
| 4 | **Decide the whole-program function bound** (owner) | until it is decided, K=1024 and K=2048 are unscoreable and the goal sentence has to name its own domain |
| 5 | Constant factor: the released CLI's ~0.78 ms/function against Clang's ~0.095 | the intercept is already 2.5× better than Clang's. Nothing here is worth doing before rank 1, because at the sizes where the claim is currently lost the quadratic term is bigger than the whole comparator |

### Iteration 2's experiment, stated before it is run

Instrument the `check` pipeline in `kotoba-sema` `frontend.cljc` — the pass
sequence between parse and `check-value-types!` — with per-pass wall time, and
run it at N ≈ 1,700 / 7,000 / 13,000 expression nodes. The prediction that
would falsify the node model: no single pass grows superlinearly and the term
is spread across all of them. The prediction that would confirm it: one or two
passes hold nearly all of the `N²` coefficient.

Do not start from reading the code. The four discriminators above were all
cheaper than the two wrong guesses this loop made from reading it
(`H-3a` backend, `H-3c` function-count), and both wrong guesses were refuted in
under ten minutes of measurement each.

## Reproducing iteration 1

```sh
git clone https://github.com/kotoba-lang/buildbench     # the harness
# the four discriminator shapes are generated variants of buildbench's own
# workload: (1) main's bindings dealt across M chunk functions, (2) main
# calling only the first C leaves, (3) one-operation leaves, (4) four-operation
# leaves with main calling one. Each is `amu check <file>` with the declared
# fuel policy, median of 3, process-cold.
```

The absolute numbers in this iteration are from Apple M1 Max at `load1` 10–23
and are **not** portable and **not** perfgate-qualified. What is claimed from
them is the shape of the curve and the ordering of the four shapes, which
survives a busy host because the load fell on all of them.
