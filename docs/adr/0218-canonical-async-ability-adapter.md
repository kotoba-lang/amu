# ADR 0218: Canonical async ability adapter

Status: accepted

## Context

The synchronous ability adapter keeps physical canonical-value bytes out of
Kotoba source, but it cannot truthfully return an affine task by encoding a
handle. A task is local authority, not a value. Earlier pending tasks also
required callers to replace their handle with a returned ready snapshot, so a
provider callback could not make completion observable to guest polling.

Kotoba-kir#46 makes the linear resource table authoritative for same-ID task
state. That permits a real callback contract without serializing a task or
inventing a fallback handle.

## Decision

`async-ability-provider` accepts exact request and response descriptors, a
bounded canonical-value limit, and `start-wire`. The start function receives
canonical request bytes plus a one-shot completion callback and must return one
exact status:

- `{:status :pending}` leaves the returned task pending for later completion.
- `{:status :completed}` is accepted only when the callback already made the
  task ready.

Completion bytes are bounded, decoded under the response descriptor, and
canonically re-encoded before they become the payload of a local bytes stream.
The provider exposes `[:task [:stream :bytes]]`; neither task nor stream handle
appears on the value wire. Invalid status, status/state mismatch, malformed or
oversized completion, duplicate completion, cancellation, and use-after-drop
fail closed.

## Consequences

- Actor, I/O, and provider adapters can share one org-owned asynchronous
  boundary instead of defining host-language promise conventions.
- Source continues to name a typed semantic ability; generated/provider code
  alone sees canonical bytes and completion callbacks.
- WIT resource lowering may use its native task/stream representation while
  preserving the same descriptor and ownership authority.
