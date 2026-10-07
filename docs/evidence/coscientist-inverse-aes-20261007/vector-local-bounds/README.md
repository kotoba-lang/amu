# Local bounds emitter checkpoint

Capture of experiment inputs, outputs and reviews; not a portable native replay recipe. The recorded drivers contain original absolute paths. Do not execute archived drivers as a new experiment without a new root authorization and input qualification.

The archive seals 315 ordinary files, 16,842,007 expanded bytes. Archive SHA-256: `f0c789fc33dd924d053018df1c85d21eb8df3c0b9742a4bb738c65d14d713019`, 4,091,083 bytes. `manifest.json` lists every member's exact size/hash. `read-capture.py` checks bounded member identities without extracting or running native code.

This continuation ran 54 native loader calls: 10 single-fixture compile/extract/functional, 38 original19 compile/extract, and 6 three-generation compiler builds. The earlier two-call candidate build is also captured. All calls closed. One actual bounds-check trio was removed in the isolated fixture; handle checks retained. All19 original containers/native outputs stayed byte-identical to V8. Three candidate generations stayed byte-identical to c75d41. No timing/C superiority/official score/product adoption/shared CID cache claim.

The initial fixedpoint driver mismatch failure and raw v2 HOLD are retained. Final raw audit v3 binds exact recovered executed driver `7cc611…` to contemporaneous root GO. Later `ed592…` adds guards and was not executed. Later source-only review applies to that later version, not retroactively to the executed version.

The context design v1 incorrectly attributed all11 nettle parameter sites to FN19. Independent raw review preserved this assertion failure; v2 correction gives FN19 eight sites and retains the original v1. These sites remain prospective, not emitted or performance-qualified.

For the human-readable result, see [report](../../../coscientist-vector-local-bounds-20261007.md). The compiler/source/loader payloads are included for inspection, not permission to rerun.

One-off experiment capture and documentation; no product source/entrypoint changes or AST mechanical refactor.
