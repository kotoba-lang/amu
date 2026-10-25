# Sglib input-table source-shape probe

Status: rejected. The compiler already lowers the original equality chain to a literal table. The source-table variant fails exact fuel and increases diagnostic native instruction count.

## Hypothesis and counter-hypothesis

Sglib's fixed 100-value input map is written as nested equality tests for indices 0 through 99. It is called in six 100-iteration body stages: `fill`, `list-build`, `hash-build`, `queue-add`, `heap-add`, and `tree-build`. This gives 600 map lookups per body. The M4 M105 record has Kotoba/C = 1.1546, so a constant-vector representation was tested as a possible way to match C's direct indexed input storage.

The counter-hypothesis was that the selfhost compiler already recognizes this map and emits a direct constant table. Disassembly confirmed that explanation.

## Build and exactness

The isolated source variant compiled to a 51,960-byte native image. At registered `n=253952`, it returned result `1` and the arena report matched the control, but official exactness failed on fuel:

- Control benchmark fuel: `3,858,038,786`
- Table benchmark fuel: `4,010,409,986`
- Difference: `152,371,200 = 600 * 253,952`
- Verification fuel increased by 100 for the final 100 input reads.

The source-level vector access therefore cannot replace the existing source form under the current exact-fuel rule.

## Generated-code evidence

The control's first function is not a 100-branch machine-code chain. It checks `0 <= i < 100`, computes the literal-table address with `adr`, and reads the selected 64-bit constant with one indexed `ldr`; the 100 values follow as inline table data. This is the code shape the source-table rewrite was trying to obtain.

At `n=8192`, one instrumented diagnostic counted 1,000,821,822 native instructions for control and 1,309,666,609 for the vector-table variant (1.3096x). The single diagnostic run is not qualified timing evidence, but it is enough to reject this source rewrite as a performance candidate.

## Disposition and next search

Keep the original port and compiler unchanged. The input map is already optimized. A guest profile now ranks linked-list merge, tree insertion/search, and heap sift-down as the main sampled regions. A branchless source-level list-merge rewrite preserved exactness but increased dynamic instruction count by 20.82%; see `../crossdomain-m105-sglib-hot-profile-20261017/README.md`. The next attempt should inspect compiler lowering of the original source shape before changing the port.

## Provenance

- Control image: 51,968 bytes, `5e0b9072eb8a404479d569c5986ba6f008bd6143b8815fb0ea2db3f2e91d0040`
- Candidate image: 51,960 bytes, `1e146fff3e9d33d63de55b74be3d9796469b1c00c5e767b14ad6a4df7571f924`
- Source diff and official exactness report: `workspaces/codex/amu-sglib-input-table-20261017/attempt-1/`
- Control disassembly: `workspaces/codex/amu-sglib-input-table-20261017/attempt-1/disassembly-control/payload.disasm.txt`
- Instruction-count diagnostics: `workspaces/codex/amu-sglib-input-table-20261017/attempt-1/instruction-count/`
