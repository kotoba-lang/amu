#!/bin/sh
set -eu
: "${AMU:?point to native Amu CLI}"
: "${TMPDIR:?point to workspace scratch}"
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
tmp=$(mktemp -d "$TMPDIR/block-guard.XXXXXXXX")
trap 'rm -rf "$tmp"' EXIT HUP INT TERM
[ "$("$AMU" run "$here/guard.kotoba")" = 0 ]
sed 's/(= (vector-at device 6) 0)/(= (vector-at device 6) 1)/' "$here/guard.kotoba" > "$tmp/mounted.kotoba"
result=$("$AMU" run "$tmp/mounted.kotoba")
[ "$result" != 0 ] && [ -n "$result" ]
sed 's/(= (vector-at ticket 7) 0)/(= (vector-at ticket 7) 1)/' "$here/guard.kotoba" > "$tmp/replay.kotoba"
result=$("$AMU" run "$tmp/replay.kotoba")
[ "$result" != 0 ] && [ -n "$result" ]
printf '%s\n' 'native block guard: 21 assertions passed; mounted and replay mutants rejected'
