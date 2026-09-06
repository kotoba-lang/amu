import datetime

path = 'docs/codegen-coscientist.md'
entry = (
    " | 2026-09-06 14:2x JST falsify tick: H-C2 timed A/B EXECUTED but "
    "quiet-gate FAILED mid-run — window closed. Setup: quiet window at 14:00-14:03 "
    "(9/9 samples load1 4.89-6.85 < 7.5); bin/amu compile bench/runtime-comparison/"
    "kernel.kotoba --target aarch64-kotoba-v1 (ok) -> amu extract-native --symbol "
    "kernel -> /private/tmp/hc2_amu_kernel.bin (offset 0, length 244, arity 1 — "
    "matches the 03:55 static diff); clang -O2 -arch arm64 -dynamiclib kernels.c "
    "(_kotoba_bench_kernel @0x364); both arms 5,000,000 calls, warmup 50,000, "
    "result checksum-agrees (1830338420 both arms). Numbers are NOT a verdict: "
    "load spiked to 98-119 (load1) during the runs (verified per-trial tail "
    "samples 114.02/112.94/99.79/106.03/99.35), so per quiet-gate policy these "
    "are recorded as busy-host pollution only, no perfgate or claim. Raw run "
    "elapsedNanoseconds per 5M calls: 248676000 / 335224000 / 270463000 / "
    "553063000 / 200306000; clang dylib: 405814000 / 523135000 / 306612000 / "
    "757273000 / 310726000. Interesting but untrusted shape: amu-mut raw arm "
    "came in FASTER than clang dylib in 5/5 polluted trials (raw-vs-dylib "
    "calling-convention confound uncontrolled — raw arm skips dlopen/dlsym "
    "dispatch layout, so this is not evidence of a codegen win). Verdict NOT "
    "recorded: requires a re-run with a sustained quiet window that holds "
    "through all trials. NEXT unchanged: H-C2 timed A/B re-run (quiet-host "
    "only), then H-Z3 quiet-host hand-patch A/B."
)

txt = open(path).read()
lines = txt.splitlines()
target = None
for i, l in enumerate(lines):
    if l.startswith('| H-C2 | the remaining ~4.4% vs Clang'):
        target = i
        break
if target is None:
    raise SystemExit('H-C2 row not found')
lines[target] = lines[target] + entry
open(path, 'w').write('\n'.join(lines) + '\n')
print('appended to line', target + 1)
