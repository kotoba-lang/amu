import datetime

entry = ("| 2026-09-06 00:24 JST (amu-bench cron): host busy — J-B fully-quiet-host rerun NOT attempted. "
         "Measurement window observation 00:16-00:24 (4 min sustained, 8 x 30s samples): load1 7.72->6.94->4.02->3.25 "
         "(00:16-00:19) looked like an opening window, but then spiked 14.58->30.32 (00:20-00:21) before decaying "
         "7.07 at 00:23; only 2/8 samples below threshold 7.5, no sustained quiet window (idle>=9/10 not observable). "
         "No bench, no perfgate, no numbers recorded. Probes via /tmp scripts (no heredoc), entry via append script "
         "per entry-117 convention. NEXT unchanged: J-B fully-quiet-host rerun (idle>=9/10) of "
         "bench/runtime-comparison/jb_imod_control.c, then H-Z3 quiet-host hand-patch A/B, then H-C2. "
         "Population unchanged: J-B confirmed-diagnostic but unqualified, H-Z3 top of the codegen ladder, "
         "H-C2/H-D/H-B/H-Y1 open; J-C blocked behind J-B.\n")

path = '/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md'
with open(path, 'r', encoding='utf-8') as f:
    doc = f.read()

marker = '## Standing honesty constraints'
idx = doc.rfind(marker)
if idx == -1:
    raise SystemExit('marker not found')

new_doc = doc[:idx] + entry + '\n' + doc[idx:]
with open(path, 'w', encoding='utf-8') as f:
    f.write(new_doc)

# verify read-back
with open(path, 'r', encoding='utf-8') as f:
    check = f.read()
ok = 'amu-bench cron): host busy — J-B fully-quiet-host rerun NOT attempted' in check and marker in check
print('appended, verify:', ok, 'len:', len(check))
