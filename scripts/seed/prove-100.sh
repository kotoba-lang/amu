#!/bin/zsh
# scripts/seed/prove-100.sh [AMU] [work-dir] -- test every clause of the selfhost 100% definition on one native `amu`
# image and print PASS / FAIL per clause with its evidence (agent PROVE, 2026-10-06). BOOTSTRAP-TOOL (zsh, python3, cc);
# stage-0 (build/native-image/amu-native, JVM-built BOOTSTRAP-REFERENCE) and bin/amu (node + nbb) run only as ORACLES, in
# their own processes, never in AMU's process tree. No seed source is edited.
#
# The definition (docs/selfhost-priority.md rules 8-11, docs/selfhost-status-20261005.md section 1): the `amu` binary
# built by `amu` itself runs the full `check`, `refactor` and `compile` on its own sources with zero node/JVM/nbb
# processes; stubs never count; plus the seed gates G1-G5 and the owner's Embench and fixed-point requirements.
#
#   C1  SELF-BUILT     AMU rebuilds its own code (seed split, amu.*, refactor library: every compile, modules, link and
#                      extract-native) with scripts/seed/launcher/build.sh --builder AMU -> U1; U1 rebuilds -> U2.
#                      PASS: U1 == U2 byte for byte, every builder process loaded the exec interposer and logged no
#                      exec/spawn/system/popen, and the build ran with a PATH holding no node/java/nbb/bb/clojure.
#   C2  FRONT-SELF     the frontend objects (kotoba.sema, kotoba.form, ...) inside AMU were compiled by an amu image.
#                      build.sh copies them from --front (they were written by a seed binary): PASS only when the image's
#                      amu.info names an amu builder for the front directory (never true today; not rebuilt here).
#   C3  CHECK-OWN      AMU `check` over (a) its own Kotoba sources (amu-main, seed split, refactor library, amu-front)
#                      and (b) the product module closure (scripts/seed/reach-twins.py farm, the selfbuild list) with
#                      absolute --source-path; stage-0 runs the same command as oracle. PASS: exit status and verdict
#                      line equal on every file, 0 traps (status >= 128), 0 stub exits (69).
#   C4  COMPILE-OWN    AMU `compile` + `extract-native` of the seed unity at tag seed-<rung> == that rung's recorded
#                      seed1_sha256 (its fixed point), plus C1's compiles of its own modules.
#   C5  REFACTOR-OWN   AMU `refactor graph` and `refactor plan all` over the farm of (b); bin/amu (node) as oracle.
#                      PASS: stdout and exit equal on every file, 0 traps, 0 stubs.
#   C6  NO-HOST        every AMU run of C3-C5 and C7 under the exec interposer (canary-verified), env -i, empty PATH:
#                      loads == runs, 0 exec/posix_spawn/system/popen; otool -L only /usr/lib; baked wires without 20.
#   C7  NO-STUBS       the documented options of check / compile / refactor answer without a declared stub (69):
#                      probes check --json / --package-lock / relative --source-path, the module-lock command, compile --module-lock,
#                      refactor verify --runner.
#   C8  FIXED-POINT    the rung's recorded seed recompiles the unity of tag seed-<rung> (clean archive) to itself.
#   C9  GATES G1-G5    scripts/seed/gates.sh --rung <rung> on a clean archive of tag seed-<rung>, BUILD by the
#                      lineage route (bootstrap.sh --no-head from the committed R0 seed), G1 G2 G3 G4 G5 all PASS.
#   C10 EMBENCH        scripts/seed/launcher/test.sh AMU: L2 = the 19 ports compiled by AMU, every correctness export
#                      BEHAVIOUR-SAME as stage-0's, 19 seals; L1 / L3 / L4 reported alongside.
#   C11 PRODUCT        the product command is the self-built binary: bin/amu is not a node/nbb launcher, and the
#                      product entries (nbb check-cli, aarch64-cli) have a Kotoba main.
# Env: PROVE_ONLY=C1,C3 (subset), PROVE_RUNG (default r6m), PROVE_K (kotoba-lang for the farm, /private/tmp/wt-K-kotoba-lang),
#      PROVE_RK (refactor library checkout; default: the one AMU's amu.info names). Output: <work>/summary.tsv + logs.
# Exit 0 only when every clause that ran is PASS. Timings on a loaded host are not results.
emulate -L zsh; setopt pipefail nullglob
renice -n 10 $$ > /dev/null 2>&1
H=${0:A:h}; R=${H:h:h}
A=${1:-$R/build/checkfull/unified/amu}; A=${A:A}
W=${2:-$R/build/prove}; mkdir -p $W; W=${W:A}
RUNG=${PROVE_RUNG:-r6m}; S0=$R/build/native-image/amu-native
K=${PROVE_K:-/private/tmp/wt-K-kotoba-lang}
GIT=/Users/junkawasaki/github/kotoba-lang/amu-measure; [ -d $R/.git ] || [ -f $R/.git ] && GIT=$R
sha() { shasum -a 256 $1 | cut -c1-64; }
want() { [ -z "$PROVE_ONLY" ] || [[ ",$PROVE_ONLY," == *",$1,"* ]]; }
: > $W/summary.tsv
row() { printf '%s\t%s\t%s\n' "$1" "$2" "$3" >> $W/summary.tsv; printf '%-4s %-4s %s\n' "$1" "$2" "$3"; }
load() { sysctl -n vm.loadavg | awk '{print $2}'; }
[ -x $A ] || { echo "prove-100: no image $A" >&2; exit 2; }
INFO=${A:h}/amu.info
echo "prove-100: image $A sha256 $(sha $A | cut -c1-16) bytes $(wc -c < $A | tr -d ' '), rung $RUNG, load $(load), $(date '+%F %T')"
[ -f $INFO ] && sed -n '1p;/^compiler/p;/^tree/p;/^front/p' $INFO | cut -c1-200 | sed 's/^/  info: /'

# ---- the exec interposer (scripts/seed/no-host-processes.sh's C source), canary-verified
NP=$W/noproc; mkdir -p $NP $W/empty-path
src=$R/build/seed/noproc/noproc.c
[ -f $src ] || { zsh $R/scripts/seed/no-host-processes.sh > $W/noproc-build.log 2>&1; }
cp $R/build/seed/noproc/noproc.c $R/build/seed/noproc/canary.c $NP/ 2>/dev/null
cc -O1 -dynamiclib $NP/noproc.c -o $NP/noproc.dylib 2> $NP/cc.log && cc -O1 $NP/canary.c -o $NP/canary 2>> $NP/cc.log \
  || { echo "prove-100: cannot build the interposer" >&2; exit 2; }
rm -f $NP/canary.log; NOPROC_LOG=$NP/canary.log DYLD_INSERT_LIBRARIES=$NP/noproc.dylib $NP/canary
ccalls=$(awk '$2 != "loaded"' $NP/canary.log 2>/dev/null | wc -l | tr -d ' ')
[ "$ccalls" -ge 3 ] || { echo "prove-100: interposer missed the canary ($ccalls calls): fail closed" >&2; exit 2; }
echo "  interposer: canary caught $ccalls calls ($(awk '$2 != "loaded" {printf "%s ", $2}' $NP/canary.log))"
LG=$W/noproc.log; : > $LG; : > $W/runs.tsv
# nr <tag> <out> <args..> : AMU under the interposer, env -i, empty PATH; appends "tag status args" to runs.tsv
nr() {
  local tag=$1 out=$2; shift 2
  env -i PATH=$W/empty-path HOME=$HOME TMPDIR=/tmp NOPROC_LOG=$LG DYLD_INSERT_LIBRARIES=$NP/noproc.dylib $A "$@" > $out 2>&1
  local st=$?; printf '%s\t%s\t%s\n' "$tag" "$st" "$*" >> $W/runs.tsv; return $st
}
s0() { (source $R/scripts/seed/lib.sh; seed_slot_take; trap seed_slot_give EXIT; ulimit -s 65500 2>/dev/null; nice $S0 "$@"); }
# verdict <out> <root>: first line, paths cut to basenames, the members of every #{...} sorted (set order is not meaning)
verdict() { head -1 $1 | sed -E "s#$2/##g; s#(at|in) [^ ]*/#\1 #g" | python3 -c 'import re,sys
l=sys.stdin.read().rstrip("\n")
def srt(m):
    b=m.group(1); parts=re.findall(r"\[[^\]]*\]|[^ \[\]]+", b); return "#{"+" ".join(sorted(parts))+"}"
print(re.sub(r"#\{([^}]*)\}", srt, l))'; }

# ---------------------------------------------------------------- C1 SELF-BUILT
if want C1; then
  C=$W/c1; rm -rf $C; mkdir -p $C/bin
  for t in zsh sh git tar python3 cc cp rm mkdir cat sed awk grep wc tr cut shasum sysctl xxd mv otool ls env head tail \
           dirname basename sort uniq paste perl seq date mktemp touch cmp strings xcrun; do
    p=$(command -v $t) && ln -sf $p $C/bin/$t
  done
  bad=""; for t in node nodejs npx nbb bb java javac clojure clj lein; do PATH=$C/bin command -v $t > /dev/null 2>&1 && bad+="$t "; done
  front=$(sed -n 's/^front \([^ ]*\) .*/\1/p' $INFO); rk=${PROVE_RK:-$(sed -n 's/.*Kotoba route amu.refactor-cli + \([^ ]*\)\/lang\/compat.*/\1/p' $INFO | head -1)}
  mkb() {  # mkb <real> <wrapper> : the builder under the interposer (zsh sets DYLD_* after its own start, so it reaches AMU)
    print -r -- "#!/bin/zsh
exec env NOPROC_LOG=$C/builder.log DYLD_INSERT_LIBRARIES=$NP/noproc.dylib $1 \"\$@\"" > $2; chmod +x $2; }
  cp $A $C/u0; mkb $C/u0 $C/b0
  ok=1
  PATH=$C/bin LAUNCHER_REFACTOR=$rk zsh $R/scripts/seed/launcher/build.sh --front $front --builder $C/b0 $C/g1 > $C/g1.out 2>&1 || ok=0
  if [ $ok = 1 ]; then cp $C/g1/amu $C/u1; mkb $C/u1 $C/b1
    PATH=$C/bin LAUNCHER_REFACTOR=$rk zsh $R/scripts/seed/launcher/build.sh --front $front --builder $C/b1 $C/g2 > $C/g2.out 2>&1 || ok=0; fi
  bl=$(awk '$2 == "loaded"' $C/builder.log 2>/dev/null | wc -l | tr -d ' ')
  bx=$(awk '$2 != "loaded" && $2 != "fork"' $C/builder.log 2>/dev/null | wc -l | tr -d ' ')
  bf=$(awk '$2 == "fork"' $C/builder.log 2>/dev/null | wc -l | tr -d ' ')
  if [ $ok = 1 ]; then
    h0=$(sha $A | cut -c1-8); h1=$(sha $C/g1/amu | cut -c1-8); h2=$(sha $C/g2/amu | cut -c1-8)
    ev="U0 $h0 -> U1 $h1 -> U2 $h2 ($(wc -c < $C/g2/amu | tr -d ' ') B; U1==U0: $([ $h0 = $h1 ] && echo yes || echo no)); objects by the builder: $(ls $C/g2/o/*.kso | wc -l | tr -d ' ') of which $(sed -n 's/^front .* \([0-9]*\) objects.*/\1/p' $C/g2/amu.info) frontend copied; builder runs $bl, exec/spawn $bx, forks $bf; PATH without node/java/nbb: ${bad:-yes}; glue zsh+python3+cc(loader)"
    [ "$h1" = "$h2" ] && [ $bx = 0 ] && [ -z "$bad" ] && [ $bl -gt 0 ] && row C1 PASS "$ev" || row C1 FAIL "$ev"
  else row C1 FAIL "build failed: $(grep -h 'FAIL' $C/g1.out $C/g2.out 2>/dev/null | head -2 | tr '\n' ' ' | cut -c1-200)"; fi
fi

# ---------------------------------------------------------------- C2 FRONT-SELF
if want C2; then
  fr=$(sed -n 's/^front \([^ ]*\) \([0-9]*\) objects.*/\1 (\2 objects)/p' $INFO)
  if [ -f ${fr%% *}/amu.info ] && grep -q '^compiler builder' ${fr%% *}/amu.info; then row C2 PASS "front $fr built by $(sed -n 's/^compiler builder \([^ ]*\).*/\1/p' ${fr%% *}/amu.info)"
  else row C2 FAIL "front $fr: written by a seed binary (amu.info: $(sed -n 's/^compiler //p' $INFO | cut -c1-60); WALL2 graph-run / CHECKFULL chain), not by an amu image; build.sh copies it, so C1 does not rebuild it"; fi
fi

# ---------------------------------------------------------------- farm for C3b / C5 (selfbuild's product closure)
# FARM = one source root holding the product closure: a fresh reach-twins + r6_scan farm of the current checkouts, or,
# when that cannot be made (a checkout on the classpath lost files), the newest recorded selfbuild farm (PROVE_FARM),
# labelled with its provenance line.
FARM=""; FARMSRC=""
farm() {
  [ -n "$FARM" ] && return 0
  rm -rf $W/farm; mkdir -p $W/farm
  if python3 $R/scripts/seed/reach-twins.py ${R6_REACH:-/private/tmp/reach-minimal.txt} ${WALL_CP:-/private/tmp/wall-cp-16.txt} $R $K > $W/farm/list.txt 2> $W/farm/list.err \
    && python3 $R/scripts/seed/r6_scan.py farm $W/farm/list.txt $W/farm > $W/farm/order.txt 2> $W/farm/external.txt; then
    FARM=$W/farm/src; FARMSRC="fresh farm of HEAD + classpath"
  else
    FARM=${PROVE_FARM:-$R/build/selfbuild-run/r6/src}
    FARMSRC="recorded farm ${FARM#$R/} ($(sed -n 2p ${FARM:h:h}/provenance.txt 2>/dev/null); fresh farm failed: $(tail -1 $W/farm/list.err | cut -c1-90))"
  fi
  echo "  farm: $FARMSRC, $(ls $FARM/**/*.(cljk|kotoba|cljc)(N) | wc -l | tr -d ' ') files"
}

# ---------------------------------------------------------------- C3 CHECK-OWN
if want C3; then
  C=$W/c3; rm -rf $C; mkdir -p $C/a $C/b
  T=$C/tree; mkdir -p $T; git -C $GIT archive HEAD seed | tar -x -C $T; python3 $T/seed/split/gen-split.py > /dev/null 2>&1
  : > $C/files.tsv
  for f in $T/seed/amu-main/src/amu/*.kotoba; do print -r -- "a	$f	$T/seed/amu-main/src" >> $C/files.tsv; done
  for f in $T/seed/amu-main/k/amu/*.kotoba $T/seed/amu-main/l/amu/*.kotoba; do print -r -- "a	$f	$T/seed/amu-main/src" >> $C/files.tsv; done
  for f in $T/seed/split/**/*.kotoba; do print -r -- "a	$f	$T/seed/split" >> $C/files.tsv; done
  rk=${PROVE_RK:-$(sed -n 's/.*Kotoba route amu.refactor-cli + \([^ ]*\)\/lang\/compat.*/\1/p' $INFO | head -1)}
  for f in $rk/lang/compat/kotoba/compiler/refactor/*.kotoba(N); do print -r -- "a	$f	$rk/lang/compat" >> $C/files.tsv; done
  farm; for f in $FARM/**/*.(cljk|kotoba|cljc)(N); do print -r -- "b	$f	$FARM" >> $C/files.tsv; done
  same=0; diff=0; trap_=0; stub=0; n=0; aok=0; bok=0; : > $C/result.tsv
  while IFS=$'\t' read set f sp; do
    n=$((n + 1)); o=$C/$set/$n
    nr C3 $o.amu check $f --source-path $sp < /dev/null; st=$?
    s0 check $f --source-path $sp > $o.s0 2>&1 < /dev/null; ss=$?
    va=$(verdict $o.amu $sp); vs=$(verdict $o.s0 $sp)
    [ $st -ge 128 ] && trap_=$((trap_ + 1)); [ $st = 69 ] && stub=$((stub + 1))
    [ $st = 0 ] && { [ $set = a ] && aok=$((aok + 1)) || bok=$((bok + 1)); }
    if [ $st = $ss ] && [ "$va" = "$vs" ]; then same=$((same + 1)); c=SAME; else diff=$((diff + 1)); c=DIFF; fi
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' $c $set $st $ss "${f#$T/}" "$va" "$vs" >> $C/result.tsv
  done < $C/files.tsv
  na=$(grep -c '^a' $C/files.tsv); nb=$(grep -c '^b' $C/files.tsv)
  ev="$n files [$FARMSRC] ($na own Kotoba sources: $aok ok; $nb product-closure farm: $bok ok): $same SAME as stage-0 (exit + verdict), $diff DIFF, $trap_ traps, $stub stubs"
  [ $diff = 0 ] && [ $trap_ = 0 ] && [ $stub = 0 ] && [ $nb -gt 0 ] && row C3 PASS "$ev" || row C3 FAIL "$ev"
fi

# ---------------------------------------------------------------- C4 COMPILE-OWN
if want C4; then
  C=$W/c4; rm -rf $C; mkdir -p $C/t
  git -C $GIT archive seed-$RUNG seed | tar -x -C $C/t
  { for p in $(grep -v '^[[:space:]]*#' $C/t/seed/MANIFEST | grep -v '^[[:space:]]*$' | sed 's/[[:space:]].*//'); do cat $C/t/$p; printf '\n'; done } > $C/unity.kotoba
  us=$(sha $C/unity.kotoba); want_u=$(sed -n 's/^unity_sha256 //p' $R/seed/rungs/$RUNG.record); want_s=$(sed -n 's/^seed1_sha256 //p' $R/seed/rungs/$RUNG.record)
  nr C4 $C/compile.out compile $C/unity.kotoba --target aarch64-macos --output $C/self.kseed; st=$?
  nr C4 $C/extract.out extract-native $C/self.kseed --symbol main --output $C/self.bin; sx=$?
  got=$( [ -s $C/self.bin ] && sha $C/self.bin )
  ev="unity of tag seed-$RUNG ${us:0:8} (record ${want_u:0:8}); AMU compile status $st, extract $sx; AMU's main ${got:0:8} vs recorded seed1 ${want_s:0:8} ($(wc -c < $C/self.bin 2>/dev/null | tr -d ' ') B)"
  [ $st = 0 ] && [ $sx = 0 ] && [ "$got" = "$want_s" ] && [ "$us" = "$want_u" ] && row C4 PASS "$ev; plus C1's module compiles" || row C4 FAIL "$ev $(grep -m1 -E 'error|E[0-9]{4}' $C/compile.out | cut -c1-100)"
fi

# ---------------------------------------------------------------- C5 REFACTOR-OWN
if want C5; then
  C=$W/c5; rm -rf $C; mkdir -p $C; farm
  same=0; diff=0; trap_=0; stub=0; n=0; : > $C/result.tsv
  for f in $FARM/**/*.(cljk|kotoba|cljc)(N); do
    for sub in "graph" "plan all"; do
      n=$((n + 1)); o=$C/$n
      nr C5 $o.amu refactor ${=sub} $f < /dev/null; st=$?
      (cd $R && bin/amu refactor ${=sub} $f > $o.host 2>&1 < /dev/null); sh=$?
      [ $st -ge 128 ] && trap_=$((trap_ + 1)); [ $st = 69 ] && stub=$((stub + 1))
      if [ $st = $sh ] && cmp -s $o.amu $o.host; then same=$((same + 1)); c=SAME; else diff=$((diff + 1)); c=DIFF; fi
      printf '%s\t%s\t%s\t%s\t%s\n' $c $st $sh "$sub" "${f#$FARM/}" >> $C/result.tsv
    done
  done
  ev="$n runs (graph + plan all over $((n / 2)) product-closure files) [$FARMSRC]: $same SAME as bin/amu (stdout + exit), $diff DIFF, $trap_ traps, $stub stubs"
  [ $diff = 0 ] && [ $trap_ = 0 ] && [ $stub = 0 ] && [ $n -gt 0 ] && row C5 PASS "$ev" || row C5 FAIL "$ev"
fi

# ---------------------------------------------------------------- C7 NO-STUBS (probes; before C6 so they are traced too)
if want C7; then
  C=$W/c7; rm -rf $C; mkdir -p $C/p/src/p
  print -r -- '(ns p.main) (defn main [] :i64 0)' > $C/p/src/p/main.kotoba
  print -r -- '(ns x) (defn main [] :i64 0)' > $C/x.kotoba
  : > $C/result.tsv; ns=0; np=0
  probe() { local nm=$1; shift; np=$((np + 1)); (cd $C; nr C7 $C/$nm.out "$@" < /dev/null); local st=$?
    [ $st = 69 ] && ns=$((ns + 1)); printf '%s\t%s\n' "$nm" "$st" >> $C/result.tsv; }
  probe check-json check $C/x.kotoba --json
  probe module-lock-command module-lock $C/p/src/p/main.kotoba --source-path $C/p/src
  probe check-package-lock check $C/x.kotoba --package-lock $C/none.edn
  probe check-relative-source-path check p/src/p/main.kotoba --source-path p/src
  probe refactor-verify refactor verify --runner $C/x.kotoba --classpath $C
  mkdir -p $C/blocks; probe compile-module-lock compile $C/x.kotoba --module-lock $C/none.edn --blocks $C/blocks --output $C/x.kexe
  ev="$ns of $np probes answer a declared stub (69): $(awk -F'\t' '$2 == 69 {printf "%s ", $1}' $C/result.tsv)"
  [ $ns = 0 ] && row C7 PASS "$ev" || row C7 FAIL "$ev"
fi

# ---------------------------------------------------------------- C6 NO-HOST
if want C6; then
  runs=$(wc -l < $W/runs.tsv | tr -d ' '); loads=$(awk '$2 == "loaded"' $LG | wc -l | tr -d ' ')
  ex=$(awk '$2 != "loaded" && $2 != "fork"' $LG | wc -l | tr -d ' '); fk=$(awk '$2 == "fork"' $LG | wc -l | tr -d ' ')
  deps=$(otool -L $A | tail -n +2 | awk '{print $1}' | tr '\n' ' ')
  allow=$(sed -n 's/^allow \([0-9,]*\).*/\1/p' $INFO)
  nonsys=$(echo $deps | tr ' ' '\n' | grep -v '^$' | grep -vc '^/usr/lib/')
  ev="$runs AMU runs traced (C3-C5,C7), interposer loaded $loads, exec/spawn/system/popen $ex, supervisor forks $fk; otool -L: $deps; wires $allow"
  [ $runs -gt 0 ] && [ $loads -ge $runs ] && [ $ex = 0 ] && [ $nonsys = 0 ] && [[ ",$allow," != *",20,"* ]] && row C6 PASS "$ev" || row C6 FAIL "$ev"
fi

# ---------------------------------------------------------------- C8 FIXED-POINT
if want C8; then
  C=$W/c8; rm -rf $C; mkdir -p $C/t
  SB=""; for c in $R/build/seed-boot/$RUNG/seed-1.bin $R/build/image/seed-$RUNG.bin $R/build/rebuild/seed-$RUNG.bin; do [ -s $c ] && SB=$c && break; done
  want_s=$(sed -n 's/^seed1_sha256 //p' $R/seed/rungs/$RUNG.record)
  if [ -n "$SB" ] && [ "$(sha $SB)" = "$want_s" ]; then
    git -C $GIT archive seed-$RUNG seed | tar -x -C $C/t
    { for p in $(grep -v '^[[:space:]]*#' $C/t/seed/MANIFEST | grep -v '^[[:space:]]*$' | sed 's/[[:space:]].*//'); do cat $C/t/$p; printf '\n'; done } > $C/unity.kotoba
    ( export SEED_REPO=$R SEED_BUILD=$C/sb SEED_PAIRS=16777216 SEED_SECONDS=1800; source $R/scripts/seed/lib.sh
      seed_run $SB 0 compile $C/unity.kotoba --target aarch64-macos --output $C/s2.kseed > $C/s2.log 2>&1 &&
      seed_run $SB 0 extract-native $C/s2.kseed --symbol main --output $C/s2.bin >> $C/s2.log 2>&1 )
    got=$( [ -s $C/s2.bin ] && sha $C/s2.bin )
    ev="seed $RUNG ${want_s:0:8} ($SB) compiles tag seed-$RUNG's unity -> ${got:0:8}"
    [ "$got" = "$want_s" ] && row C8 PASS "$ev (byte-identical)" || row C8 FAIL "$ev"
  else row C8 FAIL "no seed binary matching seed/rungs/$RUNG.record"; fi
fi

# ---------------------------------------------------------------- C9 GATES G1-G5
if want C9; then
  C=$W/c9; rm -rf $C; mkdir -p $C/tree
  git -C $GIT archive seed-$RUNG | tar -x -C $C/tree
  ( cd $C/tree; export SEED_REPO=$C/tree SEED_BUILD=$C/tree/build/seed SEED_STAGE0=$S0
    nice zsh scripts/seed/build.sh lineage > $C/build.log 2>&1 && nice zsh scripts/seed/gates.sh --rung $RUNG --no-build --only BUILD,G1,G2,G3,G4,G5 > $C/gates.log 2>&1 )
  st=$C/tree/build/seed/gates/$RUNG/summary.tsv
  if [ -s $st ]; then
    ev=$(awk -F'\t' '{printf "%s %s; ", $1, $2}' $st)
    [ $(awk -F'\t' '$1 ~ /^(G1|G2|G3|G4|G5)$/ && $2 == "PASS"' $st | wc -l | tr -d ' ') = 5 ] && row C9 PASS "clean archive of seed-$RUNG, lineage build: $ev" || row C9 FAIL "$ev"
  else row C9 FAIL "lineage build or gates did not run: $(tail -2 $C/build.log | tr '\n' ' ' | cut -c1-200)"; fi
fi

# ---------------------------------------------------------------- C10 EMBENCH
if want C10; then
  C=$W/c10; zsh $R/scripts/seed/launcher/test.sh $A $C > $W/c10.out 2>&1
  l2=$(grep -E '^(PASS|FAIL) L2' $W/c10.out); oth=$(grep -E '^(PASS|FAIL) L[134]' $W/c10.out | cut -c1-6 | tr '\n' ' ')
  [[ "$l2" == PASS* ]] && row C10 PASS "${l2#PASS }; $oth" || row C10 FAIL "${l2:-no L2 line}; $oth"
fi

# ---------------------------------------------------------------- C11 PRODUCT
if want C11; then
  b=$(head -1 $R/bin/amu); m=""
  for e in check_cli aarch64_cli; do
    f=$(ls $R/src/kotoba/compiler/nbb/$e.clj* 2>/dev/null | head -1)
    [ -n "$f" ] && grep -qE '^\(defn main\b' $f && m+="$e:main " || m+="$e:no-main "
  done
  ev="bin/amu starts with '$b'; product entries $m"
  [[ "$b" != *node* ]] && [[ "$b" != *nbb* ]] && [[ "$m" != *no-main* ]] && row C11 PASS "$ev" || row C11 FAIL "$ev"
fi

echo "prove-100: $(grep -c '	PASS	' $W/summary.tsv) PASS, $(grep -c '	FAIL	' $W/summary.tsv) FAIL of $(wc -l < $W/summary.tsv | tr -d ' ') clauses (load $(load)); summary $W/summary.tsv"
! grep -q '	FAIL	' $W/summary.tsv
