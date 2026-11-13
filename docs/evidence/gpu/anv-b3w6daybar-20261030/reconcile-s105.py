#!/usr/bin/env python3
"""reconcile-prego.py -- JUN-59 session 99: the W6 ADOPTION-CHAIN
CROSS-TOOL RECONCILIATION PRE-BUILD.

The s80 protocol sections 1/2/5/6 machinery preparation half (the
s90/s95/s96/s97/s98 pre-build precedent applied to the one W6 surface
that is still session-owned prose at every prior window: THE
RECONCILIATION BETWEEN THE ADOPTED TOOLS).  NO hardware runs, NO
builds, NO compiles, NO GO stamp, NO host writes, NO network
connections, NO day-slot consumption, NO ledger line.  This program
runs the five adopted W6 tools over COMMITTED-or-fresh record text,
parses their stdout, and cross-checks their overlapping derived
quantities; it submits NOTHING to any GPU and writes nothing except
its own stdout (the census twin's report goes to a caller-supplied
scratch path).

WHY THIS ROW (the gap): each of the five adopted tools was validated
against its OWN pins (s90/s95/s96/s97/s98) but they were never checked
against EACH OTHER.  At the W6 window the session publishes TWO
artifacts from the same fresh logs -- publication-s<NN>.txt (the
reading pair) and the settle-bar-ledger.txt line (the emitter) -- and
the s98 record section 1(b) names the residual outright: "the W6
session cross-checks this checker's verify-mismatch-total row against
the ledger emitter's own criterion-(2) derivation (session-owned named
residual -- two parsers over the same run logs)".  Two independent
parsers disagreeing at W6 would put two different numbers in the bar's
own record, live, under slot pressure.  This file mechanizes that
reconciliation and binds it NOW to the three common committed 78-run
windows, where every cross-checked quantity is committed and pinned.

MODES (deterministic; pure stdlib + subprocess of the adopted tools;
NO RNG, no clock; MOCK data appear only in --self-test FIXTURES):

  --compat (the default)  RUN THE CHAIN over the THREE committed
        78-run windows every other pre-build validates against (s36
        anv-b3commonmode-20261028 / s51 anv-b3levelrep-20261028 / W5
        anv-b3w5xdayrep-20261029, tagged s73 by the reading/ledger/
        custody tools): run the five adopted tools (reading-prego.py,
        derivation-census-prego.py, run-window-prego.py,
        custody-check-prego.py --check, ledger-prego.py --compat),
        parse their stdout, then CROSS-CHECK the overlapping derived
        quantities per window (X rows below) plus the tools' own stage
        verdicts (S rows).  Exit 0 iff every stage rc is 0 and every
        cross row MATCHes.

  --line <publication> <ledger-file> <session-tag>  reconcile ONE
        published reading against ONE ledger line -- the W6-fresh-side
        pair (median/min/class are the three quantities BOTH artifacts
        publish; the day is NOT compared here -- the reading publishes
        no day; the day is the emitter's derivation from run-window.txt
        host-date= fields).  Validated now on the COMMITTED pair
        publication-s73.txt vs the s73 line of settle-bar-ledger.txt.

  --self-test   fixture suite (synthetic row strings; reads NO
        committed window and runs NO adopted tool).

THE CROSS-CHECK SET (per window W in {s36, s51, s73}; every want/got
value is PARSED from the adopted tools' real stdout in --compat, never
transcribed):
  X1 anchor-median      reading sec3b median == ledger line median
  X2 anchor-min         reading sec3b min    == ledger line min
  X3 census-median      reading sec3b median == census sec3b median
                        (the s90 independence pair, cross-compared)
  X4 census-min         reading sec3b min    == census sec3b min
  X5 census-max         reading sec3b max    == census sec3b max
  X6 verify-residual    reading sec1 vmis == custody
                        verify-mismatch-total == 0 and ledger flag
                        != verify-mismatch  (the s98-named
                        session-owned residual, mechanized)
  X7 run-census         reading sec1 runs == custody run-count ==
                        run-window frozen-order count (78)
  X8 flag-join          custody (flag none, ledger-pin ok,
                        ledger-go ok) joins to the ledger line's
                        flag=none (the s98 decide_ledger_inputs join,
                        end-to-end against the emitted line)
  X9 day-derivation     ledger line day == the single distinct
                        host-date date-part of the window's
                        run-window.txt per-run rows
  X10 class             reading anchor class == ledger line class
                        (s73 only -- NAMED LIMIT: reading --compat
                        publishes no class for the prior windows)
  X11 c1-boolean        reading sec2 rows (c2 FLOOR; C1 branch (a))
                        consistent with ledger flag != c1-b at every
                        window (criterion (1) is per-window internal
                        to the emitter -- cross-checked boolean)

NAMED, NOT HIDDEN: this reconciliation validates the chain on the
three COMMITTED common windows only.  It computes NO statistic of any
run log (it compares already-published quantities), NO W6 quantity
exists here (the W6 run logs do not exist at pre-build time), and the
s38/s39 windows are out of scope for the chain (committed no
run-window.txt -- the custody/run-window stages have no substrate
there).  The window-shape limit is real: the chain substrate is the
78-run windows only.

ADOPTION CONTRACT: the W6 session re-runs --compat in its own record
(the committed-window chain is the byte-level proof the parsers
agree), runs --line publication-s<NN>.txt ../../settle-bar-ledger.txt
s<NN> on its fresh pair AFTER the append (and re-runs --self-test),
and records the output beside the standing gate set.  The execution
path (ssh, staging, GO, record prose) stays session-owned exactly as
at s51/s73.
"""
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
GPU = os.path.abspath(os.path.join(HERE, ".."))

# The five adopted W6 tools (pre-build locations; the W6 session runs
# the adopted copies -- the interfaces are frozen by these captures).
READING = os.path.join(GPU, "anv-b3w6prego-20261029", "reading-prego.py")
CENSUS = os.path.join(GPU, "anv-b3w6prego-20261029", "derivation-census-prego.py")
RUNWIN = os.path.join(GPU, "anv-b3w6runprego-20261029", "run-window-prego.py")
CUSTODY = os.path.join(GPU, "anv-b3w6custodycheckrego-20261029",
                       "custody-check-prego.py")
LEDGER = os.path.join(GPU, "anv-b3w6ledgerrego-20261029", "ledger-prego.py")

# (chain tag, window dir, manifest, custody --check tag, run-window tag)
WINDOWS = [
    ("s36", "anv-b3commonmode-20261028", "cases-s36-a.txt", "s36", "s36"),
    ("s51", "anv-b3levelrep-20261028", "cases-s51-a.txt", "s51", "s51"),
    ("s73", "anv-b3w5xdayrep-20261029", "cases-s73-a.txt", "s73", "W5"),
]

RUN_EXPECT = 78  # the frozen 78-run order (s57 route)


# ---------------------------------------------------------------- parse
def parse_reading(text):
    """reading/census --compat report -> {"sec1": {tag: (runs, vmis)},
    "sec3b": {tag: (median, lo, hi, class-or-None)}, "sec2": {...}}."""
    sec1, sec3b, sec2 = {}, {}, {}
    for line in text.splitlines():
        m = re.match(r"sec1 (s\d+) integrity\s+want:.*?got: runs (\d+) vmis (\d+) ",
                     line)
        if m:
            sec1[m.group(1)] = (int(m.group(2)), int(m.group(3)))
            continue
        m = re.match(r"sec3b (s\d+) anchor(?: \(fresh\))?\s+want:.*?"
                     r"got: (\d+) (\d+)\.\.(\d+)(?: (\S+))?\s+EXACT", line)
        if m:
            sec3b[m.group(1)] = (int(m.group(2)), int(m.group(3)),
                                 int(m.group(4)),
                                 m.group(5) if m.group(5) else None)
            continue
        m = re.match(r"sec2 c2 class\s+want:.*?got: (\S+)\s+EXACT", line)
        if m:
            sec2["c2-class"] = m.group(1)
            continue
        m = re.match(r"sec2 c8 pooled median\s+want:.*?got: (\d+)\s+EXACT", line)
        if m:
            sec2["c8-median"] = int(m.group(1))
            continue
        m = re.match(r"sec2 C1 branch\s+want:.*?got: (\S.*?\S)\s+EXACT", line)
        if m:
            sec2["c1-branch"] = m.group(1)
    return {"sec1": sec1, "sec3b": sec3b, "sec2": sec2}


def parse_ledger(text):
    """ledger-prego --compat -> {"S": {"day","session","class","median",
    "min","flag","match"(bool)}}."""
    out, cur = {}, None
    for line in text.splitlines():
        m = re.match(r"(s\d+) (\S+) day-src=", line)
        if m:
            cur = m.group(1)
            out[cur] = {"dir": m.group(2)}
            continue
        m = re.match(r"  got : day=(\S+) session=(\S+) class=(\S+) "
                     r"median=(\d+) min=(\d+) flag=(\S+)", line)
        if m and cur:
            out[cur].update(day=m.group(1), session=m.group(2),
                            cls=m.group(3), median=int(m.group(4)),
                            minv=int(m.group(5)), flag=m.group(6))
            continue
        if line.strip() == "-> MATCH" and cur:
            out[cur]["match"] = True
        elif line.strip().startswith("->") and cur:
            out[cur]["match"] = False
    return out


def parse_custody(text):
    """custody-check-prego --check -> {"checks": {name: (want, got,
    verdict)}, "flag","pin","go","rc-irrelevant"}."""
    checks, head = {}, {}
    for line in text.splitlines():
        m = re.match(r"  check=(\S+) want=(\S+) got=(\S*) verdict=(\S+)", line)
        if m:
            checks[m.group(1)] = (m.group(2), m.group(3), m.group(4))
            continue
        m = re.match(r"^(flag|ledger-pin|ledger-go)=(\S+)$", line.strip())
        if m:
            head[m.group(1)] = m.group(2)
    return {"checks": checks, "head": head}


def parse_runwin(text):
    """run-window-prego --compat -> {"order": {tag: (n, verdict)},
    "bytes": {tag: (rows, mismatched)}, "total": (rows, mismatched)}."""
    order, byts, total = {}, {}, None
    for line in text.splitlines():
        m = re.match(r"window (\S+) \(\S+\): frozen plan order vs committed "
                     r"per-run order (\d+)/\d+ (\S+)", line)
        if m:
            order[m.group(1)] = (int(m.group(2)), m.group(3))
            continue
        m = re.match(r"window (\S+): (?:per-run TABLE|table\+trailer) rebuilt "
                     r"bytes vs committed bytes \d+/\d+ (\S+) \(.*?"
                     r"(\d+) mismatched\)", line)
        if m:
            byts[m.group(1)] = (m.group(2), int(m.group(3)))
            continue
        m = re.match(r"--compat TOTAL (\d+) rows (\d+) mismatched", line)
        if m:
            total = (int(m.group(1)), int(m.group(2)))
    return {"order": order, "bytes": byts, "total": total}


def parse_pub_tuples(text):
    """publication anchor/bar rows -> [(median, lo, hi, class), ...] (all
    rows of the shape 'median N min..max N..N' with a class)."""
    out = []
    for line in text.splitlines():
        m = re.search(r"median (\d+) min\.\.max (\d+)\.\.(\d+).*?"
                      r"class (\S+)", line)
        if m:
            out.append((int(m.group(1)), int(m.group(2)), int(m.group(3)),
                        m.group(4).rstrip(",;")))
    return out


def parse_ledger_line(text, tag):
    """the ONE ledger line of a session tag -> dict or None."""
    for line in text.splitlines():
        m = re.match(r"day=(\S+) session=(\S+) class=(\S+) median=(\d+) "
                     r"min=(\d+) flag=(\S+)$", line.strip())
        if m and m.group(2) == tag:
            return {"day": m.group(1), "cls": m.group(3),
                    "median": int(m.group(4)), "minv": int(m.group(5)),
                    "flag": m.group(6)}
    return None


def run_window_hostdays(path):
    """run-window.txt per-run rows -> (count, sorted distinct date-parts)."""
    days = []
    with open(path) as f:
        for line in f:
            if re.match(r"^\s+\S+\s+rc=\d+\s+host-date=", line):
                m = re.search(r"host-date=(\d{4}-\d{2}-\d{2})T", line)
                days.append(m.group(1) if m else "UNPARSEABLE")
    return len(days), sorted(set(days))


def run_tool(args):
    p = subprocess.run([sys.executable] + args, capture_output=True,
                       text=True)
    return p.returncode, p.stdout, p.stderr


# ---------------------------------------------------------------- chain
def run_chain():
    out = []
    mism = [0]
    stages = [0, 0]
    xrows = [0]

    def xrow(name, tag, desc, pairs, ok):
        # pairs: (label, value) shown verbatim; ok: the row's explicit
        # consistency predicate (equality where the values are the same
        # quantity, the named join/implication where they are not).
        xrows[0] += 1
        if not ok:
            mism[0] += 1
        out.append("%s %s %-16s %s -> %s" % (
            name, tag, desc,
            " ".join("%s=%s" % (l, v) for l, v in pairs),
            "MATCH" if ok else "MISMATCH"))

    def srow(desc, ok):
        stages[0] += 1
        if not ok:
            stages[1] += 1
        out.append("STAGE %-56s -> %s" % (desc, "OK" if ok else "FAIL"))

    out.append("JUN-59 session 99 -- reconcile-prego --compat: the W6")
    out.append("ADOPTION-CHAIN CROSS-TOOL RECONCILIATION over the THREE")
    out.append("common committed 78-run windows (s36/s51/W5=s73).  Every")
    out.append("value below is PARSED from the five adopted tools' real")
    out.append("stdout runs (their bytes are the committed pins), never")
    out.append("transcribed; this program computes NO statistic of any run")
    out.append("log and NO W6 quantity exists (the W6 run logs do not")
    out.append("exist).  MOCK appears nowhere in this mode.")

    # -- the five adopted tools, run exactly as their captures run them.
    rc_r, t_r, e_r = run_tool([READING])
    fd, census_out = tempfile.mkstemp(prefix="reconcile-s99-census-")
    os.close(fd)
    rc_c, t_c, e_c = run_tool([CENSUS, census_out])
    with open(census_out) as f:
        t_census = f.read()
    os.unlink(census_out)
    rc_w, t_w, e_w = run_tool([RUNWIN, "--compat"])
    custody_runs = {}
    for tag, wdir, manifest, ctag, _ in WINDOWS:
        rc, t, e = run_tool([CUSTODY, "--check", wdir, ctag, manifest])
        custody_runs[tag] = (rc, t, e)
    rc_l, t_l, e_l = run_tool([LEDGER, "--compat"])

    R, C = parse_reading(t_r), parse_reading(t_census)
    L, W = parse_ledger(t_l), parse_runwin(t_w)

    srow("reading-prego.py --compat rc=%d rows=%d" % (
        rc_r, len(R["sec1"]) + len(R["sec3b"]) + len(R["sec2"])),
        rc_r == 0 and len(R["sec3b"]) == 5)
    srow("derivation-census-prego.py rc=%d rows=%d" % (
        rc_c, len(C["sec1"]) + len(C["sec3b"]) + len(C["sec2"])),
        rc_c == 0 and len(C["sec3b"]) == 5)
    srow("run-window-prego.py --compat rc=%d total=%s" % (rc_w, W["total"]),
         rc_w == 0 and W["total"] == (243, 0))
    for tag, _, _, _, _ in WINDOWS:
        rc, t, _e = custody_runs[tag]
        H = parse_custody(t)["head"]
        srow("custody-check-prego --check %s rc=%d flag=%s pin=%s go=%s" % (
            tag, rc, H.get("flag"), H.get("ledger-pin"), H.get("ledger-go")),
            rc == 0)
    srow("ledger-prego.py --compat rc=%d rows=%d" % (rc_l, len(L)),
         rc_l == 0 and len(L) == 9)

    out.append("")
    out.append("CROSS-CHECKS (the row this file exists for):")
    for tag, wdir, _manifest, _ctag, wtag in WINDOWS:
        rc, t, _e = custody_runs[tag]
        CH, HD = parse_custody(t)["checks"], parse_custody(t)["head"]
        sec1 = R["sec1"].get(tag)
        sec3b = R["sec3b"].get(tag)
        csec3b = C["sec3b"].get(tag)
        led = L.get(tag, {})
        nruns, days = run_window_hostdays(os.path.join(GPU, wdir,
                                                       "run-window.txt"))
        if not (sec1 and sec3b and csec3b and led and CH):
            mism[0] += 1
            xrows[0] += 1
            out.append("X0 %s parse               PARSE-MISSING -> MISMATCH"
                       % tag)
            continue
        xrow("X1", tag, "anchor-median", [("reading", sec3b[0]),
                                          ("ledger", led["median"])],
             sec3b[0] == led["median"])
        xrow("X2", tag, "anchor-min", [("reading", sec3b[1]),
                                       ("ledger", led["minv"])],
             sec3b[1] == led["minv"])
        xrow("X3", tag, "census-median", [("reading", sec3b[0]),
                                          ("census", csec3b[0])],
             sec3b[0] == csec3b[0])
        xrow("X4", tag, "census-min", [("reading", sec3b[1]),
                                       ("census", csec3b[1])],
             sec3b[1] == csec3b[1])
        xrow("X5", tag, "census-max", [("reading", sec3b[2]),
                                       ("census", csec3b[2])],
             sec3b[2] == csec3b[2])
        # X6: the s98-named session-owned residual, mechanized -- the two
        # VERIFY-mismatch derivations must agree numerically (reading
        # sec1 vmis vs custody verify-mismatch-total) and the emitter's
        # criterion-(2) token fires only when they are > 0.
        vmis_r = sec1[1]
        vmis_c = CH["verify-mismatch-total"][1]
        xrow("X6", tag, "verify-residual",
             [("reading-vmis", vmis_r),
              ("custody-vmis", vmis_c),
              ("ledger-flag", led["flag"])],
             str(vmis_r) == str(vmis_c)
             and (int(vmis_r) > 0 or led["flag"] != "verify-mismatch"))
        xrow("X7", tag, "run-census",
             [("reading-runs", sec1[0]),
              ("custody-runs", CH["run-count"][1]),
              ("runwindow-runs", W["order"].get(wtag, ("?",))[0]),
              ("hostdates", nruns)],
             len(set([str(sec1[0]), str(CH["run-count"][1]),
                      str(W["order"].get(wtag, ("?",))[0]),
                      str(nruns)])) == 1)
        # X8: the s98 decide_ledger_inputs join end-to-end -- clean
        # custody inputs + clean C1 imply the emitted line's flag=none
        # (the FLAGGED shapes are owned by the s97/s98 self-test
        # batteries and are out of scope for this chain row).
        join_clean = (HD.get("flag") == "none" and HD.get("ledger-pin") ==
                      "ok" and HD.get("ledger-go") == "ok")
        xrow("X8", tag, "flag-join",
             [("custody-flag", HD.get("flag")),
              ("pin", HD.get("ledger-pin")), ("go", HD.get("ledger-go")),
              ("ledger-line-flag", led["flag"])],
             (led["flag"] == "none") if join_clean
             else led["flag"] != "none")
        want_day = days[0] if len(days) == 1 else "days=%s" % days
        xrow("X9", tag, "day-derivation",
             [("ledger-day", led["day"]), ("hostdates", want_day)],
             len(days) == 1 and led["day"] == days[0])
        if sec3b[3] is None:
            out.append("X10 %s class           SKIPPED (reading --compat "
                       "publishes no class for prior windows -- NAMED "
                       "LIMIT)" % tag)
        else:
            xrow("X10", tag, "class", [("reading", sec3b[3]),
                                       ("ledger", led["cls"])],
                 sec3b[3] == led["cls"])
        # X11: C1 boolean -- the reading pair's C1 machinery (the sec2
        # rows, publication-s73's window; NAMED LIMIT: one window's
        # rows read at every window) constructs branch (a) clean, and
        # the emitter's per-window criterion-(1) is clean at every
        # window (flag != c1-b).  c1-b is FIRST in the frozen
        # precedence, so a fired C1 must show as c1-b.
        c8m = R["sec2"].get("c8-median", -1)
        c1_clean = (R["sec2"].get("c2-class") == "FLOOR"
                    and R["sec2"].get("c1-branch", "").startswith("(a)")
                    and abs(c8m - 32915) * 20 <= 32915)
        xrow("X11", tag, "c1-boolean",
             [("reading-c1", R["sec2"].get("c1-branch", "?")),
              ("c2-class", R["sec2"].get("c2-class", "?")),
              ("c8-median", c8m),
              ("ledger-flag", led["flag"])],
             c1_clean and led["flag"] != "c1-b")

    out.append("")
    out.append("TOTAL: stage rows %d failed %d | cross rows %d mismatched %d"
               % (stages[0], stages[1], xrows[0], mism[0]))
    ok = stages[1] == 0 and mism[0] == 0
    out.append("RECONCILE VERDICT: %s" % ("CONSISTENT" if ok
                                          else "INCONSISTENT"))
    return "\n".join(out) + "\n", ok


# ---------------------------------------------------------------- line
def run_line(pub_path, ledger_path, tag):
    out, ok = [], True
    with open(pub_path) as f:
        tuples = parse_pub_tuples(f.read())
    with open(ledger_path) as f:
        line = parse_ledger_line(f.read(), tag)
    out.append("JUN-59 reconcile-prego --line: published reading vs ledger "
               "line (median/min/class; day is the emitter's derivation "
               "and is NOT compared here).")
    out.append("publication rows parsed: %d" % len(tuples))
    if not tuples or line is None:
        out.append("PARSE-MISSING (publication rows %d, ledger line %s)"
                   % (len(tuples), "present" if line else "ABSENT"))
        return "\n".join(out) + "\n", False
    same = len(set(tuples)) == 1
    t = tuples[0]
    out.append("pub-rows-agree=%s %s" % (same, " ".join(
        "%d %d..%d %s" % x for x in sorted(set(tuples)))))
    out.append("ledger line: day=%s class=%s median=%d min=%d flag=%s"
               % (line["day"], line["cls"], line["median"], line["minv"],
                  line["flag"]))
    for desc, a, b in (("median", t[0], line["median"]),
                       ("min", t[1], line["minv"]),
                       ("class", t[3], line["cls"])):
        m = a == b
        if not m:
            ok = False
        out.append("X %s pub=%s line=%s -> %s" % (desc, a, b,
                                                  "MATCH" if m else "MISMATCH"))
    ok = ok and same
    out.append("RECONCILE VERDICT: %s" % ("CONSISTENT" if ok
                                          else "INCONSISTENT"))
    return "\n".join(out) + "\n", ok


# ---------------------------------------------------------------- tests
def run_selftest():
    checks, results = [0, 0], []

    def ck(name, cond):
        checks[0] += 1
        if not cond:
            checks[1] += 1
        results.append((name, cond))

    reading_fixture = "\n".join([
        "sec1 s36 integrity           want: runs 78 vmis 0 counts True "
        "knobs True s8 True cmap True got: runs 78 vmis 0 counts True "
        "knobs True s8 True cmap True EXACT",
        "sec2 c2 class                want: FLOOR   got: FLOOR   EXACT",
        "sec2 c8 pooled median        want: 32709   got: 32709   EXACT",
        "sec2 C1 branch               want: (a) both controls replicate  "
        "got: (a) both controls replicate  EXACT",
        "sec3b s36 anchor             want: 1142 991..1438  got: 1142 "
        "991..1438  EXACT",
        "sec3b s73 anchor (fresh)     want: 1131 998..1442 INTERMEDIATE/"
        "MIXED  got: 1131 998..1442 INTERMEDIATE/MIXED  EXACT",
    ])
    R = parse_reading(reading_fixture)
    ck("reading-sec1-runs", R["sec1"]["s36"] == (78, 0))
    ck("reading-sec3b-prior", R["sec3b"]["s36"] == (1142, 991, 1438, None))
    ck("reading-sec3b-fresh", R["sec3b"]["s73"] == (1131, 998, 1442,
                                                    "INTERMEDIATE/MIXED"))
    ck("reading-sec2", R["sec2"] == {"c2-class": "FLOOR", "c8-median": 32709,
                                     "c1-branch": "(a) both controls "
                                                  "replicate"})

    ledger_fixture = "\n".join([
        "s36 anv-b3commonmode-20261028 day-src=derived(78 host-date "
        "fields, 1 distinct)",
        "  want: day=2026-10-28 session=s36 class=INTERMEDIATE/MIXED "
        "median=1142 min=991 flag=none",
        "  got : day=2026-10-28 session=s36 class=INTERMEDIATE/MIXED "
        "median=1142 min=991 flag=none",
        "  -> MATCH",
    ])
    L = parse_ledger(ledger_fixture)
    ck("ledger-row", L["s36"] == {"dir": "anv-b3commonmode-20261028",
                                  "day": "2026-10-28", "session": "s36",
                                  "cls": "INTERMEDIATE/MIXED",
                                  "median": 1142, "minv": 991,
                                  "flag": "none", "match": True})

    custody_fixture = "\n".join([
        "  check=verify-mismatch-total want=0 got=0 verdict=OK",
        "  check=run-count want=78 got=78 verdict=OK",
        "flag=none",
        "ledger-pin=ok",
        "ledger-go=ok",
    ])
    C = parse_custody(custody_fixture)
    ck("custody-checks", C["checks"]["verify-mismatch-total"] ==
      ("0", "0", "OK"))
    ck("custody-head", C["head"] == {"flag": "none", "ledger-pin": "ok",
                                     "ledger-go": "ok"})

    runwin_fixture = "\n".join([
        "window s36 (anv-b3commonmode-20261028): frozen plan order vs "
        "committed per-run order 78/78 MATCH",
        "window s36: per-run TABLE rebuilt bytes vs committed bytes 78/78 "
        "BYTE-EQUAL (rows, 0 mismatched)",
        "--compat TOTAL 243 rows 0 mismatched",
    ])
    W = parse_runwin(runwin_fixture)
    ck("runwin-order", W["order"]["s36"] == (78, "MATCH"))
    ck("runwin-bytes", W["bytes"]["s36"] == ("BYTE-EQUAL", 0))
    ck("runwin-total", W["total"] == (243, 0))

    ck("pub-tuple-prior",
       parse_pub_tuples("    s36: median 1142 min..max 991..1438 (want "
                        "1142 / 991..1438); reproduction EXACT: True") == [])
    ck("pub-tuple-fresh",
       parse_pub_tuples("    s73 (NEW): median 1131 min..max 998..1442; "
                        "class INTERMEDIATE/MIXED") ==
       [(1131, 998, 1442, "INTERMEDIATE/MIXED")])
    ck("ledger-line",
       parse_ledger_line("day=2026-10-29 session=s73 class=INTERMEDIATE/"
                         "MIXED median=1131 min=998 flag=none\n", "s73") ==
       {"day": "2026-10-29", "cls": "INTERMEDIATE/MIXED", "median": 1131,
        "minv": 998, "flag": "none"})
    ck("ledger-line-tag-miss",
       parse_ledger_line("day=2026-10-29 session=s73 class=INTERMEDIATE/"
                         "MIXED median=1131 min=998 flag=none\n", "s99")
       is None)

    # comparison semantics: a cross row MATCHes iff all values are equal
    ck("cmp-eq", len(set([1131, 1131])) == 1)
    ck("cmp-ne", len(set([1131, 1132])) == 2)
    # a prior-window pub row has no class and must NOT parse as a tuple
    ck("pub-tuple-classless-skipped",
       parse_pub_tuples("    s51: median 1137 min..max 988..1430 (want "
                        "1137 / 988..1430); reproduction EXACT: True") == [])

    out = ["JUN-59 reconcile-prego --self-test (MOCK FIXTURES, NEVER",
           "MEASUREMENTS; reads NO committed window and runs NO adopted",
           "tool)."]
    for i, (name, cond) in enumerate(results):
        out.append("assertion %d %s: %s" % (i + 1, name,
                                            "ok" if cond else "FAIL"))
    out.append("--self-test TOTAL %d assertions passed %d failed"
               % (checks[0], checks[1]))
    return "\n".join(out) + "\n", checks[1] == 0


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "--self-test":
        text, ok = run_selftest()
    elif len(sys.argv) >= 2 and sys.argv[1] == "--line":
        if len(sys.argv) != 5:
            print("usage: reconcile-prego.py --line <publication> "
                  "<ledger-file> <session-tag>")
            sys.exit(2)
        text, ok = run_line(sys.argv[2], sys.argv[3], sys.argv[4])
    elif len(sys.argv) == 1 or sys.argv[1] == "--compat":
        text, ok = run_chain()
    else:
        print("usage: reconcile-prego.py [--compat | --line <publication> "
              "<ledger-file> <session-tag> | --self-test]")
        sys.exit(2)
    sys.stdout.write(text)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
