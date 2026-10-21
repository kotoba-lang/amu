# GPU subgroup-reduce EXEC probe — shader provenance (and what the logs are)

## The shader bytes and where they came from

The embedded GLSL literals in `scripts/test-gpu-subgroup-reduce-exec.cljk`
are the EXACT output of `kotoba.compiler.accelerator-subgroup-reduce/emit-glsl`
as of PR #1341's commit `53248c11`, for the six (W, operator) shapes in the
matrix (`64/256 x :sum/:max/:min`), produced by invoking that emitter. Each
literal carries its recorded sha256, and the probe recomputes every hash at
run time and refuses before the first dispatch if any literal was transcribed
wrong — the check protects transcription, not provenance, which is what this
file pins.

- Emitter source: `src/kotoba/compiler/accelerator_subgroup_reduce.cljk`
  (`emit-glsl`).
- At generation time (`53248c11`) the emitter rode only in PR #1341 and was
  not on `origin/main`. It has since MERGED to main (the PR landed as
  `7e0214d8`) and has been FIXED there (`4b7a1ccb`: extension list, builtin,
  cross-subgroup fold, identities). The emitter file on main at this README's
  commit has sha256
  `ce3d52dd6c30d1baf97458e7011456f920ced0f707d082fd8f97185a661aed6f`.
- Therefore the embedded bytes are the PRE-FIX emission of `53248c11`, and
  they intentionally differ from what the current emitter produces. This
  probe executes the RECORDED bytes to characterize that emission; it is not
  a test of the current emitter output (which the emitter's own tests pin by
  text, and which no harness here re-generates).

## Rung patches

The two rung patches (`as-emitted` → `categories` → `categories+id`) are the
minimal mechanical edits this host's glslang (MoltenVK path) demands,
applied in memory and recorded by name in every log line. They do not
rewrite the emission's logic.

## The logs

`run-1.log` … `run-3.log` are three fresh-process runs on the one host this
bot can measure (Apple M1 Max, MoltenVK, wire 42 via
`tools/kexe_gpu_vulkan.c`). Each `CASE` line records the rung, shape, n, the
read-back parts value and bits, and the parsed device `INFO` — the log's
device attribution is the harness's own parsed INFO, not a claim about the
machine by outside knowledge. A `CANNOT-EXECUTE` line means the shape
compiled but the case could not be executed; a `NOT-ADMITTED` line means
this host's glslang refused the shape before any dispatch. Both are recorded
by name and verbatim; neither is dressed up as a verified result.
