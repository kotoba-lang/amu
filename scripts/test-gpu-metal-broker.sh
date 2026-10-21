#!/bin/sh
# The wire-42 Metal broker's request verbs (tools/kexe_gpu_metal.m), driven
# directly by tools/test_kexe_gpu_metal.m: the review findings of amu #1404
# held to their behavior. macOS with a Metal device only; elsewhere it is
# skipped BY NAME. Run twice: plain, and under Metal shader validation, where
# an out-of-bounds kernel read is caught (MTL_SHADER_VALIDATION=1).
set -eu
root=$(cd "$(dirname "$0")/.." && pwd)
if [ "$(uname -s)" != Darwin ]; then
  echo "SKIP test-gpu-metal-broker -- not macOS (Metal)"
  exit 0
fi
work=$(mktemp -d "${TMPDIR:-/tmp}/gpu-metal-broker.XXXXXX")
trap 'rm -rf "$work"' EXIT
cc -x objective-c -fobjc-arc -O2 -Wall -Wextra -Werror -Wno-deprecated-declarations -Wno-unused-function \
  -I"$root/tools" "$root/tools/test_kexe_gpu_metal.m" -framework Metal -framework Foundation -o "$work/test"
TMPDIR="$work" "$work/test" "$root/tools" 2>/dev/null
TMPDIR="$work" MTL_DEBUG_LAYER=1 MTL_SHADER_VALIDATION=1 "$work/test" "$root/tools" 2>/dev/null
echo "test-gpu-metal-broker: passed"
