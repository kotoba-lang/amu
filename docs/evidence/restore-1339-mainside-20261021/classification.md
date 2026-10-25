# #1339 merge (e670387b) per-file classification

Source diff: e670387b^1..e670387b (449 files: 408 deleted, 41 modified). Correct merge C = git merge-tree --merge-base=bea7b9b2 bc84fa5a 740caee4 (tree 2308a8bb). Restore = diff(e670387b, C) applied 3-way onto origin/main 1b0687a5.

Classes: a = restored in this PR, a-3way = restored with a 3-way merge onto later main work, b = already restored or superseded on main, c = #1339 own change kept, exception = not restored (see note).

| class | count |
|---|---|
| a | 376 |
| a-3way | 6 |
| b | 59 |
| c | 3 |
| exception | 5 |

| class | git status in merge | file | evidence |
|---|---|---|---|
| a | M | `.github/workflows/fuzz.yml` | restored main-side hunks (file unchanged on main since e670387b) |
| a | M | `.github/workflows/seed-x86_64-linux.yml` | restored main-side hunks (file unchanged on main since e670387b) |
| a | M | `README.md` | restored main-side hunks (file unchanged on main since e670387b) |
| a | D | `docs/adr/0356-the-selfhost-seed-emits-the-aiueos-kernel-object-abi.md` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/adr/0357-the-accelerator-pipeline-enters-the-cli.md` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/adr/0358-the-dispatch-workgroup-rows-become-measured.md` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | M | `docs/architecture.md` | restored main-side hunks (file unchanged on main since e670387b) |
| a | D | `docs/evidence/entry_route_encoding_probe-20261020.py` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu-subgroup-probe-m1max-20261019/README.md` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu-subgroup-probe-m1max-20261019/run-1.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu-subgroup-probe-m1max-20261019/run-2.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu-subgroup-probe-m1max-20261019/run-3.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu-workgroup-compute-m1max-20261019/README.md` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu-workgroup-compute-m1max-20261019/run-1.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu-workgroup-compute-m1max-20261019/run-2.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu-workgroup-compute-m1max-20261019/run-3.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu-workgroup-compute-m1max-20261019/run-4.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu-workgroup-compute-m1max-20261019/run-5.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu-workgroup-sweep-m1max-20261018/README.md` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu-workgroup-sweep-m1max-20261018/run-1.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu-workgroup-sweep-m1max-20261018/run-2.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu-workgroup-sweep-m1max-20261018/run-3.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/chunksweep-20261019/run-1-a1-w64-524288-c1.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/chunksweep-20261019/run-1-a2-w64-1048576-c2.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/chunksweep-20261019/run-1-a4-w64-4194304-c8.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/chunksweep-20261019/run-1-b1-w64-2097152-c1.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/chunksweep-20261019/run-1-b2-w64-2097152-c2.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/chunksweep-20261019/run-1-b3-w64-2097152-c4.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/chunksweep-20261019/run-1-b4-w64-2097152-c8.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/chunksweep-20261019/run-2-a1-w64-524288-c1.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/chunksweep-20261019/run-2-a2-w64-1048576-c2.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/chunksweep-20261019/run-2-a4-w64-4194304-c8.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/chunksweep-20261019/run-2-b1-w64-2097152-c1.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/chunksweep-20261019/run-2-b2-w64-2097152-c2.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/chunksweep-20261019/run-2-b3-w64-2097152-c4.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/chunksweep-20261019/run-2-b4-w64-2097152-c8.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/chunksweep-20261019/run-3-a1-w64-524288-c1.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/chunksweep-20261019/run-3-a2-w64-1048576-c2.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/chunksweep-20261019/run-3-a4-w64-4194304-c8.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/chunksweep-20261019/run-3-b1-w64-2097152-c1.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/chunksweep-20261019/run-3-b2-w64-2097152-c2.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/chunksweep-20261019/run-3-b3-w64-2097152-c4.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/chunksweep-20261019/run-3-b4-w64-2097152-c8.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/chunksweep-w256-20261019/README.md` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/chunksweep-w256-20261019/gate.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/chunksweep-w256-20261019/run-1-anchor-w64-2097152-c1.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/chunksweep-w256-20261019/run-1-w256-2097152-c1.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/chunksweep-w256-20261019/run-1-w256-2097152-c2.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/chunksweep-w256-20261019/run-1-w256-2097152-c4.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/chunksweep-w256-20261019/run-1-w256-2097152-c8.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/chunksweep-w256-20261019/run-2-anchor-w64-2097152-c1.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/chunksweep-w256-20261019/run-2-w256-2097152-c1.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/chunksweep-w256-20261019/run-2-w256-2097152-c2.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/chunksweep-w256-20261019/run-2-w256-2097152-c4.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/chunksweep-w256-20261019/run-2-w256-2097152-c8.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/chunksweep-w256-20261019/run-3-anchor-w64-2097152-c1.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/chunksweep-w256-20261019/run-3-w256-2097152-c1.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/chunksweep-w256-20261019/run-3-w256-2097152-c2.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/chunksweep-w256-20261019/run-3-w256-2097152-c4.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/chunksweep-w256-20261019/run-3-w256-2097152-c8.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/flip2d-w32-t3132-20261019/README.md` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/flip2d-w32-t3132-20261019/analyze-2000.py` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/flip2d-w32-t3132-20261019/analyze-2000.txt` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/flip2d-w32-t3132-20261019/gate-vs-1716.txt` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/flip2d-w32-t3132-20261019/gate.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/flip2d-w32-t3132-20261019/norm_gate.py` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/flip2d-w32-t3132-20261019/run-1-w32t24.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/flip2d-w32-t3132-20261019/run-1-w32t31.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/flip2d-w32-t3132-20261019/run-1-w32t32.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/flip2d-w32-t3132-20261019/run-1-w64t31.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/flip2d-w32-t3132-20261019/run-1-w64t32.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/flip2d-w32-t3132-20261019/run-2-w32t24.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/flip2d-w32-t3132-20261019/run-2-w32t31.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/flip2d-w32-t3132-20261019/run-2-w32t32.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/flip2d-w32-t3132-20261019/run-2-w64t31.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/flip2d-w32-t3132-20261019/run-2-w64t32.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/flip2d-w32-t3132-20261019/run-3-w32t24.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/flip2d-w32-t3132-20261019/run-3-w32t31.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/flip2d-w32-t3132-20261019/run-3-w32t32.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/flip2d-w32-t3132-20261019/run-3-w64t31.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/flip2d-w32-t3132-20261019/run-3-w64t32.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/flip2d-w32-t3132-20261019/run-sweep-2000.sh.txt` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/isodesc-l2048-20261019/README.md` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/isodesc-l2048-20261019/gate.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/isodesc-l2048-20261019/run-1-anchor-w64-c1.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/isodesc-l2048-20261019/run-1-iso128-c16.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/isodesc-l2048-20261019/run-1-iso256-c8.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/isodesc-l2048-20261019/run-1-iso64-c32.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/isodesc-l2048-20261019/run-2-anchor-w64-c1.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/isodesc-l2048-20261019/run-2-iso128-c16.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/isodesc-l2048-20261019/run-2-iso256-c8.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/isodesc-l2048-20261019/run-2-iso64-c32.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/isodesc-l2048-20261019/run-3-anchor-w64-c1.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/isodesc-l2048-20261019/run-3-iso128-c16.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/isodesc-l2048-20261019/run-3-iso256-c8.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/isodesc-l2048-20261019/run-3-iso64-c32.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/isodesc-l2048-20261019/run-gate-1152.sh.txt` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/isodesc-l2048-20261019/run-sweep-1152.sh.txt` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-20261019/README.md` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-20261019/gate.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-20261019/run-1-b1.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-20261019/run-1-t16.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-20261019/run-1-t32.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-20261019/run-1-t8.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-20261019/run-2-b1.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-20261019/run-2-t16.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-20261019/run-2-t32.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-20261019/run-2-t8.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-20261019/run-3-b1.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-20261019/run-3-t16.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-20261019/run-3-t32.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-20261019/run-3-t8.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-20261019/run-gate-1217.sh.txt` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-20261019/run-sweep-1217.sh.txt` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t24-20261019/README.md` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t24-20261019/gate-vs-1359.txt` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t24-20261019/gate.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t24-20261019/norm_gate.py` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t24-20261019/refuse-t24-at-2pow21.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t24-20261019/run-1-cal16.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t24-20261019/run-1-n16.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t24-20261019/run-1-n24.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t24-20261019/run-1-n32.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t24-20261019/run-1-n8.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t24-20261019/run-2-cal16.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t24-20261019/run-2-n16.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t24-20261019/run-2-n24.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t24-20261019/run-2-n32.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t24-20261019/run-2-n8.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t24-20261019/run-3-cal16.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t24-20261019/run-3-n16.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t24-20261019/run-3-n24.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t24-20261019/run-3-n32.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t24-20261019/run-3-n8.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t24-20261019/run-gate-1246.sh.txt` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t24-20261019/run-sweep-1246.sh.txt` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t25t28t30-20261019/analyze-1754.py` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t25t28t30-20261019/analyze-1754.txt` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t25t28t30-20261019/gate-vs-1369.txt` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t25t28t30-20261019/gate.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t25t28t30-20261019/norm_gate.py` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t25t28t30-20261019/run-1-c24.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t25t28t30-20261019/run-1-c25.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t25t28t30-20261019/run-1-c28.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t25t28t30-20261019/run-1-c30.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t25t28t30-20261019/run-1-c32.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t25t28t30-20261019/run-1-cal31.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t25t28t30-20261019/run-2-c24.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t25t28t30-20261019/run-2-c25.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t25t28t30-20261019/run-2-c28.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t25t28t30-20261019/run-2-c30.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t25t28t30-20261019/run-2-c32.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t25t28t30-20261019/run-2-cal31.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t25t28t30-20261019/run-3-c24.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t25t28t30-20261019/run-3-c25.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t25t28t30-20261019/run-3-c28.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t25t28t30-20261019/run-3-c30.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t25t28t30-20261019/run-3-c32.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t25t28t30-20261019/run-3-cal31.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t25t28t30-20261019/run-gate-1754.sh.txt` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t25t28t30-20261019/run-sweep-1754.sh.txt` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t2627-gride-20261019/analyze-1906.py` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t2627-gride-20261019/analyze-1906.txt` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t2627-gride-20261019/run-1-e24.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t2627-gride-20261019/run-1-e26.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t2627-gride-20261019/run-1-e27.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t2627-gride-20261019/run-1-e32.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t2627-gride-20261019/run-2-e24.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t2627-gride-20261019/run-2-e26.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t2627-gride-20261019/run-2-e27.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t2627-gride-20261019/run-2-e32.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t2627-gride-20261019/run-3-e24.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t2627-gride-20261019/run-3-e26.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t2627-gride-20261019/run-3-e27.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t2627-gride-20261019/run-3-e32.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t2627-gride-20261019/run-sweep-1906.sh.txt` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t29-gridd-20261019/analyze-1830.py` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t29-gridd-20261019/analyze-1830.txt` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t29-gridd-20261019/run-1-cc28.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t29-gridd-20261019/run-1-cc30.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t29-gridd-20261019/run-1-d28.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t29-gridd-20261019/run-1-d29.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t29-gridd-20261019/run-1-d32.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t29-gridd-20261019/run-2-cc28.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t29-gridd-20261019/run-2-cc30.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t29-gridd-20261019/run-2-d28.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t29-gridd-20261019/run-2-d29.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t29-gridd-20261019/run-2-d32.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t29-gridd-20261019/run-3-cc28.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t29-gridd-20261019/run-3-cc30.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t29-gridd-20261019/run-3-d28.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t29-gridd-20261019/run-3-d29.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t29-gridd-20261019/run-3-d32.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t29-gridd-20261019/run-sweep-1837.sh.txt` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t31-20261019/README.md` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t31-20261019/analyze-1716.py` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t31-20261019/analyze-1716.txt` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t31-20261019/gate-vs-1360.txt` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t31-20261019/gate.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t31-20261019/norm_gate.py` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t31-20261019/run-1-n24.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t31-20261019/run-1-n31.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t31-20261019/run-1-n32.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t31-20261019/run-2-n24.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t31-20261019/run-2-n31.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t31-20261019/run-2-n32.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t31-20261019/run-3-n24.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t31-20261019/run-3-n31.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t31-20261019/run-3-n32.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t31-20261019/run-gate-1716.sh.txt` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t31-20261019/run-sweep-1716.sh.txt` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t3334-gridf-20261019/analyze-1937.py` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t3334-gridf-20261019/analyze-1937.txt` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t3334-gridf-20261019/run-1-e24.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t3334-gridf-20261019/run-1-e32.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t3334-gridf-20261019/run-1-e33.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t3334-gridf-20261019/run-1-e34.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t3334-gridf-20261019/run-2-e24.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t3334-gridf-20261019/run-2-e32.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t3334-gridf-20261019/run-2-e33.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t3334-gridf-20261019/run-2-e34.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t3334-gridf-20261019/run-3-e24.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t3334-gridf-20261019/run-3-e32.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t3334-gridf-20261019/run-3-e33.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t3334-gridf-20261019/run-3-e34.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/tilecross-w64-t3334-gridf-20261019/run-sweep-1937.sh.txt` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/within-tick-batches-w64t32-20261019/README.md` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/within-tick-batches-w64t32-20261019/analyze-2106.py` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/within-tick-batches-w64t32-20261019/analyze-2106.txt` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/within-tick-batches-w64t32-20261019/gate-2030.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/within-tick-batches-w64t32-20261019/gate-vs-2030.txt` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/within-tick-batches-w64t32-20261019/gate.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/within-tick-batches-w64t32-20261019/norm_gate.py` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/within-tick-batches-w64t32-20261019/run-A-1-w64t31.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/within-tick-batches-w64t32-20261019/run-A-1-w64t32.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/within-tick-batches-w64t32-20261019/run-A-2-w64t31.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/within-tick-batches-w64t32-20261019/run-A-2-w64t32.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/within-tick-batches-w64t32-20261019/run-A-3-w64t31.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/within-tick-batches-w64t32-20261019/run-A-3-w64t32.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/within-tick-batches-w64t32-20261019/run-B-1-w64t31.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/within-tick-batches-w64t32-20261019/run-B-1-w64t32.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/within-tick-batches-w64t32-20261019/run-B-2-w64t31.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/within-tick-batches-w64t32-20261019/run-B-2-w64t32.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/within-tick-batches-w64t32-20261019/run-B-3-w64t31.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/within-tick-batches-w64t32-20261019/run-B-3-w64t32.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/within-tick-batches-w64t32-20261019/run-sweep-2106.sh.txt` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/wsweep-20261019/README.md` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/wsweep-20261019/run-1-w128.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/wsweep-20261019/run-1-w256.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/wsweep-20261019/run-1-w32.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/wsweep-20261019/run-1-w64.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/wsweep-20261019/run-2-w128.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/wsweep-20261019/run-2-w256.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/wsweep-20261019/run-2-w32.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/wsweep-20261019/run-2-w64.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/xsession-rep3-w64t32-20261019/README.md` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/xsession-rep3-w64t32-20261019/analyze-2030.py` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/xsession-rep3-w64t32-20261019/analyze-2030.txt` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/xsession-rep3-w64t32-20261019/gate-vs-2000.txt` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/xsession-rep3-w64t32-20261019/gate.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/xsession-rep3-w64t32-20261019/norm_gate.py` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/xsession-rep3-w64t32-20261019/run-1-w32t24.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/xsession-rep3-w64t32-20261019/run-1-w32t31.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/xsession-rep3-w64t32-20261019/run-1-w32t32.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/xsession-rep3-w64t32-20261019/run-1-w64t31.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/xsession-rep3-w64t32-20261019/run-1-w64t32.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/xsession-rep3-w64t32-20261019/run-2-w32t24.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/xsession-rep3-w64t32-20261019/run-2-w32t31.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/xsession-rep3-w64t32-20261019/run-2-w32t32.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/xsession-rep3-w64t32-20261019/run-2-w64t31.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/xsession-rep3-w64t32-20261019/run-2-w64t32.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/xsession-rep3-w64t32-20261019/run-3-w32t24.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/xsession-rep3-w64t32-20261019/run-3-w32t31.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/xsession-rep3-w64t32-20261019/run-3-w32t32.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/xsession-rep3-w64t32-20261019/run-3-w64t31.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/xsession-rep3-w64t32-20261019/run-3-w64t32.log` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/xsession-rep3-w64t32-20261019/run-gate-2030.sh.txt` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/gpu/xsession-rep3-w64t32-20261019/run-sweep-2030.sh.txt` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/jun29-call-abi-20261019/classify-v2.json` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/jun29-call-abi-20261019/classify_v2.py` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/jun29-call-abi-20261019/scan-results.json` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/jun29-call-abi-20261019/scan_calls.py` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/jun29-call-abi-20261019/summary.json` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/jun29-call-abi-20261019/wrap_elf.py` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/jun29-slot-hits-20261019/case-slot-hits.json` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/jun29-slot-hits-20261019/runtime-slot-hits.json` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/jun29-slot-hits-20261019/slots.json` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/native-seed-c-free-runner-raw-elf-20261019/harness-output.txt` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/native-seed-c-free-runner-raw-elf-20261019/objdump-code.txt` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/native-seed-c-free-runner-raw-elf-20261019/probe-output.txt` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/native-seed-c-free-runner-raw-elf-20261019/probe_harness.c` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/native-seed-c-free-runner-raw-elf-20261019/raw_elf_runner_probe` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/native-seed-c-free-runner-raw-elf-20261019/raw_elf_runner_probe.py` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/native-seed-c-free-runner-raw-elf-20261019/receipt.json` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/native-selfhost-closure-20261019/README.md` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/native-selfhost-closure-20261019/codegen-scalars/answer.bin` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/native-selfhost-closure-20261019/codegen-scalars/answer.kseed` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/native-selfhost-closure-20261019/codegen-scalars/answer.run2.kseed` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/native-selfhost-closure-20261019/codegen-scalars/bits.bin` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/native-selfhost-closure-20261019/codegen-scalars/bits.kseed` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/native-selfhost-closure-20261019/codegen-scalars/bits.run2.kseed` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/native-selfhost-closure-20261019/codegen-scalars/quot-neg.bin` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/native-selfhost-closure-20261019/codegen-scalars/quot-neg.kseed` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/native-selfhost-closure-20261019/codegen-scalars/quot-neg.run2.kseed` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/native-selfhost-closure-20261019/codegen-scalars/subtract.bin` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/native-selfhost-closure-20261019/codegen-scalars/subtract.kseed` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/native-selfhost-closure-20261019/codegen-scalars/subtract.run2.kseed` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/native-selfhost-closure-20261019/reports/codegen-matrix-report.json` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/native-selfhost-closure-20261019/reports/pinned-graph-report.json` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/native-selfhost-closure-20261019/reports/r19cli-g1-report.json` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/native-selfhost-closure-20261019/reports/selfrebuild-g2-report.json` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/native-selfhost-closure-20261019/reports/selfrebuild-g3-report.json` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/native-selfhost-closure-20261019/scripts/build_native_cli_current_g3_r19cli.py` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/native-selfhost-closure-20261019/scripts/build_native_cli_selfrebuild_r19cli.py` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/native-selfhost-closure-20261019/scripts/build_native_cli_selfrebuild_r19cli_g2.py` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/native-selfhost-closure-20261019/scripts/pin_r19graph_selfrebuild_g2.py` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/native-selfhost-closure-20261019/scripts/probe_codegen_matrix_r19cli_g2.py` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/evidence/native-selfhost-closure-20261019/scripts/verify_native_cli_selfrebuild_r19cli_g2.py` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/native-seed-c-free-runner-admission-receipt-20261019.md` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/native-seed-c-free-runner-call-abi-20261019.md` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/native-seed-c-free-runner-data-slots-20261019.md` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/native-seed-c-free-runner-entry-route-20261020.md` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/native-seed-c-free-runner-expressiveness-20261019.md` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/native-seed-c-free-runner-kernel-profile-slice-20261020.md` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/native-seed-c-free-runner-raw-elf-emitter-20261019.md` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/native-seed-c-free-runner-seed-sequence-20261020.md` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/native-seed-c-free-runner-slot-hits-20261019.md` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/native-seed-c-free-runner-surface.md` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `docs/re-disasm-cleanroom.md` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | M | `docs/selfhost-priority.md` | restored main-side hunks (file unchanged on main since e670387b) |
| a | D | `docs/x86-64-field-descriptions.md` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | M | `package-lock.json` | restored main-side hunks (file unchanged on main since e670387b) |
| a | M | `package.json` | restored main-side hunks (file unchanged on main since e670387b) |
| a | D | `re_disasm/README.md` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `re_disasm/build-native.mjs` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `re_disasm/disasm.kotoba` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `re_disasm/x86disasm.kotoba` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `scripts/gpu-workgroup-sweep/gen-wg-shaders.py` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `scripts/runner-bookkeeping-receipt.cljk` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `scripts/runner-slice-receipt.cljk` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `scripts/seed/check-x86_64-aiueos-object.py` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `scripts/test-gpu-devclass.cljk` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `scripts/test-gpu-subgroup-probe.cljk` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `scripts/test-gpu-workgroup-compute.cljk` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `scripts/test-gpu-workgroup-sweep.cljk` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | M | `seed/72-x86-cross-entry.kotoba` | restored main-side hunks (file unchanged on main since e670387b) |
| a | M | `seed/73-x86-linux-entry.kotoba` | restored main-side hunks (file unchanged on main since e670387b) |
| a | D | `seed/74-x86_64-aiueos-object.kotoba` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | M | `seed/X86_64-LINUX-ABI` | restored main-side hunks (file unchanged on main since e670387b) |
| a | M | `seed/X86_64-LINUX-MANIFEST` | restored main-side hunks (file unchanged on main since e670387b) |
| a | M | `seed/X86_64-LINUX-SELFHOST-MANIFEST` | restored main-side hunks (file unchanged on main since e670387b) |
| a | D | `src/kotoba/compiler/accelerator_pipeline.cljk` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `src/kotoba/compiler/accelerator_subgroup_reduce.cljk` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | M | `src/kotoba/compiler/decimal_text.cljk` | restored main-side hunks (file unchanged on main since e670387b) |
| a | M | `src/kotoba/compiler/manifest_mode.cljk` | restored main-side hunks (file unchanged on main since e670387b) |
| a | M | `src/kotoba/compiler/nbb/wasm_cli.cljk` | restored main-side hunks (file unchanged on main since e670387b) |
| a | M | `src/kotoba/compiler/posix_path.cljk` | restored main-side hunks (file unchanged on main since e670387b) |
| a | M | `src/kotoba/compiler/project_files.cljk` | restored main-side hunks (file unchanged on main since e670387b) |
| a | D | `src/kotoba/compiler/runner_bookkeeping.cljk` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `src/kotoba/compiler/runner_entry.cljk` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `src/kotoba/compiler/runner_seed.cljk` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `src/kotoba/compiler/runner_slice.cljk` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | M | `src/kotoba/compiler/source_path.cljk` | restored main-side hunks (file unchanged on main since e670387b) |
| a | M | `src/kotoba/compiler/target_names.cljk` | restored main-side hunks (file unchanged on main since e670387b) |
| a | M | `src/kotoba/compiler/test_cli.cljk` | restored main-side hunks (file unchanged on main since e670387b) |
| a | M | `src/kotoba/compiler/text_bytes.cljk` | restored main-side hunks (file unchanged on main since e670387b) |
| a | D | `test/fixtures/gpu/gpu-compute-devclass.kotoba` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `test/fixtures/gpu/gpu-workgroup-sweep.kotoba` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `test/kotoba/compiler/accelerator_pipeline_test.cljk` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | M | `test/kotoba/compiler/project_test.cljk` | restored main-side hunks (file unchanged on main since e670387b) |
| a | D | `test/kotoba/compiler/runner_bookkeeping_test.cljk` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `test/kotoba/compiler/runner_entry_test.cljk` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `test/kotoba/compiler/runner_seed_test.cljk` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | D | `test/kotoba/compiler/runner_slice_test.cljk` | restored from e670387b^1 (missing on main, no later commit touches the path) |
| a | M | `test/kotoba/compiler/source_path_test.cljk` | restored main-side hunks (file unchanged on main since e670387b) |
| a | M | `test/nbb/host_abilities.cljk` | restored main-side hunks (file unchanged on main since e670387b) |
| a-3way | M | `.github/workflows/test.yml` | 3-way applied cleanly onto origin/main; changed on main since: f29c6d0a Preserve recovery evidence and clarify filesystem qualification boundary; 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| a-3way | M | `bin/amu` | 3-way; conflict on the guard comment resolved to main (4046aaf2 rewrote it after dropping the guard); gpu-compile, kir and AMU_KOTOBA_NATIVE_SRC restored |
| a-3way | M | `src/kotoba/compiler/cli.cljk` | 3-way applied cleanly onto origin/main; changed on main since: f0fd8449 cli: answer :artifact-target refusals with 65 again on both routes |
| a-3way | M | `src/kotoba/compiler/nbb/cli_support.cljk` | 3-way; conflict on the :artifact-target comment resolved to main (f0fd8449 re-added the same row) |
| a-3way | M | `src/kotoba/compiler/project.cljk` | 3-way; 5 conflicts: kept JUN-188 (3f8605e2) self-call stub-body, direct exports and defn for direct names; restored the module-schemas and same-instantiation work |
| a-3way | M | `src/kotoba/compiler/trust_cli.cljk` | 3-way applied cleanly onto origin/main; changed on main since: fd52545c Merge origin/main into hermes/jun30-land-20261020; 505b796b trust/cli: resolve the #1397 review threads (P2 x5); 917e20f6 Merge JUN-30: serve the x86-64 AIUEOS kernel image on the JDK-free route; 3d7a4c37 Serve the x86-64 AIUEOS kernel image on the JDK-free route (JUN-30) |
| b | M | `deps-lock.edn` | superseded: same pins as deps.edn (ce4cbc59 / ede96447 descend from a36ea2fc / f9ed57e7) |
| b | M | `deps.edn` | superseded: main pins artifact ce4cbc59 and kotoba-native ede96447, descendants of the lost a36ea2fc / f9ed57e7 pins (checked with merge-base --is-ancestor) |
| b | M | `run-tests.cljk` | superseded: the only lost hunk (accelerator-subgroup-reduce-test) is already on main; the 3-way result only duplicated it |
| b | D | `src/kotoba/compiler/decimal_bits.kotoba` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `src/kotoba/compiler/decimal_text.kotoba` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `src/kotoba/compiler/decimal_text_core.kotoba` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `src/kotoba/compiler/form_pipeline.kotoba` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `src/kotoba/compiler/form_transform.kotoba` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `src/kotoba/compiler/frontend_tables.kotoba` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `src/kotoba/compiler/kotoba_reader.kotoba` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `src/kotoba/compiler/native_cli.kotoba` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `src/kotoba/compiler/native_frontend.kotoba` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `src/kotoba/compiler/native_project.kotoba` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `src/kotoba/compiler/native_project_cli.kotoba` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `src/kotoba/compiler/native_project_files.kotoba` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `src/kotoba/compiler/native_project_linker.kotoba` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `src/kotoba/compiler/nbb/host/fs.kotoba` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `src/kotoba/compiler/posix_path.kotoba` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `src/kotoba/compiler/posix_path_core.kotoba` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `src/kotoba/compiler/selfhost_cli.kotoba` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `src/kotoba/compiler/source_path.kotoba` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `src/kotoba/compiler/source_path_core.kotoba` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `src/kotoba/compiler/syntax_sugar.kotoba` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `src/kotoba/compiler/target_names.kotoba` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `src/kotoba/compiler/target_names_core.kotoba` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `src/kotoba/compiler/text_bytes.kotoba` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `src/kotoba/compiler/text_bytes_core.kotoba` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `src/kotoba/compiler/validate_expr.kotoba` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `src/kotoba/compiler/value_type.kotoba` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `src/kotoba/form.kotoba` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `test/fixtures/selfhost/native-reader/README.md` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `test/fixtures/selfhost/native-reader/private-constant.cljk` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `test/fixtures/selfhost/native-reader/private-constant.kotoba` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `test/fixtures/selfhost/syntax-sugar/README.md` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `test/fixtures/selfhost/syntax-sugar/as-thread.cljk` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `test/fixtures/selfhost/syntax-sugar/as-thread.kotoba` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `test/fixtures/selfhost/syntax-sugar/cond-thread-first-collision.cljk` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `test/fixtures/selfhost/syntax-sugar/cond-thread-first-collision.kotoba` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `test/fixtures/selfhost/syntax-sugar/cond-thread-first.cljk` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `test/fixtures/selfhost/syntax-sugar/cond-thread-first.kotoba` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `test/fixtures/selfhost/syntax-sugar/cond-thread-last.cljk` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `test/fixtures/selfhost/syntax-sugar/cond-thread-last.kotoba` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `test/fixtures/selfhost/syntax-sugar/project-import/smoke/main.cljk` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `test/fixtures/selfhost/syntax-sugar/project-import/smoke/main.kotoba` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `test/fixtures/selfhost/syntax-sugar/project-import/smoke/ops.kotoba` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `test/fixtures/selfhost/syntax-sugar/quoted-reserved-data.cljk` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `test/fixtures/selfhost/syntax-sugar/quoted-symbol-defn.cljk` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `test/fixtures/selfhost/syntax-sugar/quoted-symbol-defn.kotoba` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `test/fixtures/selfhost/syntax-sugar/reserved-source.cljk` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `test/fixtures/selfhost/syntax-sugar/some-thread-last.cljk` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `test/fixtures/selfhost/syntax-sugar/some-thread-last.kotoba` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `test/fixtures/selfhost/syntax-sugar/some-thread.cljk` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `test/fixtures/selfhost/syntax-sugar/some-thread.kotoba` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `test/fixtures/selfhost/syntax-sugar/thread-first.cljk` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `test/fixtures/selfhost/syntax-sugar/thread-first.kotoba` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `test/fixtures/selfhost/syntax-sugar/thread-last.cljk` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `test/fixtures/selfhost/syntax-sugar/thread-last.kotoba` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `test/fixtures/selfhost/syntax-sugar/unsupported-empty-some-thread.cljk` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| b | D | `test/fixtures/selfhost/target_names.kotoba` | already restored: 43f881b7 Restore reviewed native compiler sources removed by a later merge |
| c | M | `docs/adr/0355-gpu-vendor-target-dispatch.md` | #1339 own change: correct 3-way merge (base bea7b9b2) gives the merged version |
| c | M | `scripts/test-gpu-compute.cljk` | #1339 own change: correct 3-way merge (base bea7b9b2) gives the merged version |
| c | M | `test/fixtures/gpu/gpu-compute-info.kotoba` | #1339 own change: correct 3-way merge (base bea7b9b2) gives the merged version |
| exception | M | `fuzz/baselines/native-parser.edn` | #1365 loader-identity group (named brk/udf value traps); NOT restored: needs a kotoba-lang/artifact runtime-identity re-pin; the lost #1365 loader also wrote a debug /tmp/checked_vector_at.log |
| exception | M | `scripts/gen-loader-decisions.cljk` | #1365 loader-identity group (named brk/udf value traps); NOT restored: needs a kotoba-lang/artifact runtime-identity re-pin; the lost #1365 loader also wrote a debug /tmp/checked_vector_at.log |
| exception | M | `tools/kexe_loader.c` | #1365 loader-identity group (named brk/udf value traps); NOT restored: needs a kotoba-lang/artifact runtime-identity re-pin; the lost #1365 loader also wrote a debug /tmp/checked_vector_at.log |
| exception | M | `tools/kexe_loader.classification.edn` | #1365 loader-identity group (named brk/udf value traps); NOT restored: needs a kotoba-lang/artifact runtime-identity re-pin; the lost #1365 loader also wrote a debug /tmp/checked_vector_at.log |
| exception | M | `tools/kexe_loader_names.kotoba` | #1365 loader-identity group (named brk/udf value traps); NOT restored: needs a kotoba-lang/artifact runtime-identity re-pin; the lost #1365 loader also wrote a debug /tmp/checked_vector_at.log |
