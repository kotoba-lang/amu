#!/usr/bin/env python3
"""design-verify-s242.py -- THE CAUSE-RESOLUTION ACT PRE-REGISTRATION'S
DESIGN-VERIFICATION (amu-gpu s242; JUN-55, JUN-59; Linear tracking JUN-499).

ROW: the s241 carry-forward's QUEUED row -- "the cause-resolution act's
PRE-REGISTRATION OPENING -- ROW DECISION ONLY (the act's design decisions
and its OWN protocol freeze BEFORE any hardware number; its measurement
half needs new runs on aiueos-6600hs)" -- TAKEN AS ITS ROW.

This script is a VERIFIER ONLY: it verifies, fail-closed, that (A) every
committed fact the frozen protocol quotes is carried verbatim BOTH in
docs/evidence/gpu/anv-b3causeprereg-20261103/protocol.txt AND in the
named committed report bytes, (B) the row-provenance quote binds to the
committed chain git history and the quoted reference arithmetic
re-derives from the committed rows, (C) the protocol carries every frozen
arm / rule / outcome branch / limitation and the frozen sample-row forms,
and (D) the freeze integrity holds (protocol pin; NO act run log exists
in this directory -- no '*.txt.gz', no 'run-*' file, no '*.sh').

It measures NOTHING on hardware (no runs, no builds, NO GO stamp); it
parses committed bytes and the protocol bytes only.  Deterministic
output; the criterion bytes are frozen in this file BEFORE any of its
numbers existed (they are all committed-row re-derivations or presence
checks).  PATTERN-LEVEL ONLY (s218 2(e)): NO p-value, NO test statistic,
NO probability claim.
"""

import hashlib
import pathlib
import re
import subprocess
import sys

SCRIPT = pathlib.Path(__file__).resolve()
DIR = SCRIPT.parent
ROOT = SCRIPT.parents[4]
PROTO = DIR / "protocol.txt"

# The protocol pin (D1): sha256 of protocol.txt as frozen at s242.
PROTO_SHA256 = "f1d500623a98693c71c3a04e4b29f15f86fda2069cf832f0de7f6ad82380f709"

# The row-provenance quote (B1), bound to the committed git history.
ROW_QUOTE = (
    "the cause-resolution act's PRE-REGISTRATION OPENING -- ROW DECISION ONLY "
    "(the act's design decisions and its OWN protocol freeze BEFORE any hardware "
    "number; its measurement half needs new runs on aiueos-6600hs)."
)

# (A) the quote pins: (committed file, verbatim quote) -- each quote must
# appear BOTH in protocol.txt and in the named committed bytes.
QUOTES = [
    ("docs/evidence/gpu/anv-b3control3state-20261102/identity-shape-s234-run1.txt",
     "(a): ['s158', 's185', 's197']"),
    ("docs/evidence/gpu/anv-b3control3state-20261102/identity-shape-s234-run1.txt",
     "(b): ['s169', 's209', 'act-rd1', 'act-rd2', 'act-rd3', 'act-rd4']"),
    ("docs/evidence/gpu/anv-b3control3state-20261102/identity-shape-s234-run1.txt",
     "W_in  = max within-group L1 = 13.6458 (s209 vs act-rd4)"),
    ("docs/evidence/gpu/anv-b3control3state-20261102/identity-shape-s234-run1.txt",
     "W_out = min between-group L1 = 178.6875 (s158 vs act-rd4)"),
    ("docs/evidence/gpu/anv-b3control3state-20261102/identity-shape-s234-run1.txt",
     "SHAPES SEPARATE (W_out 178.6875 > W_in 13.6458)."),
    ("docs/evidence/gpu/anv-b3control3state-20261102/crosscell-extent-s238-run1.txt",
     "EXTENT ROW: WHOLE-STREAM -- the (a)/(b) sample-shape"),
    ("docs/evidence/gpu/anv-b3control3state-20261102/crosscell-extent-s238-run1.txt",
     "REFUTED at 18 of 18 cells"),
    ("docs/evidence/gpu/anv-b3control3state-20261102/crosscell-extent-s238-run1.txt",
     "(a) shape at the reading cell (top1 65.0868% vs 52.3472%)."),
    ("docs/evidence/gpu/anv-b3control3state-20261102/crosscell-extent-s238-run1.txt",
     "CAUSE DICHOTOMY: NOT DECIDED -- both surviving candidates are"),
    ("docs/evidence/gpu/anv-b3control3state-20261102/crosscell-extent-s238-run1.txt",
     "whole-stream states (an execution-time state of the whole"),
    ("docs/evidence/gpu/anv-b3control3state-20261102/crosscell-extent-s238-run1.txt",
     "dispatch stream vs an instrument/timestamp-quantization state"),
    ("docs/evidence/gpu/anv-b3control3state-20261102/crosscell-extent-s238-run1.txt",
     "of the whole recording)."),
    ("docs/evidence/gpu/anv-b3control3state-20261102/crosscell-extent-s238-run1.txt",
     "metadata is byte-identical across all 27 runs of both letter"),
    ("docs/evidence/gpu/anv-b3control3state-20261102/crosscell-extent-s238-run1.txt",
     "groups (section 1: 8 header lines, timestampPeriod=52.083"),
    ("docs/evidence/gpu/anv-b3control3state-20261102/crosscell-extent-s238-run1.txt",
     "# instrument=anv-subgroupsize-batch v2-batch64 (JUN-59 subgroup 16-vs-32 floor-lifting rerun, 2026-10-27)"),
    ("docs/evidence/gpu/anv-b3control3state-20261102/crosscell-extent-s238-run1.txt",
     "# timestampPeriod=52.083 timestampComputeAndGraphics=1"),
    ("docs/evidence/gpu/anv-b3control3state-20261102/host-shape-s239-run1.txt",
     "SHAPES DO NOT SEPARATE (W_out 10.1667 <= W_in 39.7917)."),
    ("docs/evidence/gpu/anv-b3control3state-20261102/host-extent-s240-run1.txt",
     "EXTENT ROWS: NO-CELL (no host-channel letter-group shape"),
    ("docs/evidence/gpu/anv-b3control3state-20261102/run-temporal-s241-run1.txt",
     "run-level summary: class a 9 / b 18 / UNDECIDED 0; NEAR-NEITHER flags 0 of 27 (report-only)"),
    ("docs/evidence/gpu/anv-b3control3state-20261102/run-temporal-s241-run1.txt",
     "K=64 summary: class-uniform runs 27/27; runs carrying >=1 transition or UNDECIDED 0/27; total transitions 0; UNDECIDED blocks 0 of 1728; NEAR-NEITHER blocks 586 of 1728 (report-only)"),
    ("docs/evidence/gpu/anv-b3control3state-20261102/run-temporal-s241-run1.txt",
     "letter class.  The (a)/(b) difference's temporal locus is"),
    ("docs/evidence/gpu/anv-b3control3state-20261102/run-temporal-s241-run1.txt",
     "candidate is CONTRADICTED at 100-round granularity."),
    ("docs/evidence/gpu/anv-b3control3state-20261102/run-temporal-s241-run1.txt",
     "persistent variants (an execution-time state whose episodes"),
    ("docs/evidence/gpu/anv-b3control3state-20261102/run-temporal-s241-run1.txt",
     "span whole runs and a recording state whose episodes span"),
    ("docs/evidence/gpu/anv-b3control3state-20261102/run-temporal-s241-run1.txt",
     "whole runs are EQUALLY LIVE here); a cause-resolution act"),
    ("docs/evidence/gpu/anv-b3control3state-20261102/run-temporal-s241-run1.txt",
     "still needs new hardware runs, each with its own freeze."),
]

# (B4) the W_in/W_out pair rows inside the s234 pair tables.
PAIR_ROWS = [
    ("docs/evidence/gpu/anv-b3control3state-20261102/identity-shape-s234-run1.txt",
     "s209     act-rd4  13.6458", "W_in pair row"),
    ("docs/evidence/gpu/anv-b3control3state-20261102/identity-shape-s234-run1.txt",
     "s158     act-rd4  178.6875", "W_out pair row"),
]

# (C) the frozen contract tokens that must appear in protocol.txt.
CONTRACT = [
    ("C1 ARM-K sample row form",
     "SAMPLE round=<r> idx=<cell> batch=2 work_mul=1 ndiv=1 gpu_ticks=<t> gpu_ns=<x> per_dispatch_ns=<y> host_ns=<h>"),
    ("C2 ARM-Z1 sample row form",
     "PROBE round=<r> channel=zwts ticks=<d>"),
    ("C3 ARM-Z2 sample row form",
     "PROBE round=<r> channel=zwbar ticks=<d>"),
    ("C4 ARM-H sample row form",
     "PROBE round=<r> channel=isohost raw_ns=<h>"),
    ("C5 arm ids", "ARM-K"),
    ("C5 arm ids", "ARM-Z1"),
    ("C5 arm ids", "ARM-Z2"),
    ("C5 arm ids", "ARM-H"),
    ("C6 branch O1", "O1 Q-FAVOR"),
    ("C6 branch O2", "O2 E-FAVOR"),
    ("C6 branch O3", "O3 REPLICATION-FAILURE"),
    ("C6 branch O4", "O4 CONTRADICTED-CONSTRAINT"),
    ("C6 branch O5", "O5 INVALID"),
    ("C6 named outcome", "UNDECIDED-FOR-ARMS"),
    ("C6 named outcome", "UNDECIDED-DEGENERATE"),
    ("C6 named outcome", "Z-DISAGREEMENT"),
    ("C7 candidate", "CAND-E'"),
    ("C7 candidate", "CAND-Q'"),
    ("C7 limitation L1", "L1   CAND-Q' does not separate counter/quantization"),
    ("C7 limitation L2", "L2   O2 does not exclude a bracket-scheduling"),
    ("C7 limitation L3", "L3   the act's binary is a NEW build"),
    ("C7 limitation L4", "L4   probe placement effects are UNMEASURED."),
    ("C7 limitation L-Z0", "L-Z0 the Z-pair delta support may be degenerate"),
    ("C7 limitation L5", "L5   the classification carries NO noise model"),
    ("C8 rule R1", "R1 (fresh-run letters)"),
    ("C8 rule R2", "R2 (decision-bearing letters)"),
    ("C8 rule R3", "R3 (per-Z-channel split)"),
    ("C8 rule R4", "R4 (ARM-H rows)"),
    ("C8 rule R5", "R5 (run-persistence re-check)"),
    ("C9 run plan", "3 fresh sessions"),
    ("C9 run plan", "at least 2 distinct days"),
    ("C9 run plan", "n=1000003 rounds=6400 warmup=3"),
    ("C9 run plan", "aiueos-6600hs"),
    ("C9 capture form", "run-<tag>-r<NN>.txt.gz"),
    ("C10 row question", "IS THE (a)/(b) gpu_ticks SAMPLE-SHAPE STATE PRESENT IN"),
    ("C10 row qualifier", "ROW DECISION ONLY"),
    ("C11 frozen constant", "W_in = 13.6458 bound to the committed s234 row."),
    ("C11 frozen constant", "W_out^c > W_in^c"),
    ("C12 honesty", "PATTERN-LEVEL ONLY (s218 2(e)): NO\n   p-value, NO test statistic, NO probability claim."),
    ("C13 three-state", "ACCEPTED DESIGN ONLY"),
]

ok = 0
failed = 0


def check(name, cond, detail=""):
    global ok, failed
    if cond:
        ok += 1
        print("  ok    %s" % name)
    else:
        failed += 1
        print("  FAIL  %s %s" % (name, detail))


print("design-verify-s242.py -- THE CAUSE-RESOLUTION ACT PRE-REGISTRATION'S")
print("DESIGN-VERIFICATION (amu-gpu s242; quote/arithmetic verification of")
print("committed bytes + freeze integrity; NOT a measurement).")

proto_bytes = PROTO.read_bytes()
proto_text = proto_bytes.decode()

# (A) quote pins.
for i, (rel, quote) in enumerate(QUOTES, start=1):
    committed = (ROOT / rel).read_text()
    check("S242.A%02d quote binds (protocol + %s)" % (i, rel.split("/")[-1]),
          (quote in proto_text) and (quote in committed),
          detail="proto=%s committed=%s" % (quote in proto_text, quote in committed))

# (B1) row provenance binds to the committed chain git history.
git_body = subprocess.run(
    ["git", "-C", str(ROOT), "log", "-5", "--format=%B"],
    capture_output=True, text=True, check=True).stdout
check("S242.B01 row-provenance quote binds to committed git history",
      ROW_QUOTE in git_body)

# (B2) re-derive the pooled-letter L1 at the reading cell from the
# committed s234 pooled share rows; bind to the s238 D_groups row.
s234_text = (ROOT / "docs/evidence/gpu/anv-b3control3state-20261102/identity-shape-s234-run1.txt").read_text()


def parse_pool(tag):
    m = re.search(r"group \(" + tag + r"\) pooled: (.*)", s234_text)
    if m is None:
        print("  FAIL  S242.B02 pooled row (%s) not found in committed s234 bytes" % tag)
        sys.exit(1)
    d = {}
    for tok in m.group(1).split():
        k, v = tok.split(":")
        d[int(k)] = float(v)
    return d


pool_a = parse_pool("a")
pool_b = parse_pool("b")
support = sorted(set(pool_a) | set(pool_b))
l1 = sum(abs(pool_a.get(k, 0.0) - pool_b.get(k, 0.0)) for k in support)
check("S242.B02 pooled L1 re-derived %.4f == s238 D_groups 184.2153 (tol 0.005)" % l1,
      abs(l1 - 184.2153) <= 0.005)

# (B3) the sharper-(b) row: top1 shares re-derived from the pooled rows.
top_a = max(pool_a.items(), key=lambda kv: kv[1])
top_b = max(pool_b.items(), key=lambda kv: kv[1])
check("S242.B03 top1 re-derived (a) 31:52.3472 (b) 30:65.0868 == the s238 quote",
      top_a == (31, 52.3472) and top_b == (30, 65.0868),
      detail="top_a=%s top_b=%s" % (top_a, top_b))

# (B4) the W_in / W_out pair rows inside the committed pair tables.
for i, (rel, row, label) in enumerate(PAIR_ROWS, start=1):
    check("S242.B%02d %s binds (%s)" % (3 + i, label, rel.split("/")[-1]),
          row in (ROOT / rel).read_text())

# (C) the frozen contract.
for name, token in CONTRACT:
    check("S242.%s" % name, token in proto_text, detail="missing token %r" % token[:60])

# (D) freeze integrity.
check("S242.D01 protocol.txt sha256 == the frozen pin",
      hashlib.sha256(proto_bytes).hexdigest() == PROTO_SHA256)
gz = sorted(p.name for p in DIR.iterdir() if p.name.endswith(".txt.gz"))
check("S242.D02 no act run log (*.txt.gz) in this directory", not gz, detail=str(gz))
runs = sorted(p.name for p in DIR.iterdir() if p.name.startswith("run-"))
check("S242.D03 no 'run-*' capture in this directory", not runs, detail=str(runs))
shs = sorted(p.name for p in DIR.iterdir() if p.name.endswith(".sh"))
check("S242.D04 no POSIX .sh execution file in this directory", not shs, detail=str(shs))

print("# design-verify s242 (design-verify-s242.py): %d ok / %d failed" % (ok, failed))
sys.exit(0 if failed == 0 else 1)
