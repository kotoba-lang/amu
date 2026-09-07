#!/usr/bin/env python3
"""amu-rank iteration 107: rank-only pass, host busy — append to docs/codegen-cosientist.md."""
import datetime, pathlib

p = pathlib.Path("docs/codegen-coscientist.md")
t = p.read_text()
entry = """- **107 (2026-09-04 16:13 JST, rank pass; host busy, no measurement)**:
  load1 56.56 / 5min 45.37 / 15min 37.98 (up 11 days, 8:01, 6 users,
  10 CPUs) — ~7.5x above the 7.5 quiet limit; no bench, perfgate, or
  falsify measurement attempted. New evidence reviewed: ADR-0332..0334
  (UEFI alloc-region provenance, fuel-ceiling unification, BOOTX64.EFI
  page write — build-time-OS track, no measured numbers against open
  codegen hypotheses), jit-cosientist tick 10 (J-B quiet gate failed a
  10th consecutive time, still pending a quiet-host rerun),
  lang-cosientist iteration 3 (#() reader shorthand — reader-only gap,
  KIR parity CIDs identical; no codegen effect). No re-rank, no status
  transition: no new measured numbers. Population unchanged: H-C2, H-D,
  H-B, H-Y1 open. NEXT: H-C2 (unchanged — highest expected qualified
  gain x probability; ~4.4% residual vs Clang on `kernel`,
  near-identical static shape, separable).
"""
marker = "## Standing honesty constraints"
idx = t.rindex(marker)
p.write_text(t[:idx] + entry + "\n" + t[idx:])
print("appended", len(entry), "chars at", idx)
