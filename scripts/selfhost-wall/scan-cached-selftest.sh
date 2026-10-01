#!/bin/zsh
# Self-test of scan-cached.sh on a synthetic project with a counting stub checker (no amu check involved):
#   cold cached scan == uncached scan; warm scan = 100% hits; touching one leaf re-checks exactly its reverse
#   closure among the listed files; restoring the leaf is a full hit again; a tampered record is rejected.
here=$(cd "$(dirname "$0")" && pwd)
t=$(mktemp -d ${TMPDIR:-/tmp}/scan-cached-selftest.XXXXXX); trap 'rm -rf $t' EXIT
mkdir -p $t/src/p $t/amu $t/k/lang/compat; echo '{}' > $t/k/lang/selfhost-compiler-grant.edn
mk() { printf '(ns p.%s\n  (:require %s))\n(defn f [] %s)\n' $1 "$2" "$3" > $t/src/p/$1.cljk; }
mk leaf ''                    1
mk mid  '[p.leaf :as l]'      2
mk top  '[p.mid :as m]'       3
mk side '[p.leaf :as l] [p.mid :as m]' 4
mk solo ''                    5
echo "refused-me" > /dev/null
printf '%s\n' $t/src/p/{top,side,solo,leaf,mid}.cljk > $t/list.txt
echo "$t/src" > $t/cp.txt
cat > $t/check.sh <<CHK
#!/bin/zsh
echo "\$1" >> $t/runs.log
if grep -q BAD "\$1"; then printf '%s\trefused: bad\n' "\$1"; else printf '%s\tOK\n' "\$1"; fi
CHK
chmod +x $t/check.sh
export WALL_CP=$t/cp.txt WALL_K=$t/k WALL_AMU_SRC=$t/amu WALL_CHECK=$t/check.sh WALL_CACHE_DIR=$t/cache
S="$here/scan-cached.sh -j 2"
fail=0; ok() { if eval "$2"; then echo "ok   $1"; else echo "FAIL $1"; fail=1; fi; }
runs() { [ -f $t/runs.log ] && wc -l < $t/runs.log || echo 0; }

# the uncached reference: the checker over every listed file
for f in $(cat $t/list.txt); do $t/check.sh $f; done > $t/ref.tsv; rm -f $t/runs.log
$=S $t/list.txt $t/cold.tsv 2>/dev/null
ok "cold cached scan equals the uncached scan" "cmp -s $t/cold.tsv $t/ref.tsv"
ok "cold scan checked every file once" "[ $(runs) = 5 ]"
rm -f $t/runs.log; $=S $t/list.txt $t/warm.tsv 2>/dev/null
ok "warm scan equals cold" "cmp -s $t/warm.tsv $t/cold.tsv"
ok "warm scan runs no checker" "[ $(runs) = 0 ]"
# touch the middle module: affected = mid, top, side (not leaf, not solo)
cp $t/src/p/mid.cljk $t/mid.bak; echo ';; touched' >> $t/src/p/mid.cljk
$=S --affected $t/list.txt $t/touched.tsv 2>/dev/null; rc=$?
ok "touched scan exits 0 (every miss was predicted by the affected closure)" "[ $rc = 0 ]"
ok "touching mid re-checks exactly mid, top, side" "[ $(runs) = 3 ] && ! grep -q 'leaf\|solo' $t/runs.log"
ok "touched scan output unchanged (a comment cannot change a verdict)" "cmp -s $t/touched.tsv $t/cold.tsv"
cp $t/mid.bak $t/src/p/mid.cljk; rm -f $t/runs.log
$=S --affected $t/list.txt $t/restored.tsv 2>/dev/null
ok "restoring mid is a hit again" "[ $(runs) = 0 ]"
# a real change of verdict
echo 'BAD' >> $t/src/p/leaf.cljk; rm -f $t/runs.log
$=S --affected $t/list.txt $t/bad.tsv 2>/dev/null
ok "touching leaf re-checks the whole chain (leaf, mid, top, side)" "[ $(runs) = 4 ] && ! grep -q solo $t/runs.log"
ok "the new verdict is reported" "[ \$(grep -c refused $t/bad.tsv) = 1 ]"
# tampered record
k=$(ls $t/cache/records | head -1); echo corrupt > $t/cache/records/$k; rm -f $t/runs.log
$=S $t/list.txt $t/after.tsv 2>/dev/null
ok "a corrupt record is not trusted" "[ \$(wc -l < $t/after.tsv) = 5 ]"
exit $fail
