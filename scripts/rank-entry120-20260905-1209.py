from datetime import datetime
import zoneinfo, pathlib

path = pathlib.Path("docs/codegen-coscientist.md")
text = path.read_text(encoding="utf-8")
stamp = datetime.now(zoneinfo.ZoneInfo("Asia/Tokyo")).strftime("%Y-%m-%d %H:%M JST")

entry = f"""
- **120 ({stamp}, rank pass; host busy, no measurement)**:
  amu-rank tick. Host state at tick (foreground terminal empty as usual,
  evidence collected via /tmp probe files): load1 27.69 / 5m 24.48 /
  15m 25.18, up 4:52, 12 users, 10 CPUs — load1 far above the 7.5 quiet
  limit and sustained across all three windows, so the quiet gate failed
  and no measurement was attempted; no numbers recorded. Evidence
  reviewed since entry 119: one new landing, a8275805 (lang-cosientist
  iteration 7, some-> desugar correctness work in docs/lang-cosientist.md)
  — correctness-only, no perfgate or bench number, no bearing on the
  codegen hypothesis population; no re-rank. ADR 0338 re-read: J-B remains
  14 consecutive positive windows across 5, diagnostic-only, still blocked
  on the fully-quiet-host (idle >= 9/10) rerun; today's host state makes
  that rerun again impossible this tick. Population unchanged: H-C2, H-D,
  H-B, H-Y1 open; J-B confirmed-diagnostic but unqualified; J-C blocked
  behind it. No evidence-based status transition exists this tick, so none
  was made. NEXT: J-B fully-quiet-host rerun (idle >= 9/10) of
  `bench/runtime-comparison/jb_imod_control.c` for the perfgate-qualifiable
  number (entry 102 re-rank stands); lever-2-only control (non-inlined
  mulh arm) follows it once a quiet host is available.
"""
path.write_text(text.rstrip("\n") + entry, encoding="utf-8")
print("entry 120 appended")
