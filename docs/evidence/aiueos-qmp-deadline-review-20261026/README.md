# QMP stdio deadline review

The previous observer at `504d9a98fc60c45a46452b17256aedcd13835993`
waited for pipe readability, then called blocking `readline()`. A child that
wrote one byte without a newline remained blocked past the declared 30-second
reply timeout; the independent reproducer was stopped after 32 seconds.

The updated observer uses one monotonic deadline for all chunks of a reply
and preserves any following complete lines. Five pipe regression controls
cover partial/no replies, split CRLF, two buffered lines and partial EOF.
They run in native CI preflight without starting an emulated guest.

The updated observer also ran the previously native-produced positive and
negative AIUEOS EFI/kernel pairs in QEMU 10.0.3 TCG. The positive guest passed
all 17 header/request checks. The valid non-LLM negative guest failed at the
header receipt assertion and produced no successful receipt. Exact observer,
EFI and kernel hashes are in `observations.json`. The fixtures are the
unchanged artifacts of AIUEOS draft #526's `llm-header-qemu` gate; no guest
was recompiled for this observer regression run. This is emulated guest
execution and observer validation, not native x86 process qualification,
model execution, wire-11 provider dispatch or trusted human consent.

The production compiler/root pins are unchanged by the review repair.
Exact-head Mac and native Linux CI remain separate merge gates.

## Current 21-check integration

The subsequent `b60907aa43e08531e69d571e970e6cd7db02c2c2` update is
preserved. The repaired observer reran the updated native-produced UTF-8
fixture: all 12 header and 9 request/component checks passed. The non-LLM
negative guest still failed at the receipt assertion. Current observer and
fixture pins, compiler lineage and firmware are in
`observations-current.json`; the earlier 17-check record remains historical.
UTF-8 component checks do not qualify region aliasing, production host model
policy, provider dispatch, model semantics or trusted human consent.
