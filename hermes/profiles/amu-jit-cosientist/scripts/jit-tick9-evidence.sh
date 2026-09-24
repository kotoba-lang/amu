#!/bin/bash
# amu-jit tick 9 (2026-09-05): append evidence to J-B row via targeted replace
set -e
P=~/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/jit-cosientist.md
python3 - "$P" <<'PYEOF'
import sys
p = sys.argv[1]
s = open(p).read()
anchor = "(4000000 iters × 24 alternations, ratio of medians), then J-C."
add = " (2026-09-05 09:55 JST tick 9 JIT: quiet gate failed again — load1 19.2 at 09:42, 22.5 at 09:52, top idle 39–44% but no idle CPU, java ~186% CPU; measurement deferred. Source-inspection result, no quiet host needed: J-B premise re-verified on origin tree — bench/runtime-comparison/kernel_collections.kotoba defines imod as a user function with the divisor a runtime parameter, so constant-divisor specialization requires inlining+constant-fold (AOT) or runtime callee specialization (JIT). ADR 0289 ranks inlining small user functions ABOVE constant-divisor strength reduction; the J-B hand-patch arm (const divisor, inlined by the C compiler) therefore measures levers 1+2 combined and the lever-2-only saving may be smaller than the +6.2–7.8% diagnostic runs suggest. No compiler change. Next: on quiet host add a third arm (non-inlined mulh shape) to separate lever 1 from lever 2.)"
assert s.count(anchor) == 1, "anchor count: %d" % s.count(anchor)
open(p, 'w').write(s.replace(anchor, anchor + add))
print("OK")
PYEOF
