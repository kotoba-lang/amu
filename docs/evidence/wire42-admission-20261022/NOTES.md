# Wire 42 :gpu/compute admission round (ADR 0371 step 3), 2026-10-22

Status: measured and passing. **Not merged** until the security-integration sign-off
(`seed/security-integration-20261022.json`, `signOff.status` = pending).

Host: arm64 Linux, podman machine (applehv) on macOS arm64. x86_64 rows ran
under qemu-user binfmt with `KEXE_SECCOMP=if-available`. No C compiler or loader.

## The round
1. **Sources.** seed/HEADS, 00-ns, 20-names, 21-check, 30-lower, 60-proj and
   90-drv admit wire 42 as `:string :string`.
   - The generated parts were checked against the historical generators,
     replayed in memory (`gen-ns.sh` at `15626731^`, `gen-names-tables.py` at
     `bb0deb70`).
   - 00-ns equals the extraction except for the existing hand-added `FX-FADDR`.
   - The 20-names block is byte-identical to the generator's output with
     `:gpu/compute` appended.
2. **Adopted fixed point.** `adoption-candidate.json`
   (`scripts/seed/adoption-candidate.py`): the pinned bootstrap `6b158aa8`
   built G1 through the C-free aarch64 runner, and G1 = G2 = G3 = `9deed950`.
   That became `seed/adoption-20261022.json`. The previous image was `b10e3813`.
3. **Static root.** Re-pinned C-free from `cb0a7d02` to `f19ab1c4`.
   `../selfhost-bootstrap-aarch64-20261022/selfhost-bootstrap.json` shows:
   - S1 = S2 = S3 = root;
   - adopted G1 = G2 = G3 against the new receipt;
   - all 24 cases;
   - step 6 (wire 3 and scope roots);
   - hardening.

## Qualification (files in this directory)
| check | result |
| --- | --- |
| `wire42-admission.json` | three spellings × two closures compile, and each spelling gives the same image. Guests run against the scripted provider. Before the round, all three are refused. `:bytes` shapes, `http/post` and wire 43 stay refused. `--policy` gives E2170 (adopted) and E7100 (static). |
| `preserved-integration-main.json` | `--main`: the new G reproduces **all 19 workload images exactly**; 34 policy refusals; smoke 42 |
| `preserved-integration-preserved.json` | frozen 2026-10-12 closure: fixed point, 19 images exact |
| `certified-scalar-calls.json` | 54 OFF/ON pairs exact, with ON = the new G3 |
| `a64gen-controls/*` | all nine adopted-a64gen paired controls pass with the new G3 |
| `gpu-runtime-transport-*-linux.json` | aarch64: 10 + 8, including the SIGSYS control. x86_64: 10 + 7. Both now use the product compiler; the test-only admission patch is gone. |
| `gpu-compute-protocol-*-linux.json` | 107 cases, control 1, on the new root |
| `x86_64-scalar.json` | 55 programs, 14 refusals |
| `aiueos-kernel-object.json` | 8 objects, 30 refusals |

These receipts supersede, for this round, the per-topic receipts in the other
evidence directories, which pin the previous adopted image `b10e3813` or root
`cb0a7d02`. Those stay as historical records.

## Known defect (not caused by this round)
JUN-309. Under the C-free runner, the adopted compiler fails closed with
`KEXE_TRAP {:kind :signal :signal :SIGILL}` (exit 120, no output) for any
unadmitted capability, where the C loader used to print E2115. This holds
before and after the round. `check-wire42-admission.py` pins exactly that
line. The static compiler names E2115.

## Not covered
- **No GPU work ran.** The provider and launcher (ADR 0371 steps 4–6) do not
  exist yet.
- **The 20 functional sources and the 483 original paired cases** cannot be
  rebuilt from main C-free.
  - Codegen identity is shown instead by the 19 workload images, the nine
    controls and certified-54.
  - No source file of the code generator (40/41/42/50) changed.
