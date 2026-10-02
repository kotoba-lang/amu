#!/bin/zsh
# scripts/seed/io_check.sh -- after `unit.sh 02-io`: decode the hex blocks io-write-hex printed (stdout of the last run,
# build/seed/unit/02-io/stdout) with `xxd -r -p` and compare with the byte patterns the test wrote: hex256 = bytes 0..255,
# hex65 = the first 65 of them, hexwindow = bytes 250..255, hex0 = nothing. Exit 0 pass.
emulate -L zsh
source "$(dirname "$0")/lib.sh"
f=$SEED_BUILD/unit/02-io/stdout
[ -f $f ] || { echo "io_check: run scripts/seed/unit.sh 02-io first"; exit 2; }
blk() { awk -v k=$1 '$0==k{on=1;next} /^(hex|ok |FAIL|failures|exit=)/{on=0} on' $f | xxd -r -p; }
fail=0
chk() { # name expected-python-expression
  local got=$(blk $1 | xxd -p | tr -d '\n') want=$(python3 -c "import sys;sys.stdout.write(bytes($2).hex())")
  if [ "$got" = "$want" ]; then echo "io_check $1: PASS (${#want} hex digits)"; else echo "io_check $1: FAIL"; fail=1; fi
}
chk hex256 "range(256)"; chk hex65 "range(65)"; chk hexwindow "range(250,256)"; chk hex0 "b''"
exit $fail
