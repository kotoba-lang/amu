#!/bin/zsh
# hashcons-test.sh: tests of the loader's pair hash-consing (KEXE_HASHCONS, tools/kexe_loader.c). BOOTSTRAP-TOOL (zsh).
#   1. the loader compiles with -Wall -Wextra -Werror, and with ASan+UBSan (when the toolchain has them);
#   2. guests/hashcons_scope.kotoba (compiled by stage-0, the native-image amu) answers the same checksum with hash-consing off and on at
#      table sizes 2^12, 2^16, 2^22, 2^28 -- the probe releases arena scopes between iterations that reuse pair indexes and string-pool
#      offsets, so a table entry believed after its release (or without the exact two-word compare) changes the checksum or traps; and
#      hash-consing makes strictly fewer pairs;
#   3. optional: a pass image + input (as pass-driver.sh takes them): the output is byte-identical at those table sizes.
#   hashcons-test.sh [<pass.bin> <input> <pass>]
# Env: AMU_NATIVE (stage-0, default build/native-image/amu-native), TEST_OUT (default build/hashcons-test). Exit 0 = all pass.
HERE="$(cd "$(dirname "$0")" && pwd)"; AMU=${HERE:h:h}
out=${TEST_OUT:-$AMU/build/hashcons-test}; mkdir -p $out
N=${AMU_NATIVE:-$AMU/build/native-image/amu-native}
fail=0; ok() { echo "PASS $1"; }; bad() { echo "FAIL $1"; fail=1; }
cc $AMU/tools/kexe_loader.c -std=c11 -O2 -Wall -Wextra -Werror -o $out/loader && ok "loader builds with -Wall -Wextra -Werror" || { bad "loader build"; exit 1; }
if cc $AMU/tools/kexe_loader.c -std=c11 -O1 -g -fsanitize=address,undefined -o $out/loader-asan 2>/dev/null; then asan=$out/loader-asan; else asan=; echo "SKIP sanitizer build"; fi
echo "{:allow #{[:cap/call 37]}}" > $out/policy.edn
( ulimit -s 65500; $N compile $AMU/scripts/selfhost-wall/guests/hashcons_scope.kotoba --target aarch64-macos --jvm-free --policy $out/policy.edn --output $out/hs.kexe > $out/hs.compile 2>&1 ) && \
  r=$(python3 $AMU/scripts/seed/kexe_code.py $out/hs.kexe main $out/hs.bin) && off=$(echo $r | sed -n 's/.*:offset \([0-9]*\).*/\1/p') || { bad "compile hashcons_scope"; exit 1; }
run() {  # run <loader> <hashcons> : stdout line, pairs on stderr
  KEXE_HASHCONS=$2 KEXE_ARENA_USE=1 KEXE_COMMAND=1 KEXE_STRING_POOL=268435456 KEXE_PAIRS=33554432 KEXE_CPU_SECONDS=120 KEXE_WALL_SECONDS=120 \
    ASAN_OPTIONS=detect_leaks=0 $1 $out/hs.bin $off 0 aarch64 37 < /dev/null 2> $out/hs.err
}
ref=$(run $out/loader 0); p0=$(sed -n 's/.*:pairs \([0-9]*\).*/\1/p' $out/hs.err | head -1)
[ -n "$ref" ] && ok "scope probe off: $ref ($p0 pairs)" || bad "scope probe off"
for b in 12 16 22 28; do
  got=$(run $out/loader $b); p=$(sed -n 's/.*:pairs \([0-9]*\).*/\1/p' $out/hs.err | head -1)
  [ "$got" = "$ref" ] && [ -n "$p" ] && [ "$p" -lt "$p0" ] && ok "scope probe 2^$b: same checksum, $p pairs < $p0" || bad "scope probe 2^$b: '$got' vs '$ref' (pairs $p)"
done
if [ -n "$asan" ]; then got=$(run $asan 16); [ "$got" = "$ref" ] && ok "scope probe under ASan+UBSan" || bad "scope probe under ASan+UBSan"; fi
if [ $# -ge 3 ]; then
  bin=$1; in=$2; shift 2; offp=$(cat ${bin%.bin}.offset)
  { echo "!$1"; cat $in; } > $out/pass.in
  ref=; for b in 0 12 16 22 28; do
    KEXE_HASHCONS=$b KEXE_COMMAND=1 KEXE_STRING_POOL=1073741824 KEXE_PAIRS=67108864 KEXE_VECTORS=4194304 KEXE_VECTOR_ITEMS=134217728 KEXE_CPU_SECONDS=300 KEXE_WALL_SECONDS=300 \
      $out/loader $bin $offp 0 aarch64 3,37,41 < $out/pass.in > $out/pass.out.$b 2>/dev/null
    h=$(md5 -q $out/pass.out.$b); [ -n "$ref" ] || ref=$h
    [ "$h" = "$ref" ] && [ -s $out/pass.out.$b ] && ok "pass '$1' output identical at KEXE_HASHCONS=$b" || bad "pass '$1' output differs at KEXE_HASHCONS=$b"
  done
fi
exit $fail
