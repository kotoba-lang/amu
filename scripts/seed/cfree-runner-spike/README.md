# Historical seed runner spike (JUN-29, 2026-10-20)

This directory retains the Kotoba interpreter entry and the measurements
from [Amu #1411](https://github.com/kotoba-lang/amu/pull/1411). It is not an
accepted native compiler, launcher, packaging route or CDCI gate.

The 2026-10-22 owner contract requires canonical Kotoba and an Amu
selfhost-built native closure. The former JVM "final-means" exception and
C-loader bootstrap recipe are retired. The unused Python builder has been
removed; its source and build-time inputs remain in that PR's Git history.
No replacement build or execution is implied by this cleanup.

## Recorded measurements, not current qualification

1. The entry required `kotoba.runtime.native-interpreter`. The old build
   resolved and compiled 20 modules: form, form-transform, syntax-sugar,
   decimal-bits, kotoba-reader, form-pipeline, evaluator-collections,
   evaluator-strings, value-semantics, evaluator-builtins, evaluator, policy,
   reader-depth, embedded-native, raw-memory, bytes, wasm-bytes, runtime,
   native-interpreter and the entry. The driver invoked a G1 builder image
   through a C loader for module enumeration, compilation, link and extract.

   The recorded container was 442,535 bytes, SHA-256
   `7f525dfdae89ba1777c6804edca0e826054dbdd480b2da5eca9023a7f5aefb51`,
   with `mainOffset` 434,032 and a 442,504-byte extracted image. The report
   recorded the same container digest from the worktree and landed inputs.

2. The extracted image was raw data. `file` reported `data` and direct
   execution returned `Exec format error`. It still needed a mechanism to
   establish its memory/context ABI and enter the recorded offset. The old
   entry comment claiming that it ran directly from the OS was incorrect.

3. A separate CLJK/JVM-hosted interpreter evaluation reported
   `:run-ok true`, `:run-value 42`, `:run-problems nil` for the addition
   fixture. Its proof script was not included in that PR. This result used
   a JVM and is not native, selfhost, loaderless or CDCI evidence.

The build also exposed E2104 in the base64 functions of `kotoba.bytes`.
Bytes PR #1 annotated five functions on its Kotoba reading; its historical
host suite reported 21 tests / 140 assertions / zero failures. Those
measurements remain provenance, not qualification of the current closure.

## Remaining product work

[JUN-200](https://linear.app/kotobalabs/issue/JUN-200) and
[JUN-202](https://linear.app/kotobalabs/issue/JUN-202) track native bootstrap,
packaging, input resolution and compiler self-reconstruction. Do not use a
raw image, host interpreter, pinned C loader or renamed wrapper as their
replacement. [JUN-29](https://linear.app/kotobalabs/issue/JUN-29) retains the
separate KX64V1/AIUEOS runner scope and its capability/ABI requirements; it
does not substitute for native CDCI.

CDCI requires the controller and gates themselves to be Amu-selfhost-produced
loaderless `x86_64-linux-static` ELF artifacts. Record compiler generations,
source/lock pins, artifact digests, real execution and named refusals through
that complete closure. None of those receipts is supplied by this spike.
