#!/usr/bin/env bash
# Bounded inventory prototype only; this is not a repin or artifact-admission gate.
set -euo pipefail
compiler="${1:?native compiler required}"
out="${2:?new output directory required}"
mkdir "$out"
mkdir -p "$out/mutant/repin"

run_case() {
  local name="$1" source="$2" paths="$3" expected="$4" actual status=0
  "$compiler" compile "$source" --source-path "$paths" --source-path src -o "$out/$name" > "$out/$name.build.log" 2>&1
  # The pinned CLI's native fixtures print the verdict and exit successfully.
  "$out/$name" > "$out/$name.run.log" 2> "$out/$name.stderr.log" || status=$?
  actual=$(<"$out/$name.run.log")
  if [[ "$status" != 0 || "$actual" != "$expected" ]]; then
    printf '%s: expected verdict %s, got %s (process status %s)\n' "$name" "$expected" "$actual" "$status" >&2
    return 1
  fi
}

run_case inventory test/fixtures/repin/inventory.kotoba tools 0
run_case manifest test/fixtures/repin/manifest.kotoba tools 0
run_case digest test/fixtures/repin/digest.kotoba tools 0

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

# Native execution must reject same-size byte changes, not just size drift.
cat > "$out/mutant/repin/digest.kotoba" <<'EOF'
(ns repin.digest (:export [matches?]))
(defn matches? [data :bytes expected-size :i64 expected-sha256 :string] :bool
  (= (bytes-count data) expected-size))
EOF
run_case digest-mutant test/fixtures/repin/digest.kotoba "$out/mutant" 2
echo PASS_REPIN_INVENTORY_NATIVE
