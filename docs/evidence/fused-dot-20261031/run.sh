#!/bin/sh
# usage: run.sh OUTDIR COMPILER [NDOT NDQ]: compile dot-native / dq-native with COMPILER (relative basenames), link them
# with old qwen35-matvec.o into a multiboot flat image and run it under qemu-system-x86_64 TCG with -cpu qemu64
# (scalar arm), -cpu max with XCR0 AVX enabled (AVX2 arm) and -cpu max without OSXSAVE (scalar arm on an AVX2 CPU).
# MUTANT=<python patch> rewrites the native objects first.
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
out=$1 compiler=$2 ndot=${3:-3000} ndq=${4:-1500}
mkdir -p "$out"
for n in dot-native dq-native; do
  cp "$here/$n.kotoba" "$out/"; rm -f "$out/$n.o"
  (cd "$out" && "$compiler" compile $n.kotoba --target x86_64-aiueos-kernel-v1 --output $n.o --fuel 1000000 3<. </dev/null >/dev/null)
  test -f "$out/$n.o"
done
if [ -n "${MUTANT:-}" ]; then python3 -I "$here/mutate.py" "$MUTANT" "$out/dot-native.o" "$out/dq-native.o"; fi
cf="-target x86_64-freestanding-none -std=c11 -O2 -ffreestanding -fno-stack-protector -mno-red-zone -fno-pic -Wall -Werror"
zig cc $cf -mgeneral-regs-only -DNDOT=$ndot -DNDQ=$ndq -c -o "$out/driver.o" "$here/driver.c"
zig cc $cf -mgeneral-regs-only -DNO_XSAVE -DNDOT=$ndot -DNDQ=$ndq -c -o "$out/driver-noxsave.o" "$here/driver.c"
zig cc $cf -msse2 -mno-avx -ffp-contract=off -c -o "$out/ref.o" "$here/ref.c"
zig cc -target x86_64-freestanding-none -c -o "$out/entry.o" "$here/entry.S"
old="$here/qwen35-matvec.o"
zig ld.lld -nostdlib -static -T "$here/link.ld" --oformat binary -o "$out/img.bin" "$out/entry.o" "$out/driver.o" "$out/ref.o" "$old" "$out/dot-native.o" "$out/dq-native.o"
zig ld.lld -nostdlib -static -T "$here/link.ld" --oformat binary -o "$out/img-noxsave.bin" "$out/entry.o" "$out/driver-noxsave.o" "$out/ref.o" "$old" "$out/dot-native.o" "$out/dq-native.o"
run() {  # name cpu image
  rm -f "$out/serial-$1.txt"
  timeout 3000 qemu-system-x86_64 -kernel "$out/$3" -display none -no-reboot -m 256 -cpu $2 \
    -debugcon "file:$out/serial-$1.txt" -device isa-debug-exit,iobase=0xf4,iosize=4 >/dev/null 2>&1 || true
  echo "== $1 ($2)"; grep -v '^AT ' "$out/serial-$1.txt" | grep -v '^GUARD ' || true
  grep -c ' ud2$' "$out/serial-$1.txt" | sed 's/^/ud2 guards: /'
}
run qemu64 qemu64 img.bin &
run max max img.bin &
run max-noxsave max img-noxsave.bin &
wait
