#!/usr/bin/env python3
"""pull-verify-s244.py -- JUN-59 s244, the cause-resolution act's
MEASUREMENT HALF, act measurement session m1 (UTC day 2026-11-03):
fail-closed pull/custody verification over the COMMITTED bytes of
docs/evidence/gpu/anv-b3causeact-20261103/ ONLY (the s228 pull-verify
precedent shape).  Deterministic: no timestamps, no host state, no
absolute paths in the output; run TWICE BYTE-IDENTICAL as a gate of
the slice.

What it binds (every check fail-closed):
  S1  name set: exactly run-cas1-c2-r{01,02,03}.txt.gz + .stderr.txt;
      the four capture files (host-stage/host-build/run-window/
      raw-digests) present.
  S2  gzip fidelity: decompressed .gz bytes re-derive the recorded
      raw digests (raw-digests-s244.txt sections 1-2, host==local).
  S3  stderr siblings 0 bytes.
  S4  canonical aggregate re-derived THROUGH the committed form ==
      bb57b2ff... (raw-digests-s244.txt section 4 construction).
  S5  per-run structure over decompressed bytes: 134,456 lines
      (7 header + 24 CELL + 19,200 PROBE + 115,200 SAMPLE + 24
      VERIFY + tail), tail '# done cells=24'.
  S6  header lines 1-7 byte-equal to the committed c2 reference
      (run-rd1-c2-r01.txt.gz of anv-b3control3state-20261102) --
      the frozen protocol section 1c ARM-K metadata row; the knob
      line separately bound to the frozen act knob bytes.
  S7  the 24 CELL rows and 24 VERIFY rows byte-equal to the
      committed reference (the frozen section-4 byte-preserved rows).
  S8  every SAMPLE row re-rendered byte-equal via the frozen row
      form at f32(1000/19.2) (the s243 verifier's rendering bind,
      now over the act's FIRST hardware bytes).
  S9  every PROBE row matches exactly one frozen section-4 form and
      re-renders byte-equal; per channel the round set is exactly
      0..6399 (6,400 rows each of zwts / zwbar / isohost).
  S10 O5 invalidation census (protocol section 7): VERIFY ok rows
      18 with mismatch=0, pipeline-FAIL rows 6 named.
  S11 first-measured binary pin 2c216ef2... present in the
      host-build capture verbatim block; raw-digests rows bound.

This is CUSTODY + STRUCTURE only: it computes no letter, no share,
no classification (the ANALYSIS half's R1-R5 are frozen in
protocol.txt section 6 and execute in a later slice).
"""
import gzip, hashlib, re, struct, sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
REF = BASE.parent / "anv-b3control3state-20261102" / "run-rd1-c2-r01.txt.gz"
RUNS = ["r01", "r02", "r03"]
RAW = {
    "r01": "addce8e90400628554ec2022ca7e47af2e8ae7b124ca654fce7a3c7a6688654c",
    "r02": "591e5026da67c067b97ac6d4494b1eb232860828aa3d6488783cbd4ff8ae066b",
    "r03": "212d6ade6a448f5489300081166338b294e64afa52d43e5f3dba7a354033cf31",
}
EMPTY = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
AGG = "bb57b2ffc563e8cdfb367e77cace6ef89e31d1a2c93499a2f7e10974e6df0c46"
BINPIN = "2c216ef2af510641568aaaa2bf2fadbc332ad2769c290fa020c6294aa50cf4e6"
KNOB = ("# n=1000003 rounds=6400 warmup=3 batch=2 barrier_n=0 work_mul=1 "
        "ndiv=1 seed=20261027 metric=gpu_ns (vkCmdWriteTimestamp BATCH-dispatch "
        "bracket; per_dispatch_ns=gpu_ns/batch) +host_ns (CLOCK_MONOTONIC "
        "submit->completion)\n")
IDENT = ("# instrument=anv-subgroupsize-batch v2-batch64 (JUN-59 subgroup "
         "16-vs-32 floor-lifting rerun, 2026-10-27)\n")
TS = struct.unpack("f", struct.pack("f", 1000.0 / 19.2))[0]

RE_SAMPLE = re.compile(r"^SAMPLE round=(\d+) idx=(\d+) batch=2 work_mul=1 ndiv=1 "
                       r"gpu_ticks=(\d+) gpu_ns=([0-9.]+) per_dispatch_ns=([0-9.]+) "
                       r"host_ns=(\d+)\n$")
RE_ZWTS = re.compile(r"^PROBE round=(\d+) channel=zwts ticks=(\d+)\n$")
RE_ZWBAR = re.compile(r"^PROBE round=(\d+) channel=zwbar ticks=(\d+)\n$")
RE_ISO = re.compile(r"^PROBE round=(\d+) channel=isohost raw_ns=(\d+)\n$")

ok_n = 0
fail_n = 0

def chk(tag, cond, detail=""):
    global ok_n, fail_n
    if cond:
        ok_n += 1
        print(f"ok   {tag}")
    else:
        fail_n += 1
        print(f"FAIL {tag} {detail}")

def sha(b):
    return hashlib.sha256(b).hexdigest()

def render_sample(r, i, t, h):
    t = int(t)
    ns = (float(t) * TS)
    return (f"SAMPLE round={r} idx={i} batch=2 work_mul=1 ndiv=1 gpu_ticks={t} "
            f"gpu_ns={ns:.1f} per_dispatch_ns={ns/2:.2f} host_ns={h}\n").encode()

# ---- committed reference (committed c2 run log) ----
with gzip.open(REF, "rb") as f:
    ref = f.read().decode()
ref_lines = ref.splitlines(keepends=True)
ref_head = ref_lines[:7]
ref_cells = [l for l in ref_lines if l.startswith("CELL ")]
ref_verify = [l for l in ref_lines if l.startswith("VERIFY ")]
chk("S0.ref-cells-24", len(ref_cells) == 24, f"got {len(ref_cells)}")
chk("S0.ref-verify-24", len(ref_verify) == 24, f"got {len(ref_verify)}")

# ---- S1 name set ----
names = sorted(p.name for p in BASE.iterdir()
               if p.name.startswith("run-cas1-c2-"))
want = sorted([f"run-cas1-c2-{r}{s}" for r in RUNS for s in (".txt.gz", ".stderr.txt")])
chk("S1.nameset-6", names == want, f"got {names}")
for cap in ("host-stage-s244.txt", "host-build-s244.txt",
            "run-window-s244.txt", "raw-digests-s244.txt"):
    chk(f"S1.cap-{cap}", (BASE / cap).is_file())

raw_dig_file = (BASE / "raw-digests-s244.txt").read_bytes()
agg_lines = []
for r in RUNS:
    gz = (BASE / f"run-cas1-c2-{r}.txt.gz").read_bytes()
    err = (BASE / f"run-cas1-c2-{r}.stderr.txt").read_bytes()
    data = gzip.decompress(gz)
    d = sha(data)
    # S2 gzip fidelity
    chk(f"S2.{r}.gzip-fidelity", d == RAW[r], f"got {d}")
    agg_lines.append(f"{d}  run-cas1-c2-{r}.txt\n")
    # S3 stderr
    chk(f"S3.{r}.stderr-empty", len(err) == 0 and sha(err) == EMPTY)
    # S11 raw-digests rows bound
    chk(f"S11.{r}.rawdigest-row", RAW[r].encode() in raw_dig_file and
        d.encode() in raw_dig_file)

# S4 canonical aggregate through the committed form
agg = sha("".join(agg_lines).encode())
chk("S4.aggregate", agg == AGG, f"got {agg}")
chk("S11.aggregate-row", AGG.encode() in raw_dig_file)

# S11 first-measured binary pin
hb = (BASE / "host-build-s244.txt").read_text()
chk("S11.binary-pin", f"{BINPIN}  anv-causeprobe" in hb)
chk("S11.binarypin-row", BINPIN.encode() in raw_dig_file)

for r in RUNS:
    data = gzip.decompress((BASE / f"run-cas1-c2-{r}.txt.gz").read_bytes()).decode()
    lines = data.splitlines(keepends=True)
    # S5 structure
    tail_ok = lines[-1] == "# done cells=24\n"
    chk(f"S5.{r}.lines-134456", len(lines) == 134456, f"got {len(lines)}")
    chk(f"S5.{r}.tail", tail_ok, repr(lines[-1]))
    head = lines[:7]
    cells = [l for l in lines if l.startswith("CELL ")]
    verifies = [l for l in lines if l.startswith("VERIFY ")]
    samples = [l for l in lines if l.startswith("SAMPLE ")]
    probes = [l for l in lines if l.startswith("PROBE ")]
    chk(f"S5.{r}.cells-24", len(cells) == 24, f"got {len(cells)}")
    chk(f"S5.{r}.samples-115200", len(samples) == 115200, f"got {len(samples)}")
    chk(f"S5.{r}.probes-19200", len(probes) == 19200, f"got {len(probes)}")
    chk(f"S5.{r}.verifies-24", len(verifies) == 24, f"got {len(verifies)}")
    # S6 header identity + knob line
    chk(f"S6.{r}.head1-ident", head[0] == IDENT, repr(head[0][:60]))
    chk(f"S6.{r}.head7-knob", head[6] == KNOB, repr(head[6][:60]))
    chk(f"S6.{r}.head-block-eq-committed", head == ref_head)
    # S7 CELL/VERIFY byte-equality to committed reference
    chk(f"S7.{r}.cell-block-eq-committed", cells == ref_cells)
    chk(f"S7.{r}.verify-block-eq-committed", verifies == ref_verify)
    # S8 SAMPLE re-render
    bad = 0
    for l in samples:
        m = RE_SAMPLE.match(l)
        if not m or render_sample(m.group(1), m.group(2), m.group(3),
                                  m.group(6)) != l.encode():
            bad += 1
    chk(f"S8.{r}.sample-rerender-115200", bad == 0, f"bad {bad}")
    # S9 PROBE forms + round sets + re-render
    for chan, rex, rr in (("zwts", RE_ZWTS, "ticks"),
                          ("zwbar", RE_ZWBAR, "ticks"),
                          ("isohost", RE_ISO, "raw_ns")):
        rows = [l for l in probes if f"channel={chan} " in l]
        bad = 0
        rounds = set()
        for l in rows:
            m = rex.match(l)
            if not m:
                bad += 1
                continue
            rounds.add(int(m.group(1)))
            want_row = (f"PROBE round={m.group(1)} channel={chan} {rr}={m.group(2)}\n")
            if want_row != l:
                bad += 1
        chk(f"S9.{r}.{chan}-count-6400", len(rows) == 6400, f"got {len(rows)}")
        chk(f"S9.{r}.{chan}-forms-rerender", bad == 0, f"bad {bad}")
        chk(f"S9.{r}.{chan}-rounds-0..6399", rounds == set(range(6400)))
    # S10 O5 census
    ok_rows = [l for l in verifies if " note=pipeline-failed" not in l and l.rstrip().endswith("ok=1")]
    fail_rows = [l for l in verifies if "note=pipeline-failed" in l]
    mis = sum(1 for l in ok_rows if not l.rstrip().endswith("mismatch=0 ok=1"))
    chk(f"S10.{r}.verify-ok-18-mismatch0", len(ok_rows) == 18 and mis == 0,
        f"ok_rows {len(ok_rows)} mis {mis}")
    chk(f"S10.{r}.verify-pipeline-failed-6", len(fail_rows) == 6, f"got {len(fail_rows)}")

print(f"# pull-verify s244 (pull-verify-s244.py): {ok_n} ok / {fail_n} failed")
sys.exit(1 if fail_n else 0)
