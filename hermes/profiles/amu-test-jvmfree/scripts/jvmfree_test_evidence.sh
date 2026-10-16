#!/bin/sh
# Hermes no_agent jobs dispatch shell suffixes through the shell. Delegate
# the Hy source explicitly so it is not passed to Python as ordinary source.
set -eu
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
hy_bin=${HY_BIN:-hy}
if ! command -v "$hy_bin" >/dev/null 2>&1; then
  printf '%s\n' "REFUSED Hy interpreter not found: $hy_bin" >&2
  exit 2
fi
exec "$hy_bin" "$script_dir/jvmfree_test_evidence.hy"
