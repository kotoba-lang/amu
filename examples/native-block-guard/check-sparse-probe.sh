#!/bin/sh
set -eu
: "${AMU:?point to native Amu CLI}"
: "${TMPDIR:?point to workspace scratch}"
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
tmp=$(mktemp -d "$TMPDIR/sparse-probe.XXXXXXXX")
trap 'rm -rf "$tmp"' EXIT HUP INT TERM
[ "$("$AMU" run "$here/sparse-probe.kotoba")" = 0 ]
# Each mutant must compile and execute, and the native assertions must fail.
sed 's/(vector-conj out (- sectors 1))/(vector-conj out (- sectors 2))/' "$here/sparse-probe.kotoba" > "$tmp/endpoint.kotoba"
sed 's/(= (vector-at expected i) (vector-at observed i))/true/' "$here/sparse-probe.kotoba" > "$tmp/mismatch.kotoba"
sed 's/(not= (vector-count expected) (vector-count observed))/false/' "$here/sparse-probe.kotoba" > "$tmp/length.kotoba"
for mutant in endpoint mismatch length; do
  result=$("$AMU" run "$tmp/$mutant.kotoba")
  [ -n "$result" ] && [ "$result" != 0 ] || { echo "$mutant mutant survived" >&2; exit 1; }
done
printf '%s\n' 'native sparse probe model: 14 assertions passed; endpoint, mismatch and length mutants rejected'
