# R5 part A tests (owner R5A): modules and linking

Gate: `seed/tests/r5a/gate-r5a.sh` (after `scripts/seed/build.sh 1` and `2` with seed-0 = the R4 seed): every previous gate
(`gates.sh --rung r4 --no-build --skip G3`), G3 against `seed/tests/golden/refusal-r5a.txt`, the part-A cases of
`seed/tests/r5/check-r5.sh` (namespace_priority, entry_extensions, reader_target, and the module/link feature programs;
the effect programs of part B are listed in `part-b.txt` and only reported), and the rung proof on the project route: the
seed split into namespaces (`seed/split/gen-split.py` -> `seed/split/seed/*.kotoba`, 14 namespaces) compiled through
60-proj by the unity seed and by itself (fixed point), compiling the unity to the same container, G1/G2 with the linked seed.
