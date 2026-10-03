#!/bin/zsh
# front-native.sh -- the big frontend's Kotoba-route passes as NATIVE closed guests through the SEED backend (H-F1, agent FRONT,
# 2026-10-03). Reproduces docs/selfhost-front-native-20261003.md.
#
#   front-native.sh <work-dir> ie|ana|e2e [seed.bin]
#
# 1. guest: ie = ie-gen.py over kotoba-sema frontend/infer.cljk + ie-tail.cljk (the six infer passes); ana = guests/ana.cljk
#    (state_ability, row, record_projection); e2e = guests/e2e.cljk (the whole linked frontend: an/analyze). A `main` that reads
#    stdin (:io/read) and writes the entry's answer (:io/write) is appended, as guest-run.sh does.
# 2. KIR: kir-dump.clj on the JVM-built compiler classes (BOOTSTRAP-REFERENCE, build/native-image/work, the pre-ADR-0363
#    lineage the frontend's Kotoba code is written for; the stable native image refuses the guests at its aarch64 admission
#    and, since ADR 0363, at expand.cljk line 149). RAISE=1 for ana/e2e (whole-frontend link).
# 3. slice.py slice ... main (the call closure of main), then `seed compile-kir` and `extract-native` under the C loader only.
#    e2e needs a seed whose M holds 435k KIR tokens: FRONT_SEED=<seed.bin> (the R6A seed's M is 8 Mi words, TOK 131,072
#    records; see CONTRACT-REQUESTS 2026-10-03 FRONT), and its one `decimal-f64-parse` (reader twin, float literals) is
#    replaced by `(option-none-of [:option :f64])` (no seed lowering; a float-literal program is then refused by the guest).
# 4. host cases: ie-host.cljs / ana-record.cljs / e2e-record.cljs (nbb, BOOTSTRAP host) -> native-batch.py, one loader process
#    per batch (FRONT_BATCH, default 200; e2e 1), KEXE_HASHCONS=16 unless FRONT_HC=0, arena marks per process.
# Env: WALL_CP (default /private/tmp/wall-cp-16.txt), WALL_K (default /private/tmp/wt-K-kotoba-lang), KSEMA (kotoba-sema checkout).
emulate -L zsh; setopt pipefail
HERE=${0:A:h}; R=${HERE:h:h}
W=${1:?usage: front-native.sh <work-dir> ie|ana|e2e [seed.bin]}; G=${2:?}; mkdir -p $W; W=${W:A}
SB=${3:-${FRONT_SEED:-$R/build/seed-r6a/seed-1.bin}}; SB=${SB:A}
K=${WALL_K:-/private/tmp/wt-K-kotoba-lang}; CP=$(cat ${WALL_CP:-/private/tmp/wall-cp-16.txt})
KSEMA=${KSEMA:-/Users/junkawasaki/github/kotoba-lang/kotoba-sema}
KR="$(echo "$CP" | tr ':' '\n' | grep '/src$' | tr '\n' ':')$R/src:$K/lang/compat"
JW=$R/build/native-image/work
case $G in
  ie) python3 $HERE/ie-gen.py $KSEMA/src/kotoba/compiler/frontend/infer.cljk $HERE/ie-tail.cljk $W/ie_guest.cljk || exit 1
      src=$W/ie_guest.cljk; entry=ie-diff-run; raise=0;;
  ana) src=$HERE/guests/ana.cljk; entry=ana-run; raise=1;;
  e2e) src=$HERE/guests/e2e.cljk; entry=e2e-run; raise=1;;
  *) echo "front-native: unknown guest $G" >&2; exit 2;;
esac
m=$W/${G}_main.cljk
awk '!d && sub(/:kotoba\/export \[[^]]*\]/, ":kotoba/export [main]") {d=1} {print}' $src > $m
printf '\n(defn main [] :i64\n  (let [text (typed-cap-call :io/read :string :string "")\n        out (%s text)\n        n (typed-cap-call :io/write :string :string out)]\n    0))\n' $entry >> $m
if [ ! -s $W/$G.kir ] || [ $m -nt $W/$G.kir ]; then
  ( ulimit -s 65500; RAISE=$raise GUEST=$m OUT=$W/$G.kir KROOTS=$KR nice java -Xss1g -Xmx6g -cp "$JW/classes:$(cat $JW/classpath.txt)" \
      clojure.main $HERE/kir-dump.clj ) || exit 1
fi
python3 $R/seed/tests/kir/slice.py slice $W/$G.kir $W/$G.main.kir main || exit 1
[ $G = e2e ] && python3 -c "
import sys; p=sys.argv[1]; s=open(p).read(); s=s.replace('(decimal-f64-parse tok)','(option-none-of [:option :f64])'); open(p,'w').write(s)" $W/$G.main.kir
export SEED_BUILD=$W/sb; source $R/scripts/seed/lib.sh
SEED_VECTOR_ITEMS=67108864 SEED_SECONDS=600 KEXE_ARENA_USE=1 seed_run $SB 0 compile-kir $W/$G.main.kir --output $W/$G.kseed || exit 1
off=$(SEED_VECTOR_ITEMS=67108864 seed_run $SB 0 extract-native $W/$G.kseed --symbol main --output $W/$G.bin | sed -n 's/.*:offset \([0-9]*\).*/\1/p')
[ -n "$off" ] || exit 1
cases=$W/$G-cases.txt
if [ ! -s $cases ]; then
  ( cd $R; ulimit -s 65520
    case $G in
      ie) KTEST=$KSEMA/test IE_EXTRA=$HERE/ds-corpus SELFHOST_WALL_DIR=$HERE node --stack-size=56000 node_modules/nbb/cli.js --classpath "$CP:$R/src" \
            $HERE/ie-host.cljs --cases $W/ie-cases-raw.txt && awk '!s[$0]++ && length($0) <= 120000' $W/ie-cases-raw.txt > $cases;;
      ana) DS_TESTS=$KSEMA/test DS_EXTRA=$HERE/ds-corpus OUT=$cases node --stack-size=56000 node_modules/nbb/cli.js --classpath "$CP:$R/src" $HERE/ana-record.cljs;;
      e2e) DS_TESTS=$KSEMA/test OUT=$cases node --stack-size=56000 node_modules/nbb/cli.js --classpath "$CP:$R/src" $HERE/e2e-record.cljs;;
    esac ) || exit 1
fi
bs=${FRONT_BATCH:-200}; [ $G = e2e ] && bs=${FRONT_BATCH:-1}
hc="KEXE_HASHCONS=16"; [ "${FRONT_HC:-1}" = 0 ] && hc=""
echo "front-native $G: load $(sysctl -n vm.loadavg)"
NB_ENV="$hc" NB_MARKS=$W/$G.marks.tsv python3 $HERE/native-batch.py $(seed_loader) $W/$G.bin $off $cases $W/$G.answers.txt $bs
sed 's/ ||.*//' $W/$G.answers.txt | awk '{print $1}' | sort | uniq -c
