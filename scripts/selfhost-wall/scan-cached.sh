#!/bin/zsh
# Content-addressed, affected-only selfhost wall scan.
#
#   scan-cached.sh [--affected] [--no-cache] [--changed <paths.txt>] [-j N] <list.txt> <out.tsv>
#
# Same output as scan.sh (<file> TAB <verdict>, in list order), but a file is only re-checked when its KEY
# changed. The key is src/kotoba/compiler/wall_cache.cljk's: the CID of the file's bytes + the bytes of every
# module in its transitive require closure + the classpath identity + the checker version. All decisions
# (keys, the reverse-dependency closure, record digests) are made by that pure Kotoba module; this script only
# does effects: find/awk to read the require graph, shasum to hash bytes, the cache directory, the checker.
#
#   default       lookup every key; check only the misses; report hit rate
#   --affected    trust the previous scan for every file the require graph says is NOT affected by the changes
#                 since that scan (no record reads for them), re-check the affected ones (cache first)
#   --no-cache    ignore stored records (still writes them); the "uncached" reference scan
#   --changed F   F lists changed paths (one per line) instead of the content comparison with the last scan
#   -j N          parallel checker processes (default 4)
#
# Env: WALL_CP WALL_K [WALL_AMU_SRC] as for check-one.sh;
#      WALL_CHECK       checker command, `<cmd> <file>` prints "<file>\t<verdict>" (default check-one.sh next to
#                       this script; /private/tmp/wall-one.sh works; check-native.sh later)
#      WALL_PLAN        command that runs wall_cache `plan` (stdin -> stdout). Default: the nbb run of
#                       wall-cache-plan.cljs -- BOOTSTRAP scaffolding; replace with the Kotoba-built binary
#      WALL_CACHE_DIR   default $HOME/.cache/kotoba-wall-cache (created 0700)
#      WALL_CHECKER_EXTRA   extra files whose bytes are part of the checker identity
#      WALL_SUBJECT_DIRS  extra classpath dirs treated as subject (edits invalidate dependents only), not checker.
#                       A classpath src/resources dir holding a listed file is subject automatically; every other
#                       local classpath dir is checker (an edit there invalidates every verdict: it may be the compiler)
#      WALL_STRICT=1    also hash every amu-src module wall's wasm_cli requires into the checker identity
# Verified: --verify is implicit. After planning, every miss must be inside the predicted affected set when the
# last scan had the same checker identity; a violation is printed and the exit status is 3.
zmodload zsh/datetime
export LC_ALL=C
here=$(cd "$(dirname "$0")" && pwd)
AMU=${WALL_AMU_ROOT:-$(cd "$here/../.." && pwd)}
mode=cached; changed_file=""; jobs=4; nocache=0
while [ $# -gt 0 ]; do case $1 in
  --affected) mode=affected; shift;; --no-cache) nocache=1; shift;;
  --changed) changed_file=$2; shift 2;; -j) jobs=$2; shift 2;; *) break;; esac; done
list=${1:?list.txt}; out=${2:?out.tsv}
K=${WALL_K:?set WALL_K}; CPF=${WALL_CP:?set WALL_CP}; CP=$(cat $CPF)
AMU_SRC=${WALL_AMU_SRC:-$AMU/src}
CHECK=${WALL_CHECK:-$here/check-one.sh}
CACHE=${WALL_CACHE_DIR:-$HOME/.cache/kotoba-wall-cache}
t0=$EPOCHREALTIME
umask 077; mkdir -p $CACHE/records $CACHE/state; chmod 700 $CACHE $CACHE/records $CACHE/state 2>/dev/null
work=$(mktemp -d ${TMPDIR:-/tmp}/wall-cache.XXXXXX); trap 'rm -rf $work' EXIT
export WALL_CP WALL_K WALL_AMU_SRC

. $here/wall-cache-lib.sh

# 1. the require graph, hashed, and the checker identity
wc_graph $list
t_graph=$EPOCHREALTIME

# 3. what changed since the last scan of this list (content, not mtime) ---------------------------------------
sid=$(echo "$list" | sha | cut -c1-16)
state=$CACHE/state/$sid
printf '%s\t%s\n' $cpid $chk > $work/h.now
same_checker=0; [ -f $state.h ] && cmp -s $state.h $work/h.now && same_checker=1
if [ -n "$changed_file" ]; then cp $changed_file $work/changed.txt
elif [ -f $state.sha ] && [ $same_checker = 1 ]; then
  comm -13 $state.sha $work/sha.tsv | cut -f1 > $work/changed.txt   # (path, sha) pairs only in the new set: new or different
else cut -f1 $work/sha.tsv > $work/changed.txt; fi                         # no comparable last scan: everything is new

# 4. plan call 1: keys + affected set -------------------------------------------------------------------------
{ printf 'H\t%s\t%s\n' $cpid $chk; cat $work/nodes.plan; sed 's/^/X\t/' $work/changed.txt; } > $work/in1.txt
t_p1=$EPOCHREALTIME
plan < $work/in1.txt > $work/out1.txt || { echo "scan-cached: plan failed" >&2; exit 2; }
awk -F'\t' '$1=="K"{print $2 "\t" $3}' $work/out1.txt | sort > $work/keys.tsv
awk -F'\t' '$1=="A"{print $2}' $work/out1.txt | sort > $work/affected.txt
t_plan1=$EPOCHREALTIME

# 5. per-file: hit, trusted-from-last-scan, or miss -----------------------------------------------------------
sort -u $list > $work/files.sorted
join -t$'\t' $work/files.sorted $work/keys.tsv > $work/fk.tsv              # file TAB key
nfiles=$(wc -l < $work/files.sorted)
: > $work/res.tsv; : > $work/rlines.txt; : > $work/miss.txt; nhit=0; ntrust=0
while IFS=$'\t' read f k; do
  if [ $mode = affected ] && [ $same_checker = 1 ] && ! grep -qxF -- "$f" $work/affected.txt && [ -f $state.res ]; then
    v=$(awk -F'\t' -v f="$f" -v k="$k" '$1==f && $2==k {print $3; exit}' $state.res)
    if [ -n "$v" ]; then printf '%s\t%s\t%s\n' "$f" "$k" "$v" >> $work/res.tsv; ntrust=$((ntrust+1)); continue; fi
  fi
  rec=$CACHE/records/$k
  if [ $nocache = 0 ] && [ -f $rec ] && [ ! -L $rec ]; then
    { IFS=$'\t' read -r fmt rk dg; IFS= read -r vd; } < $rec
    if [ "$fmt" = kotoba.wall-cache/v1 ] && [ "$rk" = "$k" ]; then printf 'R\t%s\t%s\t%s\n' "$k" "$vd" "$dg" >> $work/rlines.txt; printf '%s\t%s\t%s\n' "$f" "$k" "$vd" >> $work/cand.tsv; continue; fi
  fi
  printf '%s\t%s\n' "$f" "$k" >> $work/miss.txt
done < $work/fk.tsv
touch $work/cand.tsv $work/miss.txt

# 6. validate the stored records (Kotoba), demote any bad one to a miss ---------------------------------------
if [ -s $work/rlines.txt ]; then
  { printf 'H\t%s\t%s\n' $cpid $chk; cat $work/rlines.txt; } | plan | awk -F'\t' '$1=="V"&&$3=="bad"{print $2}' > $work/bad.txt
  while IFS=$'\t' read f k v; do
    if grep -qxF -- "$k" $work/bad.txt; then echo "scan-cached: rejected record $k (digest mismatch)" >&2; rm -f $CACHE/records/$k; printf '%s\t%s\n' "$f" "$k" >> $work/miss.txt
    else printf '%s\t%s\t%s\n' "$f" "$k" "$v" >> $work/res.tsv; nhit=$((nhit+1)); fi
  done < $work/cand.tsv
fi
nmiss=$(wc -l < $work/miss.txt)

# 7. every miss must be predicted by the affected closure (same checker, comparable last scan) ----------------
viol=0
if [ $same_checker = 1 ] && [ -f $state.sha ] && [ -z "$changed_file" ] && [ $nocache = 0 ]; then
  while IFS=$'\t' read f k; do grep -qxF -- "$f" $work/affected.txt || { echo "scan-cached: MISS OUTSIDE AFFECTED SET: $f" >&2; viol=$((viol+1)); }; done < $work/miss.txt
fi

# 8. check the misses --------------------------------------------------------------------------------------
t_c0=$EPOCHREALTIME
cut -f1 $work/miss.txt | xargs -P $jobs -n1 $CHECK > $work/checked.tsv 2>/dev/null
t_c1=$EPOCHREALTIME
# 9. store the new verdicts: digests from the pure module, written by this script ------------------------------
awk -F'\t' 'NR==FNR{ if ($0 != "") v[$1] = $2; next } { print $1 "\t" $2 "\t" (($1 in v) ? v[$1] : "NO-RESULT") }' $work/checked.tsv $work/miss.txt |
  tr -d '\r' > $work/new.tsv
awk -F'\t' '{ v = $3; gsub(/[\t\n]/, " ", v); printf "S\t%s\t%s\n", $2, v }' $work/new.tsv > $work/slines.txt
if [ -s $work/slines.txt ]; then
  { printf 'H\t%s\t%s\n' $cpid $chk; cat $work/slines.txt; } | plan | awk -F'\t' '$1=="D"{print $2 "\t" $3}' > $work/digests.tsv
  while IFS=$'\t' read f k v; do
    v=${v//$'\t'/ }; dg=$(awk -F'\t' -v k=$k '$1==k{print $2; exit}' $work/digests.tsv)
    printf '%s\t%s\t%s\n' "$f" "$k" "$v" >> $work/res.tsv
    if [ "$v" != NO-RESULT ] && [ -n "$dg" ]; then   # a missing result is never stored
      printf 'kotoba.wall-cache/v1\t%s\t%s\n%s\n' "$k" "$dg" "$v" > $work/rec.tmp && mv $work/rec.tmp $CACHE/records/$k
    fi
  done < $work/new.tsv
fi

# 10. output in list order, remember this scan --------------------------------------------------------------
sort -t$'\t' -k1,1 $work/res.tsv > $work/res.sorted
awk -F'\t' 'NR==FNR{v[$1]=$3; next} {print $0 "\t" ($0 in v ? v[$0] : "NO-KEY")}' $work/res.sorted $list | awk -F'\t' '{print $1 "\t" $2}' > $out
cp $work/res.sorted $state.res; cp $work/sha.tsv $state.sha; cp $work/h.now $state.h
t1=$EPOCHREALTIME
ok=$(grep -c '	OK$' $out)
printf 'scan-cached: files=%d nodes=%d changed=%d affected=%d | hit=%d trusted=%d miss=%d (hit rate %.1f%%) | checker runs=%d violations=%d\n' \
  $nfiles $(wc -l < $work/nodes.txt) $(wc -l < $work/changed.txt) $(wc -l < $work/affected.txt) $nhit $ntrust $nmiss \
  $(( nfiles ? 100.0*(nhit+ntrust)/nfiles : 0 )) $nmiss $viol >&2
printf 'scan-cached: seconds total=%.1f graph+hash=%.1f plan1=%.1f check=%.1f | OK: %d of %d\n' \
  $((t1-t0)) $((t_graph-t0)) $((t_plan1-t_p1)) $((t_c1-t_c0)) $ok $nfiles >&2
[ $viol = 0 ] || exit 3
