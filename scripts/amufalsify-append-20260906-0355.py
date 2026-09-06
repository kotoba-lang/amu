#!/usr/bin/env python3
"""amu-falsify 2026-09-06 03:5x JST: append H-C2 static instruction-order-diff evidence."""
path = 'docs/codegen-coscientist.md'
text = open(path, encoding='utf-8').read()
line = ("2026-09-06 03:55 JST (amu-falsify cron, STATIC only — load-robust; sustained-window probe 03:46-03:50 was NOT quiet: load1 4.67-8.47 with 2/8 samples over gate 7.5 and iostat idle 17-73% of 10 CPUs, idle>=9/10 never met, so no timed run; no bench, no perfgate run, no timing numbers): "
        "ran H-C2's queued instruction-order diff statically. Recompiled bench/runtime-comparison/kernel.kotoba -> aarch64-kotoba-v1 kexe and decoded the `kernel` export (offset 0, length 244B) as 61 aarch64 instructions; disassembled clang -O2 -arch arm64 kernels.c for _kotoba_bench_kernel (0x34-0x124 = 61 instructions). "
        "FINDINGS: (1) amu-mut kernel is now 61 instructions — the earlier 62 vs 61 shape gap is GONE; (2) the now-dead `0x7fffffff` constant load is GONE from the emission — the stream opens movz 48271 / mov 1 and thereafter uses only register-resident madd/mulhi/asr/sub/add modulo steps, no LDR literal, no sdiv; "
        "(3) clang's stream is also 61 instructions (one mov/movk constant pair hoisted, then smulh;add;asr;add;sub;add per round; madd for the multiply). Both streams are equal-length, sdiv-free, and differ only in per-round scheduling order (amu: madd,mulhi,add,asr,add,sub,add vs clang: madd,smulh,add,asr,add,sub,add — amu materializes an extra intermediate add the clang stream folds). "
        "H-C2's premise (residue is scheduling/front-end shaped, not extra instructions) is STATICALLY CONFIRMED at equal 61/61; the timed verdict (~4.4% vs clang) still requires a quiet-host A/B and remains deferred per quiet-gate rule. No compiler change made. NEXT unchanged: J-B fully-quiet-host rerun (idle>=9/10, sustained-window), then H-Z3 quiet-host hand-patch A/B, then H-C2 timed A/B.\n")
if '2026-09-06 03:55 JST (amu-falsify cron, STATIC only' not in text:
    open(path, 'a', encoding='utf-8').write(line)
    print("appended")
else:
    print("already present")
