#!/usr/bin/env python3
"""run-window-prego.py -- JUN-59 session 95: the W6 RUN-WINDOW DRIVER PRE-BUILD.

The s80 protocol section-2 RUN path machinery preparation half (the
s69/s90 pre-build precedent applied to the route half of the W6
measurement row that no pre-build covers yet: the s90 pre-build built
the section-6 READING path; this builds the section-2 RUN-WINDOW
path).  NO hardware runs, NO builds, NO compiles, NO GO stamp, NO
host writes, NO day-slot consumption, NO ledger line.  This program
submits NOTHING to any GPU and opens NO network connection: it reads
committed-or-fresh run logs and emits text.

WHAT IT IS (frozen-route machinery, deterministic, pure stdlib, NO
RNG, no clock):

  --plan            emit the frozen 78-run order of the s57 route
                    (s80 section 2, UNCHANGED): c2 r1-3, then for
                    k = 1..12 hi block k (runs 3k-2..3k) immediately
                    followed by tw block k, then c8 r1-3 -- with the
                    per-run artifact names (run-<tag>.txt /
                    run-<tag>.stderr.txt) and the invocation
                    (./anv-bb-<arm> <manifest>; the instrument's
                    main takes exactly one argument -- the manifest
                    -- per gpu-subgroup-reduce-anv-ndiv.c).

  --rebuild         given a window directory of run logs and the
                    LIVE-FIELDS capture (per-run rc + host-date, the
                    two fields the driver captures live on the host
                    and that NO run log contains), deterministically
                    construct run-window.txt's per-run table (78
                    lines) and its three trailer lines in the frozen
                    committed transcript format.

  --self-test       fixture suite (MOCK window data are FIXTURES,
                    never measurements).
  --compat          validation over the THREE committed 78-run
                    run-window transcripts (s36/s51/W5 -- the two
                    other fixed windows s38/s39 committed no
                    run-window.txt): frozen plan order == committed
                    per-run order 78/78 per window, and rebuilt
                    table+trailer bytes == committed bytes, where
                    stderr_bytes is RE-DERIVED from the committed
                    .stderr.txt byte counts and
                    samples/verifies/cells/tail are RE-DERIVED from
                    the committed run logs, while rc and host-date
                    are QUOTED from the committed transcript as
                    INPUT (they are live-only fields -- named, not
                    hidden).  NAMED, NOT HIDDEN: s36's transcript
                    PREDATES the s57 route freeze -- its per-run
                    table is the same frozen byte format but its
                    trailer is session prose (inline-count
                    attestation + a host-file-mtime cross-check
                    block), so the frozen 3-line trailer comparison
                    covers the s57-route windows s51/W5 only.

ADOPTION CONTRACT (named): the frozen route names no driver script
filename (every prior window's driver was improvised live); the W6
session adopts this file as its run-window driver under whatever name
it records (the s90 precedent: adoption as run-window-s<NN>.py), and
re-verifies this file's --compat in its own record.  The execution
path (ssh, the live rc/host-date capture, the staging and GO) stays
session-owned exactly as at s51/s73; this pre-build covers the two
mechanical surfaces the frozen route specifies byte-precisely -- the
run ORDER and the TRANSCRIPT construction.

FAIL-CLOSED (named): a tail containing a single quote, a non-uniform
trailer window (rc/stderr_bytes/samples/verifies/cells not identical
across the 78 runs), missing/extra runs in the live fields, or a
missing run log are hard errors -- the committed transcript format
only attests uniform 78-run windows and this pre-build refuses to
invent bytes for any other shape.

LIVE-ONLY FIELDS (named, not hidden): rc (process exit status) and
host-date (the host `date -u` taken immediately BEFORE the run
invocation) exist nowhere in the run logs; at a live session the
driver captures them at run time; at --compat time they are parsed
from the committed run-window.txt and quoted as input.  Every other
transcript field is re-derived from committed bytes.
"""

import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# The frozen run order (s57 route section 6 / s80 section 2, UNCHANGED).
# ---------------------------------------------------------------------------

def frozen_order():
    """78 steps: (tag, arm, block, r).  block is 1..12 for hi/tw, None
    for the c2/c8 controls.  c2 r1-3, then for k=1..12 hi block k
    (runs 3k-2..3k) immediately followed by tw block k, then c8 r1-3."""
    steps = []
    for r in (1, 2, 3):
        steps.append(("c2-r%d" % r, "c2", None, r))
    for k in range(1, 13):
        for arm in ("hi", "tw"):
            for r in (3 * k - 2, 3 * k - 1, 3 * k):
                steps.append(("%s-r%d" % (arm, r), arm, k, r))
    for r in (1, 2, 3):
        steps.append(("c8-r%d" % r, "c8", None, r))
    return steps


ORDER = frozen_order()
TAGS = [s[0] for s in ORDER]

# The committed per-run transcript line format (stable across s36/s51/W5;
# proven against 234 committed lines by --compat, never assumed silently).
LINE_RE = re.compile(
    r"^  (\S+) rc=(\d+) host-date=(\S+) stderr_bytes=(\d+) "
    r"samples=(\d+) verifies=(\d+) cells=(\d+) tail='([^']*)'$")


def fmt_line(tag, rc, hd, sb, samples, verifies, cells, tail):
    return ("  %s rc=%d host-date=%s stderr_bytes=%d samples=%d "
            "verifies=%d cells=%d tail='%s'"
            % (tag, rc, hd, sb, samples, verifies, cells, tail))


def fmt_trailer(first_hd, last_hd, rc, sb, samples, verifies, cells):
    return [
        "window span (host-date, first..last): %s .. %s" % (first_hd, last_hd),
        "78/78 runs rc=%d, stderr_bytes=%d, samples=%d, verifies=%d, cells=%d."
        % (rc, sb, samples, verifies, cells),
        "the run order table above is the frozen section-6 order verbatim.",
    ]


def derive_run_fields(window_dir, tag):
    """Re-derive the four log-census fields and the stderr byte count
    from a run's committed/fresh artifacts.  Nothing here is quoted."""
    out = Path(window_dir) / ("run-%s.txt" % tag)
    err = Path(window_dir) / ("run-%s.stderr.txt" % tag)
    if not out.is_file():
        raise SystemExit("run-window-prego: missing run log: %s" % out)
    if not err.is_file():
        raise SystemExit("run-window-prego: missing stderr log: %s" % err)
    lines = out.read_text().splitlines()
    if not lines:
        raise SystemExit("run-window-prego: empty run log: %s" % out)
    samples = sum(1 for ln in lines if ln.split(" ", 1)[0] == "SAMPLE")
    verifies = sum(1 for ln in lines if ln.split(" ", 1)[0] == "VERIFY")
    cells = sum(1 for ln in lines if ln.split(" ", 1)[0] == "CELL")
    tail = lines[-1]
    if "'" in tail:
        raise SystemExit(
            "run-window-prego: tail contains a single quote (fail-closed): %r"
            % tail)
    sb = err.stat().st_size
    return sb, samples, verifies, cells, tail


def rebuild_table(window_dir, live):
    """live: tag -> (rc, host-date).  Returns the 78 table lines + 3
    trailer lines, built strictly in the frozen order."""
    missing = [t for t in TAGS if t not in live]
    extra = [t for t in sorted(live) if t not in TAGS]
    if missing or extra:
        raise SystemExit(
            "run-window-prego: live-fields tag set != frozen order "
            "(missing=%s extra=%s)" % (missing, extra))
    rows = []
    for tag in TAGS:
        rc, hd = live[tag]
        sb, samples, verifies, cells, tail = derive_run_fields(window_dir, tag)
        rows.append((tag, rc, hd, sb, samples, verifies, cells, tail))
    for idx, name in ((1, "rc"), (3, "stderr_bytes"), (4, "samples"),
                      (5, "verifies"), (6, "cells")):
        vals = set(row[idx] for row in rows)
        if len(vals) != 1:
            raise SystemExit(
                "run-window-prego: non-uniform %s across the 78 runs %s "
                "(fail-closed: the committed trailer format only attests "
                "uniform windows)" % (name, sorted(vals)))
    table = [fmt_line(*row) for row in rows]
    trailer = fmt_trailer(rows[0][2], rows[-1][2], rows[0][1], rows[0][3],
                          rows[0][4], rows[0][5], rows[0][6])
    return table + trailer


def parse_committed_run_window(path):
    """Parse a committed run-window.txt: the 78 per-run rows (tag, rc,
    host-date + the quoted fields for reporting) and the table+trailer
    region as committed bytes.  rc and host-date come back as the
    LIVE-FIELDS input for rebuild_table."""
    text = Path(path).read_text()
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    idxs = [i for i, ln in enumerate(lines) if LINE_RE.match(ln)]
    if len(idxs) != 78:
        raise SystemExit(
            "run-window-prego: %s: expected 78 per-run lines, found %d"
            % (path, len(idxs)))
    if idxs != list(range(idxs[0], idxs[0] + 78)):
        raise SystemExit("run-window-prego: %s: per-run lines not contiguous"
                         % path)
    rows = []
    for i in idxs:
        m = LINE_RE.match(lines[i])
        assert m is not None  # idxs was filtered by the same regex
        rows.append((m.group(1), int(m.group(2)), m.group(3),
                     int(m.group(4)), int(m.group(5)), int(m.group(6)),
                     int(m.group(7)), m.group(8)))
    region = lines[idxs[0]:]
    return rows, region


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------

def mode_plan():
    print("JUN-59 W6 run-window plan (frozen s57 route / s80 section 2 "
          "order, UNCHANGED -- 78 steps).")
    print("Invocation per step: ./anv-bb-<arm> <manifest> "
          "(<manifest> = the session's fresh cases-s<NN>-a.txt; the "
          "instrument's main takes exactly one argument).")
    print("Per-run capture (the driver's live step): host `date -u` "
          "immediately BEFORE the invocation; stdout -> run-<tag>.txt; "
          "stderr -> run-<tag>.stderr.txt; rc + host-date -> the "
          "live-fields file consumed by --rebuild.")
    print("step tag arm block run bin stdout stderr")
    for i, (tag, arm, block, r) in enumerate(ORDER, 1):
        print("%d %s %s %s %d ./anv-bb-%s run-%s.txt run-%s.stderr.txt"
              % (i, tag, arm, block if block is not None else "CTRL", r,
                 arm, tag, tag))
    print("END 78 steps (c2 r1-3, k=1..12 hi block k then tw block k, "
          "c8 r1-3).")


def mode_rebuild(window_dir, live_path, out_path):
    live = {}
    for ln in Path(live_path).read_text().splitlines():
        if not ln.strip():
            continue
        m = re.match(r"^(\S+) rc=(\d+) host-date=(\S+)$", ln)
        if not m:
            raise SystemExit("run-window-prego: bad live-fields line: %r" % ln)
        if m.group(1) in live:
            raise SystemExit(
                "run-window-prego: duplicate live-fields tag: %s" % m.group(1))
        live[m.group(1)] = (int(m.group(2)), m.group(3))
    lines = rebuild_table(window_dir, live)
    text = "\n".join(lines) + "\n"
    if out_path:
        Path(out_path).write_text(text)
        print("run-window-prego: wrote %d lines -> %s" % (len(lines), out_path))
    else:
        sys.stdout.write(text)


def mode_self_test():
    import shutil
    import tempfile

    checks = [0]

    def check(cond, name):
        checks[0] += 1
        if not cond:
            raise SystemExit("self-test FAIL: %s" % name)

    # -- plan properties (frozen order, asserted from the prose spec).
    check(len(ORDER) == 78, "plan has 78 steps")
    check(TAGS[0] == "c2-r1" and TAGS[1] == "c2-r2" and TAGS[2] == "c2-r3",
          "plan starts with c2 r1-3")
    check(TAGS[-3] == "c8-r1" and TAGS[-2] == "c8-r2" and TAGS[-1] == "c8-r3",
          "plan ends with c8 r1-3")
    ok = True
    for k in range(1, 13):
        base = 3 + (k - 1) * 6
        want_hi = ["hi-r%d" % (3 * k - 2 + j) for j in range(3)]
        want_tw = ["tw-r%d" % (3 * k - 2 + j) for j in range(3)]
        if TAGS[base:base + 3] != want_hi or TAGS[base + 3:base + 6] != want_tw:
            ok = False
    check(ok, "plan interleaves hi block k then tw block k for k=1..12")
    ok = all(ORDER[3 + (k - 1) * 6 + j][2] == k for k in range(1, 13)
             for j in range(6))
    check(ok, "plan block labels 1..12 on the hi/tw steps")
    check(all(ORDER[3 + (k - 1) * 6 + j][3] == 3 * k - 2 + (j % 3)
              for k in range(1, 13) for j in range(6)),
          "plan run numbers 3k-2..3k per block")
    check(ORDER[3][1] == "hi" and ORDER[6][1] == "tw" and ORDER[-4][1] == "tw",
          "plan arms at sentinel steps")

    # -- rebuild on a MOCK 78-run window (FIXTURES, never measurements).
    tmp = Path(tempfile.mkdtemp(prefix="runwindow-prego-selftest-"))
    try:
        live = {}
        for i, (tag, arm, block, r) in enumerate(ORDER):
            (tmp / ("run-%s.txt" % tag)).write_text(
                "# hdr\n"
                "CELL idx=0 a\nCELL idx=1 b\n"
                "SAMPLE x\nSAMPLE y\n"
                "VERIFY idx=0 ok\n"
                "# done cells=2\n")
            (tmp / ("run-%s.stderr.txt" % tag)).write_bytes(b"xyz")
            live[tag] = (0, "2026-01-0%dT0%d:00:00Z" % (1 + i % 7, i % 10))
        lines = rebuild_table(tmp, live)
        check(len(lines) == 81, "mock rebuild emits 78 table + 3 trailer lines")
        want0 = fmt_line("c2-r1", 0, live["c2-r1"][1], 3, 2, 1, 2,
                         "# done cells=2")
        check(lines[0] == want0, "mock table line 1 format")
        check(lines[77].startswith("  c8-r3 rc=0 host-date="),
              "mock table line 78 is c8-r3")
        check(lines[78] == "window span (host-date, first..last): %s .. %s"
              % (live["c2-r1"][1], live["c8-r3"][1]),
              "mock trailer span line")
        check(lines[79] == "78/78 runs rc=0, stderr_bytes=3, samples=2, "
              "verifies=1, cells=2.", "mock trailer counts line")
        check(lines[80] == "the run order table above is the frozen "
              "section-6 order verbatim.", "mock trailer attestation line")

        # -- fail-closed cases (each must raise SystemExit).
        def fails(fn, name):
            try:
                fn()
            except SystemExit:
                check(True, name)
                return
            check(False, name)

        def drop_one():
            bad = dict(live)
            del bad["tw-r36"]
            rebuild_table(tmp, bad)

        fails(drop_one, "missing live-fields tag is a hard error")

        def extra_one():
            bad = dict(live)
            bad["tw-r37"] = (0, "2026-01-01T00:00:00Z")
            rebuild_table(tmp, bad)

        fails(extra_one, "extra live-fields tag is a hard error")

        (tmp / "run-c2-r1.txt").write_text(
            "# hdr\nCELL idx=0 a\nSAMPLE x\nVERIFY idx=0 ok\n"
            "# done it's broken\n")
        fails(lambda: rebuild_table(tmp, live),
              "tail with a single quote is a hard error")
        (tmp / "run-c2-r1.txt").write_text(
            "# hdr\nCELL idx=0 a\nCELL idx=1 b\nSAMPLE x\nSAMPLE y\n"
            "VERIFY idx=0 ok\n# done cells=2\n")

        (tmp / "run-c2-r1.txt").write_text(
            "# hdr\nCELL idx=0 a\nCELL idx=1 b\nSAMPLE x\n"
            "VERIFY idx=0 ok\n# done cells=2\n")
        fails(lambda: rebuild_table(tmp, live),
              "non-uniform samples is a hard error")
        (tmp / "run-c2-r1.txt").write_text(
            "# hdr\nCELL idx=0 a\nCELL idx=1 b\nSAMPLE x\nSAMPLE y\n"
            "VERIFY idx=0 ok\n# done cells=2\n")

        (tmp / "run-hi-r5.txt").unlink()
        fails(lambda: rebuild_table(tmp, live), "missing run log is a hard error")
    finally:
        shutil.rmtree(tmp)
    print("--self-test TOTAL %d assertions passed 0 failed" % checks[0])


def mode_compat():
    gpu_evidence = Path(__file__).resolve().parent.parent
    # s51 is the s57-route prototype and W5 is the s57-route window: their
    # transcripts carry the frozen 3-line trailer this pre-build constructs.
    # s36 PREDATES the s57 route freeze: its per-run table is the same frozen
    # byte format, but its trailer is session prose (inline-count attestation
    # + a host-file-mtime cross-check block) -- named, not hidden; the
    # trailer comparison covers the s57-route windows only.
    windows = [
        ("s36", gpu_evidence / "anv-b3commonmode-20261028", False),
        ("s51", gpu_evidence / "anv-b3levelrep-20261028", True),
        ("W5", gpu_evidence / "anv-b3w5xdayrep-20261029", True),
    ]
    total = 0
    mismatched = 0
    for tag, wdir, route_window in windows:
        rows, region = parse_committed_run_window(wdir / "run-window.txt")
        live = {r[0]: (r[1], r[2]) for r in rows}
        order_ok = [r[0] for r in rows] == TAGS
        total += 1
        if not order_ok:
            mismatched += 1
        print("window %s (%s): frozen plan order vs committed per-run "
              "order 78/78 %s"
              % (tag, wdir.name, "MATCH" if order_ok else "MISMATCH"))
        rebuilt = rebuild_table(wdir, live)
        n_cmp = 81 if route_window else 78
        if route_window and len(region) != 81:
            mismatched += 1
            total += 1
            print("  MISMATCH: s57-route transcript region is %d lines, "
                  "expected 81 (78 table + 3 trailer)" % len(region))
        row_bad = 0
        for i in range(n_cmp):
            total += 1
            if rebuilt[i] != region[i]:
                mismatched += 1
                row_bad += 1
                print("  MISMATCH line %d:\n    rebuilt  %r\n    commit   %r"
                      % (i + 1, rebuilt[i], region[i]))
        if route_window:
            print("window %s: table+trailer rebuilt bytes vs committed bytes "
                  "81/81 %s (%s rows, %d mismatched)"
                  % (tag, "BYTE-EQUAL" if row_bad == 0 else "MISMATCH",
                     wdir.name, row_bad))
        else:
            print("window %s: per-run TABLE rebuilt bytes vs committed bytes "
                  "78/78 %s (%s rows, %d mismatched); NAMED NOT HIDDEN: this "
                  "transcript PREDATES the s57 route freeze and its trailer "
                  "is session prose (inline-count attestation + host-file-"
                  "mtime cross-check), NOT the frozen 3-line trailer -- the "
                  "trailer comparison covers the s57-route windows s51/W5 "
                  "only, and this pre-build constructs the frozen trailer"
                  % (tag, "BYTE-EQUAL" if row_bad == 0 else "MISMATCH",
                     wdir.name, row_bad))
    print("live-only fields (rc, host-date) quoted from the committed "
          "transcripts as INPUT (named, not hidden); stderr_bytes "
          "re-derived from committed .stderr.txt byte counts; "
          "samples/verifies/cells/tail re-derived from the committed "
          "run logs.")
    print("--compat TOTAL %d rows %d mismatched" % (total, mismatched))
    if mismatched:
        raise SystemExit(1)


def main(argv):
    if argv == ["--self-test"]:
        mode_self_test()
    elif argv == ["--compat"]:
        mode_compat()
    elif argv == ["--plan"]:
        mode_plan()
    elif len(argv) >= 3 and argv[0] == "--rebuild":
        window_dir = None
        live_path = None
        out_path = None
        i = 1
        while i < len(argv):
            if argv[i] == "--window-dir" and i + 1 < len(argv):
                window_dir = argv[i + 1]
                i += 2
            elif argv[i] == "--live" and i + 1 < len(argv):
                live_path = argv[i + 1]
                i += 2
            elif argv[i] == "--out" and i + 1 < len(argv):
                out_path = argv[i + 1]
                i += 2
            else:
                raise SystemExit("run-window-prego: bad argument: %r" % argv[i])
        if not window_dir or not live_path:
            raise SystemExit("run-window-prego: --rebuild needs --window-dir "
                             "and --live")
        mode_rebuild(window_dir, live_path, out_path)
    else:
        raise SystemExit("usage: run-window-prego.py --plan | --rebuild "
                         "--window-dir DIR --live FILE [--out FILE] | "
                         "--self-test | --compat")


if __name__ == "__main__":
    main(sys.argv[1:])
