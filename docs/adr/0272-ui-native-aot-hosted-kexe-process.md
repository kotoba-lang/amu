# ADR 0272: ui-v1 native-aot is a hosted kexe process proof

Status: accepted

## Decision

`ui-v1` `:native-aot` is `:implemented` because a real kexe process ran
typed-cap-call 9 and 10 and returned a packed i64. That is the dataspace
qualification, not clock's host-authority block, and not ADR 0270's
"every remaining application kit stays pending".

Dataspace was already the exception to ADR 0270. UI joins that exception.
Clock stays pending (`:native-aot-blocked-by`). log/http/llm/state/storage
stay pending on their own schemas or missing injects. This ADR does not
implement log-v1.

The hosted inject is in-process: CAS on `base_rev == ui_revision`, result
`pair(new_rev, pair(count, 0))`, one auto-enqueued `:ui/committed` event
from the first node, event none = `pair(0,0)`, some = `pair(1, event)`.
No new syscalls. Production C-free aiueos is still not claimed. Backend-wide
native stays `:pending` on `backend-provider-qualification-v2.edn`.

Two GMIR kinds, not one: `:ui-commit-v1 = 6` and `:ui-event-v1 = 7`.
`checked_typed_cap_call` requires `request_kind == result_kind`, and the
commit record pair is not the event `[:option record]` pair.

Native `:set` of a UI node record lowers to the existing vector host table
(type descriptor skipped). `[:option record]` already lowers to a pair;
admission now allows option-of-record. The node set is not encoded as
`:document`.

## Evidence

`ui-native-aot-test` must:

1. Compile the kit-shaped guest on the host native ISA
2. Execute through the real loader (`executor/execute`)
3. Return `:ok` and packed result 15 (pending-none, rev==1, count==1,
   event-rev==1)
4. Flip `ui-v1.edn` `:native-aot` only in the same commit as that proof
5. Appear in `wasm32-kotoba-v1-qualification-test/native-aot-kits`

Identity echo of the commit request cannot satisfy revision 1: the guest
would walk a node-set handle as a commit-result and trap.

## What this does NOT claim

- C-free aiueos typed-provider syscall
- Backend-wide native `:qualified`
- Clock, log, http, llm, or storage native-aot
- JIT of kit-typed guests
- Closing `:typed-provider-syscall-abi` or
  `:c-free-aiueos-cpl3-syscall-substrate`
