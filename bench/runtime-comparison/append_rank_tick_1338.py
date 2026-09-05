import re
import subprocess
from datetime import datetime, timezone, timedelta

PATH = "docs/codegen-coscientist.md"
TICK = "bench/runtime-comparison/append_hc2_busy_tick_1335.py"

# Host load, measured live (NOT from the pre-run script snapshot).
up = subprocess.run(["uptime"], capture_output=True, text=True).stdout.strip()
m = re.search(r"load averages: ([\d.]+) ([\d.]+) ([\d.]+)", up)
assert m, f"unexpected uptime output: {up!r}"
l1, l5, l15 = m.group(1), m.group(2), m.group(3)

now = datetime.now(timezone(timedelta(hours=9)))
ts = now.strftime("%Y-%m-%d %H:%M JST")

ratio = float(l1) / 7.5
entry = (
    f"- **96 ({ts}, rank pass; host busy, no measurement)**:\n"
    f"  load1 {l1} / 5min {l5} / 15min {l15} (up 11 days, 5:26, 9 users, 10\n"
    f"  CPUs) — ~{ratio:.1f}x above the 7.5 quiet limit; per policy no bench,\n"
    f"  perfgate, or hand-patch measurement attempted, no numbers recorded.\n"
    f"  git fetch reviewed: one new commit since ef7ac8dd — 532e9891\n"
    f"  (amu-falsify busy-tick evidence append to H-C2, itself no\n"
    f"  measurement). No new measured numbers against any open hypothesis\n"
    f"  (H-C2, H-D, H-B, H-Y1), so no re-rank, no status transition, no new\n"
    f"  hypothesis — a re-rank without measured numbers would be fabrication.\n"
    f"  Population unchanged. NEXT: H-C2 (unchanged — highest expected\n"
    f"  qualified gain × probability; ~4.4% residual vs Clang on `kernel`,\n"
    f"  near-identical static shape, separable).\n"
)

with open(PATH, "r", encoding="utf-8") as f:
    text = f.read()

anchor = "## Standing honesty constraints"
assert anchor in text and "- **96 (" not in text, "anchor missing or entry already present"
text = text.replace(anchor, entry + "\n" + anchor, 1)

with open(PATH, "w", encoding="utf-8") as f:
    f.write(text)

print("appended iteration 96 at", ts, "load", l1, l5, l15)
