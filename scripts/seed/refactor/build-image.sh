#!/bin/zsh
# scripts/seed/refactor/build-image.sh <out-dir> [kotoba-lang] -- the whole amu.main entry (seed/amu-main, route s as
# build.sh assembles it: HEAD's seed split + patch-split, src + s + l/compile) with `amu refactor` switched to the
# Kotoba-route dispatcher (src/amu/refactor.kotoba replaced by the one-line delegate to amu.refactor-cli) and the
# kotoba-lang compat root on the source path. Compiled by the seed (RF_SEED, lib.sh); no stage-0, JVM or node.
# Output <out-dir>/amu.{kseed,bin,offset}; scripts/seed/refactor/all.sh <out-dir>/amu runs every differential on it.
# Agent REFAC, 2026-10-04 (until CMD's build.sh takes the compat root: seed/CONTRACT-REQUESTS.md REFAC -> CMD).
emulate -L zsh; setopt pipefail
H=${0:A:h}; R=${H:h:h:h}; W=${1:A}; K=${2:-/private/tmp/wt-K-port-kotoba-lang}; K=${K:A}
M=$R/seed/amu-main
rm -rf $W; mkdir -p $W/tree $W/am
git -C $R archive HEAD seed/split seed/MANIFEST seed/*.kotoba | tar -x -C $W/tree || exit 1
python3 $W/tree/seed/split/gen-split.py --check || exit 1
python3 $M/patch-split.py $W/tree/seed/split || exit 1
cp -R $M/src $M/s $W/am/
[ -f $M/l/amu/compile.kotoba ] && cp $M/l/amu/compile.kotoba $W/am/s/amu/compile.kotoba
cat > $W/am/src/amu/refactor.kotoba <<'EOK'
(ns amu.refactor
  {:kotoba/export [run]}
  (:require [amu.refactor-cli :as rc]))

;; `amu refactor`: the Kotoba-route dispatcher amu.refactor-cli (scripts/seed/refactor/build-image.sh delegate)
(defn run [] :i64 (rc/run))
EOK
source $H/lib.sh
RF_SECONDS=1800 rf_compile $W/am/src/amu/main.kotoba $W/amu $W/am/src $W/am/s $W/tree/seed/split $K/lang/compat || exit 1
echo "image $W/amu.bin $(wc -c < $W/amu.bin | tr -d ' ') B sha256 $(shasum -a 256 $W/amu.bin | cut -c1-16) seed $(shasum -a 256 $RF_SEED | cut -c1-8) kotoba-lang $(git -C $K rev-parse --short HEAD)"
