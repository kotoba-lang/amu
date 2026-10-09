#!/bin/zsh
# seed/tests/compile-cli/refusals.sh <work-dir> -- the commands, targets, flags and modes nbb.cli's Kotoba reading does
# not serve, run on the guest built by run.sh (<work-dir>/a64cli.bin) and on the HOST ENTRY it twins,
# src/kotoba/compiler/nbb/aarch64_cli.cljk under nbb (BOOTSTRAP-REFERENCE; spawned as bin/amu spawns it, with the locked
# classpath, but without bin/amu's own routing: bin/amu sends `check`, `extract-native` and x86-64 / packaged targets
# to other entries and fills an omitted --target). One row per case in <work-dir>/refusals.tsv:
#   case  host-status  guest-status  guest-phase  guest-message
# The guest must refuse every case by name (a :kotoba.cli-error/v1 report, never a silent fallthrough or an artifact);
# its exit code is the host's code for the refusal's phase (64 usage, 65 refused input, 70 :artifact-target).
emulate -L zsh
H=${0:A:h}; R=${H:h:h:h}
W=${1:?usage: refusals.sh <work-dir>}; W=${W:A}
L=$(cat $W/loader); off=$(cat $W/offset); F=$R/examples/fuel.kotoba; D=$W/refusals; mkdir -p $D
cp=$(cd $R && node node_modules/nbb/cli.js --classpath src scripts/print-classpath.cljk $R | tr '\n' ':')
host() { (cd $R && node --stack-size=4096 node_modules/nbb/cli.js --classpath "src:resources:$cp" \
            src/kotoba/compiler/nbb/aarch64_cli.cljk "$@" < /dev/null); }
guest() { KEXE_COMMAND=1 KEXE_CAP_RESOURCES_35=$R:$W KEXE_STRING_POOL=1073741824 KEXE_PAIRS=67108864 KEXE_VECTORS=67108864 \
            KEXE_VECTOR_ITEMS=134217728 KEXE_HASHCONS=16 KEXE_KGRAPH=1048576 KEXE_CPU_SECONDS=600 KEXE_WALL_SECONDS=900 \
            $L $W/a64cli.bin $off 0 aarch64 3,35,37,38,39 -- "$@" < /dev/null; }
: > $W/refusals.tsv
t() {
  local name=$1; shift; rm -f $D/o.kexe*(N)
  host "$@" > $D/$name.h.out 2> $D/$name.h.err; local hs=$?; rm -f $D/o.kexe*(N)
  guest "$@" > $D/$name.g.out 2> $D/$name.g.err; local gs=$?
  local ge=$(sed -n 's/.*:error \(:[a-z0-9-]*\).*/\1/p' $D/$name.g.err | head -1)
  local gm=$(sed -n 's/.*:message "\(.*\)"}$/\1/p' $D/$name.g.err | head -1)
  [ -e $D/o.kexe ] && gm="WROTE AN ARTIFACT: $gm"
  printf '%s\t%s\t%s\t%s\t%s\n' $name $hs $gs "${ge:--}" "$gm" >> $W/refusals.tsv
}
t no-command
t command-check check $F
t command-extract-native extract-native $D/o.kexe
t target-missing compile $F --output $D/o.kexe
t target-unknown compile $F --target sparc --output $D/o.kexe
t target-x86_64-macos compile $F --target x86_64-macos --output $D/o.kexe
t target-x86_64-linux-static compile $F --target x86_64-linux-static --output $D/o.kexe
t target-aarch64 compile $F --target aarch64 --output $D/o.kexe
t target-aarch64-linux compile $F --target aarch64-linux --output $D/o.kexe
t target-aarch64-linux-static compile $F --target aarch64-linux-static --output $D/o.kexe
t target-aarch64-aiueos-kernel compile $F --target aarch64-aiueos-kernel-v1 --output $D/o.kexe
t artifact-object compile $F --target aarch64-macos --artifact object --output $D/o.kexe
t artifact-bogus compile $F --target aarch64-macos --artifact bogus --output $D/o.kexe
t backend-seed compile $F --target aarch64-macos --backend seed --output $D/o.kexe
t module-lock compile $F --target aarch64-macos --module-lock $D/x.edn --blocks $D --output $D/o.kexe
t package-lock compile $F --target aarch64-macos --package-lock $D/x.edn --packages $D --output $D/o.kexe
t worker worker --target aarch64-macos
t fuel-not-decimal compile $F --target aarch64-macos --fuel abc --output $D/o.kexe
t fuel-metered-5000 compile $F --target aarch64-macos --fuel 5000 --output $D/o.kexe
t source-missing compile --target aarch64-macos
t source-extension compile $R/README.md --target aarch64-macos --output $D/o.kexe
t source-absent compile $R/no-such-file.kotoba --target aarch64-macos --output $D/o.kexe
column -t -s$'\t' $W/refusals.tsv | cut -c1-200
