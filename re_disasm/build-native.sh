#!/bin/sh
# Build re-disasm as a native aarch64 program and run its checks with NO
# JVM, GraalVM or Node.js in the runtime tree.
#
#   sh re_disasm/build-native.sh [output-prefix]
#
# default output prefix: /Volumes/MithrilWork/scratch/re-disasm
#
# Phase 1 is the COMPILE DOOR: `bin/amu` is still the node-hosted bootstrap
# compiler (docs/selfhost-priority.md). `--jvm-free` proves no JVM is used;
# Node is used only here. When the selfhost-built amu binary lands, replace
# phase 1 with it and the whole script is Node-free too.
#
# Phase 2 and 3 are pure: cc builds the reviewed C loader
# (tools/kexe_loader.c), and the loader executes the extracted machine code
# as a standalone Mach-O process (it spawns no children and reads no
# configuration).
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
OUT=${1:-/Volumes/MithrilWork/scratch/re-disasm}
mkdir -p "$(dirname "$OUT")"

# Phase 1 -- compile + extract (bootstrap door; --jvm-free, no JVM).
node "$HERE/bin/amu" compile "$HERE/re_disasm/disasm.kotoba" \
  --jvm-free --output "$OUT.kexe" >/dev/null
EXTRACT=$(node "$HERE/bin/amu" extract-native "$OUT.kexe" \
  --symbol main --output "$OUT.bin")
OFFSET=$(printf '%s' "$EXTRACT" | sed -n 's/.*:offset \([0-9][0-9]*\).*/\1/p')
test -n "$OFFSET"

# Phase 2 -- reviewed C loader (cc only).
cc -O2 -o "$OUT.loader" "$HERE/tools/kexe_loader.c"

# Phase 3 -- run: the loader prints main's i64 result; 1 = all checks pass.
RESULT=$("$OUT.loader" "$OUT.bin" "$OFFSET" 0 aarch64 -)
if [ "$RESULT" = "1" ]; then
  echo "re-disasm native checks: PASS (main returned 1)"
else
  echo "re-disasm native checks: FAIL (main returned $RESULT)" >&2
  exit 1
fi
