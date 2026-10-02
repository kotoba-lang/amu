#!/bin/zsh
ulimit -s 65500
W=/private/tmp/wt-A-amu-measure/build/native-image/work
exec /usr/bin/time -l java -Xss512m -cp $W/classes:$(cat $W/classpath.txt) kotoba.compiler.cli compile $1 --target aarch64-macos --output ${1%.kotoba}.kexe
