D=/data/local/tmp/jun902; cd $D; chmod 755 hello.elf spin.elf deep.elf
run(){ n=$1; shift; echo "--- $n"; "$@"; echo "exit=$?"; }
run hello-exit ./hello.elf
run hello-report env KEXE_STRUCTURED_REPORT=1 ./hello.elf
run sandbox-probe env KEXE_STRUCTURED_REPORT=1 KEXE_SANDBOX_PROBE=1 ./hello.elf
run cpu1 env KEXE_STRUCTURED_REPORT=1 KEXE_CPU_SECONDS=1 ./spin.elf
run wall3 env KEXE_STRUCTURED_REPORT=1 KEXE_WALL_SECONDS=3 ./spin.elf
run stack env KEXE_STRUCTURED_REPORT=1 ./deep.elf
grep -E 'Seccomp|NoNewPrivs' /proc/self/status
