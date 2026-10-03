#!/bin/zsh
# scripts/seed/lexread.sh [build|check [name...]] -- golden gate of seed modules 10-lex and 11-read. BOOTSTRAP-TOOL.
#   build   assemble 00-ns + 10-lex + 11-read + seed/tests/lexread/dump.kotoba, compile it with STAGE-0
#   check   (default) build if needed, then for every file in lexread_ref.py's list (19 ports + corpus) run the
#           native dumper in both modes (tok, tree) and byte-compare with seed/tests/lexread/golden/<name>.{tok,tree}
#   live    like check, but the expected dumps are made on the fly by lexread_ref.py for the seed's OWN sources (every
#           seed/*.kotoba of the MANIFEST that exists, plus the other modules' tests are not included): the lexer and reader
#           must accept the compiler's own text (needed for the fixed point)
#   stat    print the dumper's STAT line (bytes toks nodes lits litb) for the files named (or the ports)
# The goldens come from scripts/seed/lexread_ref.py (python3, independent of the Kotoba code).
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/lib.sh"
R=$SEED_REPO; W=$SEED_BUILD/lexread; mkdir -p $W
cmd=${1:-check}; [ $# -gt 0 ] && shift
build() {
  : > $W/dump.kotoba
  for p in seed/00-ns.kotoba seed/10-lex.kotoba seed/11-read.kotoba seed/tests/lexread/dump.kotoba; do
    cat $R/$p >> $W/dump.kotoba; printf '\n' >> $W/dump.kotoba
  done
  if [ -f $W/dump.bin ] && [ $W/dump.bin -nt $W/dump.kotoba ] && [ -s $W/dump.offset ]; then return 0; fi
  seed_stage0_build $W/dump.kotoba $W/dump || { echo "lexread: stage-0 refused the dumper"; grep -o ':message "[^"]*"' $W/dump.log | head -3; head -c 600 $W/dump.log; return 1; }
}
files() { python3 - <<PY
import sys; sys.path.insert(0, "$R/scripts/seed")
import lexread_ref as r
for n, p in r.FILES: print(n, p)
PY
}
run1() { ( cd $W; seed_run $W/dump.bin $(cat $W/dump.offset) $1 $R/$2 ) }
case $cmd in
  build) build ;;
  stat) build || exit 1
        for line in ${(f)"$(files)"}; do n=${line%% *}; p=${line#* }; [ $# -eq 0 ] || (( ${@[(I)$n]} )) || continue; echo -n "$n: "; run1 stat $p; done ;;
  check) build || exit 1
        fail=0; cnt=0; widened=0
        wl=$(grep -v '^#' $R/seed/tests/lexread/WIDENED 2>/dev/null | cut -f1)
        for line in ${(f)"$(files)"}; do
          n=${line%% *}; p=${line#* }
          if [[ $'\n'$wl$'\n' == *$'\n'$n$'\n'* ]]; then widened=$((widened+1)); continue; fi
          [ $# -eq 0 ] || (( ${@[(I)$n]} )) || continue
          for m in tok tree; do
            run1 $m $p > $W/out.$m 2> $W/err.$m
            cnt=$((cnt+1))
            if ! cmp -s $W/out.$m $R/seed/tests/lexread/golden/$n.$m; then echo "FAIL $n $m"; diff $W/out.$m $R/seed/tests/lexread/golden/$n.$m | head -5; head -3 $W/err.$m; fail=1; fi
          done
        done
        [ $fail -eq 0 ] && echo "lexread: PASS ($cnt dumps byte-identical to the goldens; $widened files skipped: grammar widened on purpose, seed/tests/lexread/WIDENED)" || { echo "lexread: FAIL"; exit 1; } ;;
  live) build || exit 1
        fail=0
        for p in ${(f)"$(seed_manifest)"}; do
          [ -f $R/$p ] || continue
          for m in tok tree; do
            run1 $m $p > $W/out.$m 2> $W/err.$m
            python3 $R/scripts/seed/lexread_ref.py dump $m $R/$p > $W/exp.$m
            if cmp -s $W/out.$m $W/exp.$m; then :; else echo "FAIL $p $m"; diff $W/out.$m $W/exp.$m | head -5; fail=1; fi
          done
          echo -n "$p: "; run1 stat $p
        done
        [ $fail -eq 0 ] && echo "lexread live: PASS" || { echo "lexread live: FAIL"; exit 1; } ;;
  *) echo "usage: lexread.sh build|check|live|stat [name...]" >&2; exit 2 ;;
esac
