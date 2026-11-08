#!/usr/bin/env bash
# Bounded inventory prototype only; this is not a repin or artifact-admission gate.
set -euo pipefail
compiler="${1:?native compiler required}"
out="${2:?new output directory required}"
mkdir "$out"
mkdir -p "$out/mutant/repin"

run_case() {
  local name="$1" source="$2" paths="$3" expected="$4" actual
  "$compiler" compile "$source" --source-path "$paths" -o "$out/$name" > "$out/$name.build.log" 2>&1
  actual=$("$out/$name")
  if [[ "$actual" != "$expected" ]]; then
    printf '%s: expected %s, got %s\n' "$name" "$expected" "$actual" >&2
    return 1
  fi
}

run_case inventory test/fixtures/repin/inventory.kotoba tools 0
run_case manifest test/fixtures/repin/manifest.kotoba tools 0

# Build and execute a native mutant that accepts every inventory. The fixture
# must catch an extra generated path, rather than merely building successfully.
awk '/^\(defn exact-source-paths\?/ {exit} {print}' tools/repin/inventory.kotoba > "$out/mutant/repin/inventory.kotoba"
printf '(defn exact-source-paths? [expected [:list :string] reported [:list :string]] :bool true)\n' >> "$out/mutant/repin/inventory.kotoba"
run_case inventory-mutant test/fixtures/repin/inventory.kotoba "$out/mutant" 3

# The sentinel establishes the CLI-source prefix. A parser that can never
# recognize it must fail the positive fixture when actually compiled and run.
cp tools/repin/inventory.kotoba "$out/mutant/repin/inventory.kotoba"
sed 's/(= line "seed\/90-drv.kotoba")/false/' tools/repin/manifest.kotoba > "$out/mutant/repin/manifest.kotoba"
cmp -s tools/repin/manifest.kotoba "$out/mutant/repin/manifest.kotoba" && { echo 'sentinel mutation failed' >&2; exit 1; }
run_case manifest-mutant test/fixtures/repin/manifest.kotoba "$out/mutant" 1
echo PASS_REPIN_INVENTORY_NATIVE
