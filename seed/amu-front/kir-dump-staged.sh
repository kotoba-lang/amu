#!/bin/zsh
# seed/amu-front/kir-dump-staged.sh <work> <kotoba-sema checkout> <ksema rev> -- KIR of seed/amu-front/check.cljk over the
# ADR-0363 lineage of kotoba-sema (HEAD 15e45a3 and its descendants). BOOTSTRAP-REFERENCE (JVM, build time only).
# Why: build.sh's kir-dump step runs on the Oct-2 AOT classes of build/native-image/work (pre-ADR-0363 sema), which reject the
# 0363 frontend ("call to aborting function `normalize-effect-ceiling` in a function that neither catches it nor aborts ..."),
# measured with kotoba-sema 15e45a3 and 1d1eb1a. Here every directory of the wall classpath is staged from the CURRENT
# sources (scripts/build-native-image.py stage_directory), kotoba-sema replaced by the given checkout, and run from source
# (no AOT classes). Then: AF_KSEMA_REV=<rev> seed/amu-front/build.sh <work> reuses <work>/check.kir.
# Agent MERGE, 2026-10-04.
emulate -L zsh; setopt pipefail
H=${0:A:h}; R=${H:h:h}; W=${1:?work}; mkdir -p $W; W=${W:A}; SEMA=${2:?sema checkout}; REV=${3:?rev}
K=${WALL_K:-/private/tmp/wt-K-kotoba-lang}; CPF=${WALL_CP:-/private/tmp/wall-cp-16.txt}; CP=$(cat $CPF)
KS=$W/ksema-$REV; [ -d $KS/src ] || { mkdir -p $KS; git -C ${AF_KSEMA:-/Users/junkawasaki/github/kotoba-lang/kotoba-sema} archive $REV src resources | tar -x -C $KS || exit 1; }
(cd $R && python3 - $W/jstage $CPF $SEMA <<'P'
import importlib.util, os, shutil, sys
from pathlib import Path
s = importlib.util.spec_from_file_location('bni', 'scripts/build-native-image.py'); m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
out = Path(sys.argv[1]); shutil.rmtree(out, ignore_errors=True); out.mkdir(parents=True)
cp = [e.replace('/Users/junkawasaki/github/kotoba-lang/kotoba-sema/', sys.argv[3].rstrip('/') + '/') for e in open(sys.argv[2]).read().strip().split(':') if e]
ents = []
for i, e in enumerate(cp):
    src = (Path.cwd() / e).resolve() if not os.path.isabs(e) else Path(e)
    if src.is_dir():
        d = out / ('%03d' % i); m.stage_directory(src, d); ents.append(str(d))
    else: ents.append(str(src))
(out.parent / 'jstage-cp.txt').write_text(':'.join(ents))
P
) || exit 1
KR="$(echo "$CP" | tr ':' '\n' | grep '/src$' | grep -v '/kotoba-sema/src$' | tr '\n' ':')$KS/src:$R/src:$K/lang/compat"
( ulimit -s 65500; RAISE=1 GUEST=$H/check.cljk OUT=$W/check.kir KROOTS=$KR nice java -Xss1g -Xmx6g -cp "$(cat $W/jstage-cp.txt)" \
    clojure.main $R/scripts/selfhost-wall/kir-dump.clj ) > $W/kir-dump.log 2>&1 || { tail -5 $W/kir-dump.log; exit 1; }
tail -2 $W/kir-dump.log
