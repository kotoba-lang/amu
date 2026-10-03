#!/bin/zsh
# seed/tests/r6b/gate-r6b.sh [--extra] -- the extra gate of rung R6B (agent R6B, 2026-10-03: the R6 source-route features).
# BOOTSTRAP-TOOL (zsh). gates.sh --rung r6b runs it as its XTRA row; BUILD ERR G1 G2 G3 G4 G5 GR (every earlier rung's tests)
# and, with --with-aux --with-unit, UNIT KIR LEXREAD LW A64GEN are gates.sh's own rows. Rows here:
#   R6B    seed/tests/r6b/check-r6b.sh with seed-1: :document in the source route, hex literals, str / ex-info / min / max /
#          string-find-byte / rem / string-to-utf8 / string-parse-i64 / parse-long, comparison chains, record-assoc, friendly
#          capability names of the catalogue, :symbol, keyword defs, opaque constant defs, docstrings / nil / clojure.core/
#          on the single-module route; every positive also through the project route (byte-identical image)
#   SRCLIB seed/tests/r6b/srclib/gen-srclib.py --check: 21-check's embedded library == r6b-lib.kotoba + the KIR doclib, and the
#          capability table == resources/kotoba/lang/capability-catalog.edn (== kotoba-lang's when that worktree exists)
#   R6A-X  seed/tests/r6a/gate-r6a.sh --extra: R6A's cases, R5B's extra cases and R5A's namespace-split rung proof
# Exit 0 iff every row passes.
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/../../../scripts/seed/lib.sh"
R=$SEED_REPO; B=${SEED_BUILD:A}; D=$R/seed/tests/r6b
fails=0
row() { printf "%-6s %s\n" $1 "$2"; [ $1 = FAIL ] && fails=$((fails+1)); return 0; }
SEED_BUILD=$B zsh $D/check-r6b.sh $B/seed-1.bin > $B/gate-r6b-check.log 2>&1 && row PASS "R6B $(tail -1 $B/gate-r6b-check.log)" \
  || row FAIL "R6B $(grep -E '^FAIL' $B/gate-r6b-check.log | head -4 | tr '\n' ' ')"
python3 $D/srclib/gen-srclib.py --check > $B/gate-r6b-srclib.log 2>&1 && row PASS "SRCLIB $(tail -1 $B/gate-r6b-srclib.log)" \
  || row FAIL "SRCLIB $(tail -1 $B/gate-r6b-srclib.log)"
SEED_BUILD=$B zsh $R/seed/tests/r6a/gate-r6a.sh --extra > $B/gate-r6b-r6a.log 2>&1 && row PASS "R6A-X $(tail -1 $B/gate-r6b-r6a.log)" \
  || row FAIL "R6A-X $(grep -E '^FAIL' $B/gate-r6b-r6a.log | head -3 | tr '\n' ' ')"
echo "gate-r6b: $([ $fails -eq 0 ] && echo READY || echo "NOT READY ($fails failed)") (load $(uptime | sed 's/.*averages: //'))"
[ $fails -eq 0 ]
