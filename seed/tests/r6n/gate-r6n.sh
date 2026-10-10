#!/bin/zsh
# seed/tests/r6n/gate-r6n.sh [--extra] -- the extra gate of rung R6N (agent claude, 2026-10-10): extract-native of a
# container over the 8 MiB bytes value bound (seed/02-io.kotoba io-read-bytes reads a file over 4 MiB in RANGE windows;
# docs/adr/0362 addendum). BOOTSTRAP-TOOL (zsh, python3 writes the synthetic containers and checks the slices). Only the
# seed and the C loader run. Rows:
#   XBIG   a synthetic KSEED1 container with a 12 MiB + 13 B code region (random bytes, one WRITE_SEP and one APPEND_SEP
#          spelled inside, so the 256 KiB write pieces are cut too) and two exports: `extract-native --symbol b` writes
#          exactly that code region and prints its offset, length and arity (r6m: :bytes/too-large, exit != 0)
#   XSMALL the same with a 1 MiB code region (the one-request path, unchanged since r6h)
#   R6M-X  seed/tests/r6m/gate-r6m.sh --extra (R6M's rows, and through it R6L .. R5A)
# Exit 0 iff no row FAILs.
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/../../../scripts/seed/lib.sh"
R=$SEED_REPO; B=${SEED_BUILD:A}; W=$B/gate-r6n; rm -rf $W; mkdir -p $W
bin=$B/seed-1.bin; off=$(cat $B/seed-1.offset 2>/dev/null || echo 0)
fails=0
row() { printf "%-7s %s\n" $1 "$2"; [ $1 = FAIL ] && fails=$((fails+1)); return 0; }
xrow() {   # xrow <name> <code bytes>
  local name=$1 n=$2 out rc
  python3 - $W/$name.kseed $W/$name.expected $n <<'EOP' || { row FAIL "$name: could not write the container"; return; }
import os, random, sys
path, exp, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
rnd = random.Random(20261010)
code = bytearray(rnd.getrandbits(8) for _ in range(n))
for at, tok in ((n // 3, b'WRITE_SEP'), (2 * n // 3, b'APPEND_SEP')):
    code[at:at + len(tok)] = tok
hdr = b'KSEED1 %d 2\na 0 1\nb %d 0\n\n' % (n, n - 8)
open(path, 'wb').write(hdr + bytes(code))
open(exp, 'wb').write(bytes(code))
EOP
  out=$(SEED_RESOURCES_35=$R:$W SEED_VECTOR_ITEMS=134217728 seed_run $bin $off extract-native $W/$name.kseed --symbol b --output $W/$name.bin 2> $W/$name.err); rc=$?
  if [ $rc = 0 ] && cmp -s $W/$name.bin $W/$name.expected && [[ $out == *":offset $((n - 8)), :length $n, :arity 0}"* ]]; then
    row PASS "$name: $n code bytes extracted byte-identical, $out"
  else row FAIL "$name: exit $rc, $out $(head -c 200 $W/$name.err), cmp $(cmp $W/$name.bin $W/$name.expected 2>&1 | head -1)"; fi
}
xrow XBIG $((12 * 1024 * 1024 + 13))
xrow XSMALL $((1024 * 1024))
rm -f $W/*.kseed $W/*.bin $W/*.expected
if [ "$1" = --extra ]; then
  if SEED_BUILD=$B zsh $R/seed/tests/r6m/gate-r6m.sh --extra > $W/r6m-x.log 2>&1; then row PASS "R6M-X $(tail -1 $W/r6m-x.log)"
  else row FAIL "R6M-X $W/r6m-x.log: $(grep '^FAIL' $W/r6m-x.log | head -3 | tr '\n' ' ')"; fi
fi
echo "gate-r6n: $fails FAIL"
exit $((fails > 0))
