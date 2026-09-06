import datetime, io, os

path = "/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md"
now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
ts = now.strftime("%Y-%m-%d %H:%M JST")

entry = f"""- **121 ({ts}, bench pass; host busy, no measurement)**:
  bench tick. Host state at tick (probe via foreground `uptime > /tmp`
  + read_file; output non-empty this tick): load1 14.61 / 5m 19.36 /
  15m 22.67, up 5:32, 12 users — load1 well above the 7.5 quiet limit
  and sustained across all three windows, so the quiet gate failed.
  The NEXT item (J-B fully-quiet-host rerun of
  `bench/runtime-comparison/jb_imod_control.c`, idle >=9/10) was not
  attempted and no bench or perfgate numbers were recorded. amu-falsify
  evidence checked via the iteration log: no new "要 quiet-host 測定"
  item pending. Population unchanged: H-C2, H-D, H-B, H-Y1 open;
  J-B confirmed-diagnostic (14 consecutive positive windows across 5)
  but unqualified, still awaiting the idle>=9/10 rerun; J-C blocked
  behind it. NEXT unchanged (entry 102 re-rank stands).
"""

with io.open(path, "r", encoding="utf-8") as f:
    txt = f.read()
if not txt.endswith("\n"):
    txt += "\n"
txt += entry
with io.open(path, "w", encoding="utf-8") as f:
    f.write(txt)
print("appended", len(entry), "chars; size", os.path.getsize(path))
