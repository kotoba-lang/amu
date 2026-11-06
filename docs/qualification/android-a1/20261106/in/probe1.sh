D=/data/local/tmp/jun902; cd $D; chmod 755 root.elf
sha256sum root.elf
echo "--- context"; id -Z; ls -Z root.elf
run(){ n=$1; shift; echo "--- $n"; "$@"; echo "exit=$?"; }
S="env KEXE_CAP_RESOURCES_35=$D KEXE_STACK_BYTES=8388608"
for p in hello spin deep; do run compile-$p $S ./root.elf compile $D/$p.kotoba --target aarch64-linux --output $D/$p.elf --format static; done
ls -la *.elf; sha256sum hello.elf
run hello-exit ./hello.elf
run hello-report env KEXE_STRUCTURED_REPORT=1 ./hello.elf
run sandbox-probe env KEXE_STRUCTURED_REPORT=1 KEXE_SANDBOX_PROBE=1 ./hello.elf
run cpu1 env KEXE_STRUCTURED_REPORT=1 KEXE_CPU_SECONDS=1 ./spin.elf
run wall3 env KEXE_STRUCTURED_REPORT=1 KEXE_WALL_SECONDS=3 ./spin.elf
run stack env KEXE_STRUCTURED_REPORT=1 ./deep.elf
