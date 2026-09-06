#!/usr/bin/env python3
"""amu-falsify 2026-09-06 04:13 JST: append sustained-window busy-refusal evidence."""
path = 'docs/codegen-coscientist.md'
text = open(path, encoding='utf-8').read()
line = ("2026-09-06 04:13 JST (amu-falsify cron): host busy under sustained-window protocol (8x~30s samples, 04:09:33-04:12:51 JST): "
        "load1 11.45-18.23 in ALL 8 samples (threshold 7.5, 0/8 below gate; rising 11.45->18.23 then partially decaying to 12.05), "
        "load5 11.62-14.17, load15 14.12-14.83, iostat idle 42-61% of 10 CPUs (idle>=9/10 never met). "
        "Per quiet-gate policy the J-B idle>=9/10 sustained-window rerun of bench/runtime-comparison/jb_imod_control.c and the H-Z3 hand-patch A/B were NOT started; "
        "no bench, no perfgate run, no numbers. Note: foreground terminal again returned empty output (known shape, entries 96/99/104 etc.); "
        "probes via script + file redirect, doc edit via python script (no heredoc, per the entry-117 convention). "
        "NEXT unchanged: J-B fully-quiet-host rerun (idle>=9/10, sustained-window protocol), then H-Z3 quiet-host hand-patch A/B, then H-C2 timed A/B. "
        "Population unchanged: J-B confirmed-diagnostic but unqualified, H-Z3 top of the codegen ladder, H-C2 statically confirmed but timed A/B pending, H-D/H-B/H-Y1 open; J-C blocked behind J-B.\n")
if '2026-09-06 04:13 JST (amu-falsify cron): host busy under sustained-window protocol' not in text:
    open(path, 'a', encoding='utf-8').write(line)
    print("appended")
else:
    print("already present")
