#!/bin/zsh
# bytes-cap.sh: the :bytes payload of the file wire (fs/app-data-bytes, wire 35) on the native backend, end to end.
# Compiles bytes-cap/probe.cljk (write 5 raw bytes incl. non-UTF-8, read the file, read a RANGE window) with the amu
# native backend (aarch64-macos), extracts it and runs it on tools/kexe_loader.c built from this checkout.
# Expected stdout "n=503255" = 100000 * 5 (bytes read) + 1000 * 3 (window) + 255 (second byte); the file must hold
# 00 ff 80 0a c8. Then two negative runs: a scope that does not contain the path, and a grant without wire 35, both trap.
# Env as guest-run.sh: WALL_CP, WALL_K, WALL_AMU_SRC, WALL_NBB_DIR. Compile and extract run on nbb (BOOTSTRAP); the
# run is the C loader only.
HERE="$(cd "$(dirname "$0")" && pwd)"
AMU=${WALL_AMU_ROOT:-$(cd "$HERE/../.." && pwd)}
CPFILE=${WALL_CP:?set WALL_CP}; K=${WALL_K:?set WALL_K}
CP="$(cat $CPFILE):${WALL_AMU_SRC:-$AMU/src}"
SP=(); for d in ${(f)"$(tr ':' '\n' < $CPFILE | grep '/src$')"} ${WALL_AMU_SRC:-$AMU/src} $K/lang/compat; do SP+=(--source-path $d); done
W=$(mktemp -d /tmp/bytes-cap.XXXXXX); D=/tmp/kexe-bytes-cap; rm -rf $D; mkdir -p $D $W/other
cc $AMU/tools/kexe_loader.c -std=c11 -O2 -o $W/loader || exit 2
echo '{:allow #{[:cap/call 35] [:cap/call 37]}}' > $W/policy.edn
cd ${WALL_NBB_DIR:-$AMU}; ulimit -s 65520 2>/dev/null
nbb() { node --stack-size=56000 node_modules/nbb/cli.js --classpath "$CP" "$@"; }
nbb $AMU/src/kotoba/compiler/nbb/aarch64_cli.cljk compile $HERE/bytes-cap/probe.cljk --target aarch64-macos --jvm-free --policy $W/policy.edn --output $W/p.kexe $SP | grep -q ':ok true' || { echo "bytes-cap: compile refused"; exit 1; }
out=$(nbb $AMU/src/kotoba/compiler/nbb/x86_64_cli.cljk extract-native $W/p.kexe --symbol main --output $W/p.bin)
off=$(echo "$out" | sed -n 's/.*:offset \([0-9]*\).*/\1/p')
run() { KEXE_COMMAND=1 KEXE_CPU_SECONDS=20 KEXE_WALL_SECONDS=20 "$@" $W/loader $W/p.bin $off 0 aarch64 $grant 2>&1; }
fail=0
grant=35,37 got=$(KEXE_CAP_RESOURCES_35=$D run env); [ "$got" = "n=503255" ] || { echo "FAIL read-back: $got"; fail=1; }
[ "$(xxd -p $D/f.bin)" = "00ff800ac8" ] || { echo "FAIL file bytes: $(xxd -p $D/f.bin)"; fail=1; }
grant=35,37 got=$(KEXE_CAP_RESOURCES_35=$W/other run env); case "$got" in *KEXE_TRAP*) ;; *) echo "FAIL out-of-scope path was not refused: $got"; fail=1;; esac
grant=37 got=$(KEXE_CAP_RESOURCES_35=$D run env); case "$got" in *KEXE_TRAP*) ;; *) echo "FAIL ungranted wire 35 was not refused: $got"; fail=1;; esac
rm -rf $W
[ $fail -eq 0 ] && echo "bytes-cap: ok" || exit 1
