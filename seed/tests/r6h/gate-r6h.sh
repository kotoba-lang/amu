#!/bin/zsh
# seed/tests/r6h/gate-r6h.sh [--extra] -- the extra gate of rung R6H (agent LINK, 2026-10-04: link capacity; 60-proj packed
# image, 50-out header-only OUT, streamed container/slice writes). BOOTSTRAP-TOOL (zsh). Rows:
#   CAP     scripts/seed/link-capacity.sh with seed-1 (DIFF: recorded selfbuild images linked and extracted byte-identically at the
#           default profile and budget; SCALE: 3 renamed copies of the selfbuild objects + a probe requiring every module, equal to
#           the independent linker scripts/seed/link_oracle.py, packaged and run = 0; MAX: the largest link, then E6020 by name).
#           Needs the selfbuild objects (build/selfbuild-run/r6/o, scripts/seed/selfbuild.sh); without them the row is SKIP.
#   R6F-X   seed/tests/r6f/gate-r6f.sh --extra (R6F's rows, and through it R6D .. R5A: SPLIT, separate mode == in-process).
# Exit 0 iff no row FAILs.
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/../../../scripts/seed/lib.sh"
R=$SEED_REPO; B=${SEED_BUILD:A}; W=$B/gate-r6h; rm -rf $W; mkdir -p $W
fails=0
row() { printf "%-7s %s\n" $1 "$2"; [ $1 = FAIL ] && fails=$((fails+1)); return 0; }
O=${LINK_OBJS:-$R/build/selfbuild-run/r6/o}   # LINK_OBJS / LINK_IMGS: another worktree's selfbuild run (a clean gate worktree has none)
if [ -d $O ] && [ -n "$(ls $O/*.kso(N) 2>/dev/null)" ]; then
  LC_ITEMS=${LC_ITEMS:-134217728} zsh $R/scripts/seed/link-capacity.sh --seed $B/seed-1.bin --objs $O --copies 3 --work $W/cap > $W/cap.log 2>&1
  if [ $? -eq 0 ]; then row PASS "CAP $(grep -E '^(SCALE|MAX)' $W/cap/report.txt | cut -c1-160 | tr '\n' ' ')"
  else row FAIL "CAP $(grep -E 'FAIL' $W/cap/report.txt | head -3 | tr '\n' ' ')"; fi
else row SKIP "CAP no selfbuild objects at $O"; fi
SEED_BUILD=$B zsh $R/seed/tests/r6f/gate-r6f.sh --extra > $W/r6f.log 2>&1 && row PASS "R6F-X $(tail -1 $W/r6f.log)" \
  || row FAIL "R6F-X $(grep -E '^FAIL' $W/r6f.log | head -3 | tr '\n' ' ')"
[ $fails -eq 0 ] && echo "gate-r6h: READY" || echo "gate-r6h: $fails FAIL"
exit $(( fails > 0 ))
