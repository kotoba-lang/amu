#!/bin/zsh
# scripts/seed/g3.sh [--rung rN] [--update] [seed.bin [offset]] -- gate G3: the refusal texts of the seed front end.
# BOOTSTRAP-TOOL (zsh), owner GATES. After the compiler is built only the C loader and the seed run.
#
# Programs (every one is checked with `seed check` AND `seed compile`):
#   neg/<n>   seed/tests/neg/*.kotoba           the seed negatives (30 at R0)
#   conf/<d>/<n>  seed/tests/conformance/*/*.kotoba   verbatim kotoba-lang conformance programs (55)
#   case/<n>  seed/tests/check/cases/err-*.kotoba     21-check's own refusal cases
#   rKneg/<n> seed/tests/rK/neg/*.kotoba         the negatives of every rung K = 1..N up to the gated rung N (r1neg from r1 on, r3neg from r3,
#             r4neg from r4: since 2026-10-03; before, only r1/neg was included), plus seed/tests/<rung>/neg for an extension rung
#             such as r4b (label <rung>neg/<n>)
# Result of one program: `ACCEPT` (check exits 0 and prints "ok") or `REFUSED <the single stderr line>`; anything else
# (no stderr line, exit status other than 0/1, a line not starting "seed: E<code> ", a crash) is
# BROKEN. `compile` must give the SAME refusal line as `check`, exit 1 and leave NO output file behind.
# The golden is seed/tests/golden/refusal-<rung>.txt, one line `<label><TAB><result>`; the gate fails on any difference
# (a program that is accepted at the rung is recorded as ACCEPT, so a new feature changes the golden DELIBERATELY:
# run `g3.sh --rung rN --update` after the rung lands, and review `git diff` of the golden). Rule: a golden line may
# change from REFUSED to ACCEPT only for a program the rung's features cover.
# Default rung r0, default compiler build/seed/seed-1.bin (the self-built seed).
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/lib.sh"
rung=r0; update=0
while [ $# -gt 0 ]; do
  case $1 in --rung) rung=$2; shift 2 ;; --update) update=1; shift ;; *) break ;; esac
done
bin=${1:-$SEED_BUILD/seed-1.bin}; off=${2:-$(cat ${bin%.bin}.offset)}
R=$SEED_REPO; W=$SEED_BUILD/g3-${bin:t:r}; mkdir -p $W $R/seed/tests/golden
# the golden: refusal-<rung>.txt; a rung without its own golden uses the alias target's (seed/tests/ALIASES) and --update refuses to
# write that (record a golden of its own by creating the file or adding no alias)
gname=$(seed_rung_golden $rung) || gname=$rung
G=$R/seed/tests/golden/refusal-$gname.txt
rn=$(seed_rung_num $rung)
[ -s $bin ] || { echo "G3: no compiler at $bin" >&2; exit 2; }
export SEED_RESOURCES_35=$R:$W

progs() {
  local f
  for f in $R/seed/tests/neg/*.kotoba(N); do echo "neg/${f:t:r} $f"; done
  for f in $R/seed/tests/conformance/*/*.kotoba(N); do echo "conf/${${f:h}:t}/${f:t:r} $f"; done
  for f in $R/seed/tests/check/cases/err-*.kotoba(N); do echo "case/${f:t:r} $f"; done
  local k d
  for k in $(seq 1 $rn 2>/dev/null); do [ $rn -ge 1 ] || break; for f in $R/seed/tests/r$k/neg/*.kotoba(N); do echo "r${k}neg/${f:t:r} $f"; done; done
  # every EXTENSION rung rNx (r4b, r5a, r5b ..) whose key is <= the gated rung's: an earlier extension rung's negatives stay in later
  # goldens (HOUSE4 2026-10-03; before, only the gated rung's own extension dir was read, so r4bneg dropped out at r5b and r6a)
  local e ek rk=$(seed_rung_key $rung)
  for d in $R/seed/tests/r<->[a-z](N/); do
    e=${d:t}; ek=$(seed_rung_key $e)
    [ $ek -le $rk ] && [ -d $d/neg ] || continue
    for f in $d/neg/*.kotoba(N); do echo "${e}neg/${f:t:r} $f"; done
  done
}

: > $W/out.txt; broken=0; n=0; nref=0; nacc=0
for line in ${(f)"$(progs)"}; do
  lab=${line%% *}; f=${line#* }; n=$((n+1))
  rm -f $W/o.kseed
  seed_run $bin $off check $f > $W/chk.out 2> $W/chk.err; crc=$?
  seed_run $bin $off compile $f $W/o.kseed > $W/cmp.out 2> $W/cmp.err; mrc=$?
  cl=$(head -1 $W/chk.err); ml=$(head -1 $W/cmp.err)
  if [ $crc -eq 0 ] && [ "$(head -1 $W/chk.out)" = ok ] && [ $mrc -eq 0 ] && [ -s $W/o.kseed ]; then
    res=ACCEPT; nacc=$((nacc+1))
  elif [ $crc -eq 1 ] && [ $mrc -eq 1 ] && [ "$cl" = "$ml" ] && [ ! -e $W/o.kseed ] \
       && [ $(wc -l < $W/chk.err | tr -d ' ') -eq 1 ] && [[ $cl =~ '^seed: E[0-9]+ ' ]]; then
    res="REFUSED $cl"; nref=$((nref+1))
  else
    res="BROKEN check rc=$crc [$cl] compile rc=$mrc [$ml] out=$([ -e $W/o.kseed ] && echo left || echo none)"; broken=$((broken+1))
  fi
  printf '%s\t%s\n' $lab $res >> $W/out.txt
done

if [ $update -eq 1 ]; then
  G=$R/seed/tests/golden/refusal-$rung.txt   # --update always records the rung's OWN golden (also for an aliased rung)
  [ $broken -eq 0 ] || { echo "G3: refusing to record a golden with $broken BROKEN lines"; grep BROKEN $W/out.txt | head; exit 1; }
  cp $W/out.txt $G; echo "G3: golden $G written ($n programs)"
fi
[ -s $G ] || { echo "G3: no golden $G (run with --update once the rung is built and reviewed)" >&2; exit 2; }
diff=$(diff $G $W/out.txt)
nd=$(echo "$diff" | grep -c '^>')
[ -z "$diff" ] || { echo "$diff" | head -30; }
echo "G3 [$rung]: $n programs, $nref refused with golden text, $nacc accepted, $broken broken, $nd differ from $G:t (compiler $bin:t sha256 $(shasum -a 256 $bin | cut -c1-16))"
[ $broken -eq 0 ] && [ -z "$diff" ]
