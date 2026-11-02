#!/bin/sh
# usage: run.sh OUTDIR COMPILER [STRIDE NRAND]: compile f2i.kotoba with COMPILER (a native Amu compiler, relative
# basenames), link it with driver.c / ref.c into a multiboot flat image and run it under qemu-system-x86_64 TCG with
# -cpu qemu64 and -cpu max. MUTANT=<name> (mutate.py) patches the native object first. STRIDE 1 with NRAND 0 is the
# exhaustive run (every 32-bit pattern, both MXCSR passes; give it TIMEOUT=7200).
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
out=$1 compiler=$2 stride=${3:-4099} nrand=${4:-1000000}
mkdir -p "$out"
cp "$here/f2i.kotoba" "$out/"; rm -f "$out/f2i.o"
(cd "$out" && "$compiler" compile f2i.kotoba --target x86_64-aiueos-kernel-v1 --output f2i.o --fuel 1000000 3<. </dev/null >/dev/null)
test -f "$out/f2i.o"
if [ -n "${MUTANT:-}" ]; then python3 -I "$here/mutate.py" "$MUTANT" "$out/f2i.o"; fi
shasum -a 256 "$out/f2i.o"
cf="-target x86_64-freestanding-none -std=c11 -O2 -ffreestanding -fno-stack-protector -mno-red-zone -fno-pic -Wall -Werror"
zig cc $cf -mgeneral-regs-only -DSTRIDE=${stride}ull -DNRAND=$nrand -c -o "$out/driver.o" "$here/driver.c"
zig cc $cf -mgeneral-regs-only -c -o "$out/ref.o" "$here/ref.c"
zig cc -target x86_64-freestanding-none -c -o "$out/entry.o" "$here/entry.S"
zig ld.lld -nostdlib -static -T "$here/link.ld" --oformat binary -o "$out/img.bin" "$out/entry.o" "$out/driver.o" "$out/ref.o" "$out/f2i.o"
run() {  # name cpu
  rm -f "$out/serial-$1.txt"
  timeout "${TIMEOUT:-3000}" qemu-system-x86_64 -kernel "$out/img.bin" -display none -no-reboot -m 256 -cpu $2 \
    -debugcon "file:$out/serial-$1.txt" -device isa-debug-exit,iobase=0xf4,iosize=4 >/dev/null 2>&1 || true
}
run qemu64 qemu64 &
run max max &
wait
for c in qemu64 max; do echo "== $c (-cpu $c)"; cat "$out/serial-$c.txt"; done
