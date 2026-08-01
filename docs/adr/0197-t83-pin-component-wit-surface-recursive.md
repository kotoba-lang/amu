# ADR 0197: T8.3 pin kotoba-component ADR 0119 (WIT surface-only recursive reject)

- Status: Accepted
- Date: 2026-08-01
- Depends: kotoba-component ADR 0119 (`aeae037e`)

## Decision

1. Pin `kotoba-component` to `aeae037e` (ADR 0119).
2. WIT recursive-schema reject applies only to export/capability surface.
3. Guest-internal recursive ADTs (provider W4 record-kv) no longer fail at
   WIT emit when kit exports are scalar.

Honesty: Component **core** Canonical lowering still has no recursive ADT
body path (`component function body has no qualified Canonical lowering`).
W4 Component twins remain blocked on that residual; wasm32 typed packages
are the production W4 surface today.

## Related

- T8.3; component 0119; provider 0250–0255
