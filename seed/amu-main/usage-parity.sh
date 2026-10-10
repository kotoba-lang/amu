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
# Output: <work>/usage.tsv (case, class, detail) and a summary line. Classes: SAME, SAME-DATA (H: equal as data and by
# refusal phase and message, not byte for byte), DECLARED (a listed declared difference that holds), DIFF.
# 2026-10-10 (product entries): `compile` and `check` are the product entries nbb.aarch64-cli / nbb.check-cli, so their
# cases are `H:` cases: the oracle is bin/amu itself under node (KOTOBA_VERDICT_CACHE=off, the route of the same code,
# BOOTSTRAP-REFERENCE), compared by seed/amu-main/answer_cmp.py (exit status, the answer map as data with the host's
# absolute case directory removed, the refusal's :error and :message, the created file names). Declared there: a
# relative --source-path root (no cwd wire), --module-lock (refused by name), check's :definitions marker, bin/amu's own
# launcher line for a --target it routes nowhere, check-driver's message for a missing source. The other
# cases (launcher layer, extract-native, stubs) keep their oracle.
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
  cp $W/s0.kexe $1/s0.kexe 2>/dev/null
}
cases=(
  'B:'
  'B:-h'
  'B:--help'
  'B:--jvm-free'
  'help'
  'bogus-command'
  'H:compile'
  'H:compile x.txt'
  'H:compile x.kotoba'
  'H:compile x.kotoba --output q.kexe'
  'H:compile --jvm-free x.kotoba --output q.kexe'
  'H:compile x.kotoba --target'
  'H:compile x.kotoba --target bogus --output q.kexe'
  'H:compile nonexist.kotoba --target aarch64-macos --output q.kexe'
  'H:compile nonexist.kotoba --target bogus --output q.kexe'
  'H:compile d.kotoba --target aarch64-macos --output q.kexe'
  'H:compile --target aarch64-macos x.kotoba --output q.kexe'
  'H:compile x.kotoba --target aarch64-macos --output sub/none/q.kexe'
  'H:compile x.kotoba --target aarch64-macos --output q.kexe'
  'H:compile x.kotoba --target aarch64-macos'
  'H:compile x.kotoba --target aarch64-macos --output'
  'H:compile x.kotoba --target aarch64-macos-kotoba-v1 --output q.kexe'
  'H:compile x.kotoba y.kotoba --target aarch64-macos --output q.kexe'
  'H:compile p/app/main.kotoba --source-path p --target aarch64-macos --output pm.kexe'
  'H:compile p/app/main.kotoba --source-path p --unpinned --target aarch64-macos --output pm.kexe'
  'H:compile p/app/main.kotoba --module-lock zz --target aarch64-macos'
  'H:compile r.kotoba --target aarch64-macos --output r.kexe'
  'H:compile f.kotoba --target aarch64-macos --output f.kexe'
  'H:compile p/app/main.kotoba --module-lock zz --blocks bb --target aarch64-macos'
  'H:check'
  'H:check x.txt'
  'H:check x.kotoba'
  'H:check --jvm-free r.kotoba'
  'inspect x.kotoba'
  'extract-native'
  'extract-native nonexist.kexe'
  'extract-native s0.kexe'
  'extract-native s0.kexe --symbol fact --output f.bin'
  'extract-native s0.kexe --symbol nope'
)
# s0.kexe: stage-0's own artifact of x.kotoba (the extract-native cases read it on both sides)
mkdir -p $W/k0; ( cd $W/k0; print -r -- '(ns x) (defn fact [n :i64] :i64 (if (<= n 1) 1 (* n (fact (- n 1))))) (defn main [] :i64 (fact 5))' > x.kotoba
  nice $S0 compile x.kotoba --target aarch64-macos --output ../s0.kexe > /dev/null 2>&1 ) || echo "usage-parity: stage-0 could not compile s0.kexe" >&2
: > $W/usage.tsv
i=0
for c in "${cases[@]}"; do
  i=$((i+1)); D0=$W/$i/s0 D1=$W/$i/amu; mkenv $D0; mkenv $D1
  # oracle: stage-0's in-process CLI; `T:` = stage-0 with `--target aarch64-macos` appended (bin/amu's host default, ADR
  # 0351); `B:` = bin/amu itself under node (its launcher layer only: usage text, --jvm-free; BOOTSTRAP-REFERENCE)
  o=S; cc=$c; case $c in T:*) o=T; cc=${c#T:} ;; B:*) o=B; cc=${c#B:} ;; H:*) o=H; cc=${c#H:} ;; esac
  argv=(${=cc})
  case $o in
    S) ( cd $D0; nice $S0 $argv > ../s0.out 2> ../s0.err; echo $? > ../s0.rc ) ;;
    T) argv=(${argv:#--jvm-free}); ( cd $D0; nice $S0 $argv --target aarch64-macos > ../s0.out 2> ../s0.err; echo $? > ../s0.rc ) ;;
    B) ( cd $D0; node $R/bin/amu $argv > ../s0.out 2> ../s0.err; echo $? > ../s0.rc ) ;;
    H) ( cd $D0; KOTOBA_VERDICT_CACHE=off node $R/bin/amu $argv > ../s0.out 2> ../s0.err; echo $? > ../s0.rc ) ;;
  esac
  ( cd $D1; $A $argv > ../amu.out 2> ../amu.err; echo $? > ../amu.rc )
  ( cd $D0; find . -newer x.kotoba -type f | sort ) > $W/$i/s0.files
  ( cd $D1; find . -newer x.kotoba -type f | sort ) > $W/$i/amu.files
  r0=$(cat $W/$i/s0.rc) r1=$(cat $W/$i/amu.rc)
  cls=SAME; det=""
  [ $r0 = $r1 ] || { cls=DIFF; det="rc $r0/$r1"; }
  if [ $o = H ]; then
    # the product entries against bin/amu: answers as data, refusals by phase and message (answer_cmp.py)
    set -- $(python3 $H/answer_cmp.py $W/$i/s0.out $W/$i/amu.out $W/$i/s0.err $W/$i/amu.err ${D0:A})
    [ "$1" = SAME ] || { cls=DIFF; det="$det stdout($2)"; }
    [ "$3" = DIFF ] && { cls=DIFF; det="$det stderr"; }
    [ $cls = SAME ] && { cmp -s $W/$i/s0.out $W/$i/amu.out && cmp -s $W/$i/s0.err $W/$i/amu.err || cls=SAME-DATA; }
  else
  cmp -s $W/$i/s0.out $W/$i/amu.out || { cls=DIFF; det="$det stdout"; }
  cmp -s $W/$i/s0.err $W/$i/amu.err || { cls=DIFF; det="$det stderr"; }
  fi
  cmp -s $W/$i/s0.files $W/$i/amu.files || { cls=DIFF; det="$det files"; }
  for b in $D0/*.bin(N); do cmp -s $b $D1/${b:t} || { cls=DIFF; det="$det bytes(${b:t})"; }; done
  if [ $o = H ]; then
    # declared differences of the product entries against bin/amu (each holds only in the shape named)
    if [[ $c == *"--source-path p"* ]] && [ $r1 = 65 ] && grep -q ':project-link, :message "project path is not readable"' $W/$i/amu.err; then
      cls=DECLARED; det="$det (no cwd wire 40: a relative project root is refused; bin/amu makes caller paths absolute)"; fi
    if [[ $c == *--module-lock* ]] && [ $r1 = 64 ] && grep -q 'module-lock is not available on the Kotoba route' $W/$i/amu.err; then
      cls=DECLARED; det="$det (named refusal: no module locks on the Kotoba route)"; fi
    if [[ $cc == check* ]] && [ $cls = DIFF ] && [ "$det" = " stdout(:definitions)" ]; then
      cls=DECLARED; det="$det (check-driver's named difference: :definitions is the unavailability marker)"; fi
    if [ $r0 = 64 ] && [ $r1 = 64 ] && grep -q 'has no implementation on the nbb/native route' $W/$i/s0.err \
       && grep -q ':error :usage, :message "error: nbb native path does not cover target' $W/$i/amu.err; then
      cls=DECLARED; det="$det (bin/amu refuses a --target it routes to no compiler with its own launcher line; the image answers nbb.cli's usage refusal, same exit 64)"; fi
    if [ "$cc" = check ] && [ $r0 = 64 ] && [ $r1 = 64 ] && grep -q ':error :usage, :message "missing source input"' $W/$i/amu.err; then
      cls=DECLARED; det="$det (check-driver's Kotoba reading names a missing source 'missing source input'; same phase and exit)"; fi
  fi
  if [[ $c == *r.kotoba* ]] && [ $o != H ] && [ $r0 = $r1 ] && [ $cls = DIFF ]; then cls=DECLARED; det="$det (the seed's refusal line)"; fi
  if [[ $c == inspect* ]] && [ $r1 = 69 ]; then cls=DECLARED; det="$det (a bin/amu command with no native implementation in the image: declared stub naming it)"; fi
  if [ $r1 = 0 ] && [ $o != H ] && [ $cls = SAME ]; then
    for kp in $D1/*.kexe(N); do
      k=${kp:t}; s=$(python3 $H/kexe_check.py seal $kp 2>&1 | tail -1); [[ $s == "seal ok"* ]] || { cls=DIFF; det="$det seal($k): $s"; }
      head -c 30 $kp | grep -q '^{:format :kotoba.kexe/v1' || { cls=DIFF; det="$det format($k)"; }
    done
  fi
  print -r -- "$i	$cls	[$c]	$det" >> $W/usage.tsv
done
cat $W/usage.tsv
echo "usage-parity: $(wc -l < $W/usage.tsv | tr -d ' ') cases: $(cut -f2 $W/usage.tsv | sort | uniq -c | tr -s ' ' | tr '\n' ' ') amu $(shasum -a 256 $A | cut -c1-16) stage-0 $(shasum -a 256 $S0 | cut -c1-16) (BOOTSTRAP-REFERENCE)"
