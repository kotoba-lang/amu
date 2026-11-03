#!/bin/sh
# usage: run-a64.sh OUTDIR COMPILER [STRIDE NRAND THREADS]: compile ../f32-to-i64-20261031/f2i.kotoba (the x86 run's
# source) with COMPILER (a native Amu compiler) for --target aarch64-macos, cut the function out with extract-native,
# and run the differential natively on this Mac (clang) and on Linux arm64 in the local podman machine (a static musl
# build from zig cc, in debian:12-slim). MUTANT=<name> (mutate-a64.py) patches the payload first. STRIDE 1 with NRAND 0
# is the exhaustive run. LINUX=0 skips the podman run.
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
x86=$here/../f32-to-i64-20261031
out=$1 compiler=$2 stride=${3:-4099} nrand=${4:-1000000} threads=${5:-8}
mkdir -p "$out"; out=$(CDPATH= cd -- "$out" && pwd)
cp "$x86/f2i.kotoba" "$out/"; rm -f "$out/f2i.kseed" "$out/f2i.bin"
(cd "$out" && "$compiler" compile f2i.kotoba --target aarch64-macos --output f2i.kseed 3<. </dev/null >/dev/null &&
  "$compiler" extract-native f2i.kseed --symbol kotoba_aiueos_f32_to_i64 --output f2i.bin 3<. </dev/null >/dev/null)
guard=$(python3 -I -c "import struct,sys; b=open(sys.argv[1],'rb').read(); t=struct.pack('<3I',0x1e202020,0x5400004c,0xd4200000); assert b.count(t)==1; print(hex(b.find(t)+8))" "$out/f2i.bin")
if [ -n "${MUTANT:-}" ]; then python3 -I "$here/mutate-a64.py" "$MUTANT" "$out/f2i.bin"; fi
shasum -a 256 "$out/f2i.bin"
d="-DSTRIDE=${stride}ull -DNRAND=$nrand"
clang -O2 -Wall -Werror $d -o "$out/f2idiff-macos" "$here/driver-a64.c" "$x86/ref.c" "$here/call-a64.S" -lpthread
zig cc -target aarch64-linux-musl -static -O2 -Wall -Werror $d -o "$out/f2idiff-linux" "$here/driver-a64.c" "$x86/ref.c" "$here/call-a64.S"
"$out/f2idiff-macos" "$out/f2i.bin" "$threads" "$guard" > "$out/macos.txt" &
if [ "${LINUX:-1}" = 1 ]; then
  podman run --rm --platform linux/arm64 --network none -v "$out:/w:Z" docker.io/library/debian:12-slim \
    sh -c "uname -sm; /w/f2idiff-linux /w/f2i.bin $threads $guard" > "$out/linux.txt" &
fi
wait
for c in macos linux; do [ -f "$out/$c.txt" ] && { echo "== $c"; cat "$out/$c.txt"; }; done
