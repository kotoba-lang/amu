from datetime import datetime
p = "docs/codegen-cosientist.md"
ts = datetime.now().strftime("%Y-%m-%d %H:%M JST")
line = f"- [{ts}] amu-falsify tick: host busy (load1 10.72 > 7.5, 1min avg) — no measurement run this tick; no hypothesis advanced.\n"
with open(p, "a") as f:
    f.write(line)
print("appended:", line)
