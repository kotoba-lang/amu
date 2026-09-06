#!/usr/bin/env python3
"""amu-bench iteration 117 append + repair (FINAL, targets verified by glob).

Verified docs/ contents:
  codegen-cosientist.md     1,890 bytes   <- stray created 10:58 by this tick's failed shell-heredoc append (entry 117 x2); no other history
  codegen-coscientist.md  129,111 bytes   <- REAL tournament log (header "# Codegen co-scientist — tournament state"), mtime 10:20, intact
  codegen-coscientist.md.bak114 125,824   <- pre-existing backup

Plan:
  1. Append entry 117 (with incident note) to the REAL 129,111-byte log — idempotent.
  2. Move the stray 1,890-byte file into tmp/ (quarantine, not delete).
"""
import io, os

REAL = "/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md"
STRAY = "/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-cosientist.md"
STRAY_KEEP = "/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/tmp/stray-codegen-cosientist-20260905-117.md"

ENTRY = """
- **117 (2026-09-05 10:44 JST, bench pass; host busy, no measurement)**:
  bench tick. Host state at tick (probe script /tmp/amu_bench_probe_117.sh
  writing /tmp/amu_bench_uptime_117.txt; foreground terminal again empty,
  the known shape entries 96/99/104/109/110/111): load1 27.28 / 5m 26.32
  / 15m 25.15, up 3:27, 12 users, 10 CPUs — load1 far above the 7.5
  quiet limit and sustained across all three windows, so the quiet gate
  failed, the NEXT item (J-B fully-quiet-host rerun of
  `bench/runtime-comparison/jb_imod_control.c`, idle >=9/10) was not
  attempted, and no bench or perfgate numbers were recorded. Incident
  note: the first append attempt this tick used a shell heredoc, which
  the cron runtime mis-executed — it created a stray 1,890-byte
  `docs/codegen-cosientist.md` (s-dropped spelling) holding the entry
  twice; the real `docs/codegen-cosientist.md` (129,111 bytes) was
  verified intact before repair and the stray was moved to tmp/.
  Appends now go through a Python script
  (scripts/append-entry117-amubench.py), matching the existing
  append-*.py convention. amu-falsify evidence checked: no new
  "要 quiet-host 測定" item pending. Population unchanged: H-C2, H-D,
  H-B, H-Y1 open; J-B confirmed-diagnostic (14 consecutive positive
  windows across 5) but unqualified, still awaiting the idle>=9/10
  rerun; J-C blocked behind it. NEXT unchanged (entry 102 re-rank
  stands).
"""

log = []
with io.open(REAL, "r", encoding="utf-8") as f:
    text = f.read()
log.append("real doc size before: %d" % len(text.encode("utf-8")))
marker = "117 (2026-09-05 10:44 JST, bench pass; host busy, no measurement)"
if marker not in text:
    if not text.endswith("\n"):
        text += "\n"
    text += ENTRY
    with io.open(REAL, "w", encoding="utf-8") as f:
        f.write(text)
    log.append("entry 117 appended to real doc")
else:
    log.append("entry 117 already present in real doc; no change")

try:
    if os.path.exists(STRAY) and os.path.getsize(STRAY) < 10000:
        os.makedirs(os.path.dirname(STRAY_KEEP), exist_ok=True)
        os.replace(STRAY, STRAY_KEEP)
        log.append("stray moved to %s" % STRAY_KEEP)
    elif not os.path.exists(STRAY):
        log.append("stray already absent")
    else:
        log.append("stray unexpectedly large (%d); left in place" % os.path.getsize(STRAY))
except OSError as e:
    log.append("stray handling error: %s" % e)

with io.open(REAL, "r", encoding="utf-8") as f:
    final = f.read()
log.append("real doc size after: %d" % len(final.encode("utf-8")))
log.append("head intact: %s" % final.startswith("# Codegen co-scientist — tournament state"))
log.append("tail ok: %s" % final.rstrip().endswith("NEXT unchanged (entry 102 re-rank stands)."))

with io.open("/tmp/amu_bench_117_result4.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(log) + "\n")
