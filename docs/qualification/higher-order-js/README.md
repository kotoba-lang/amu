# Higher-order guest closures through normal Amu

The previous published Sema pin refused callable results returning another
callable. This advance uses published Sema PR100 and language authority PR719,
regenerates the dependency lock, and updates grammar prose/history together.
The existing record/list-field pin advance remains included.

The maintained portable Node suite passes 80 tests / 568 assertions. New cases
cover nested callable results and a lexical callable parameter shadowing a global
function on both JS targets, plus refusal before lowering on six non-JS targets.

Normal `bin/amu compile --target js|js-browser --jvm-free` compiles the actual
Mithril-lowered eight-export fixture. On frozen offline Node v24.21.0, each
artifact preserves 112 opaque identities, performs zero Proxy reads, supports
2,000 fresh instances, and retains fuel/allocation traps (1,024 higher-order
calls before allocation exhaustion). JS and JS-browser output bytes match.
CLI cljs, wasm32-browser and x86_64 attempts exit 65 without artifacts or JVM
markers. The lock was generated at authoring time; compilation shadowed JVM
launchers and wrote no marker.

This is a Node bootstrap compiler qualification. It is not native selfhost,
actual browser execution, escaping host callbacks, unbounded per-instance calls,
full package migration or complete harness API/plugin parity. System One had no
model attempt for this change. PR1250 passed all ten required checks and was merged as a0604488.
The tested and published source trees match. That publication is separate from
these local receipts; no additional runtime coverage is implied.
