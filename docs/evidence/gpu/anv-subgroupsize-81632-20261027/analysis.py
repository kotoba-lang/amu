#!/usr/bin/env python3
# analysis.py -- the ONLY analysis route for the JUN-59 subgroup 8/16/32
# session's publication (protocol.txt letter: "the analysis is publication.txt,
# produced only by analysis.py over those logs"). Committed inside the
# evidence directory so the publication is re-derivable from the committed
# logs byte-for-byte. Deterministic: fixed iteration orders, no timestamps,
# no wall clock, no environment reads.
#
# Usage: python3 analysis.py run-1.txt run-2.txt run-3.txt > publication.txt
#
# Boundaries are exactly the ones fixed in protocol.txt BEFORE the runs:
#   P1  stage/barrier count: at fixed (op, W) the gpu_ns median is
#       NON-INCREASING in forced S; HOLDS iff S=32's median is strictly
#       below BOTH S=8's and S=16's at every (op, W). S=8 is not realizable
#       on this device (pipeline=FAIL, fail-closed branch), so the S=8 half
#       is NOT EVALUABLE and is named so -- the evaluable (narrowed) letter
#       is S=32 strictly below S=16 at every (op, W); any (op, W) where
#       S=32 is not the fastest measured cell is NAMED as a P1 refutation
#       at that cell under the protocol's "S=32 is not the fastest" clause.
#   P2  forcing reality: probe gl_SubgroupSize == forced size at every
#       forced cell, == device-reported subgroupSize at every default cell,
#       probe gl_NumSubgroups == W / probe_size. Any deviation VOIDS that
#       cell's timing and the void is NAMED (never dropped silently).
#   P3  correctness: VERIFY mismatch == 0 at every cell of every run.
#   P4  cross-run order: the per-cell gpu_ns medians' ORDER by S at fixed
#       (op, W) is IDENTICAL across the three fresh processes.
# Fail-closed branches (protocol.txt): pipeline=FAIL cells carry no samples
# and are named; samples with gpu_ticks=0 carry no gpu_ns reading and are
# named absent (excluded from gpu_ns medians, counted).

import hashlib
import re
import sys

EXPECTED_HEADER = {
    "n": "1000003",
    "rounds": "25",
    "warmup": "3",
    "seed": "20261027",
}
EXPECTED_SUBGROUP_SIZE = 32
EXPECTED_MIN_SUB = 16
EXPECTED_MAX_SUB = 32


def die(msg):
    sys.stderr.write("ANALYSIS-FATAL: %s\n" % msg)
    sys.exit(2)


def parse_kv(rest):
    out = {}
    for tok in rest.split():
        if "=" not in tok:
            die("token without =: %r" % tok)
        k, v = tok.split("=", 1)
        out[k] = v
    return out


def parse_log(path):
    log = {"path": path, "header": [], "cells": {}, "samples": {}, "verify": {},
           "done": None, "exit": None, "sha256": None}
    with open(path, "rb") as f:
        raw = f.read()
    log["sha256"] = hashlib.sha256(raw).hexdigest()
    text = raw.decode("utf-8")
    for lineno, line in enumerate(text.splitlines(), 1):
        if line.startswith("#"):
            log["header"].append(line)
            if line.startswith("# done"):
                log["done"] = line
            continue
        if line.startswith("CELL "):
            kv = parse_kv(line[5:])
            idx = int(kv.pop("idx"))
            if idx in log["cells"]:
                die("%s:%d duplicate CELL idx=%d" % (path, lineno, idx))
            log["cells"][idx] = kv
        elif line.startswith("SAMPLE "):
            kv = parse_kv(line[7:])
            idx = int(kv["idx"])
            log["samples"].setdefault(idx, []).append(kv)
        elif line.startswith("VERIFY "):
            kv = parse_kv(line[7:])
            idx = int(kv.pop("idx"))
            log["verify"][idx] = kv
        elif line.startswith("INSTRUMENT-EXIT="):
            log["exit"] = line.split("=", 1)[1]
        elif line == "":
            continue
        else:
            die("%s:%d unparsable line: %r" % (path, lineno, line))
    return log


def median(vals):
    if not vals:
        return None
    s = sorted(vals)
    n = len(s)
    if n % 2 == 1:
        return s[n // 2]
    return (s[n // 2 - 1] + s[n // 2]) / 2.0


def f1(x):
    return "%.1f" % x


def header_field(log, key):
    # "# n=1000003 rounds=25 warmup=3 seed=20261027 metric=..."
    for line in log["header"]:
        for tok in line[1:].split():
            if tok.startswith(key + "="):
                return tok.split("=", 1)[1]
    return None


def subgroup_header(log):
    # "# subgroupSize=32 subgroupStages=... subgroupOps=..."
    for line in log["header"]:
        m = re.search(r"subgroupSize=(\d+)", line)
        if m and "subgroupStages=" in line:
            return int(m.group(1))
    return None


def sizecontrol_header(log):
    # "# subgroupSizeControl: feature=1 computeFullSubgroups=1 min=16 max=32 ..."
    for line in log["header"]:
        if "subgroupSizeControl:" in line:
            mn = re.search(r"min=(\d+)", line)
            mx = re.search(r"max=(\d+)", line)
            if mn is None or mx is None:
                return (None, None)
            return (int(mn.group(1)), int(mx.group(1)))
    return (None, None)


def s_label(cell):
    return "default" if cell["forced"] == "default" else cell["forced"]


def s_rank(label):
    # numeric order by forced size; default tracked separately
    return {"16": 16, "32": 32, "8": 8}.get(label, 10 ** 6)


def main(argv):
    if len(argv) != 4:
        die("usage: analysis.py run-1.txt run-2.txt run-3.txt")
    logs = [parse_log(p) for p in argv[1:4]]
    out = []
    w = out.append

    w("# publication -- JUN-59 subgroup 8/16/32, FIRST session, INSTRUMENT")
    w("# channel (raw ANV on aiueos-6600hs-1; not the removed wire-42 loader")
    w("# path, not the ADR-0371 provider). Produced ONLY by analysis.py over")
    w("# run-1.txt run-2.txt run-3.txt -- no hand analysis, no other route.")
    w("# Rule 4 binds in full: NO workgroup row, NO :measured? flag, NO")
    w("# selection answer moves anywhere from this publication.")
    w("")
    w("== 0. inputs (sha256, verbatim) ==")
    for log in logs:
        w("%s  %s" % (log["sha256"], log["path"]))
    w("analysis.py sha256 %s" % hashlib.sha256(open(__file__, "rb").read()).hexdigest())
    w("")

    w("== 1. structural checks (all must hold; fail-closed) ==")
    ok_all = True
    for log in logs:
        ncells = len(log["cells"])
        idxs = sorted(log["cells"])
        nsamp = sum(len(v) for v in log["samples"].values())
        problems = []
        if ncells != 24 or idxs != list(range(24)):
            problems.append("cells=%d idxs=%s" % (ncells, idxs))
        if log["exit"] != "0":
            problems.append("INSTRUMENT-EXIT=%s" % log["exit"])
        if log["done"] != "# done cells=24":
            problems.append("done=%r" % log["done"])
        if sorted(log["verify"]) != list(range(24)):
            problems.append("verify idxs=%s" % sorted(log["verify"]))
        for key, val in EXPECTED_HEADER.items():
            got = header_field(log, key)
            if got != val:
                problems.append("header %s=%s (want %s)" % (key, got, val))
        sg = subgroup_header(log)
        if sg != EXPECTED_SUBGROUP_SIZE:
            problems.append("header subgroupSize=%s" % sg)
        mn, mx = sizecontrol_header(log)
        if (mn, mx) != (EXPECTED_MIN_SUB, EXPECTED_MAX_SUB):
            problems.append("header min/max=%s/%s" % (mn, mx))
        # per-cell sample counts: pipeline-ok cells must carry rounds samples
        for idx in idxs:
            cell = log["cells"][idx]
            got = len(log["samples"].get(idx, []))
            if cell["pipeline"] == "ok":
                if got != 25:
                    problems.append("idx=%d samples=%d (want 25)" % (idx, got))
            else:
                if got != 0:
                    problems.append("idx=%d FAIL cell carries %d samples" % (idx, got))
        ok = not problems
        ok_all = ok_all and ok
        w("%s  cells=%d samples=%d exit=%s structure=%s" %
          (log["path"], ncells, nsamp, log["exit"], "ok" if ok else "FAIL"))
        for p in problems:
            w("    STRUCTURE-PROBLEM %s" % p)
    # cross-run identity of headers and CELL lines
    h0 = logs[0]["header"]
    c0 = [logs[0]["cells"][i] for i in range(24)]
    for log in logs[1:]:
        if log["header"] != h0:
            ok_all = False
            w("STRUCTURE-PROBLEM %s header differs from %s" % (log["path"], logs[0]["path"]))
        for i in range(24):
            if log["cells"][i] != c0[i]:
                ok_all = False
                w("STRUCTURE-PROBLEM %s CELL idx=%d differs from %s" %
                  (log["path"], i, logs[0]["path"]))
    w("cross-run header+CELL identity: %s" % ("ok" if ok_all else "FAIL"))
    w("")

    w("== 2. fail-closed table (S=8 cells; named, never dropped silently) ==")
    w("device facts: subgroupSize=%d minSubgroupSize=%d maxSubgroupSize=%d --" %
      (EXPECTED_SUBGROUP_SIZE, EXPECTED_MIN_SUB, EXPECTED_MAX_SUB))
    w("forced S=8 is NOT REALIZABLE on this device (8 < minSubgroupSize=16).")
    fail_cells = [i for i in range(24) if c0[i]["pipeline"] != "ok"]
    w("named FAIL cells (idx, op, W, forced, void_reason), identical in every run:")
    for i in fail_cells:
        c = c0[i]
        w("  idx=%d op=%s wg=%s forced=%s pipeline=%s void=%s void_reason=%s" %
          (i, c["op"], c["wg"], s_label(c), c["pipeline"], c["void"], c["void_reason"]))
    w("count: %d of 24 cells; excluded from every timing table below with" % len(fail_cells))
    w("this reason; the S=8 half of P1 is NOT EVALUABLE (named, not hidden).")
    w("")

    w("== 3. P2 forcing reality (probe readback per cell per run) ==")
    p2_fail = 0
    for log in logs:
        for i in range(24):
            c = log["cells"][i]
            if c["pipeline"] != "ok":
                continue
            forced = s_label(c)
            wg = int(c["wg"])
            want_size = EXPECTED_SUBGROUP_SIZE if forced == "default" else int(forced)
            want_nsub = wg // want_size
            got_size = int(c["probe_size"])
            got_nsub = int(c["probe_nsub"])
            got_wg = int(c["probe_wg"])
            okp = (got_size == want_size and got_nsub == want_nsub and got_wg == wg
                   and c["void"] == "0")
            if not okp:
                p2_fail += 1
            w("%s idx=%d forced=%s probe_size=%d(want %d) probe_nsub=%d(want %d) "
              "probe_wg=%d(want %d) void=%s reason=%r P2=%s" %
              (log["path"], i, forced, got_size, want_size, got_nsub, want_nsub,
               got_wg, wg, c["void"], c["void_reason"], "ok" if okp else "VOID"))
    w("P2 verdict: %s (%d deviations; any deviation VOIDS that cell's timing)" %
      ("HOLDS" if p2_fail == 0 else "DEVIATIONS NAMED", p2_fail))
    w("")

    w("== 4. P3 correctness (VERIFY readback, bit-exact CPU reference) ==")
    p3_bad = 0
    for log in logs:
        for i in range(24):
            v = log["verify"][i]
            if v.get("note") == "pipeline-failed":
                w("%s idx=%d checked=%s mismatch=%s ok=%s note=pipeline-failed" %
                  (log["path"], i, v["checked"], v["mismatch"], v["ok"]))
                continue
            good = (v["mismatch"] == "0" and v["ok"] == "1")
            if not good:
                p3_bad += 1
            w("%s idx=%d checked=%s mismatch=%s ok=%s P3=%s" %
              (log["path"], i, v["checked"], v["mismatch"], v["ok"],
               "ok" if good else "MISMATCH"))
    w("P3 verdict: %s (%d mismatching cells across all runs)" %
      ("HOLDS (mismatch=0 at every cell of every run)" if p3_bad == 0 else "FAILURES NAMED",
       p3_bad))
    w("")

    w("== 5. timing table (gpu_ns = vkCmdWriteTimestamp dispatch bracket;")
    w("    host_ns = CLOCK_MONOTONIC submit->completion; never mixed) ==")
    w("per cell per run: n=sample count, absent=gpu_ticks==0 samples (named,")
    w("excluded from gpu_ns medians), gpu_ns min/median/max, host_ns min/median/max.")
    stats = {}  # (run, idx) -> dict
    for ri, log in enumerate(logs, 1):
        for i in range(24):
            c = log["cells"][i]
            if c["pipeline"] != "ok":
                continue
            samples = log["samples"][i]
            gpu = [float(s["gpu_ns"]) for s in samples if int(s["gpu_ticks"]) > 0]
            absent = sum(1 for s in samples if int(s["gpu_ticks"]) == 0)
            host = [int(s["host_ns"]) for s in samples]
            med = median(gpu)
            stats[(ri, i)] = {"med": med, "n": len(gpu), "absent": absent}
            w("run-%d idx=%d op=%s wg=%s S=%s n=%d absent=%d gpu_ns %s/%s/%s host_ns %d/%s/%d" %
              (ri, i, c["op"], c["wg"], s_label(c), len(gpu), absent,
               f1(min(gpu)) if gpu else "-", f1(med) if med is not None else "-",
               f1(max(gpu)) if gpu else "-",
               min(host), f1(median(host)), max(host)))
    w("")

    w("== 6. P1 (stage/barrier count), evaluated at its letter ==")
    ops = ["sum", "max", "min"]
    wss = ["128", "256"]
    s_order = ["16", "32", "default"]
    p1_refutations = []
    for op in ops:
        for wg in wss:
            idxs = [i for i in range(24)
                    if c0[i]["op"] == op and c0[i]["wg"] == wg]
            by_s = {s_label(c0[i]): i for i in idxs}
            row = []
            for s in s_order:
                i = by_s[s]
                meds = [stats[(ri, i)]["med"] for ri in (1, 2, 3)]
                row.append((s, meds))
            w("(%s, W=%s): per-run gpu_ns medians by S: %s" %
              (op, wg, "  ".join("S=%s [%s]" % (s, ", ".join(f1(m) for m in meds))
                                 for s, meds in row)))
            # evaluable forced pair on this device: 16 vs 32 (S=8 FAIL, not evaluable)
            med16 = median([m for m in row[0][1] if m is not None])
            med32 = median([m for m in row[1][1] if m is not None])
            meddef = median([m for m in row[2][1] if m is not None])
            if med16 is None or med32 is None:
                w("  no gpu_ns timing at S=16/S=32 -- comparison NOT EVALUABLE here")
                p1_refutations.append((op, wg, False, "no-timing"))
                continue
            pooled = [("S=16", med16), ("S=32", med32), ("S=default", meddef)]
            present = [(m, s) for s, m in pooled if m is not None]
            best = min(m for m, _ in present)
            winners = [s for m, s in present if m == best]
            fastest = winners[0] if len(winners) == 1 else "TIE(%s)" % ",".join(winners)
            narrow = med32 < med16
            eq = "EQUAL medians (tie -- no S=32 advantage measured)" if med32 == med16 else "different"
            w("  pooled median S=16 %s | S=32 %s | default %s -- S=32 strictly below "
              "S=16: %s (%s); fastest measured cell: %s" %
              (f1(med16), f1(med32), f1(meddef), "yes" if narrow else "NO", eq, fastest))
            w("  S=8 half: NOT EVALUABLE (pipeline=FAIL, no samples).")
            if not narrow or fastest != "S=32":
                p1_refutations.append((op, wg, narrow, fastest))
    w("P1 verdict (letter: S=32 median strictly below BOTH S=8's and S=16's at")
    w("every (op, W)): NOT EVALUABLE AT ITS FULL LETTER -- the S=8 comparison")
    w("has no timing on this device (fail-closed, named). At the NARROWED")
    w("letter (S=32 strictly below S=16 at every (op, W)) P1 %s." %
      ("HOLDS" if not p1_refutations else "IS REFUTED AT: %s" % p1_refutations))
    w("This is a design-reasoning check at the INSTRUMENT channel; it is NOT")
    w("an optimization claim and no selection answer may move from it.")
    w("")

    w("== 7. P4 cross-run order (per-cell gpu_ns medians' ORDER by S,")
    w("    identical across the three fresh processes?) ==")
    w("orders are strict orders of the per-run medians; EXACT TIES are broken")
    w("by the S label lexicographically (16 < 32 < default) -- an all-tie cell")
    w("therefore always prints 16>32>default and is NAMED degenerate in the")
    w("per-cell line below (its order carries no rank information).")
    p4_mismatch = []
    for op in ops:
        for wg in wss:
            idxs = [i for i in range(24)
                    if c0[i]["op"] == op and c0[i]["wg"] == wg]
            by_s = {s_label(c0[i]): i for i in idxs}
            orders = []
            for ri in (1, 2, 3):
                pairs = [(stats[(ri, by_s[s])]["med"], s) for s in s_order]
                order = [s for _, s in sorted(pairs)]
                orders.append(order)
            same = orders[0] == orders[1] == orders[2]
            all_meds = [stats[(ri, by_s[s])]["med"] for ri in (1, 2, 3) for s in s_order]
            tie_mark = "  [ALL-TIE CELL, order degenerate]" if len(set(all_meds)) == 1 else ""
            if not same:
                p4_mismatch.append((op, wg, orders))
            w("(%s, W=%s): run-1 %s | run-2 %s | run-3 %s -- %s%s" %
              (op, wg, ">".join(orders[0]), ">".join(orders[1]), ">".join(orders[2]),
               "IDENTICAL" if same else "DIFFERS", tie_mark))
    w("P4 verdict: %s" %
      ("HOLDS (order identical at every (op, W))" if not p4_mismatch
       else "FAILURES NAMED: %s" % p4_mismatch))
    w("")

    w("== 8. scope (rule 4, verbatim from protocol.txt) ==")
    w("CHANNEL: INSTRUMENT channel -- a standalone measurement instrument on")
    w("raw ANV, neither the removed wire-42 loader path nor its ADR-0371")
    w("provider successor. Rule 4 binds in full: no workgroup row moves (no")
    w(":measured? flag, no :size, no :shapes, no selection answer -- the :intel")
    w("row 128 / :measured? true / key \"g31\" keeps its ADR-0358 provenance),")
    w("and this session is NOT the basis-replacing baseline-vs-variant")
    w("contract named in accelerator-subgroup-reduce.cljk (that contract is its")
    w("own future row and its own channel question). :arm/:unknown stay")
    w("provisional :measured? false.")
    w("UNMEASURED named: every W outside {128,256}; shape 2; any")
    w("baseline-vs-variant sign; cross-day replication; anything off this")
    w("host; the S=8 cells' timing (not realizable here); every workgroup-row")
    w("question.")
    sys.stdout.write("\n".join(out) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
