import io
p = "/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md"
entry = "2026-09-05 19:53 JST (amu-bench cron, tick 125): host busy (load1 36.16 / 5m 32.55 / 15m 35.73 at 19:53, threshold 7.5) — measurement refused, no bench/perfgate run, no numbers. NEXT unchanged: J-B fully-quiet-host rerun (idle>=9/10) of bench/runtime-comparison/jb_imod_control.c, then H-Z3 quiet-host hand-patch A/B, then H-C2. Population unchanged: J-B confirmed-diagnostic but unqualified, H-Z3 top of the codegen ladder (quiet-host A/B pending), H-C2/H-D/H-B/H-Y1 open; J-C blocked behind J-B.\n"
s = io.open(p, encoding="utf-8").read()
m = s.rfind("## Standing honesty constraints")
assert m != -1
s = s[:m] + entry + "\n" + s[m:]
io.open(p, "w", encoding="utf-8").write(s)
print("appended", len(entry))
