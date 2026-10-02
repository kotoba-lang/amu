#!/bin/zsh
# usage: nbbc.sh src.kotoba out.kexe
cd /private/tmp/wt-A-amu-measure; export WALL_K=/private/tmp/wt-K-kotoba-lang; AMU=$PWD; CP="$(cat /private/tmp/t23/cp.txt):$AMU/src"; SP=(); for d in ${(f)"$(tr ':' '\n' < /private/tmp/t23/cp.txt | grep '/src$')"} $AMU/src $WALL_K/lang/compat; do SP+=(--source-path $d); done; ulimit -s 65520
nice node --stack-size=56000 node_modules/nbb/cli.js --classpath "$CP" src/kotoba/compiler/nbb/aarch64_cli.cljk compile $1 --target aarch64-macos --jvm-free --policy /private/tmp/t23/policy.edn --output $2 $SP 2>&1 | cut -c1-500
