#!/bin/zsh
# scripts/seed/golden.sh <rung> [--allow-regress] [seed.bin] -- generate the G3 refusal golden seed/tests/golden/refusal-<rung>.txt for a
# rung (r4, r4b, r5 ...) with the given seed (default $SEED_BUILD/seed-1.bin, the self-built compiler of that rung) and REVIEW it against
# the previous golden (the newest earlier refusal-*.txt by rung order): prints the labels added, REFUSED->ACCEPT flips (allowed: a feature the
# rung covers), ACCEPT->REFUSED flips (a regression: exit 1 unless --allow-regress) and refusal-text changes. BOOTSTRAP-TOOL (zsh), owner HOUSE2.
# The golden is written by g3.sh --update (which refuses a golden with BROKEN lines). Review `git diff` before committing.
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/lib.sh"
rung=${1:?usage: golden.sh <rung> [--allow-regress] [seed.bin]}; shift
allow=0; [ "$1" = "--allow-regress" ] && { allow=1; shift; }
bin=${1:-$SEED_BUILD/seed-1.bin}
G=$SEED_REPO/seed/tests/golden
zsh $SEED_REPO/scripts/seed/g3.sh --rung $rung --update $bin | tail -2 || exit 1
# previous golden: the greatest (number, suffix) below this rung
prev=""; n=$(seed_rung_num $rung)
for f in $G/refusal-r*.txt(N); do
  k=${${f:t:r}#refusal-}; [ "$k" = "$rung" ] && continue
  kn=$(seed_rung_num $k); { [ $kn -lt $n ] || { [ $kn -eq $n ] && [[ $k < $rung ]]; }; } && prev=$k
done
[ -n "$prev" ] || { echo "golden: no earlier golden to compare with"; exit 0; }
python3 - $G/refusal-$prev.txt $G/refusal-$rung.txt $prev $rung $allow <<'PY'
import sys
a, b, pa, pb, allow = sys.argv[1:6]
def load(p): return dict(l.rstrip('\n').split('\t', 1) for l in open(p) if '\t' in l)
A, B = load(a), load(b)
add = [k for k in B if k not in A]; gone = [k for k in A if k not in B]
r2a = [k for k in B if k in A and A[k].startswith('REFUSED') and B[k] == 'ACCEPT']
a2r = [k for k in B if k in A and A[k] == 'ACCEPT' and B[k].startswith('REFUSED')]
txt = [k for k in B if k in A and A[k].startswith('REFUSED') and B[k].startswith('REFUSED') and A[k] != B[k]]
print(f"golden {pb} vs {pa}: {len(B)} programs; {len(add)} added, {len(gone)} removed, {len(r2a)} REFUSED->ACCEPT, {len(a2r)} ACCEPT->REFUSED, {len(txt)} refusal texts changed")
for t, ks in (('added', add), ('removed', gone), ('REFUSED->ACCEPT', r2a), ('ACCEPT->REFUSED (REGRESSION)', a2r)):
    for k in ks[:60]: print(f"  {t}: {k}" + (f"  [{A.get(k, '')[:70]}]" if t.startswith('REFUSED') else ''))
for k in txt[:20]: print(f"  text: {k}\n    {A[k][:100]}\n    {B[k][:100]}")
sys.exit(1 if a2r and allow != '1' else 0)
PY
