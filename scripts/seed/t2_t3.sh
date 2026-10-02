#!/bin/zsh
# T2/T3 risk tests of docs/selfhost-seed-design-20261002.md section 6. Reproduces docs/selfhost-seed-t2-t3-20261002.md.
# BOOTSTRAP-REFERENCE parts are labelled: the T3 program is compiled by nbb (node) because the stable stage-0 native image
# (build/native-image/amu-native, built 2026-10-02 00:24) does not yet admit typed-cap-call 35 over :bytes (osaho e77ffff does).
# Everything that RUNS is the C loader only. Env: T23 (work dir, default /private/tmp/t23), SEMA_COMMIT (default 452269a).
AMU=$(cd "$(dirname "$0")/../.." && pwd)
T=${T23:-/private/tmp/t23}; mkdir -p $T/d; cd $AMU
cc tools/kexe_loader.c -std=c11 -O2 -o $T/loader || exit 2
# ---------------- T2: hand-encoded words, no compiler involved ----------------
python3 seed/tests/t2/t2_asm.py $T/t2.bin --oracle || exit 1          # encoder == clang on every word
OFF=$(python3 seed/tests/t2/t2_asm.py $T/t2.bin | sed -n 's/main offset \([0-9]*\).*/\1/p')
export KEXE_CAP_RESOURCES_35=$T/d
rm -f $T/d/t2.bin
r=$($T/loader $T/t2.bin $OFF 0 aarch64 35,37); [ "$r" = "aé€x10536" ] && echo "T2 result ok" || { echo "T2 FAIL: $r"; exit 1; }
python3 -c "import sys;sys.exit(0 if open('$T/d/t2.bin','rb').read()==bytes(range(256)) else 1)" && echo "T2 kind-8 write ok (256 bytes)" || exit 1
rem=$(KEXE_FUEL=100000 KEXE_STRUCTURED_REPORT=1 $T/loader $T/t2.bin $OFF 0 aarch64 35,37 | sed -n 's/.*:remaining \([0-9]*\).*/\1/p' | head -1)
[ $((100000 - rem)) -eq 1313 ] && echo "T2 fuel charges 1313 ok" || { echo "T2 FAIL fuel $rem"; exit 1; }
KEXE_FUEL=1312 $T/loader $T/t2.bin $OFF 0 aarch64 35,37 2>&1 | grep -q 'budget/fuel' && echo "T2 fuel trap at 1312 ok" || exit 1
# ---------------- T3: Kotoba program, :bytes through wire 35 ----------------
# (bootstrap compile; see header)  nbb classpath with a consistent kotoba-sema: $T/cp.txt and $T/nbbc.sh are built by the doc's commands
[ -x $T/nbbc.sh ] && [ -f $T/t3.bin ] || { echo "T3: run the compile steps of the doc first (needs $T/nbbc.sh)"; exit 0; }
head -c 1048576 /dev/urandom > $T/d/in.bin
KEXE_COMMAND=1 KEXE_STRING_POOL=268435456 KEXE_VECTOR_ITEMS=134217728 $T/loader $T/t3.bin ${T3_OFF:?set T3_OFF} 0 aarch64 35,38,39 -- $T/d/in.bin $T/d/copy.bin $T/d/gen.bin 1048576
cmp $T/d/in.bin $T/d/copy.bin && echo "T3 1 MiB copy identical"
