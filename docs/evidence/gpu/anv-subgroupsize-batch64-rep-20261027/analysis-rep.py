#!/usr/bin/env python3
"""analysis-rep.py -- JUN-59 batch64 sign REPLICATION (session 3, 2026-10-27).

The ONLY analysis route for this session: it reads the committed run
logs (run-rep-1..6.txt) and prints the publication to stdout. It is run
twice and the two outputs must be byte-identical (diff exit 0). It
contains no wall-clock time and reads no other data source except the
named DERIVED cross-session section, which reads sessions 2's committed
logs (anv-subgroupsize-batch64-20261027/run-1..3.txt) for arithmetic
only.

Protocol letters (protocol.txt, frozen before the first run):
P1r sign recurrence at (sum,128),(max,128); P2r the dip; P3r forcing +
correctness; P4r floor still lifted. Rule 4 binds: nothing here moves a
row.
"""
import statistics
import sys

CHAIN = "/Users/junkawasaki/github/wt/amu-gpu/chain"
EV = CHAIN + "/docs/evidence/gpu/anv-subgroupsize-batch64-rep-20261027"
S2 = CHAIN + "/docs/evidence/gpu/anv-subgroupsize-batch64-20261027"
RUNS = [EV + "/run-rep-%d.txt" % i for i in range(1, 7)]
S2RUNS = [S2 + "/run-%d.txt" % i for i in range(1, 4)]
OPS = ["sum", "max", "min"]
WS = [128, 256]
S_ARMS = ["16", "32", "default"]


def parse(path):
    headers, cells, samples, verifies = [], {}, [], []
    exit_line = None
    with open(path) as f:
        for ln in f:
            ln = ln.rstrip("\n")
            if ln.startswith("# "):
                headers.append(ln)
            elif ln.startswith("CELL "):
                kv = {}
                for tok in ln.split()[1:]:
                    k, _, v = tok.partition("=")
                    kv[k] = v
                cells[int(kv["idx"])] = kv
            elif ln.startswith("SAMPLE "):
                kv = {}
                for tok in ln.split()[1:]:
                    k, _, v = tok.partition("=")
                    kv[k] = v
                samples.append(kv)
            elif ln.startswith("VERIFY "):
                kv = {}
                for tok in ln.split()[1:]:
                    k, _, v = tok.partition("=")
                    kv[k] = v
                verifies.append(kv)
            elif ln.startswith("INSTRUMENT-EXIT"):
                exit_line = ln
    return headers, cells, samples, verifies, exit_line


def arm_samples(cells, samples, op, w, s):
    idxs = {i for i, c in cells.items()
            if c["op"] == op and int(c["wg"]) == w and c["forced"] == s
            and c.get("pipeline") == "ok" and c.get("void") == "0"}
    out = []
    for sm in samples:
        if int(sm["idx"]) in idxs:
            out.append(sm)
    return out


def med(vals):
    return statistics.median(vals)


def f2(x):
    return "%.2f" % x


def sign_of(m32, m16):
    return "32faster" if m32 < m16 else "16faster-or-tie"


def main():
    out = []
    A = out.append
    parsed = [parse(p) for p in RUNS]
    parsed_s2 = [parse(p) for p in S2RUNS]

    A("PUBLICATION -- JUN-59 subgroup 16-vs-32 sign REPLICATION")
    A("(batch64 route), session 3 (2026-10-27). Produced ONLY by")
    A("analysis-rep.py over run-rep-1..6.txt (the committed logs of THIS")
    A("session); the cross-session section 7 is DERIVED arithmetic over")
    A("session 2's committed logs and says so. Rule 4 binds: no row moves.")
    A("")

    # 1. identity
    A("1. RUN IDENTITY (programmatic)")
    h0 = parsed[0][0]
    hdr_ok = all(p[0] == h0 for p in parsed)
    A("   header lines: %d per run; byte-identical across all 6 runs: %s"
      % (len(h0), "YES" if hdr_ok else "NO"))
    for h in h0:
        A("   " + h)
    for i, p in enumerate(parsed, 1):
        _, cells, samples, verifies, ex = p
        okc = sum(1 for c in cells.values() if c.get("pipeline") == "ok")
        A("   run-rep-%d: %s | cells=%d pipeline-ok=%d samples=%d verify-lines=%d"
          % (i, ex, len(cells), okc, len(samples), len(verifies)))
    A("")

    # 2. P3r forcing + correctness
    A("2. P3r (FORCING REALITY + CORRECTNESS)")
    force_ok = force_tot = 0
    mism = 0
    for i, p in enumerate(parsed, 1):
        _, cells, samples, verifies, _ = p
        for idx, c in sorted(cells.items()):
            if c.get("pipeline") != "ok":
                continue
            force_tot += 1
            want = 32 if c["forced"] == "default" else int(c["forced"])
            nsub = int(c["wg"]) // want
            if int(c["probe_size"]) == want and int(c["probe_nsub"]) == nsub:
                force_ok += 1
            else:
                A("   FORCING-MISMATCH run-rep-%d idx=%d" % (i, idx))
        for v in verifies:
            mism += int(v["mismatch"])
    A("   forcing reality: %d/%d pipeline-ok cell-runs verify (probe_size"
      % (force_ok, force_tot))
    A("   == forced size (32 at default), probe_nsub == W/size)" % ())
    A("   correctness: total mismatch across all VERIFY lines of all 6")
    A("   runs = %d  -> %s" % (mism, "HOLDS (mismatch=0 everywhere)" if mism == 0 else "FAILS"))
    A("")

    # 3. per-run arm medians
    A("3. PER-RUN ARM MEDIANS (per_dispatch_ns; gpu_ticks in parens)")
    A("   med(r, op, W, S) per protocol.txt; 25 samples per arm per run")
    med_cache = {}
    ticks_cache = {}
    for op in OPS:
        for w in WS:
            for s in S_ARMS:
                row = []
                for i, p in enumerate(parsed, 1):
                    _, cells, samples, _, _ = p
                    ss = arm_samples(cells, samples, op, w, s)
                    if not ss:
                        row.append("run-rep-%d:no-samples" % i)
                        continue
                    mns = med([float(x["per_dispatch_ns"]) for x in ss])
                    mt = med([int(x["gpu_ticks"]) for x in ss])
                    med_cache[(i, op, w, s)] = mns
                    ticks_cache[(i, op, w, s)] = mt
                    row.append("r%d:%s(%d)" % (i, f2(mns), mt))
                A("   (%s,W=%d,S=%s) %s" % (op, w, s, "  ".join(row)))
    A("")

    # 4. P1r signs
    A("4. P1r (SIGN RECURRENCE) -- sign per run at each (op, W)")
    A("   SIGN(r, op, W) = 32faster iff med(S=32) < med(S=16), else")
    A("   16faster-or-tie (protocol.txt's named definition)")
    signs = {}
    for op in OPS:
        for w in WS:
            row = []
            for i in range(1, 7):
                s = sign_of(med_cache[(i, op, w, "32")], med_cache[(i, op, w, "16")])
                signs[(i, op, w)] = s
                row.append("r%d:%s" % (i, s))
            A("   (%s,W=%d) %s" % (op, w, "  ".join(row)))
    A("")
    A("   P1r verdicts (the two session-2 RUN-SENSITIVE cells first):")
    for op, w in [("sum", 128), ("max", 128), ("sum", 256), ("max", 256), ("min", 128), ("min", 256)]:
        ss = [signs[(i, op, w)] for i in range(1, 7)]
        n32 = ss.count("32faster")
        n16 = 6 - n32
        verdict = "CONSISTENT (%s 6/6)" % ss[0] if n32 in (0, 6) else "SPLIT (32faster=%d, 16faster-or-tie=%d)" % (n32, n16)
        tag = "SESSION-2-RUN-SENSITIVE" if (op, w) in (("sum", 128), ("max", 128)) else "session-2-consistent"
        A("   (%s,W=%d) [%s] %s" % (op, w, tag, verdict))
    A("")

    # 5. P2r dip
    A("5. P2r (THE DIP) -- per-run med gpu_ticks of the (op, W=128, S=16) arms")
    A("   DIP-RUN pre-defined: >= 1000 ticks below the median of the six")
    A("   runs' medians at that arm (protocol.txt)")
    for op in ("sum", "max"):
        vals = [ticks_cache[(i, op, 128, "16")] for i in range(1, 7)]
        m = med(vals)
        A("   (%s,128,16) per-run med gpu_ticks: %s | median-of-six=%s"
          % (op, " ".join("r%d:%d" % (i + 1, v) for i, v in enumerate(vals)), f2(m)))
        for i, v in enumerate(vals, 1):
            if v <= m - 1000:
                A("   DIP-RUN run-rep-%d at (%s,128): med %d <= %s - 1000"
                  % (i, op, v, f2(m)))
        dips = [i for i, v in enumerate(vals, 1) if v <= m - 1000]
        A("   (%s,128) dip classification: %s"
          % (op, ("DIP-RUNS at run-rep-%s" % ",".join(map(str, dips))) if dips else "no DIP-RUN in the six"))
    A("")

    # 6. P4r floor
    A("6. P4r (FLOOR STILL LIFTED) -- pooled median bracket gpu_ticks per")
    A("   measured (op, W, S) arm over all 6 runs x 25 rounds; condition")
    A("   >= 248 ticks (session 2's pre-registered floor-lift threshold)")
    floor_fail = []
    for op in OPS:
        for w in WS:
            for s in S_ARMS:
                vals = []
                for i in range(1, 7):
                    _, cells, samples, _, _ = parsed[i - 1]
                    vals += [int(x["gpu_ticks"]) for x in arm_samples(cells, samples, op, w, s)]
                pm = med(vals)
                st = "ok" if pm >= 248 else "FLOOR-NOT-LIFTED"
                if pm < 248:
                    floor_fail.append((op, w, s))
                A("   (%s,W=%d,S=%s) pooled median %s ticks over %d samples: %s"
                  % (op, w, s, f2(pm), len(vals), st))
    A("   P4r: %s" % ("HOLDS (every measured cell >= 248 ticks)" if not floor_fail
                      else "FAILS at %s (S comparison void there)" % floor_fail))
    A("")

    # 7. DERIVED cross-session
    A("7. DERIVED CROSS-SESSION (arithmetic over session 2's committed")
    A("   logs anv-subgroupsize-batch64-20261027/run-1..3.txt -- NOT a")
    A("   measurement of this session; the logs are read for arithmetic")
    A("   only and are not rewritten)")
    s2_signs = {}
    for i, p in enumerate(parsed_s2, 1):
        _, cells, samples, _, _ = p
        for op in OPS:
            for w in WS:
                s16 = med([float(x["per_dispatch_ns"]) for x in arm_samples(cells, samples, op, w, "16")])
                s32 = med([float(x["per_dispatch_ns"]) for x in arm_samples(cells, samples, op, w, "32")])
                s2_signs[(i, op, w)] = sign_of(s32, s16)
    for op in OPS:
        for w in WS:
            row = ["s2r%d:%s" % (i, s2_signs[(i, op, w)]) for i in range(1, 4)]
            row += ["r%d:%s" % (i, signs[(i, op, w)]) for i in range(1, 7)]
            n32 = sum(1 for x in row if x.endswith("32faster"))
            A("   (%s,W=%d) %s | 32faster in %d/9" % (op, w, "  ".join(row), n32))
    A("")

    # 8. states
    A("8. STATES / UNMEASURED (echo of protocol.txt, unchanged)")
    A("   MEASURED: only sections 2-6 above, from THIS session's six")
    A("   committed logs. UNMEASURED (named, unchanged): the cause of any")
    A("   dip (including session 2's run-1 dip), cross-day replication,")
    A("   every W outside {128,256}, shape 2, isolated single-dispatch")
    A("   timing above any floor, any baseline-vs-variant sign, anything")
    A("   off this host. RULE 4: no workgroup row, no :measured? flag, no")
    A("   :size/:shapes, no selection answer moves on this evidence.")
    A("   NO vendor optimization exists for Intel and none is claimed.")
    A("   END.")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
