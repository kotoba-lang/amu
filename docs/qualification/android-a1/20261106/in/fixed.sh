D=/data/local/tmp/jun902; cd $D; rm -f F1.kseed F1.elf
E="env KEXE_CAP_RESOURCES_35=$D KEXE_STACK_BYTES=8388608"
hw(){ pid=$1; m=0; while [ -r /proc/$pid/status ]; do v=$(grep VmHWM /proc/$pid/status 2>/dev/null | tr -s ' \t' ' ' | cut -d' ' -f2); [ -n "$v" ] && [ "$v" -gt "$m" ] && m=$v; sleep 1; done; echo "peakRSSkB=$m"; }
s=$(date +%s); $E ./root.elf compile $D/full-unity.kotoba --target aarch64-macos --output $D/F1.kseed & p=$!; hw $p & h=$!; wait $p; echo "F1-compile exit=$? seconds=$(( $(date +%s)-s ))"; wait $h
s=$(date +%s); $E ./root.elf compile $D/runner.kotoba --target aarch64-linux --output $D/F1.elf --format packed --payload $D/F1.kseed; echo "F1-pack exit=$? seconds=$(( $(date +%s)-s ))"; chmod 755 F1.elf
sha256sum root.elf F1.kseed F1.elf; ls -l root.elf F1.kseed F1.elf
cmp root.elf F1.elf && echo ROOT_REPRODUCES || echo ROOT_DIFFERS
