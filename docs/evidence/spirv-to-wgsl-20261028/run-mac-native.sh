#!/bin/bash
# usage: run.sh <src.kotoba> <name>   (in scratch dir S); compile, package, sign, run with FD3 = S
S=${S:?scratch directory with amu, pk (the pinned root and packager copies)}
cd $S || exit 1
E="env -i PATH=/usr/bin:/bin LANG=C TMPDIR=$S"
$E ./amu compile $1 --target aarch64-macos --output $2.kseed 3< . || exit 2
OUT=$($E ./amu extract-native $2.kseed --symbol main --output $2.raw 3< .) || exit 3
ENTRY=$(echo "$OUT" | sed -n 's/.*:offset \([0-9]*\),.*/\1/p')
$E ./pk $2.unsigned $2.raw fs2-cli-stdio-general $ENTRY 3< . || exit 4
cp $2.unsigned $2.macho && chmod +x $2.macho && codesign -s - -f $2.macho 2>/dev/null || exit 5
$E ./$2.macho 3< .
echo "run-exit=$?"
