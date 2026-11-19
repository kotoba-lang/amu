#!/usr/bin/env python3
"""JUN-59 session 97 -- W6 LEDGER-LINE PRE-BUILD (the W6 measurement
row's LEDGER-PATH IMPLEMENTATION preparation half -- the s69/s90/s95/s96
pre-build precedent applied to the settle-bar-ledger.txt line surface of
the s80 protocol sections 1/5; NO hardware runs, NO builds, NO compiles,
NO GO stamp, NO host writes, NO network connections, NO day-slot
consumption, NO ledger line appended).

WHAT THIS IS (honest states): an IMPLEMENTATION pre-build of the one
surface of the W6 session's chore that had NO machinery anywhere in the
tree: THE LEDGER LINE ITSELF -- the byte construction of the single
"day=... session=... class=... median=... min=... flag=..." line the s80
protocol section 5 appends to docs/evidence/gpu/settle-bar-ledger.txt
after the gates, and the FLAGGED join that decides its flag= field.  The
s96 custody checker named criterion (1) C1 a scope cut ("(1) C1 is the
s90 reading pair's surface and is NOT computed here"); this file closes
that cut at the join: it re-derives criterion (1) from the window's run
logs under the frozen construction and joins it with the custody/build
criteria in the frozen precedence order.  It is NOT the W6 session's
script yet: the W6 session (the first measurement session starting at or
after 2026-10-30T00:00:00Z) adopts this file as ledger-s<NN>.py and owns
the append (this machinery EMITS the line; the append to the tracked
ledger happens ONLY after the standing gate set verifies -- s80 section
5).  NO W6 quantity exists or is computed here -- the W6 run logs do not
exist at pre-build time.

THE LINE (frozen; settle-bar.txt section 2 + the s80 protocol section 1):
  day     = the window run's ACTUAL UTC day (run-window.txt per-run
            host-date= fields; the single distinct day; a window spanning
            two days refuses -- fail-closed),
  session = the running session's tag s<NN>,
  class   = the bar's frozen section-4 threshold read on hi block A's
            18 pipeline-ok cells (FLOOR <= 100 ticks at all 18; CAPTURED
            >= 1000 at all 18; anything else INTERMEDIATE/MIXED),
  median  = hi block A's (sum,128,S=16) pooled median (3 fresh
            processes pooled over 25 rounds per cell -- settle-bar.txt
            F3, the frozen estimator unit),
  min     = the minimum of hi block A's 18 per-cell pooled medians,
  flag    = none for a qualifying reading; else the first fired frozen
            FLAGGED criterion's token.

THE FLAG JOIN (frozen order, settle-bar.txt section 2 FLAGGED + the s80
protocol section 1): (1) C1 fired (b) -> "c1-b"; (2) VERIFY mismatch >
0 -> "verify-mismatch"; (3) build pin not byte-identical -> "pin-missing";
(4) custody GO missing/after the builds -> "custody-go".  First fired in
that order wins.  Criterion (1) is RE-DERERIVED here from the run logs
(the c2 FLOOR control over c2 r1-3 and the c8 (sum,128,S=16) pooled
median within +/-5% of the committed 32,915 over c8 r1-3 -- the frozen
construction, the reading pair's surface, derived a second time so the
join depends on no other script's output).  Criteria (2) is re-derived
from the run logs' VERIFY mismatch totals.  Criteria (3)/(4) are the s96
custody checker's surface (custody-s<NN>.py) and are consumed here as
EXPLICIT INPUTS (--pin ok|flagged, --go ok|flagged); an undecided or
absent input REFUSES fail-closed (REFUSED-INPUT-UNDECIDED) -- this
machinery can only lead to a correct line, never to a qualifying line
whose custody half was never decided.  The token spellings c1-b /
verify-mismatch / pin-missing follow the frozen evaluator's committed
fixture vocabulary (settle-bar-eval.py fixtures); custody-go has no
fixture and is NAMED here (any non-none token is FLAGGED identically --
settle-bar-eval.py treats all tokens the same; the spelling is
descriptive only).

VALIDATION AVAILABLE NOW (--compat mode, the default under this
pre-build name): the derivation run over the NINE committed
bar-executing windows (s31 anv-b3xday-20261028, s32 anv-b3x1rec-20261028,
s33 anv-b3repr-20261028, s34 anv-b3minwander-20261028, s36
anv-b3commonmode-20261028, s38 anv-b3joint3-20261028, s39
anv-b3joint4-20261028, s51 anv-b3levelrep-20261028, s73
anv-b3w5xdayrep-20261029 -- five window SHAPES: 9/9/12/42/78 runs) must
reproduce the nine committed settle-bar-ledger.txt lines BYTE-EXACT,
with want values PARSED from the committed ledger bytes, never
transcribed.  That validates the run-log parsing, the pooled-median
estimator, the class threshold, the C1 construction and the line byte
shape end-to-end against the committed ledger, on shapes far beyond the
78-run route the reading pair parses.  NAMED, NOT HIDDEN: the per-run
host-date= fields exist in no run log (live-only at capture); they are
read at --compat time from the committed run-window.txt transcripts (7
windows) and QUOTED from the committed ledger line as INPUT for s38/s39
(committed no run-window.txt); pin=ok/go=ok are QUOTED inputs for all
nine (the committed records attest B1 qualifying and the committed lines
carry flag=none -- re-checking the custody records is the s96 checker's
job, run alongside this one at W6).  The W6-dependent parts (the W6
line itself, its live host-date, its live pin/go inputs) are
UNVALIDATED here, named, not hidden.

--self-test runs MOCK windows (synthetic in-memory run logs -- FIXTURES,
never measurements; it opens NO committed window and touches NO
filesystem): the clean line, every FLAGGED criterion alone, the frozen
precedence order at every overlap, the fail-closed refusals (undecided
input, missing anchor run, two-day window, missing/unparseable day,
cell-map drift, short sample census, no ok (sum,128,S=16) cell) and a
line-grammar conformance check (six k=v tokens, exact key order, int
median/min, class vocabulary).  THIS FILE COMPUTES NO BAR VERDICT:
settle-bar-eval.py is the only verdict source (settle-bar.txt section
3); the grammar check validates byte shape only.

Frozen implementation paths (s80 protocol section 6): deterministic
scripts only; the frozen filename is ledger-s<NN>.py with <NN> the
running session's number (enforced below -- the W6 emit mode under the
pre-build name refuses to run).
"""
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
GPU = os.path.join(ROOT, "docs", "evidence", "gpu")
LEDGER = os.path.join(GPU, "settle-bar-ledger.txt")

_name = os.path.basename(__file__)
_m = re.match(r"ledger-s(\d+)\.py$", _name)
MODE = "w6" if _m else "compat"

WIN9 = [("s31", "anv-b3xday-20261028"),
        ("s32", "anv-b3x1rec-20261028"),
        ("s33", "anv-b3repr-20261028"),
        ("s34", "anv-b3minwander-20261028"),
        ("s36", "anv-b3commonmode-20261028"),
        ("s38", "anv-b3joint3-20261028"),
        ("s39", "anv-b3joint4-20261028"),
        ("s51", "anv-b3levelrep-20261028"),
        ("s73", "anv-b3w5xdayrep-20261029")]
W6_DIR = "anv-b3w6daybar-20261030"

COMMITTED_C8 = 32915            # settle-bar/protocol C1 construction
BAR_REFS = (1129, 1132, 1131)   # settle-bar.txt D3 frozen refs (quoted)
CELLKEY_SUM128 = ("sum", 128, "16")
CLASS_VOCAB = ("FLOOR", "CAPTURED", "INTERMEDIATE/MIXED")
FLAG_VOCAB = ("none", "c1-b", "verify-mismatch", "pin-missing", "custody-go")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SESSION_RE = re.compile(r"^s\d+$")

cell_re = re.compile(
    r"^CELL idx=(\d+) spv=(\S+) op=(\S+) wg=(\d+) forced=(\S+) probe_size=(-?\d+) "
    r"probe_nsub=(-?\d+) probe_wg=(-?\d+) pipeline=(\S+) void=(\d)")
verify_re = re.compile(r"^VERIFY idx=(\d+) checked=(\d+) mismatch=(\d+) ok=(\d)")
sample_re = re.compile(
    r"^SAMPLE round=(\d+) idx=(\d+) batch=(\d+) work_mul=(\d+) ndiv=(\d+) gpu_ticks=(\d+)")
hostdate_re = re.compile(r"host-date=(\d{4}-\d{2}-\d{2})T\d{2}:\d{2}:\d{2}Z")
runfile_re = re.compile(r"^run-(.+)-r(\d+)\.txt$")


def load_log(text):
    """One run log's text -> (cells, mismatches, samples)."""
    cells, mismatches, samples = {}, [], []
    for raw in text.splitlines():
        line = raw.rstrip("\n")
        if line.startswith("CELL "):
            m = cell_re.match(line)
            assert m, line
            cells[int(m.group(1))] = dict(
                op=m.group(3), wg=int(m.group(4)), forced=m.group(5),
                pipeline=m.group(9), void=m.group(10))
        elif line.startswith("VERIFY "):
            m = verify_re.match(line)
            assert m, line
            mismatches.append(int(m.group(3)))
        elif line.startswith("SAMPLE "):
            m = sample_re.match(line)
            assert m, line
            samples.append((int(m.group(2)), int(m.group(6))))
    return cells, mismatches, samples


def bar_class(bvals):
    if all(v <= 100 for v in bvals):
        return "FLOOR"
    if all(v >= 1000 for v in bvals):
        return "CAPTURED"
    return "INTERMEDIATE/MIXED"


def line_shape(day, session, cls, med, mn, flag):
    return "day=%s session=%s class=%s median=%d min=%d flag=%s" % (
        day, session, cls, med, mn, flag)


def grammar_ok(line):
    """Byte-shape conformance with settle-bar-eval.py's documented
    grammar ONLY -- this is not a verdict and computes none."""
    toks = line.split(" ")
    if len(toks) != 6:
        return False
    keys = ["day", "session", "class", "median", "min", "flag"]
    vals = []
    for tok, key in zip(toks, keys):
        k, _, v = tok.partition("=")
        if k != key or not v:
            return False
        vals.append(v)
    day, session, cls, med, mn, flag = vals
    return (DATE_RE.match(day) is not None
            and SESSION_RE.match(session) is not None
            and cls in CLASS_VOCAB
            and med.isdigit() and mn.isdigit()
            and flag in FLAG_VOCAB)


def derive(files, session, pin, go, day_quoted=None):
    """One window -> its ledger line, or a REFUSED-... token.

    files: {filename: text} (a real window dir's bytes at --compat/w6
    time, or an in-memory MOCK at --self-test -- the MOCK bytes are
    FIXTURES, never measurements).  pin/go: "ok" | "flagged" | anything
    else = undecided (refuse).  day_quoted: the YYYY-MM-DD to quote when
    no run-window.txt host-date= field exists (named quoted input).
    """
    if pin not in ("ok", "flagged"):
        return "REFUSED-INPUT-UNDECIDED"
    if go not in ("ok", "flagged"):
        return "REFUSED-INPUT-UNDECIDED"

    runs = {}
    for fn in sorted(files):
        m = runfile_re.match(fn)
        if m:
            runs.setdefault(m.group(1), set()).add(int(m.group(2)))
    for need in (("hi", (1, 2, 3)), ("c2", (1, 2, 3)), ("c8", (1, 2, 3))):
        tag, rs = need
        if not all(r in runs.get(tag, set()) for r in rs):
            return "REFUSED-NO-READING"

    parsed = {}
    ref_map = None
    vmis = 0
    for tag in sorted(runs):
        for r in sorted(runs[tag]):
            cells, mismatches, samples = load_log(files["run-%s-r%d.txt" % (tag, r)])
            parsed[(tag, r)] = (cells, mismatches, samples)
            vmis += sum(mismatches)
            cmap = tuple(sorted((k, v["op"], v["wg"], v["forced"],
                                 v["pipeline"], v["void"])
                                for k, v in cells.items()))
            if ref_map is None:
                ref_map = cmap
            elif cmap != ref_map:
                return "REFUSED-CELL-MAP"

    base = parsed[("c2", 1)][0]
    ok_cells = sorted(k for k, v in base.items() if v["pipeline"] == "ok")
    sum128 = [k for k in ok_cells
              if (base[k]["op"], base[k]["wg"], base[k]["forced"]) == CELLKEY_SUM128]
    if len(sum128) != 1:
        return "REFUSED-NO-SUM128"
    sum128 = sum128[0]

    def pooled(tag, idx, rs):
        xs = []
        for r in rs:
            xs += [s[1] for s in parsed[(tag, r)][2] if s[0] == idx]
        if len(xs) != 25 * len(rs):
            return None
        return int(statistics.median(xs))

    def block_vals(tag, rs):
        vals = []
        for k in ok_cells:
            v = pooled(tag, k, rs)
            if v is None:
                return None
            vals.append(v)
        return vals

    bvals = block_vals("hi", (1, 2, 3))
    if bvals is None:
        return "REFUSED-SAMPLE-COUNT"
    med = pooled("hi", sum128, (1, 2, 3))
    cls = bar_class(bvals)
    mn = min(bvals)

    # criterion (1): C1 re-derived here (frozen construction)
    c2_vals = block_vals("c2", (1, 2, 3))
    c8_m = pooled("c8", sum128, (1, 2, 3))
    if c2_vals is None or c8_m is None:
        return "REFUSED-SAMPLE-COUNT"
    c1_ok = (bar_class(c2_vals) == "FLOOR"
             and abs(c8_m - COMMITTED_C8) <= 0.05 * COMMITTED_C8)

    # the day
    dates = []
    rw = files.get("run-window.txt", None)
    if rw is not None:
        dates = hostdate_re.findall(rw)
    if dates:
        distinct = sorted(set(dates))
        if len(distinct) != 1:
            return "REFUSED-NOT-SINGLE-DAY"
        day = distinct[0]
    else:
        if day_quoted is None or DATE_RE.match(day_quoted) is None:
            return "REFUSED-NO-DAY"
        day = day_quoted

    # the flag join (frozen precedence 1..4)
    if not c1_ok:
        flag = "c1-b"
    elif vmis > 0:
        flag = "verify-mismatch"
    elif pin == "flagged":
        flag = "pin-missing"
    elif go == "flagged":
        flag = "custody-go"
    else:
        flag = "none"

    line = line_shape(day, session, cls, med, mn, flag)
    assert grammar_ok(line), line
    return line


def load_window_dir(dirname):
    """A committed window dir -> the {filename: text} input of derive()."""
    src = os.path.join(GPU, dirname)
    files = {}
    for fn in sorted(os.listdir(src)):
        if runfile_re.match(fn) or fn == "run-window.txt":
            with open(os.path.join(src, fn)) as f:
                files[fn] = f.read()
    return files


# ------------------------------------------------------------------
# --compat: the nine committed ledger lines, re-derived
# ------------------------------------------------------------------
def compat():
    out = []
    P = out.append
    P("JUN-59 session 97 -- ledger-prego --compat (the nine committed")
    P("bar-executing windows; want values PARSED from the committed")
    P("settle-bar-ledger.txt bytes, never transcribed; MOCK bytes appear")
    P("nowhere in this mode).  QUOTED INPUTS (named, not hidden):")
    P("pin=ok go=ok for all nine windows (the custody/build surface is")
    P("the s96 checker's; the committed records attest B1 qualifying and")
    P("the committed lines carry flag=none); day quoted from the")
    P("committed ledger line for s38 s39 (committed no run-window.txt);")
    P("day derived from run-window.txt host-date= fields for the other")
    P("seven.  Everything else is re-derived from committed run-log")
    P("bytes.")
    want_lines = {}
    order = []
    for raw in open(LEDGER):
        line = raw.strip()
        if line.startswith("day="):
            f = dict(t.split("=", 1) for t in line.split())
            want_lines[f["session"]] = line
            order.append(f["session"])
    if order != [w for w, _d in WIN9]:
        print("REFUSED-LEDGER-SHAPE: committed ledger sessions %r != "
              "the frozen nine %r" % (order, [w for w, _d in WIN9]))
        return 2
    mismatched = 0
    quoted_day = 0
    for win, dirname in WIN9:
        files = load_window_dir(dirname)
        day_quoted = None
        if "run-window.txt" not in files or not hostdate_re.findall(
                files.get("run-window.txt", "")):
            day_quoted = dict(t.split("=", 1)
                              for t in want_lines[win].split())["day"]
            quoted_day += 1
            day_src = "quoted(ledger)"
        else:
            day_src = "derived(%d host-date fields, 1 distinct)" % len(
                hostdate_re.findall(files["run-window.txt"]))
        got = derive(files, win, "ok", "ok", day_quoted=day_quoted)
        want = want_lines[win]
        ok = (got == want)
        if not ok:
            mismatched += 1
        P("%s %s day-src=%s" % (win, dirname, day_src))
        P("  want: %s" % want)
        P("  got : %s" % got)
        P("  -> %s" % ("MATCH" if ok else "MISMATCH"))
    P("TOTAL: %d rows, %d mismatched | day-src derived %d quoted %d"
      % (len(WIN9), mismatched, len(WIN9) - quoted_day, quoted_day))
    text = "\n".join(out) + "\n"
    if len(sys.argv) > 2:
        with open(sys.argv[2], "w") as f:
            f.write(text)
    else:
        sys.stdout.write(text)
    return 1 if mismatched else 0


# ------------------------------------------------------------------
# --self-test: MOCK windows (FIXTURES, never measurements)
# ------------------------------------------------------------------
def mock_window(c2_ticks=31, c8_ticks=32915, hi_ticks=None,
                mismatch_at=None, drop_sample=False, drift_cell=False,
                no_sum128=False, dates=("2026-10-30T00:01:02Z",),
                with_run_window=True, extra_runs=()):
    """A synthetic 9-run window (c2/hi/c8 r1-3) as {filename: text}.

    Every number below is a MOCK fixture value and is never a
    measurement.  The cell map follows the committed instrument's shape
    (24 cells: 6 groups x forced 8/16/32/default, forced=8 fail-closed,
    18 pipeline-ok)."""
    def hi_ticks_fn(idx):
        if hi_ticks is not None:
            return hi_ticks(idx)
        return 900 + (idx * 7) % 300
    groups = [("sum", 128), ("max", 128), ("min", 128),
              ("sum", 256), ("max", 256), ("min", 256)]
    cells = []
    idx = 0
    for op, wg in groups:
        for forced in ("8", "16", "32", "default"):
            fail = forced == "8"
            if fail:
                cells.append((idx, op, wg, forced, "FAIL", "1"))
            else:
                cells.append((idx, op, wg, forced, "ok", "0"))
            idx += 1
    if no_sum128:
        cells = [(i, op, wg, fr, ("FAIL" if (op, wg, fr) == ("sum", 128, "16") else pl),
                  ("1" if (op, wg, fr) == ("sum", 128, "16") else vd))
                 for (i, op, wg, fr, pl, vd) in cells]
    ok_cells = [c[0] for c in cells if c[4] == "ok"]

    def ticks_for(tag, idx):
        if tag == "c2":
            return c2_ticks
        if tag == "c8":
            return c8_ticks
        return hi_ticks_fn(idx)

    def log_text(tag, r):
        lines = ["# MOCK fixture run log (FIXTURE, never a measurement)"]
        for (i, op, wg, forced, pl, vd) in cells:
            use_pl, use_vd = pl, vd
            if drift_cell and tag == "hi" and r == 2 and i == 3:
                use_pl, use_vd = "FAIL", "1"
            lines.append("CELL idx=%d spv=mock-%s.emitted.spv op=%s wg=%d forced=%s "
                         "probe_size=%d probe_nsub=%d probe_wg=%d pipeline=%s void=%s "
                         "void_reason=" % (i, op, op, wg, forced, 16, 4, 128, use_pl, use_vd))
            mm = 1 if (mismatch_at is not None
                       and mismatch_at == (tag, r, i)) else 0
            lines.append("VERIFY idx=%d checked=24 mismatch=%d ok=1" % (i, mm))
        rounds = 24 if (drop_sample and tag == "hi" and r == 1) else 25
        for i in ok_cells:
            for rnd in range(rounds):
                lines.append("SAMPLE round=%d idx=%d batch=3 work_mul=1024 ndiv=4033 "
                             "gpu_ticks=%d gpu_ns=1.0 per_dispatch_ns=2.0 host_ns=3"
                             % (rnd, i, ticks_for(tag, i)))
        return "\n".join(lines) + "\n"

    files = {}
    for tag in ("c2", "hi", "c8"):
        for r in (1, 2, 3):
            files["run-%s-r%d.txt" % (tag, r)] = log_text(tag, r)
    for (tag, r) in extra_runs:
        files["run-%s-r%d.txt" % (tag, r)] = log_text(tag, r)
    if with_run_window:
        rw = ["# MOCK fixture run window"]
        for d in dates:
            rw.append("run host-date=%s rc=0" % d)
        files["run-window.txt"] = "\n".join(rw) + "\n"
    return files


def selftest():
    total = 0
    failed = 0
    L = lambda **kw: derive(kw.pop("files"), kw.pop("session", "s99"),
                            kw.pop("pin", "ok"), kw.pop("go", "ok"), **kw)

    def check(what, got, exp):
        nonlocal total, failed
        total += 1
        ok = got == exp
        if not ok:
            failed += 1
        print("check %s: got %r want %r -> %s" % (what, got, exp, "ok" if ok else "FAIL"))

    def mock_line(files, **kw):
        got = L(files=files, **kw)
        assert isinstance(got, str) and not got.startswith("REFUSED"), got
        return got

    clean = mock_window()
    line = mock_line(clean)
    check("clean-window-line", line,
          "day=2026-10-30 session=s99 class=INTERMEDIATE/MIXED median=907 "
          "min=907 flag=none")
    check("clean-window-grammar", grammar_ok(line), True)
    check("clean-window-determinism", mock_line(clean), line)
    check("grammar-rejects-bad-shape", grammar_ok("day=2026-10-30 session=s99"), False)
    check("grammar-rejects-unknown-flag",
          grammar_ok("day=2026-10-30 session=s99 class=FLOOR median=1 min=1 flag=nope"),
          False)

    check("c2-not-floor-c1-b", mock_line(mock_window(c2_ticks=300)).split()[-1],
          "flag=c1-b")
    check("c8-out-of-band-c1-b", mock_line(mock_window(c8_ticks=20000)).split()[-1],
          "flag=c1-b")
    check("precedence-c1-over-verify",
          mock_line(mock_window(c2_ticks=300,
                                mismatch_at=("hi", 3, 5))).split()[-1], "flag=c1-b")
    check("verify-only",
          mock_line(mock_window(mismatch_at=("c2", 1, 0))).split()[-1],
          "flag=verify-mismatch")
    check("precedence-verify-over-pin",
          mock_line(mock_window(mismatch_at=("c8", 2, 7)), pin="flagged").split()[-1],
          "flag=verify-mismatch")
    check("pin-only", mock_line(mock_window(), pin="flagged").split()[-1],
          "flag=pin-missing")
    check("precedence-pin-over-go",
          mock_line(mock_window(), pin="flagged", go="flagged").split()[-1],
          "flag=pin-missing")
    check("go-only", mock_line(mock_window(), go="flagged").split()[-1],
          "flag=custody-go")
    check("all-four-fired", mock_line(mock_window(c2_ticks=300,
                                                  mismatch_at=("hi", 1, 2)),
                                      pin="flagged", go="flagged").split()[-1],
          "flag=c1-b")

    check("pin-undecided-refuses", L(files=mock_window(), pin=None),
          "REFUSED-INPUT-UNDECIDED")
    check("go-undecided-refuses", L(files=mock_window(), go="maybe"),
          "REFUSED-INPUT-UNDECIDED")
    no_hi2 = mock_window()
    del no_hi2["run-hi-r2.txt"]
    check("missing-anchor-run-refuses", L(files=no_hi2), "REFUSED-NO-READING")
    no_c83 = mock_window()
    del no_c83["run-c8-r3.txt"]
    check("missing-c8-run-refuses", L(files=no_c83), "REFUSED-NO-READING")
    check("two-day-window-refuses",
          L(files=mock_window(dates=("2026-10-30T00:01:02Z",
                                     "2026-10-31T00:01:02Z"))),
          "REFUSED-NOT-SINGLE-DAY")
    no_rw = mock_window(with_run_window=False)
    check("no-run-window-no-day-refuses", L(files=no_rw), "REFUSED-NO-DAY")
    check("no-run-window-quoted-day",
          mock_line(no_rw, day_quoted="2026-10-28").split()[0], "day=2026-10-28")
    check("bad-quoted-day-refuses", L(files=no_rw, day_quoted="2026-10-30T00:00:00Z"),
          "REFUSED-NO-DAY")
    check("cell-map-drift-refuses", L(files=mock_window(drift_cell=True)),
          "REFUSED-CELL-MAP")
    check("short-sample-census-refuses", L(files=mock_window(drop_sample=True)),
          "REFUSED-SAMPLE-COUNT")
    check("no-ok-sum128-refuses", L(files=mock_window(no_sum128=True)),
          "REFUSED-NO-SUM128")

    extra = mock_window(extra_runs=[("tw", r) for r in (1, 2, 3)])
    line_extra = mock_line(extra)
    check("extra-arm-shape-still-derives", line_extra.split()[2:8],
          ["class=INTERMEDIATE/MIXED", "median=907", "min=907", "flag=none"])
    check("extra-arm-determinism", mock_line(extra), line_extra)

    print("TOTAL: %d assertions passed, %d failed" % (total, failed))
    return 1 if failed else 0


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "--self-test":
        sys.exit(selftest())
    if MODE == "w6":
        # the W6 session's emit path: adopted as ledger-s<NN>.py
        if len(sys.argv) < 5:
            print("usage: ledger-s<NN>.py --emit <window-dir> <pin> <go> "
                  "[day-quoted] -- emits the one ledger line, never appends")
            sys.exit(2)
        if sys.argv[1] != "--emit":
            print("REFUSED-UNKNOWN-MODE")
            sys.exit(2)
        assert _m is not None
        session = "s%d" % int(_m.group(1))
        files = load_window_dir(sys.argv[2])
        pin, go = sys.argv[3], sys.argv[4]
        day_quoted = sys.argv[5] if len(sys.argv) > 5 else None
        got = derive(files, session, pin, go, day_quoted=day_quoted)
        print(got)
        sys.exit(0 if not got.startswith("REFUSED") else 3)
    sys.exit(compat())


if __name__ == "__main__":
    main()
