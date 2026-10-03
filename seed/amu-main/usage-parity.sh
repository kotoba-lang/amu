#!/bin/zsh
# seed/amu-main/usage-parity.sh <amu> [work-dir] -- the argument layer of `amu` against stage-0, byte for byte (agent CMD,
# 2026-10-04). BOOTSTRAP-TOOL (zsh, python3). Stage-0 = build/native-image/amu-native (SEED_STAGE0), BOOTSTRAP-REFERENCE:
# the oracle only, never in the amu image's process tree.
#
# Each case runs `<cmd> <argv..>` in its own directory holding x.kotoba (a typed factorial both compile), f.kotoba
# (examples/fuel.kotoba: stage-0 compiles it, the seed refuses its untyped `fact`), r.kotoba (a program both refuse), d.kotoba/ (a directory) and p/app/{main,util}.kotoba (a two-module project), once with stage-0 and once with
# <amu> (`T:` / `B:` cases: see the oracle note in the loop). Compared: exit status, stdout, stderr (exact bytes), and the names of the files the command created. For a
# compile both accept, the artifact is compared by kind only (stage-0's kexe/v1 vs amu's kexe/v1 from the seed: the code
# differs by construction) and amu's seal is checked (kexe_check.py seal). A refusal of the language is the seed's own
# line (declared difference, class DECLARED), so r.kotoba is compared by exit status only.
# Output: <work>/usage.tsv (case, class, detail) and a summary line. Classes: SAME, DECLARED (a listed declared
# difference that holds), DIFF.
emulate -L zsh; setopt pipefail nullglob
H=${0:A:h}; R=${H:h:h}
A=${1:?usage: usage-parity.sh <amu> [work-dir]}; A=${A:A}
W=${2:-$R/build/cmd/usage}; rm -rf $W; mkdir -p $W; W=${W:A}
S0=${SEED_STAGE0:-$R/build/native-image/amu-native}
mkenv() {  # <dir>
  mkdir -p $1/d.kotoba $1/p/app
  print -r -- '(ns x) (defn fact [n :i64] :i64 (if (<= n 1) 1 (* n (fact (- n 1))))) (defn main [] :i64 (fact 5))' > $1/x.kotoba
  cp $R/examples/fuel.kotoba $1/f.kotoba
  print -r -- '(ns r) (defn main [] :i64 (if-some [x nil] 1 2))' > $1/r.kotoba
  print -r -- '(ns app.util) (defn twice [x :i64] :i64 (* 2 x))' > $1/p/app/util.kotoba
  print -r -- '(ns app.main (:require [app.util :as u])) (defn main [] :i64 (u/twice 21))' > $1/p/app/main.kotoba
  print -r -- 'not a source' > $1/x.txt
}
cases=(
  'B:'
  'B:-h'
  'B:--help'
  'B:--jvm-free'
  'help'
  'bogus-command'
  'compile'
  'compile x.txt'
  'T:compile x.kotoba'
  'T:compile x.kotoba --output q.kexe'
  'T:compile --jvm-free x.kotoba --output q.kexe'
  'compile x.kotoba --target'
  'compile x.kotoba --target bogus --output q.kexe'
  'compile nonexist.kotoba --target aarch64-macos --output q.kexe'
  'compile nonexist.kotoba --target bogus --output q.kexe'
  'compile d.kotoba --target aarch64-macos --output q.kexe'
  'compile --target aarch64-macos x.kotoba --output q.kexe'
  'compile x.kotoba --target aarch64-macos --output sub/none/q.kexe'
  'compile x.kotoba --target aarch64-macos --output q.kexe'
  'compile x.kotoba --target aarch64-macos'
  'compile x.kotoba --target aarch64-macos --output'
  'compile x.kotoba --target aarch64-macos-kotoba-v1 --output q.kexe'
  'compile x.kotoba y.kotoba --target aarch64-macos --output q.kexe'
  'compile p/app/main.kotoba --source-path p --target aarch64-macos --output pm.kexe'
  'compile p/app/main.kotoba --source-path p --unpinned --target aarch64-macos --output pm.kexe'
  'compile p/app/main.kotoba --module-lock zz --target aarch64-macos'
  'compile r.kotoba --target aarch64-macos --output r.kexe'
  'compile f.kotoba --target aarch64-macos --output f.kexe'
  'compile p/app/main.kotoba --module-lock zz --blocks bb --target aarch64-macos'
  'check'
  'check x.txt'
  'inspect x.kotoba'
)
: > $W/usage.tsv
i=0
for c in "${cases[@]}"; do
  i=$((i+1)); D0=$W/$i/s0 D1=$W/$i/amu; mkenv $D0; mkenv $D1
  # oracle: stage-0's in-process CLI; `T:` = stage-0 with `--target aarch64-macos` appended (bin/amu's host default, ADR
  # 0351); `B:` = bin/amu itself under node (its launcher layer only: usage text, --jvm-free; BOOTSTRAP-REFERENCE)
  o=S; cc=$c; case $c in T:*) o=T; cc=${c#T:} ;; B:*) o=B; cc=${c#B:} ;; esac
  argv=(${=cc})
  case $o in
    S) ( cd $D0; nice $S0 $argv > ../s0.out 2> ../s0.err; echo $? > ../s0.rc ) ;;
    T) argv=(${argv:#--jvm-free}); ( cd $D0; nice $S0 $argv --target aarch64-macos > ../s0.out 2> ../s0.err; echo $? > ../s0.rc ) ;;
    B) ( cd $D0; node $R/bin/amu $argv > ../s0.out 2> ../s0.err; echo $? > ../s0.rc ) ;;
  esac
  ( cd $D1; $A $argv > ../amu.out 2> ../amu.err; echo $? > ../amu.rc )
  ( cd $D0; find . -newer x.kotoba -type f | sort ) > $W/$i/s0.files
  ( cd $D1; find . -newer x.kotoba -type f | sort ) > $W/$i/amu.files
  r0=$(cat $W/$i/s0.rc) r1=$(cat $W/$i/amu.rc)
  cls=SAME; det=""
  [ $r0 = $r1 ] || { cls=DIFF; det="rc $r0/$r1"; }
  cmp -s $W/$i/s0.out $W/$i/amu.out || { cls=DIFF; det="$det stdout"; }
  cmp -s $W/$i/s0.err $W/$i/amu.err || { cls=DIFF; det="$det stderr"; }
  cmp -s $W/$i/s0.files $W/$i/amu.files || { cls=DIFF; det="$det files"; }
  if [[ $c == *r.kotoba* ]] && [ $r0 = $r1 ] && [ $cls = DIFF ]; then cls=DECLARED; det="$det (the seed's refusal line)"; fi
  if [[ $c == inspect* ]] && [ $r0 = 64 ] && [ $r1 = 69 ]; then cls=DECLARED; det="$det (a bin/amu command with no native implementation: declared stub naming it; stage-0's in-process CLI does not know it)"; fi
  if [[ $c == *--blocks* ]] && [ $r1 = 69 ]; then cls=DECLARED; det="$det (declared stub: module locks are not on the seed route)"; fi
  if [[ $c == *f.kotoba* ]] && [ $r0 = 0 ] && [ $r1 = 65 ]; then cls=DECLARED; det="$det (language: the seed refuses what stage-0 compiles, AMU-REFUSES)"; fi
  if [ $r1 = 0 ] && [ $cls = SAME ]; then
    for kp in $D1/*.kexe(N); do
      k=${kp:t}; s=$(python3 $H/kexe_check.py seal $kp 2>&1 | tail -1); [[ $s == "seal ok"* ]] || { cls=DIFF; det="$det seal($k): $s"; }
      head -c 30 $kp | grep -q '^{:format :kotoba.kexe/v1' || { cls=DIFF; det="$det format($k)"; }
    done
  fi
  print -r -- "$i	$cls	[$c]	$det" >> $W/usage.tsv
done
cat $W/usage.tsv
echo "usage-parity: $(wc -l < $W/usage.tsv | tr -d ' ') cases: $(cut -f2 $W/usage.tsv | sort | uniq -c | tr -s ' ' | tr '\n' ' ') amu $(shasum -a 256 $A | cut -c1-16) stage-0 $(shasum -a 256 $S0 | cut -c1-16) (BOOTSTRAP-REFERENCE)"
