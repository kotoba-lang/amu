# ADR 0378: AIUEOS user LLM calls require the canonical typed host boundary

Status: proposed for JUN-444; implementation and qualification pending

## Observed boundary

The selfhost `x86_64-aiueos-user-v3` target emits a fixed 8,280-byte ELF
with one 4 KiB writable page. Its extra primitive, `kernel-local-model-call`,
packs a 104-byte version-2 request and reaches AIUEOS syscall 5. The paired
AIUEOS image consumes a fresh local Y/N choice and returns one character
bigram token. The headless QMP gate exercises denial, approval, cold Goal
restore, the CPL3 call, and a changed-ELF refusal. These are real guest
observations, but the QMP key is synthetic and the operation is a fixed local
token function. Neither is a `llm/generate` kit execution or human consent.

`resources/kotoba/lang/capability-kits/llm-v1.edn` defines wire 11 with a
five-field request and nested completion/error result. It admits up to
65,536 bytes each for system, prompt, and output text. `seed/21-check.kotoba`
names wire 11 in the catalogue but does not admit it in the current friendly
capability call or the seed's scalar `typed-cap-call` shape. The user target
also refuses nonzero `MM-CAPS`. A direct declared-capability source was
measured to fail before ELF emission. Changing a kit qualification flag or
renaming the 104-byte primitive would not connect these paths.

## Decision

Implement `llm/generate` as the existing kit's typed capability, with an
AIUEOS user target and a versioned, bounded C-free host transport. Keep the
current `kernel-local-model-call` profile separate as a diagnostic until the
kit path replaces it. The compiler must emit an explicit wire-11 requirement
in signed artifact metadata. AIUEOS must admit the sealed artifact and a
host-owned, exact model allowlist before any request is accepted. No string,
integer, source comment, or guest-written envelope may grant that authority.

The 4 KiB user page cannot carry the kit's maximum request and result.
Introduce checked, process-owned request and result regions sized for the
kit's actual bounds, or a bounded chunk transport that proves equivalent
whole-value reconstruction. Preserve v1/v2/v3 target bytes and refusals;
use a new target/ABI version for the expanded mapping. Encode the five
request fields and both result arms with a canonical version, lengths, type
tags, and nested usage values. Reject overflow, unknown fields/tags,
noncanonical encodings, invalid UTF-8, out-of-range token/temperature values,
and region aliasing before provider dispatch.

The kernel owns a one-use request ticket bound to the process, capability
generation, model, request digest, and the displayed approval. Denial emits
no provider request. Consumption precedes validation/dispatch so malformed
or replayed calls cannot reuse an approval. A synchronous kit call may park
the user task while an authorized provider executes; it must not hold a
kernel dispatcher or capability lock during model work. The provider keeps
model selection, weights, and any credentials on the host side. Its result
is copied back only through the checked result region and is decoded as the
kit's nested `:ok` or `:error` value. The host records model identity,
request/result digests, completion reason, and usage without logging prompt
or system text.

Test automation may inject a choice only to prove the guest path. A
production grant requires a trusted direct user choice tied to the displayed
operation, endpoint/provider, model, and data categories. Restored Goal text
is not restored approval. A local model operation and a remote inference
operation need separate declarations and fresh choices.

## Qualification order

1. Extend the adopted selfhost seed frontend and target with explicit wire-11
   metadata and canonical nested value lowering. Keep unsupported shapes and
   undeclared capabilities refused, with no output ELF. Rebuild the same
   compiler lineage through native ARM and x86 fixed points.
2. Add AIUEOS host admission and a bounded request/result codec. Exercise
   positive nested completion and error values, then malformed lengths,
   aliases, mismatched model, missing grant, revoked generation, budget
   exhaustion, and replay. No provider call may occur in a refusal case.
3. Run a real local model on the selected AIUEOS QEMU reference path and
   compare a source-bound user result and usage receipt across the CPL3
   boundary. An injected echo or the current bigram token can test transport
   only; it does not qualify model semantics.
4. Connect Itonami Goal to the trusted approval path, `llm/generate`, and a
   bounded tool/agent turn, then cold-restore the resulting workspace state.
   QMP automation verifies mechanics; human UI approval remains a separate
   release observation.

`llm-v1` remains `:native-aot :pending` and the AIUEOS/ChromeOS release
score remains unqualified until the corresponding gates actually pass. This
ADR does not make the historical JVM provider or C loader a fallback.
