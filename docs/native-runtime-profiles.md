# Explicit native Linux runtime profiles

Implementation candidate, KOTOBA-144. Owner approved the opt-in capacity
change on2026-10-26. Root, public product, privileged-role pins and terminal
native ARM/x86 qualification are not promoted by this document or by a
candidate fixed point. Existing historical benchmark records stay unchanged.

Use the same complete native Amu compiler, frontend and emitters:

    amu compile guest.kotoba --target x86_64-linux --output new.elf --format static --runtime-profile large-vectors-v1

The profile option is last, after the existing format arguments (and after
the payload for ARM packed builds). Omission selects standard-v1. Explicit
standard-v1 and omission must produce identical artifact bytes. Linux x86
static/kx64-runner/launcher and ARM static/runner/launcher/packed build
runtime artifacts. KX64 payloads do not select a runtime; the separately
built runner owns that immutable choice. Locked project compilation and
other targets must reject a runtime-profile flag, not silently ignore it.

| Profile | Vector descriptors | Private growth rows |
| --- | ---: | ---: |
| standard-v1 (default) |4,194,304|4,194,304|
| large-vectors-v1 (explicit)|67,108,864|4,194,304|

Items, pairs, string bytes, individual vector length, fuel, scope rollback,
absolute highwater, capabilities and named refusal behavior retain their
existing bounds. The per-descriptor region map grows with descriptors; the
separate growth-row table does not. Exhausting optional growth rows retains
the existing exact-copy fallback. No guest, environment variable, workload
name or failed execution may select or change the built profile.

The successful compiler record includes runtime-profile and
vector-descriptors. Preserve that raw record, exact build argv, source and
compiler pins, profile, image size/hash and actual host memory usage in an
artifact descriptor. A record alone does not authenticate arbitrary image
bytes. A later benchmark manifest must pin the actual runtime image and
profile; default and explicit-profile results are different observations.

## Required observations

The shared native gate plan adds check-native-runtime-profile.py on both
ISAs, without removing any prior gate. It stages sources and observes native
processes; it is not the native controller or a replacement performance
verdict. Controls include actual4,194,304 and67,108,864 descriptor boundaries,
one-past named refusals, exact-copy fallback at the unchanged growth-row
limit, malformed/duplicate/unknown options, existing24 runtime cases and
native zero/rollback oracles. Built/executed mutants cover wrong selection,
vector off-by-one, widened region bounds and missing/relative/last-word
highwater clearing. Compilation failures cannot count as mutant detection.

Complete candidate derivation, both ISA executions, the previous uncached
main/full tiers, controller/public checks and all six CI job executions
remain required before adoption. Full19 original Embench counts, independent
fuel/arena references and preregistered timing controls remain separate.
