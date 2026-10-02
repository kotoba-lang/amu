#!/bin/zsh
# scripts/seed/io_bytes_check.sh -- test of the binary writer io-write-bytes (seed/02-io.kotoba; was 02-io-bytes.snippet) (module 02-io, T3).
#   Assembles build/seed/io-bytes/unity.kotoba = 00-ns + 01-mem + 02-io + the snippet + seed/tests/io-bytes/io_bytes_t.kotoba,
#   compiles it, runs it under tools/kexe_loader.c for n = 0, 1, 256, 100000 and compares the written file with the pattern
#   (i*7 + (i >> 8)) & 255 byte for byte (python3 only as the comparer).
#   Compiler: 1. STAGE-0 ($SEED_STAGE0, default the stable native image): it refuses every :bytes capability call until it
#   is rebuilt with osaho e77ffff -> prints BLOCKED. 2. IO_BYTES_NBB=1: nbb (node, BOOTSTRAP-REFERENCE, compile time only;
#   the run is the C loader) using the T3 recipe files /private/tmp/t23/cp.txt (see docs/selfhost-seed-t2-t3-20261002.md).
# Exit 0 pass, 1 fail, 3 blocked (no compiler admits :bytes).
emulate -L zsh
source "$(dirname "$0")/lib.sh"
R=$SEED_REPO; W=$SEED_BUILD/io-bytes; rm -rf $W; mkdir -p $W/sc
U=$W/unity.kotoba; : > $U
for p in seed/00-ns.kotoba seed/01-mem.kotoba seed/02-io.kotoba seed/tests/io-bytes/io_bytes_t.kotoba; do cat $R/$p >> $U; printf '\n' >> $U; done
off=""
if seed_stage0_build $U $W/u; then
  off=$(cat $W/u.offset); bin=$W/u.bin; echo "io-bytes: compiled by STAGE-0 ($SEED_STAGE0)"
elif [ -n "$IO_BYTES_NBB" ]; then
  T=/private/tmp/t23
  [ -f $T/cp.txt ] || { echo "io-bytes: BLOCKED (no $T/cp.txt for nbb)"; exit 3; }
  echo '{:allow #{[:cap/call 35] [:cap/call 37] [:cap/call 38] [:cap/call 39]}}' > $W/pol.edn
  cd $R; export WALL_K=${WALL_K:-/private/tmp/wt-K-kotoba-lang}
  CP="$(cat $T/cp.txt):$R/src"; SP=(); for d in ${(f)"$(tr ':' '\n' < $T/cp.txt | grep '/src$')"} $R/src $WALL_K/lang/compat; do SP+=(--source-path $d); done
  ulimit -s 65520
  nice node --stack-size=56000 node_modules/nbb/cli.js --classpath "$CP" src/kotoba/compiler/nbb/aarch64_cli.cljk compile $U --target aarch64-macos --jvm-free --policy $W/pol.edn --output $W/u.kexe $SP > $W/u.log 2>&1
  grep -q ':ok true' $W/u.log || { echo "io-bytes: nbb refused:"; cut -c1-300 $W/u.log | head -3; exit 1; }
  nice node --stack-size=56000 node_modules/nbb/cli.js --classpath "$CP" src/kotoba/compiler/nbb/x86_64_cli.cljk extract-native $W/u.kexe --symbol main --output $W/u.bin $SP > $W/x.log 2>&1
  off=$(sed -n 's/.*:offset \([0-9]*\).*/\1/p' $W/x.log); bin=$W/u.bin
  [ -n "$off" ] || { echo "io-bytes: extract failed"; head -3 $W/x.log; exit 1; }
  echo "io-bytes: compiled by nbb (BOOTSTRAP-REFERENCE, compile time only)"
else
  echo "io-bytes: BLOCKED (stage-0 refuses :bytes capability calls: $(grep -o ':message "[^"]*"' $W/u.log | head -1 | cut -c1-110)); set IO_BYTES_NBB=1 for the nbb bootstrap route"
  exit 3
fi
export SEED_RESOURCES_35=$W/sc SEED_VECTOR_ITEMS=134217728
fail=0
for n in 0 1 256 100000; do
  rm -f $W/sc/*(N)
  seed_run $bin $off $W/sc $n > $W/run.$n.out 2>&1; rc=$?
  python3 - $W/sc/b.bin $W/sc/b0.bin $n <<'PY' || fail=1
import sys
n=int(sys.argv[3]); want=bytes(((i*7+(i>>8))&255) for i in range(n))
got=open(sys.argv[1],'rb').read(); z=open(sys.argv[2],'rb').read()
ok = got==want and z==b''
print("io-bytes n=%d: %s (%d bytes, %d distinct)" % (n, "PASS" if ok else "FAIL", len(got), len(set(got))))
sys.exit(0 if ok else 1)
PY
  [ $rc -eq 0 ] || { echo "io-bytes n=$n: run exit $rc: $(head -2 $W/run.$n.out)"; fail=1; }
done
exit $fail
