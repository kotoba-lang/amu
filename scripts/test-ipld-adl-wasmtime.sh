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
clojure -Sdeps '{:paths ["src" "resources" "scripts"]}' -M \
  -m ipld-adl-source-compile "$tmp/kotoba-closed.wasm" closed
wasm-tools validate "$tmp/kotoba-closed.wasm"
clojure -Sdeps '{:paths ["src" "resources" "scripts"]}' -M \
  -m ipld-adl-source-compile "$tmp/kotoba-projection.wasm" projection
wasm-tools validate "$tmp/kotoba-projection.wasm"
clojure -Sdeps '{:paths ["src" "resources" "scripts"]}' -M \
  -m ipld-adl-source-compile "$tmp/kotoba-input-count.wasm" input-count
wasm-tools validate "$tmp/kotoba-input-count.wasm"
clojure -Sdeps '{:paths ["src" "resources" "scripts"]}' -M \
  -m ipld-adl-source-compile "$tmp/kotoba-byte-at.wasm" byte-at
wasm-tools validate "$tmp/kotoba-byte-at.wasm"
clojure -Sdeps '{:paths ["src" "resources" "scripts"]}' -M \
  -m ipld-adl-source-compile "$tmp/kotoba-byte-at-3.wasm" byte-at-3
wasm-tools validate "$tmp/kotoba-byte-at-3.wasm"
clojure -Sdeps '{:paths ["src" "resources" "scripts"]}' -M \
  -m ipld-adl-source-compile "$tmp/kotoba-byte-at-cbor.wasm" byte-at-cbor
wasm-tools validate "$tmp/kotoba-byte-at-cbor.wasm"

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

# The validator result is derived from the actual ABI input length.
for operation in 0 3; do
  $tmp/runner "$tmp/kotoba-input-count.wasm" "$tmp/input.cbor" "$tmp/kotoba-output.cbor" \
    "$operation" 100000 1024 2 1000 1048576 >/dev/null
  printf '\365' | cmp - "$tmp/kotoba-output.cbor"
  printf '\100' > "$tmp/short.cbor"
  $tmp/runner "$tmp/kotoba-input-count.wasm" "$tmp/short.cbor" "$tmp/kotoba-output.cbor" \
    "$operation" 100000 1024 2 1000 1048576 >/dev/null
  printf '\364' | cmp - "$tmp/kotoba-output.cbor"
done

# bytes-at reads one unsigned byte out of the ABI input. The bound is the
# input length, not the linear memory size: the input sits at offset 1024 of a
# two-page memory, so an out-of-range index would otherwise read whatever
# follows it and answer confidently.
printf '\100' > "$tmp/short.cbor"
: > "$tmp/empty.cbor"
head -c 200000 /dev/zero > "$tmp/big.cbor"
for operation in 0 3; do
  # Byte 0 of the four-byte input is 0xA1 = 161.
  $tmp/runner "$tmp/kotoba-byte-at.wasm" "$tmp/input.cbor" "$tmp/kotoba-output.cbor" \
    "$operation" 100000 1024 2 1000 1048576 >/dev/null
  printf '\365' | cmp - "$tmp/kotoba-output.cbor"
  # Byte 0 of the one-byte input is 0x40: in range, and a well-formed false.
  $tmp/runner "$tmp/kotoba-byte-at.wasm" "$tmp/short.cbor" "$tmp/kotoba-output.cbor" \
    "$operation" 100000 1024 2 1000 1048576 >/dev/null
  printf '\364' | cmp - "$tmp/kotoba-output.cbor"
  # Byte 3 of the four-byte input is 0x01.
  $tmp/runner "$tmp/kotoba-byte-at-3.wasm" "$tmp/input.cbor" "$tmp/kotoba-output.cbor" \
    "$operation" 100000 1024 2 1000 1048576 >/dev/null
  printf '\365' | cmp - "$tmp/kotoba-output.cbor"
  # Index 3 of a one-byte input traps rather than reading past the operand.
  if $tmp/runner "$tmp/kotoba-byte-at-3.wasm" "$tmp/short.cbor" "$tmp/out" \
    "$operation" 100000 1024 2 1000 1048576 | grep -q '"code":"guest-trap"'; then :; else exit 1; fi
  # Every index is out of range for an empty input, including index 0.
  if $tmp/runner "$tmp/kotoba-byte-at.wasm" "$tmp/empty.cbor" "$tmp/out" \
    "$operation" 100000 1024 2 1000 1048576 | grep -q '"code":"guest-trap"'; then :; else exit 1; fi
  # An input larger than the fixed allocation traps in adl_alloc, before any
  # byte is read.
  if $tmp/runner "$tmp/kotoba-byte-at.wasm" "$tmp/big.cbor" "$tmp/out" \
    "$operation" 100000 1024 2 1000 1048576 | grep -q '"code":"allocation-trap"'; then :; else exit 1; fi
done

# Non-identity source semantics: decode returns the canonical empty bytes node,
# encode stays identity, and validate-logical returns canonical false.
$tmp/runner "$tmp/kotoba-closed.wasm" "$tmp/input.cbor" "$tmp/kotoba-output.cbor" \
  1 100000 1024 2 1000 1048576 >/dev/null
printf '\100' | cmp - "$tmp/kotoba-output.cbor"
$tmp/runner "$tmp/kotoba-closed.wasm" "$tmp/input.cbor" "$tmp/kotoba-output.cbor" \
  2 100000 1024 2 1000 1048576 >/dev/null
cmp "$tmp/input.cbor" "$tmp/kotoba-output.cbor"
$tmp/runner "$tmp/kotoba-closed.wasm" "$tmp/input.cbor" "$tmp/kotoba-output.cbor" \
  3 100000 1024 2 1000 1048576 >/dev/null
printf '\364' | cmp - "$tmp/kotoba-output.cbor"

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
clojure -M:ipld-adl-conformance \
  "$tmp/runner" "$tmp/kotoba-projection.wasm" empty
# The indexed-byte lowering also runs through the schema capability, so its
# bounded execution is covered by the same signed measured receipts. Note the
# operand there is the DAG-CBOR encoded node, not the payload bytes.
clojure -M:ipld-adl-conformance \
  "$tmp/runner" "$tmp/kotoba-byte-at-cbor.wasm"

echo "ipld-adl-wasmtime: Kotoba-source input-dependent validation, indexed unsigned byte reads with operand-length bounds traps, non-identity projection, engine fuel, timeout, import denial, memory, and output bounds passed"
