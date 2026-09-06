import datetime, pathlib
p = pathlib.Path("docs/codegen-coscientist.md")
now = datetime.datetime.now().astimezone()
line = (
    f"\n{now:%Y-%m-%d %H:%M} JST (amu-falsify cron): host busy "
    "(load1 95.81 / 5m 71.91 / 15m 65.71 at 06:44, threshold 7.5) — timed "
    "measurement refused per quiet-gate rule; H-Z3 hand-patch A/B and all "
    "timed hypotheses unattemptable this tick. No bench, no perfgate run, "
    "no numbers. NEXT unchanged (H-Z3 quiet-host hand-patch A/B).\n"
)
with p.open("a", encoding="utf-8") as f:
    f.write(line)
print("appended", len(line), "chars")
