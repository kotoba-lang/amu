#!/bin/zsh
# scripts/seed/selfbuild.sh [--seed seed.bin] [--stage0] [--no-link] [work-dir] -- milestone (f), first end-to-end attempt
# (agent SELF, 2026-10-04): how far does the SEED get toward building the big amu image from source, and what blocks it.
# BOOTSTRAP-TOOL (zsh + python summaries). After the loader is built only seeds run, except the optional --stage0 column.
#
#   1 LIST   scripts/seed/reach-twins.py over the minimal reach set (/private/tmp/reach-minimal.txt, WALL_CP, kotoba-lang
#            lang/compat): the loader-faithful module list of the image (138 files today).
#   2 SCAN   scripts/seed/r6-scan.sh with the seed: every module compiled from source in separate mode (--emit-module),
#            dependency-first; OK / REFUSED (first refusal) / BLOCKED (a require has no object).
#   3 S0     (--stage0) stage-0 `check` of every farm file (BOOTSTRAP-REFERENCE, nice, at most 2 at a time): whether the
#            SOURCE is admissible at all, and at which module stage-0 stops (its :source). This only classifies walls.
#   4 LINK   the seed links the OK modules into packaged native images: a probe entry (`main` = 0) requires the OK modules
#            no other OK module requires; tops are packed greedily into images while `seed link` succeeds (the large-M
#            profile of the seed's rung, scripts/seed/large-m.sh, links and extracts: the default profile's OUT region
#            refuses a 1.4 MB image, E5001); each image is extracted, packaged with tools/kexe_loader.c
#            (scripts/seed/package.sh) and run once (exit status 0 expected).
#   5 REPORT scripts/seed/selfbuild.py report: counts, walls ranked by modules made attemptable, per amu command the
#            walls in its closure and whether its entry has a Kotoba `main`, the link table.
# Default seed: build/seed-boot/r6e/seed-1.bin (bootstrap.sh) else build/export/g/seed-1.bin; it must be rung r6e's
# seed1_sha256 (seed/rungs/r6e.record) unless --seed names another one (then labelled "unrecorded seed").
# Output: <work>/report.txt (default work dir build/selfbuild), <work>/r6/ (scan), <work>/s0/, <work>/link/.
emulate -L zsh
setopt pipefail
R=$(cd "$(dirname "$0")/../.." && pwd)
seed=""; s0=0; link=1; W=""
while [ $# -gt 0 ]; do
  case $1 in
    --seed) seed=$2; shift 2 ;; --stage0) s0=1; shift ;; --no-link) link=0; shift ;;
    -*) echo "usage: selfbuild.sh [--seed seed.bin] [--stage0] [--no-link] [work-dir]" >&2; exit 2 ;;
    *) W=$1; shift ;;
  esac
done
W=${W:-$R/build/selfbuild}; mkdir -p $W; W=${W:A}
die() { echo "selfbuild: FAIL: $*" >&2; exit 1; }
# the frontend's desugar (10,680 lines) needs a 16 Mi pair arena in the compiler (4 Mi traps :budget/cells :pairs;
# FRONTSRC 2026-10-04): the default for every seed run of this script (scan and link)
export SEED_PAIRS=${SEED_PAIRS:-16777216}
sha() { shasum -a 256 $1 | cut -c1-64; }
want=$(sed -n 's/^seed1_sha256 //p' $R/seed/rungs/r6e.record)
if [ -z "$seed" ]; then
  for c in $R/build/seed-boot/r6e/seed-1.bin $R/build/export/g/seed-1.bin; do [ -f $c ] && [ "$(sha $c)" = "$want" ] && { seed=$c; break; }; done
  [ -n "$seed" ] || die "no r6e seed ($want): run scripts/seed/bootstrap.sh or pass --seed"
fi
label="rung r6e"; [ "$(sha $seed)" = "$want" ] || label="unrecorded seed"
cp $seed $W/seed-1.bin; echo ${SELF_OFFSET:-0} > $W/seed-1.offset
CP=${WALL_CP:-/private/tmp/wall-cp-16.txt}; K=${WALL_K:-/private/tmp/wt-K-kotoba-lang}; LIST0=${R6_REACH:-/private/tmp/reach-minimal.txt}
load0=$(sysctl -n vm.loadavg | awk '{print $2}')
{ echo "selfbuild $(date '+%F %T') seed $(sha $W/seed-1.bin | cut -c1-16) ($label) load $load0"
  echo "amu $(git -C $R rev-parse --short HEAD) kotoba-lang $(git -C $K rev-parse --short HEAD 2>/dev/null)"
  echo "reach $LIST0 classpath $CP"; } > $W/provenance.txt

# 1 LIST
python3 $R/scripts/seed/reach-twins.py $LIST0 $CP $R $K > $W/list.txt 2> $W/list.err || die "reach-twins"
# the source roots of the image and their heads (the files are read from live worktrees)
for d in $(sed 's#/src/.*#/src#; s#/lang/compat/.*#/lang/compat#' $W/list.txt | sort -u); do
  g=$(git -C $d rev-parse --short HEAD 2>/dev/null); echo "root $d ${g:-?} $(git -C $d status --short 2>/dev/null | grep -c .) dirty" >> $W/provenance.txt
done
# 2 SCAN
SEED_BUILD=$W R6_LIST=$W/list.txt nice zsh $R/scripts/seed/r6-scan.sh > $W/scan.out 2>&1 || die "r6-scan (see $W/scan.out)"
# 3 S0
if [ $s0 -eq 1 ]; then
  mkdir -p $W/s0
  cat > $W/s0/one.sh <<EOF
#!/bin/zsh
# stage-0 (BOOTSTRAP-REFERENCE) check of one farm file: file, verdict, source, line
f=\$1; ulimit -s 65500 2>/dev/null
r=\$(nice ${SEED_STAGE0:-$R/build/native-image/amu-native} check \$f --policy $K/lang/selfhost-compiler-grant.edn --source-path $W/r6/src --json --no-definitions 2>&1)
if echo "\$r" | grep -q ':ok true\|:format :kotoba.check/v1'; then printf "%s\tOK\t-\t-\n" "\$f"; exit 0; fi
m=\$(echo "\$r" | grep -o ':message "[^"]*' | head -1 | cut -c11-200); [ -n "\$m" ] || m="NOANSWER \$(echo "\$r" | tail -1 | tr '\t' ' ' | cut -c1-150)"
s=\$(echo "\$r" | grep -o ':source "[^"]*' | head -1 | cut -c10-); l=\$(echo "\$r" | grep -o ':line [0-9]*' | head -1 | cut -c7-)
printf "%s\t%s\t%s\t%s\n" "\$f" "\$m" "\${s:--}" "\${l:--}"
EOF
  chmod +x $W/s0/one.sh
  awk '{print $2}' $W/r6/order.txt | xargs -P${SEED_STAGE0_SLOTS:-2} -n1 $W/s0/one.sh > $W/s0/s0.tsv 2> $W/s0/s0.err
fi
# 4 LINK
if [ $link -eq 1 ]; then
  source $R/scripts/seed/lib.sh
  export SEED_BUILD=$W SEED_RESOURCES_35=$R:$W
  LM=$W/large-m-r6e/b/seed-1.bin
  if [ ! -f $LM ]; then zsh $R/scripts/seed/large-m.sh --rung r6e --prev $W/seed-1.bin $W/large-m-r6e > $W/large-m.out 2>&1 || die "large-m (see $W/large-m.out)"; fi
  L=$W/link; rm -rf $L; mkdir -p $L
  tops=($(python3 $R/scripts/seed/selfbuild.py tops $W))
  # try <dir> ns.. : probe entry + link; 0 iff the image was written
  try() {
    local D=$1 i=0 req="" n; shift; rm -rf $D; mkdir -p $D/o; cp $W/r6/o/*.kso $D/o/
    for n in "$@"; do req="$req [$n :as m$i]"; i=$((i+1)); done
    printf '(ns selfbuild.probe\n  {:kotoba/export [main]}\n  (:require%s))\n\n(defn main [] :i64 0)\n' "$req" > $D/probe.kotoba
    seed_run $W/seed-1.bin 0 compile $D/probe.kotoba --emit-module --entry --object-dir $D/o --output $D/o/selfbuild.probe.kso > $D/emit.log 2>&1 || return 1
    SEED_VECTOR_ITEMS=67108864 seed_run $LM 0 link $D/o/selfbuild.probe.kso --object-dir $D/o --output $D/image.kseed > $D/link.log 2>&1 && [ -s $D/image.kseed ]
  }
  print -r -- "image	tops	modules	lines	code_bytes	run_exit	first_failure_when_one_more_top_is_added" > $L/images.tsv
  k=1; cur=(); last=""
  finish() {
    local D=$L/img$k cnt off st
    try $D $cur || { echo "img$k: link of a set that linked before failed" >&2; return 1; }
    SEED_VECTOR_ITEMS=67108864 seed_run $LM 0 extract-native $D/image.kseed --symbol main --output $D/code.bin > $D/extract.log 2>&1
    off=$(sed -n 's/.*:offset \([0-9]*\).*/\1/p' $D/extract.log); mkdir -p $D/pkg; cp $D/code.bin $D/pkg/seed-1.bin; echo $off > $D/pkg/seed-1.offset
    SEED_BUILD=$D/pkg zsh $R/scripts/seed/package.sh 1 --out $D/pkg/image --allow 3,35,37,38,39 > $D/package.log 2>&1
    $D/pkg/image > $D/run.out 2>&1; st=$?
    cnt=$(python3 $R/scripts/seed/selfbuild.py count $W $cur)
    print -r -- "img$k	${#cur}	${cnt% *}	${cnt#* }	$(wc -c < $D/code.bin | tr -d ' ')	$st	$last" >> $L/images.tsv
    k=$((k+1)); cur=(); last=""
  }
  for t in $tops; do
    if try $L/t $cur $t; then cur+=($t)
    else
      last="+$t: $(grep -h -m1 -E 'seed: E|KEXE_TRAP' $L/t/emit.log $L/t/link.log | tr '\t' ' ' | cut -c1-80)"
      [ ${#cur} -gt 0 ] && finish
      try $L/t $t && cur=($t) || print -r -- "single	1	-	-	-	-	$t does not link alone" >> $L/images.tsv
    fi
  done
  [ ${#cur} -gt 0 ] && finish
  rm -rf $L/t
fi
# 5 REPORT
{ cat $W/provenance.txt; echo "load at end $(sysctl -n vm.loadavg | awk '{print $2}')"; python3 $R/scripts/seed/selfbuild.py report $W; } > $W/report.txt
cat $W/report.txt
