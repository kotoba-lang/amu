#!/bin/sh
set -eu

prefix="${WASMTIME_PREFIX:-$(brew --prefix wasmtime)}"
output="${1:-target/ipld-adl-wasmtime}"
mkdir -p "$(dirname "$output")"
cc -std=c11 -O2 -Wall -Wextra -Werror -pthread \
  -I"$prefix/include" runtime/ipld-adl-wasmtime.c \
  -L"$prefix/lib" -Wl,-rpath,"$prefix/lib" -lwasmtime -o "$output"
