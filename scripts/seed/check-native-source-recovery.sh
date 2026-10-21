#!/usr/bin/env bash
# The compiler/loader are explicit native tools; no hosted compiler fallback.
set -euo pipefail
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd -P)
compiler=${1:?usage: check-native-source-recovery.sh COMPILER LOADER NEW_OUTPUT}
loader=${2:?missing native loader}
output=${3:?missing new output directory}
[ ! -e "$output" ] || { echo "output already exists" >&2; exit 73; }
mkdir -p "$output/objects" "$output/logs"
output=$(CDPATH= cd -- "$output" && pwd -P)
fixture=$root/test/fixtures/selfhost/native-source-recovery.kotoba
sha() { shasum -a 256 "$1" | awk '{print $1}'; }
compiler_sha=$(sha "$compiler")
loader_sha=$(sha "$loader")
invoke() {
  local name=$1
  shift
  [ "$(sha "$compiler")" = "$compiler_sha" ]
  [ "$(sha "$loader")" = "$loader_sha" ]
  env -i PATH="$PATH" TMPDIR="$output" \
    KEXE_COMMAND=1 KEXE_CAP_RESOURCES_35="$output:$root/src:$root/test/fixtures" \
    KEXE_FUEL=500000000 KEXE_PAIRS=16777216 KEXE_VECTORS=4194304 \
    KEXE_VECTOR_ITEMS=134217728 KEXE_STRING_POOL=268435456 \
    KEXE_CPU_SECONDS=300 KEXE_WALL_SECONDS=300 \
    "$loader" "$compiler" 0 0 aarch64 3,35,37,38,39 -- "$@" \
    > "$output/logs/$name.stdout" 2> "$output/logs/$name.stderr"
}
invoke modules modules "$fixture" --source-path "$root/src" --unpinned
entry=
count=0
: > "$output/sources.sha256"
while IFS=' ' read -r namespace file; do
  [[ "$namespace" =~ ^[a-zA-Z0-9_.-]+$ ]] || exit 65
  shasum -a 256 "$file" >> "$output/sources.sha256"
  if [ "$file" = "$fixture" ]; then
    entry=$namespace
    invoke "compile-$count" compile "$file" --emit-module --entry \
      --object-dir "$output/objects" --output "$output/objects/$namespace.kso"
  else
    invoke "compile-$count" compile "$file" --emit-module \
      --object-dir "$output/objects" --output "$output/objects/$namespace.kso"
  fi
  count=$((count + 1))
done < "$output/logs/modules.stdout"
[ -n "$entry" ] && [ "$count" -eq 6 ]
invoke link link "$output/objects/$entry.kso" --object-dir "$output/objects" --output "$output/recovery.kseed"
invoke extract extract-native "$output/recovery.kseed" --symbol main --output "$output/recovery.bin"
offset=$(sed -n 's/.*:offset \([0-9][0-9]*\).*/\1/p' "$output/logs/extract.stdout")
[[ "$offset" =~ ^[0-9]+$ ]] || exit 65
env -i PATH="$PATH" KEXE_STRUCTURED_REPORT=1 KEXE_FUEL=5000000 \
  KEXE_PAIRS=1048576 KEXE_VECTORS=262144 KEXE_VECTOR_ITEMS=4194304 \
  KEXE_STRING_POOL=16777216 KEXE_CPU_SECONDS=30 KEXE_WALL_SECONDS=30 \
  "$loader" "$output/recovery.bin" "$offset" 0 aarch64 - \
  > "$output/logs/execute.stdout" 2> "$output/logs/execute.stderr"
grep -Eq ':status :ok :result 31([ }]|$)' "$output/logs/execute.stdout"
shasum -a 256 -c "$output/sources.sha256" > "$output/logs/source-readback.stdout"
printf '{"status":"pass","scope":"restored-native-reader-targets","checks":5,"modules":6,"result":31,"compiler_sha256":"%s","loader_sha256":"%s"}\n' \
  "$compiler_sha" "$loader_sha" > "$output/report.json"
cat "$output/report.json"
