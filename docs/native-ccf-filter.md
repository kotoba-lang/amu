# Conservative native instruction-class filtering (JUN-27 / JUN-332)

CCF evaluates every emitted CODE prefix for relocation eligibility. The old
loop classified ordinary words with every PC-relative mask. The candidate
uses an immutable64-bit high-byte superset mask before those full predicates.
Every read, unsigned word bound, ADRP refusal, target comparison and limit
remains. There is no mutable-prefix cache or retained proof result.

The native gate compares131072 cases against an unchanged original-evaluator
snapshot and compiles/executes four mutants: unsigned word bound, ADRP refusal,
missing ADR-class bit and missing literal-class bit. The production source
is the mutated subject. Each mutant must compile successfully then exit1;
compiler failure does not count. This group appends to both native ISA plans.
All existing gates, original label mutants/unannotated control, zero controls,
uncached main/full, source-lock, controller and browser checks remain.

The first pre-adoption observer incorrectly refused normal successful compiler
stdout before executing the oracle. The corrected observer distinguishes build
output from silent oracle execution; v2 passed all11 native ARM calls. The
failed attempt is excluded from correctness/performance claims.

## Performance provenance and adoption state

Earlier mixed-image screens reported x86 ratio0.90128 and ARM0.87252, with
byte-identical frozen-core outputs. They built candidate programs from an
older runtime/factory source graph than the staged producer; those ratios
cannot isolate the CCF filter. The adjacent historical-mixed-source JSON files retain those
observations only. Adoption waits for the corrected x86 experiment,
which freezes the complete baseline graph to6abd468dc/source6f9388a6 and
changes only the CCF evaluator, on the same native host/CPU/lock/limits.
The corrected local ARM ABBA passed with ratio0.89172 (17.9035->15.9649s),
all four outputs6ad407c2 and all four executable mutants; actual x86 is reported below.

Native ARM derivation reached F1=F2 and agreement of two new core generations.
Core source31245020/container ec62a5ea and Amu-role8d015478 identities change
with the compiler implementation. Update controller, factory, root/public pins
in that dependency order. The native Kotoba gate and all24 canonical case
source/image/result/exit/fuel expectations remain unchanged. Source/image
qualification flags stay candidate until fresh full/corpus, actual native x86,
controller/public/shared UI/Chrome and final-head CI pass.

DefCID/SCC persistent differential builds, a complete PR CI at most20min and
any deployed behavior remain separate unfinished goals. No performance screen
is an admission verdict, operation approval or full qualification.


## Uncached local full qualification

The exact new root e71d5f18 passed native ARM full tier with126 fresh calls,
read/store reuse disabled, root reproduction and cold C0/core/Kw/Pw/full paths.
The unchanged full19/MIR/GMIR/resource/lock corpus passed146 calls and18 pin
refusals. All27 guest containers and the native runner are byte-identical
to the preceding qualified runtime. The large MIR release count remains
155688217 and its seven released arena fields remain zero. These local
results do not substitute for fresh actual x86/controller/public/shared/Chrome.


## Source-isolated actual x86 and full native qualification

[Run40231614883](https://github.com/kotoba-lang/amu/actions/runs/40231614883)
froze the complete preceding source6f9388a6 at6abd468dc and changed only the
CCF evaluator. Native x86 EPYC7763/CPU0, input44faa79a, source lock, producer
dd289a23 and resource limits were held fixed in ABBA order. Baseline times
were471.612/471.925s, candidate463.599/462.830s: medians471.768->463.214s,
ratio0.981868 (about1.81% less). Both candidate samples were below both baseline
samples. All four outputs were6ad407c2 and all131072 grid cases/four built and
executed mutants passed. These two-pair measurements are a bounded result,
not an official benchmark or a whole-workflow percentage. The larger earlier
mixed-image ratios remain withdrawn as an isolated filter claim.

[Native CI40231995266](https://github.com/kotoba-lang/amu/actions/runs/40231995266)
passed all five mandatory jobs for source637152147/head bbe534fc1. Actual x86
F1=F2=F3 matches public67838fcf; controller24 cases/18 refusals/parent-death,
public3 aliases/source-lock90, shared UI and Chrome passed. Both ISAs passed
the integrated131072 filter cases/four executable mutants, and retained
original label24 calls/nine mutants/unannotated control and zero11/three mutants.
Controller time was253.311s, rebuild247.464s; whole PR24m47s. Different runners
prevent a causal comparison to PR1583's34m15s. The20min goal remains open.

The source/image qualification flags now reflect this complete evidence.
The final metadata/merge head still requires fresh native CI before review
and merge; no image or compiler source byte changes in that promotion.
