#!/usr/bin/env python3
"""impl-verify-s243.py -- the s243 implementation slice's fail-closed
verifier (JUN-59, the cause-resolution act's instrument probe
implementation: ARM-Z1/ARM-Z2/H rows added to the named Vulkan instrument
family, source captured in the committed evidence form; implementation +
capture only, NO runs, NO measurement claims).

Every check binds the committed bytes of
docs/evidence/gpu/anv-b3causeimpl-20261103/ (the instrument source, its
byte capture, manifest.json, cases.txt) against (a) the FROZEN act protocol
docs/evidence/gpu/anv-b3causeprereg-20261103/protocol.txt (sha256
f1d50062...) and (b) the committed c2 run-log byte forms of the s234
nine-window universe (27 c2 run logs) plus 3 committed c8 run logs (the
timestampPeriod discriminator).  No hardware is touched, no number here is
newly measured: every sample re-parsed below is a named run's landed
MEASURED QUANTITY on aiueos-6600hs (Intel BMG G31) under the named
instrument; the arithmetic is DERIVED.

Fail-closed: any failed check -> rc 1.  Deterministic: pure stdlib, sorted
globs, no wall clock, no locale dependence.
"""

import glob
import gzip
import hashlib
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GPU = os.path.dirname(HERE)                      # docs/evidence/gpu
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(GPU)))  # chain root

SRC = os.path.join(HERE, "gpu-subgroup-reduce-anv-causeprobe.c")
CAP = os.path.join(HERE, "gpu-subgroup-reduce-anv-causeprobe.c.txt")
MAN = os.path.join(HERE, "manifest.json")
CASES = os.path.join(HERE, "cases.txt")
PROTOCOL = os.path.join(GPU, "anv-b3causeprereg-20261103", "protocol.txt")
BASE = os.path.join(GPU, "anv-instrument-source-snapshots-20261027",
                    "gpu-subgroup-reduce-anv-subgroupsize-batch.c.txt")
CASES_COMMITTED = os.path.join(GPU, "anv-subgroupsize-batch64-20261027", "cases.txt")

PROTO_SHA = "f1d500623a98693c71c3a04e4b29f15f86fda2069cf832f0de7f6ad82380f709"
PROTO_BYTES = 16913
BASE_SHA = "34d56fa11831cbb3ea0ef61a5580f10689ae6af25f15912d731182e6efd51e06"
BASE_BYTES = 27780
SEED = 20261027

# The s234 nine-window universe: (label, run dir, run name pattern)
WINDOWS = [
    ("s158", "anv-b3bisect15-20261101", "run-c2-r0{}.txt.gz"),
    ("s169", "anv-b3bisect16-20261101", "run-c2-r0{}.txt.gz"),
    ("s185", "anv-b3bisect17-20261101", "run-c2-r0{}.txt.gz"),
    ("s197", "anv-b3bisect18-20261101", "run-c2-r0{}.txt.gz"),
    ("s209", "anv-b3bisect19-20261102", "run-c2-r0{}.txt.gz"),
    ("act-rd1", "anv-b3control3state-20261102", "run-rd1-c2-r0{}.txt.gz"),
    ("act-rd2", "anv-b3control3state-20261102", "run-rd2-c2-r0{}.txt.gz"),
    ("act-rd3", "anv-b3control3state-20261102", "run-rd3-c2-r0{}.txt.gz"),
    ("act-rd4", "anv-b3control3state-20261102", "run-rd4-c2-r0{}.txt.gz"),
]
# The timestampPeriod discriminator universe: the committed c8 knob set
# (batch=8, high tick counts discriminate the period float).
C8_LOGS = [("c8-rd1-r0%d" % k,
            os.path.join(GPU, "anv-b3control3state-20261102",
                         "run-rd1-c8-r0%d.txt.gz" % k)) for k in (1, 2, 3)]

oks = 0
fails = 0
report = []


def check(label, cond, detail=""):
    global oks, fails
    if cond:
        oks += 1
        report.append("ok   %s" % label)
    else:
        fails += 1
        report.append("FAIL %s%s" % (label, (" -- " + detail) if detail else ""))


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def f32(x):
    return struct.unpack("f", struct.pack("f", x))[0]


# ---------------------------------------------------------------- section 1
# capture / manifest pins

src_bytes = open(SRC, "rb").read()
cap_bytes = open(CAP, "rb").read()
check("S1.1 capture bytes == implementation bytes", cap_bytes == src_bytes)
check("S1.2 implementation is non-empty", len(src_bytes) > 1000)

man = json.load(open(MAN))
src_row = man["sources"][0]
check("S1.3 manifest bytes row == implementation length",
      src_row["bytes"] == len(src_bytes), "row %d vs %d" % (src_row["bytes"], len(src_bytes)))
check("S1.4 manifest sha256 row == implementation sha256",
      src_row["sha256"] == hashlib.sha256(src_bytes).hexdigest())
check("S1.5 manifest snapshotPath names the committed capture",
      src_row["snapshotPath"].endswith("anv-b3causeimpl-20261103/gpu-subgroup-reduce-anv-causeprobe.c.txt"))
check("S1.6 manifest channel is INSTRUMENT", man.get("channel") == "INSTRUMENT")
check("S1.7 manifest asserts no binary built / no runs",
      man.get("binaryBuilt") is False and "measuring session" in man.get("runs", ""))

base_bytes_disk = open(BASE, "rb").read()
check("S1.8 family base snapshot length == %d" % BASE_BYTES,
      len(base_bytes_disk) == BASE_BYTES)
check("S1.9 family base snapshot sha256 == committed pin",
      hashlib.sha256(base_bytes_disk).hexdigest() == BASE_SHA)
check("S1.10 manifest derivedFrom row binds the family base",
      man["derivedFrom"]["sha256"] == BASE_SHA and man["derivedFrom"]["bytes"] == BASE_BYTES)

hist = json.load(open(os.path.join(GPU, "anv-instrument-source-snapshots-20261027",
                                   "manifest.json")))
hist_row = [s for s in hist["sources"]
            if s["originalPath"].endswith("gpu-subgroup-reduce-anv-subgroupsize-batch.c")][0]
check("S1.11 the historical manifest's own base row == this base pin",
      hist_row["sha256"] == BASE_SHA and hist_row["bytes"] == BASE_BYTES)

# ---------------------------------------------------------------- section 2
# frozen-protocol pins

proto_bytes = open(PROTOCOL, "rb").read()
check("S2.1 frozen protocol length == %d" % PROTO_BYTES, len(proto_bytes) == PROTO_BYTES)
check("S2.2 frozen protocol sha256 == freeze pin",
      hashlib.sha256(proto_bytes).hexdigest() == PROTO_SHA)
proto_text = proto_bytes.decode("utf-8")

# The frozen row forms (protocol section 4) must be realized by the source's
# printf forms (field-for-field).
src_text = src_bytes.decode("utf-8")
FORMS = [
    ("PROBE round=<r> channel=zwts ticks=<d>",
     'printf("PROBE round=%d channel=zwts ticks=%llu\\n"'),
    ("PROBE round=<r> channel=zwbar ticks=<d>",
     'printf("PROBE round=%d channel=zwbar ticks=%llu\\n"'),
    ("PROBE round=<r> channel=isohost raw_ns=<h>",
     'printf("PROBE round=%d channel=isohost raw_ns=%llu\\n"'),
    ("SAMPLE round=<r> idx=<cell> batch=2 work_mul=1 ndiv=1 gpu_ticks=<t> gpu_ns=<x> per_dispatch_ns=<y> host_ns=<h>",
     'printf("SAMPLE round=%d idx=%d batch=%d work_mul=%d ndiv=%d gpu_ticks=%llu gpu_ns=%.1f per_dispatch_ns=%.2f host_ns=%llu\\n"'),
]
for i, (frozen, fmt) in enumerate(FORMS):
    check("S2.%d frozen form present in protocol AND realized by source (%s)"
          % (3 + i, frozen.split("channel=")[-1] if "channel=" in frozen else "SAMPLE"),
          frozen in proto_text and fmt in src_text)

# The instrument identity line: printed BYTE-IDENTICAL because protocol 1c
# requires ARM-K to reproduce the committed metadata exactly.
IDENT = ("# instrument=anv-subgroupsize-batch v2-batch64 "
         "(JUN-59 subgroup 16-vs-32 floor-lifting rerun, 2026-10-27)")
check("S2.7 instrument identity literal in source == the committed c2 header line 1 form",
      ('printf("%s\\n")' % IDENT) in src_text)
check("S2.8 protocol section-1c metadata quote present in the frozen bytes",
      IDENT in proto_text)

# The act's frozen knob values (protocol section 4 ARM-K).
for name, val in [("ROUNDS", "6400"), ("WARMUP", "3"), ("BATCH", "2"),
                  ("BARRIER_N", "0"), ("WORK_MUL", "1"), ("NDIV", "1"),
                  ("SEED", "20261027u"), ("N_ELEMENTS", "1000003u")]:
    check("S2.9.%s knob #define %s = %s (the act's frozen set)" % (name, name, val),
          ("#define %s %s" % (name, val)) in src_text)

# ---------------------------------------------------------------- section 3
# placement / semantics token pins in the source

roundloop_start = src_text.index("for (int r = 0; r < ROUNDS; r++) {")
roundloop_end = src_text.index("/* ---- correctness, inside the run ---- */")
loop = src_text[roundloop_start:roundloop_end]
marks = ["probe_zpair(&d1, &d2);",
         'printf("PROBE round=%d channel=zwts ticks=%llu\\n"',
         'printf("PROBE round=%d channel=zwbar ticks=%llu\\n"',
         "submit_timed(c->pipeline, playout, dset, c->groups, &ticks, &host);",
         "probe_isohost(reading->pipeline, reading->groups, &h);",
         'printf("PROBE round=%d channel=isohost raw_ns=%llu\\n"']
pos = [loop.find(m) for m in marks]
check("S3.1 frozen placement order in the round loop "
      "(Z1/Z2 rows -> ARM-K stream -> H row at round end)",
      all(p >= 0 for p in pos) and pos == sorted(pos),
      "positions %s" % pos)

zpair_start = src_text.index("static void probe_zpair(")
zpair = src_text[zpair_start:src_text.index("/* ---- ACT ARM-H probe")]
ts_calls = re.findall(r"vkCmdWriteTimestamp\(cmd, (\w+), querypool, (\d)\);", zpair)
check("S3.2 Z1 pair: two vkCmdWriteTimestamp calls back to back, SAME stage, queries 2 then 3",
      ts_calls[:2] == [("VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT", "2"),
                       ("VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT", "3")], str(ts_calls))
between_z1 = zpair[zpair.index("querypool, 2);"):zpair.index("querypool, 3);")]
check("S3.3 Z1 pair has NO command between the two timestamps",
      "vkCmd" not in between_z1.replace("vkCmdWriteTimestamp", ""))
check("S3.4 Z2 pair: TOP_OF_PIPE q4 then BOTTOM_OF_PIPE q5",
      ts_calls[2:] == [("VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT", "4"),
                       ("VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT", "5")], str(ts_calls))
between_z2 = zpair[zpair.index("querypool, 4);"):zpair.index("querypool, 5);")]
n_bar = between_z2.count("vkCmdPipelineBarrier")
n_other = between_z2.count("vkCmd") - n_bar - between_z2.count("vkCmdWriteTimestamp")
check("S3.5 Z2 has exactly ONE vkCmdPipelineBarrier and no other command between its timestamps",
      n_bar == 1 and n_other == 0, "bar=%d other=%d" % (n_bar, n_other))
check("S3.6 Z2 barrier is empty (zero memory barriers, zero access masks, "
      "TOP_OF_PIPE -> BOTTOM_OF_PIPE)",
      "vkCmdPipelineBarrier(cmd, VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT," in between_z2
      and "VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT, 0," in between_z2
      and "0, &mb, 0, NULL, 0, NULL);" in between_z2
      and "memset(&mb, 0, sizeof mb);" in between_z2)

isohost = src_text[src_text.index("static void probe_isohost("):
                   src_text.index("int main(")]
check("S3.7 ARM-H times with CLOCK_MONOTONIC_RAW (the frozen host clock)",
      "clock_gettime(CLOCK_MONOTONIC_RAW, &ts)" in src_text
      and "now_raw_ns()" in isohost)
check("S3.8 ARM-H bracket is submit->completion by BUSY POLLING a fence",
      "while (vkGetFenceStatus(device, isohost_fence) != VK_SUCCESS)" in isohost
      and "vkQueueWaitIdle" not in isohost)
check("S3.9 ARM-H submits exactly ONE dispatch (batch=1)",
      isohost.count("vkCmdDispatch(cmd, groups, 1, 1);") == 1)
check("S3.10 ARM-H reading-cell selection is fail-closed (op=sum wg=128 forced=16)",
      'strcmp(c->op, "sum") == 0 && c->wg == 128 && c->forced == 16 && c->pipeline_ok' in src_text
      and 'die("reading cell (op=sum wg=128 forced=16) missing or failed");' in src_text)

timed = src_text[src_text.index("static void submit_timed("):
                 src_text.index("/* ---- ACT ARM-Z1 + ARM-Z2 probe")]
check("S3.11 ARM-K host_ns keeps the committed CLOCK_MONOTONIC submit->completion form",
      "*host_ns = now_ns() - t0;" in timed
      and "clock_gettime(CLOCK_MONOTONIC, &ts)" in src_text
      and "clock_gettime(CLOCK_MONOTONIC_RAW" not in timed)
check("S3.12 ARM-K bracket byte-preserved (BATCH dispatches, BARRIER_N interleave inert at 0, "
      "TOP_OF_PIPE -> BOTTOM_OF_PIPE)",
      "for (int b = 0; b < BATCH; b++) {" in timed
      and "vkCmdDispatch(cmd, groups, 1, 1);" in timed
      and "if (b < BARRIER_N) {" in timed
      and timed.index("querypool, 0);") < timed.index("for (int b = 0;")
      < timed.index("querypool, 1);"))
check("S3.13 per-round order algorithm byte-preserved (lcg_state = SEED + round, in-place FY)",
      "lcg_state = SEED + (uint32_t)r;" in loop
      and "int j = (int)(lcg_next() % (uint32_t)(i + 1));" in loop)
check("S3.14 knob formula in source (n = floor(N_ELEMENTS * work_mul / ndiv))",
      "((uint64_t)N_ELEMENTS * (uint64_t)WORK_MUL) / (uint64_t)NDIV" in src_text)
check("S3.15 query pool carries 6 queries (K 0-1, Z1 2-3, Z2 4-5)",
      "qpci.queryCount = 6;" in src_text)
check("S3.16 source docstring pins the frozen protocol sha256 and the family base sha256",
      PROTO_SHA in src_text and BASE_SHA in src_text)
check("S3.17 source names the c2-source-absence reconstruction residual",
      "NO committed source" in src_text and "UNVERIFIABLE" in src_text)

# The source's header knob-line printf form (extracted, then bound to the
# committed header bytes in section 4).
knob_fmt = ('# n=%u rounds=%d warmup=%d batch=%d barrier_n=%d work_mul=%d '
            'ndiv=%d seed=%u metric=gpu_ns (vkCmdWriteTimestamp BATCH-dispatch '
            'bracket; per_dispatch_ns=gpu_ns/batch) +host_ns (CLOCK_MONOTONIC '
            'submit->completion)\\n')
check("S3.18 header knob-line printf form present (the committed c2 header form)",
      'printf("%s"' % knob_fmt in src_text)
CELL_FMT = ("CELL idx=%d spv=%s op=%s wg=%u forced=%s probe_size=%d probe_nsub=%d "
            "probe_wg=%d pipeline=%s void=%d void_reason=%s\\n")
check("S3.19 CELL row printf form byte-preserved from the family base",
      'printf("%s"' % CELL_FMT in src_text)
check("S3.20 VERIFY row printf forms byte-preserved from the family base",
      'printf("VERIFY idx=%d checked=0 mismatch=0 ok=0 note=pipeline-failed\\n", i);' in src_text
      and 'printf("VERIFY idx=%d checked=%u mismatch=%d ok=%d\\n", i, c->groups, mismatch,' in src_text)
check("S3.21 tail row form byte-preserved ('# done cells=%d')",
      'printf("# done cells=%d\\n", ncells);' in src_text)

# ---------------------------------------------------------------- section 4
# committed run-log byte binds (the empirical core; every sample re-parsed
# is a named run's landed MEASURED QUANTITY on aiueos-6600hs, never a new
# measurement)

def parse_log(path):
    """Parse a committed run log into headers/CELL/SAMPLE/VERIFY rows."""
    hdr, cells, samples, verifies, tails = [], [], [], [], []
    op = gzip.open if path.endswith(".gz") else open
    with op(path, "rt") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("# "):
                hdr.append(line)
            elif line.startswith("CELL "):
                cells.append(line)
            elif line.startswith("SAMPLE "):
                samples.append(line)
            elif line.startswith("VERIFY "):
                verifies.append(line)
            else:
                tails.append(line)
    return hdr, cells, samples, verifies, tails


# (a) the instrument identity + knob header bind on ONE c2 log, byte-exact
sample_c2 = os.path.join(GPU, WINDOWS[0][1], WINDOWS[0][2].format(1))
hdr, cells, samples, verifies, tails = parse_log(sample_c2)
check("S4.1 committed c2 header line 1 == the source's identity literal", hdr[0] == IDENT)
knob_line = hdr[6]
m = re.match(r"^# n=(\d+) rounds=(\d+) warmup=(\d+) batch=(\d+) barrier_n=(\d+) "
             r"work_mul=(\d+) ndiv=(\d+) seed=(\d+) metric=", knob_line)
check("S4.2 committed c2 knob line parses under the source's header form", m is not None)
if m:
    rendered = ("# n=%s rounds=%s warmup=%s batch=%s barrier_n=%s work_mul=%s "
                "ndiv=%s seed=%s metric=gpu_ns (vkCmdWriteTimestamp BATCH-dispatch "
                "bracket; per_dispatch_ns=gpu_ns/batch) +host_ns (CLOCK_MONOTONIC "
                "submit->completion)") % m.groups()
    check("S4.3 committed c2 knob line RE-RENDERED from parsed fields via the "
          "source's header form is byte-equal", rendered == knob_line)

# (b) CELL / VERIFY row re-render bind (byte forms), on the same log
cell_ok = True
for row in cells:
    mm = re.match(r"^CELL idx=(\d+) spv=(\S+) op=(\S+) wg=(\d+) forced=(\S+) "
                  r"probe_size=(-?\d+) probe_nsub=(-?\d+) probe_wg=(-?\d+) "
                  r"pipeline=(\S+) void=(\d+) void_reason=(.*)$", row)
    if not mm:
        cell_ok = False
        break
    g = mm.groups()
    rerender = ("CELL idx=%s spv=%s op=%s wg=%s forced=%s probe_size=%s probe_nsub=%s "
                "probe_wg=%s pipeline=%s void=%s void_reason=%s") % g
    if rerender != row:
        cell_ok = False
        break
check("S4.4 all 24 committed CELL rows re-render byte-equal via the source's CELL form",
      cell_ok and len(cells) == 24, "cells=%d" % len(cells))
ver_ok = True
for row in verifies:
    mm = re.match(r"^VERIFY idx=(\d+) checked=(\d+) mismatch=(\d+) ok=(\d+)$", row)
    if mm:
        rerender = "VERIFY idx=%s checked=%s mismatch=%s ok=%s" % mm.groups()
    else:
        mm2 = re.match(r"^VERIFY idx=(\d+) checked=0 mismatch=0 ok=0 note=pipeline-failed$", row)
        rerender = ("VERIFY idx=%s checked=0 mismatch=0 ok=0 note=pipeline-failed"
                    % mm2.group(1)) if mm2 else ""
    if rerender != row:
        ver_ok = False
        break
check("S4.5 all 24 committed VERIFY rows re-render byte-equal via the source's VERIFY forms",
      ver_ok and len(verifies) == 24, "verifies=%d" % len(verifies))

# (c) cases.txt bind: the act's 24 manifest data lines byte-equal the
# committed batch64 manifest's data lines and agree with the CELL rows
def data_lines(path):
    return [l for l in open(path).read().split("\n")
            if l and not l.startswith("#")]
act_cases = data_lines(CASES)
com_cases = data_lines(CASES_COMMITTED)
check("S4.6 act cases.txt data lines == committed batch64 cases.txt data lines (24)",
      act_cases == com_cases and len(act_cases) == 24, "%d vs %d" % (len(act_cases), len(com_cases)))
case_rows = [l.split() for l in act_cases]
cells_fields = []
for row in cells:
    mm = re.match(r"^CELL idx=(\d+) spv=(\S+) op=(\S+) wg=(\d+) forced=(\S+) ", row)
    cells_fields.append(mm.groups())
case_bind = all(
    cf[1] == cr[0] and cf[2] == cr[3] and cf[3] == cr[1] and cf[4] == cr[2]
    for cf, cr in zip(cells_fields, case_rows))
check("S4.7 cases.txt fields == committed CELL rows (spv/op/wg/forced per idx)",
      case_bind and len(case_rows) == 24)

# (d) the knob formula census over EVERY committed knob-bearing run log
# (run-*.txt and run-*.txt.gz under docs/evidence/gpu)
knob_re = re.compile(r"^# n=(\d+) rounds=(\d+) warmup=(\d+) batch=(\d+) barrier_n=(\d+) "
                     r"work_mul=(\d+) ndiv=(\d+) seed=(\d+) metric=")
knob_files = sorted(set(glob.glob(os.path.join(GPU, "**", "run-*.txt"), recursive=True))
                    | set(glob.glob(os.path.join(GPU, "**", "run-*.txt.gz"), recursive=True)))
knob_logs = 0
formula_bad = []
for p in knob_files:
    op = gzip.open if p.endswith(".gz") else open
    try:
        with op(p, "rt", errors="replace") as f:
            head = [next(f, "") for _ in range(8)]
    except OSError:
        continue
    for line in head:
        mm = knob_re.match(line.rstrip("\n"))
        if mm:
            knob_logs += 1
            n, _r, _w, _b, _bn, wm, nd, _s = (int(x) for x in mm.groups())
            if (1000003 * wm) // nd != n:
                formula_bad.append(p)
            break
check("S4.8 knob formula n == floor(1000003 * work_mul / ndiv) holds in EVERY "
      "committed knob-bearing run-log header (%d logs)" % knob_logs,
      knob_logs > 0 and not formula_bad, "%d bad: %s" % (len(formula_bad), formula_bad[:3]))

# (e) the timestampPeriod pin: the committed rows discriminate exactly one
# float32 value (c8 rows carry high tick counts)
def scan_period(paths):
    rows = []
    for p in paths:
        with gzip.open(p, "rt") as f:
            for line in f:
                if line.startswith("SAMPLE "):
                    t = line.split()
                    rows.append((int(t[6].split("=")[1]), t[7].split("=")[1],
                                 int(t[9].split("=")[1]), int(t[2].split("=")[1])))
    return rows

c8_rows = scan_period([p for _l, p in C8_LOGS])
cand_labels = ["f32(52.083)", "f32(52.0833)", "f32(52.08333)", "f32(1000/19.2)"]
cands = [f32(52.083), f32(52.0833), f32(52.08333), f32(1000.0 / 19.2)]
cand_pass = []
for p in cands:
    bad = 0
    for ticks, gs, _h, _b in c8_rows:
        if "%.1f" % (ticks * p) != gs:
            bad += 1
    cand_pass.append(bad == 0)
check("S4.9 the committed c8 rows discriminate EXACTLY ONE timestampPeriod float "
      "(f32(1000/19.2) == 52.08333206176758; f32(52.083) refuted at the high-tick rows)",
      cand_pass == [False, False, False, True], "pass pattern %s" % cand_pass)
PERIOD = cands[3]

# (f) the full committed-byte binds over the 27 c2 logs + 3 c8 logs:
# per-round order + SAMPLE row re-render + row census
def lcg(s):
    return (s * 1664525 + 1013904223) & 0xFFFFFFFF


universe = []
for label, d, pat in WINDOWS:
    for k in (1, 2, 3):
        universe.append(("%s-r%02d" % (label, k), os.path.join(GPU, d, pat.format(k))))
universe += C8_LOGS

total_rows = 0
for tag, path in universe:
    hdr, cells, samples, verifies, tails = parse_log(path)
    okset = set()
    for row in cells:
        mm = re.match(r"^CELL idx=(\d+) .* pipeline=(\S+) ", row)
        if mm and mm.group(2) == "ok":
            okset.add(int(mm.group(1)))
    # per-round observed idx order
    observed = {}
    render_bad = 0
    form_bad = 0
    for line in samples:
        mm = re.match(r"^SAMPLE round=(\d+) idx=(\d+) batch=(\d+) work_mul=(\d+) "
                      r"ndiv=(\d+) gpu_ticks=(\d+) gpu_ns=(\S+) per_dispatch_ns=(\S+) "
                      r"host_ns=(\d+)$", line)
        if not mm:
            form_bad += 1
            continue
        r, i, b, wm, nd, ticks, gs, ps, host = mm.groups()
        ticks_i = int(ticks)
        rerender = ("SAMPLE round=%s idx=%s batch=%s work_mul=%s ndiv=%s gpu_ticks=%s "
                    "gpu_ns=%s per_dispatch_ns=%s host_ns=%s") % (
            r, i, b, wm, nd, ticks, "%.1f" % (ticks_i * PERIOD),
            "%.2f" % (ticks_i * PERIOD / int(b)), host)
        if rerender != line:
            render_bad += 1
        observed.setdefault(int(r), []).append(int(i))
    total_rows += len(samples)
    check("S4.10.%s SAMPLE rows re-render byte-equal via the source's SAMPLE form "
          "at PERIOD=%r (115200 rows)" % (tag, PERIOD),
          render_bad == 0 and form_bad == 0 and len(samples) == 115200,
          "render_bad=%d form_bad=%d rows=%d" % (render_bad, form_bad, len(samples)))
    # the per-round order bind (the family's FY algorithm, seeded SEED+r)
    order = list(range(24))
    order_bad = 0
    for r in range(6400):
        state = (SEED + r) & 0xFFFFFFFF
        for i in range(23, 0, -1):
            state = lcg(state)
            j = state % (i + 1)
            order[i], order[j] = order[j], order[i]
        expect = [x for x in order if x in okset]
        if observed.get(r) != expect:
            order_bad += 1
    check("S4.11.%s per-round cell order REPRODUCED by the source's algorithm "
          "(seeded FY, lcg_state=SEED+r, in-place; 6400 rounds, %d ok cells)"
          % (tag, len(okset)),
          order_bad == 0, "bad rounds=%d" % order_bad)
    check("S4.12.%s row census (8 '#' lines incl. the tail, 24 CELL, 115200 SAMPLE, "
          "24 VERIFY, tail '# done cells=24')" % tag,
          len(hdr) == 8 and hdr[-1] == "# done cells=24" and len(cells) == 24
          and len(verifies) == 24 and tails == []
          and sorted(observed) == list(range(6400)),
          "hdr=%d cells=%d ver=%d tails=%s rounds=%d"
          % (len(hdr), len(cells), len(verifies), tails, len(observed)))

check("S4.13 universe census: 30 committed run logs, 3,456,000 SAMPLE rows "
      "re-parsed from committed bytes", len(universe) == 30 and total_rows == 3456000,
      "logs=%d rows=%d" % (len(universe), total_rows))

# (g) implementation + capture only: the act's evidence dir holds NO run log
stray = sorted(os.path.basename(p) for p in
               glob.glob(os.path.join(HERE, "run-*"))
               + glob.glob(os.path.join(HERE, "*.gz")))
check("S4.14 NO run log / no '*.gz' in the act's evidence dir "
      "(implementation + capture only, NO runs)", stray == [], str(stray))

# ---------------------------------------------------------------- report
print("impl-verify s243 -- the act's instrument probe implementation, "
      "fail-closed over committed bytes")
print("scope: implementation + capture only; NO runs; every act quantity "
      "UNMEASURED (measurement half = the measuring session on aiueos-6600hs)")
print("universe: 27 committed c2 run logs (the s234 nine windows) + 3 committed "
      "c8 run logs (timestampPeriod discriminator)")
print("")
for line in report:
    print(line)
print("")
print("# impl-verify s243 (impl-verify-s243.py): %d ok / %d failed" % (oks, fails))
sys.exit(1 if fails else 0)
