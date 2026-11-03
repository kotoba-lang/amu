# Native byte-copy and checked-access optimization

JUN-573. The public six-domain run measured 1 MiB read-and-sum x12 at
1163.732 ms on native Linux x86_64. Syscall tracing accounted for about3 ms;
most elapsed time was in value expansion, copying and checked byte access.
The benchmark source also unnecessarily converted the FS2 bytes response to
an integer vector and repeatedly requested the immutable response length.

Both native runtime sources now derive vector metadata once per operation,
while freshly checking the handle and index before every access. The private
item-copy, byte-expansion and byte-value-validation loops derive their stable
items mapping base once outside the loop. No proof or descriptor is retained
across operations. No callbacks, arena rollbacks or mapping mutation occur
inside these private scalar loops. Copy order stays scalar/forward, including
overlap; byte order, all bounds, fuel, arena counts, capacities, descriptor
creation, and absolute item highwater remain unchanged.

## Executed evidence

The baseline is the complete49-module source at `c1c9d7c6fabb28f2cba4cfc8f44e1e306f2f3924`.
The candidate differs only in the two runtime sources. Both were built from
the previously native-qualified selfhost image `d5450320` with
`PATH=/nonexistent` and actual single-executable build traces. All49 modules
were retained. The baseline has three equal native images `cffe1701`; the
candidate's initial image `f1a07529` was emitted with its predecessor's outer
runtime, followed by three identical native images `fee02dbb`.

`seed/tests/native-byte-copy.kotoba` executes all byte values over lengths
0..260 and4095/4096/4097, including empty/slice/concat/copy behavior and
mutation of both source and returned vector to check byte immutability.
Its native positive verdict is42; a built wrong-expectation control returns-1.
The unchanged runtime24 and five extra byte-range/index/slice refusals execute
on both compilers. Their exit, full result, fuel and arena observations match
exactly. The observer supplies no compiler, evaluator or runtime fallback.

The compact packet under `docs/evidence/native-io-copy-20261029/` contains
native fixed-point records, build execve traces and every gate output.
Focused paired timing is maintained with the public benchmark evidence in
kotoba-lang/kotoba-lang PR836. Preliminary three-sample diagnostics are not
published as a ranking.

## Reproduce without changing public pins

On native Linux x86_64, use the exact previously qualified native bootstrap
and a new output directory. Run through the shared build queue:

```sh
python3 scripts/seed/native_build_queue.py -- \
  python3 scripts/seed/observe-full-native-fixedpoint.py \
  --bootstrap /absolute/path/to/qualified-amu \
  --bootstrap-sha256 d545032000f25e30fd1990ca454f81ac469921e90d8dbac9e38680606174b242 \
  --output /absolute/new/candidate-output
```

For the baseline, add `--source-revision c1c9d7c6fabb28f2cba4cfc8f44e1e306f2f3924`
and use a different new output directory. Require three consecutive equal
images; retain any initial unequal image. Run the native differential fixture
and the unchanged runtime24 with the final compiler image from each side:

```sh
python3 scripts/seed/native_build_queue.py -- \
  python3 scripts/seed/check-native-byte-copy.py \
  --baseline /absolute/baseline/G2.elf \
  --compiler /absolute/candidate/G3.elf \
  --output /absolute/new/copy-gate
```

These are scoped native x86 engineering observations. ARM execution, all
mandatory native CI/controller gates, regenerated root/public/role pins,
merge/main readback and release qualification remain separate. No descriptor,
public binary, authority or production route is promoted by this patch.

Existing documentation discrepancy: `AGENTS.md:93` describes FULL-MANIFEST as
48 modules, while the current manifest contains49 source entries (lines2–50).
This work preserves all49 actual modules. The owner-controlled AGENTS wording
has been reported and left unchanged.
