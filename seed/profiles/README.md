# seed/profiles -- recorded build profiles beside the rung lineage (agent ARENA, 2026-10-04)

A profile is the SAME seed source as a recorded rung (seed/rungs/<rung>.record, its `unity_commit`) built with a
different `seed/MEMORY-MAP`. It is an option, not a rung: `scripts/seed/bootstrap.sh` never builds from it and no later
rung depends on it. Each `<profile>-<rung>.record` is reproduced and checked by its script.

| profile | script | what changes | why |
|---|---|---|---|
| large-m | `scripts/seed/large-m.sh --rung r6d --check` (map rewrite: `scripts/seed/large_m.py`) | M 8 Mi -> 16 Mi words (the loader's per-vector boundary); TOK 655,360, NODE/SIR 458,752, CODE 1 Mi, OUT 3 Mi, LABEL 262,144, LITB 512 Ki, LIT 32 Ki, FN 16 Ki, FIX 128 Ki, EXP 8,192 | `compile-kir` of the whole linked kotoba-sema frontend (amu-front, ~454k KIR tokens after the ARENA table change; the default TOK holds 262,144) and of a marked KIR for the arena census (3,670 exports) |

Checks the script makes (all measured 2026-10-04, record `large-m-r6d.record`): seed-1 == seed-2 (fixed point
9e7895f1, 698,960 B); the large-M seed compiles the rung's own default-map unity to exactly the rung seed (e3654a64): a
compiler's output does not depend on its own table sizes; NODE-CAP stays within 30-lower's loop-node mask (2^20).
Use: `AF_SEED=build/seed-large-m-r6d/b/seed-1.bin seed/amu-front/build.sh <work>`.
