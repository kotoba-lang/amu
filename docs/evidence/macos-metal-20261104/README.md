# Metal from Amu selfhost (JUN-819, ADR 0405), 2026-11-04

Author-run, diagnostic. MacBook Pro M1 Max, 32 GB, macOS 26.4, on a shared host (load average 19 to 24). Not a quiet-host
measurement and not a published benchmark.

`scripts/seed/check-macos-metal.py --output <dir>`: `PASS_MACOS_METAL_KERNEL`. Machine report: [`report.json`](report.json).

## Checks

| Check | Result |
| --- | --- |
| Metal = Kotoba CPU twin = C twin, 4,864 x 896, 3 reps | `167148804883970`, all equal |
| Mutant: `sumi -=` in the kernel | `127422356340536`, differs |
| A kernel Metal cannot compile | prints `program_source:14:40: error: ...`, traps, no stdout |
| The same program in the default profile | traps at wire 42, no stdout |
| Dylibs | Metal image: libSystem only; default image: none |

Run by hand on the same day:

- Metal = C twin at 77,824 x 896, 16 reps: `166280673969053`.
- Packaging one program with the previous and the new packager gives identical bytes in `amu-program`, `amu-program-fs35`
  and `fs2-cli-stdio-general`.

## Speed

Fastest of the dispatches, from `commit` to `waitUntilCompleted`, one command buffer each:

| Rows x 896 | MACs | Reps | Best |
| ---: | ---: | ---: | ---: |
| 32 | 28,672 | 64 | 275 us |
| 4,864 | 4.36 M | 64 | 308 us |
| 19,456 | 17.4 M | 32 | 544 us |
| 77,824 | 69.7 M | 16 | 1,618 us |

- About 275 us is the floor of one command buffer. From 4,864 to 77,824 rows the slope is about 50 G MACs/s.
- CPU time per 4,864 x 896 product in the gate's run: Kotoba scalar 2.42 ms, C `-O2` 1.40 ms.
- The kernel is the plain loop, with no packed or SIMD forms, so 50 G MACs/s is not this GPU's limit.

## What this does not show

No model ran. A decode step's cost depends on how many kernels share a command buffer, which is not measured here. So this is
no claim against the engines in the murakumo benchmark tables, whose Metal numbers are whole decode steps.
