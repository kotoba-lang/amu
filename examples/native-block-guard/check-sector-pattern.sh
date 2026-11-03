#!/bin/sh
set -eu
: "${AMU:?point to native Amu CLI}"
: "${TMPDIR:?point to workspace scratch}"
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
tmp=$(mktemp -d "$TMPDIR/sector-pattern.XXXXXXXX")
trap 'rm -rf "$tmp"' EXIT HUP INT TERM
[ "$("$AMU" run "$here/sector-pattern.kotoba")" = 0 ]
sed 's/(if (< (mod i 16) 8) sector nonce)/nonce/' "$here/sector-pattern.kotoba" > "$tmp/address.kotoba"
sed 's/(if (< (mod i 16) 8) sector nonce)/sector/' "$here/sector-pattern.kotoba" > "$tmp/nonce.kotoba"
sed 's/(= (vector-at bytes i) (vector-at expected i))/true/' "$here/sector-pattern.kotoba" > "$tmp/compare.kotoba"
for mutant in address nonce compare; do
  result=$("$AMU" run "$tmp/$mutant.kotoba")
  [ -n "$result" ] && [ "$result" != 0 ] || { echo "$mutant mutant survived" >&2; exit 1; }
done
printf '%s\n' 'native sector pattern: 12 assertions passed; address, nonce and comparison mutants rejected'
