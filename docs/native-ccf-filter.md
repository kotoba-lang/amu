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
all four outputs6ad407c2 and all four executable mutants; actual x86 is pending.

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
