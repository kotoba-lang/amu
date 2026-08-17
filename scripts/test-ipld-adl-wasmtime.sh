#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
tmp=$(mktemp -d "${TMPDIR:-/tmp}/kotoba-ipld-adl.XXXXXX")
trap 'rm -rf "$tmp"' EXIT HUP INT TERM

cd "$root"
./scripts/build-ipld-adl-wasmtime.sh "$tmp/runner"

make_wasm() {
  printf '%s\n' "$2" > "$tmp/$1.wat"
  wasm-tools parse "$tmp/$1.wat" -o "$tmp/$1.wasm"
}

make_wasm identity '(module
  (memory (export "memory") 1 2)
  (data (i32.const 0) "\f5")
  (func (export "adl_alloc") (param i32) (result i32) i32.const 1024)
  (func (export "adl_transform") (param i32 i32 i32) (result i64)
    local.get 0 i32.const 0 i32.eq
    local.get 0 i32.const 3 i32.eq
    i32.or
    if (result i64)
      i64.const 1
    else
      local.get 1 i64.extend_i32_u i64.const 32 i64.shl
      local.get 2 i64.extend_i32_u i64.or
    end))'
make_wasm forever '(module
  (memory (export "memory") 1 1)
  (func (export "adl_alloc") (param i32) (result i32) i32.const 0)
  (func (export "adl_transform") (param i32 i32 i32) (result i64)
    (loop $again br $again) i64.const 0))'
make_wasm imported '(module
  (import "wasi_snapshot_preview1" "random_get" (func))
  (memory (export "memory") 1 1)
  (func (export "adl_alloc") (param i32) (result i32) i32.const 0)
  (func (export "adl_transform") (param i32 i32 i32) (result i64) i64.const 0))'
make_wasm growing '(module
  (memory (export "memory") 1)
  (func (export "adl_alloc") (param i32) (result i32)
    i32.const 1 memory.grow drop i32.const 0)
  (func (export "adl_transform") (param i32 i32 i32) (result i64) i64.const 0))'

# Compile the same ABI from Kotoba source, not a hand-authored Wasm fixture.
clojure -Sdeps '{:paths ["src" "resources" "scripts"]}' -M \
  -m ipld-adl-source-compile "$tmp/kotoba-identity.wasm"
wasm-tools validate "$tmp/kotoba-identity.wasm"

printf '\241aa\001' > "$tmp/input.cbor"
receipt=$($tmp/runner "$tmp/identity.wasm" "$tmp/input.cbor" "$tmp/output.cbor" \
  1 100000 1024 2 1000 1048576)
cmp "$tmp/input.cbor" "$tmp/output.cbor"
printf '%s' "$receipt" | grep -q '"status":"ok"'
printf '%s' "$receipt" | grep -q '"fuelUsed":'
printf '%s' "$receipt" | grep -q '"memoryPages":1'

for operation in 1 2; do
  $tmp/runner "$tmp/kotoba-identity.wasm" "$tmp/input.cbor" "$tmp/kotoba-output.cbor" \
    "$operation" 100000 1024 2 1000 1048576 >/dev/null
  cmp "$tmp/input.cbor" "$tmp/kotoba-output.cbor"
done
for operation in 0 3; do
  $tmp/runner "$tmp/kotoba-identity.wasm" "$tmp/input.cbor" "$tmp/kotoba-output.cbor" \
    "$operation" 100000 1024 2 1000 1048576 >/dev/null
  printf '\365' | cmp - "$tmp/kotoba-output.cbor"
done

if $tmp/runner "$tmp/forever.wasm" "$tmp/input.cbor" "$tmp/out" \
  1 5 1024 1 1000 1048576 | grep -q '"code":"fuel-exhausted"'; then :; else exit 1; fi
if $tmp/runner "$tmp/forever.wasm" "$tmp/input.cbor" "$tmp/out" \
  1 100000000000 1024 1 10 1048576 | grep -q '"code":"timeout"'; then :; else exit 1; fi
if $tmp/runner "$tmp/imported.wasm" "$tmp/input.cbor" "$tmp/out" \
  1 100000 1024 1 1000 1048576 | grep -q '"code":"forbidden-import"'; then :; else exit 1; fi
if $tmp/runner "$tmp/growing.wasm" "$tmp/input.cbor" "$tmp/out" \
  1 100000 1024 1 1000 1048576 | grep -q '"memoryPages":1'; then :; else exit 1; fi
if $tmp/runner "$tmp/identity.wasm" "$tmp/input.cbor" "$tmp/out" \
  1 100000 1 2 1000 1048576 | grep -q '"code":"output-limit-exceeded"'; then :; else exit 1; fi

clojure -M:ipld-adl-conformance \
  "$tmp/runner" "$tmp/identity.wasm"

echo "ipld-adl-wasmtime: Kotoba-source ABI, identity, engine fuel, timeout, import denial, memory, and output bounds passed"
