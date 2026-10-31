#!/bin/sh
# usage: run.sh OUTDIR COMPILER -- the hand check of README.md: msr.kotoba built by COMPILER, linked with driver.c,
# guard.S and entry.S, run under qemu-system-x86_64 on two CPU models. Not a gate.
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
out=$1; mkdir -p "$out"; cp "$here/msr.kotoba" "$out/"
(cd "$out" && rm -f msr.o && "$2" compile msr.kotoba --target x86_64-aiueos-kernel-v1 --output msr.o --fuel 4194304 3<. </dev/null >/dev/null)
cf="-target x86_64-freestanding-none -std=c11 -O2 -ffreestanding -fno-stack-protector -mno-red-zone -fno-pic -mgeneral-regs-only -Wall -Werror"
zig cc $cf -c -o "$out/driver.o" "$here/driver.c"
zig cc -target x86_64-freestanding-none -c -o "$out/entry.o" "$here/entry.S"
zig cc -target x86_64-freestanding-none -c -o "$out/guard.o" "$here/guard.S"
zig ld.lld -nostdlib -static -T "$here/link.ld" --oformat binary -o "$out/img.bin" "$out/entry.o" "$out/driver.o" "$out/guard.o" "$out/msr.o"
for cpu in qemu64 max; do
  rm -f "$out/serial-$cpu.txt"
  timeout 300 qemu-system-x86_64 -kernel "$out/img.bin" -display none -no-reboot -m 64 -cpu $cpu \
    -debugcon "file:$out/serial-$cpu.txt" -device isa-debug-exit,iobase=0xf4,iosize=4 >/dev/null 2>&1 || true
  grep -q DONE "$out/serial-$cpu.txt"; grep -q 'DIFFS 0000' "$out/serial-$cpu.txt"
done
echo "MSR_IN_INTRINSICS_OK"
