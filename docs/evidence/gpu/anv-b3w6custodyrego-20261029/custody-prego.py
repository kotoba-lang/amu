#!/usr/bin/env python3
"""custody-prego.py -- JUN-59 session 96: the W6 PRE-GO CUSTODY CHECKER
PRE-BUILD.

The s80 protocol section-2 CUSTODY path machinery preparation half (the
s69/s90/s95 pre-build precedent applied to the last un-machinery'd
surface of the W6/W7 measurement rows: the host-verify + build-census
records and the frozen FLAGGED criteria's custody/build half).  NO
hardware runs, NO builds, NO compiles, NO GO stamp, NO host writes, NO
network connections, NO day-slot consumption, NO ledger line.  This
program reads committed-or-fresh record TEXT and emits text; it submits
NOTHING to any GPU.

WHAT IT IS (record-checking machinery, deterministic, pure stdlib, NO
RNG, no clock):

  --compat          run the custody check over the THREE committed
                    78-run run-window windows (s36 anv-b3commonmode-
                    20261028 / s51 anv-b3levelrep-20261028 / W5
                    anv-b3w5xdayrep-20261029 -- the same three
                    transcripts run-window-prego.py validates against;
                    s38/s39 committed no run-window.txt).  Every
                    custody fact the frozen route names is re-derived
                    from committed bytes and printed as one
                    want/got/verdict row per check per window, plus the
                    derived FLAG decision per window.

  --self-test       fixture suite (MOCK window records are FIXTURES,
                    never measurements; --self-test reads NO committed
                    window).

THE CHECKED SURFACE (the s80/s85 section-2 route + the settle-bar.txt
section-2 FLAGGED criteria's custody/build half):

  (i)   custody inputs (host-verify-s<NN>.txt): the local-vs-host
        sha256 MATCH lines for the instrument source, the manifest and
        the expected-corpus census -- 3/3 present, local == host on
        every line, local re-derived from the committed artifact bytes,
        and the instrument/expected-corpus digests on the frozen chain
        values (a5e539f0... / eefba52e...);
  (ii)  the manifest cell-line chain: 24 non-comment cell lines and
        their digest == 873025d650afae23... (sha256 over the cell lines
        as they appear, byte-for-byte);
  (iii) the corpus census: 16/16 OK (both committed shapes parsed --
        s36's per-file ': OK' lines and the s51/W5 '16/16 OK' summary)
        and corpus_rc=0, and the custody summary line;
  (iv)  GO stamp present; NOT after the builds (the frozen FLAGGED
        criterion "the custody GO is missing/after the builds");
        before all runs; builds before the first run (the build
        window's own committed attestation);
  (v)   the four pinned compiles: 4 build lines at the frozen knob
        sets (c2 2/1/1, hi 3/1024/4033, tw 3/2048/8066, c8 8/1/1),
        all rc=0, build stderr byte counts total 0;
  (vi)  the build pins: the four binary digests == the four s51-frozen
        build pins (BYTE-IDENTICAL required -- the frozen FLAGGED
        criterion "the build pin is not byte-identical") and the
        committed census's own 4/4 verdict line;
  (vii) the run window: 78 per-run transcript lines;
  (viii) VERIFY: 24 VERIFY lines per run (1872 over the window) and
        the VERIFY mismatch total (the frozen FLAGGED criterion
        "VERIFY mismatch > 0").

THE FLAG DECISION (named, partial by construction): the settle-bar.txt
section-2 FLAGGED criteria are EXACTLY four -- (1) C1 fired (b), (2)
VERIFY mismatch > 0, (3) the build pin is not byte-identical, (4) the
custody GO is missing/after the builds.  This checker derives (2), (3)
and (4) fail-closed; (1) C1 is the s90 reading pair's surface and is
NOT computed here (named scope cut).  Flag tokens are the criteria's
own names: verify-mismatch / build-pin-not-byte-identical /
custody-go-missing / custody-go-after-builds.  Any OTHER failing
custody row (corpus, chain digests, build window shape) refuses to
bless the record with the checker-level token
REFUSED-RECORD-INCONSISTENT -- a conservative token that can only lead
to a FLAGGED ledger line, never a qualifying one; the checker never
invents a ledger flag for criteria outside the frozen four.

LIVE-ONLY FIELDS (named, not hidden): the host= half of every MATCH
line, the GO stamp, the build timestamps and the per-run host dates are
captured live on the host and exist in no run log; at --compat time
they are QUOTED from the committed records as INPUT; every other value
is re-derived from committed bytes.

ADOPTION CONTRACT (named): the frozen route names no checker filename;
the W6 session adopts this file as its custody checker under whatever
name it records (the s90/s95 precedent: adoption as custody-s<NN>.py),
re-runs --compat in its own record, and runs the checker over its own
fresh host-verify/build-census/run-window records BEFORE the ledger
line; the W7 session does the same (this surface is window-generic --
the frozen pins, knob sets, chain digests and 78-run shape are the
s57 route's, UNCHANGED at W6/W7 per s80/s85 section 2).  The
execution path (ssh, staging, GO, the record prose) stays session-owned
exactly as at s51/s73.

FAIL-CLOSED (named): a missing file, an unparseable required line, a
missing run log or a run-window row count != 78 are hard errors in the
row stream (verdict=MISMATCH, exit 1) -- this checker refuses to
invent bytes for any shape it cannot derive.
"""

import hashlib
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Frozen constants (the s57 route / s51-frozen pins / the chain digests).
# ---------------------------------------------------------------------------

FROZEN_PINS = {
    "c2": "e5ed903e5b9dfd64168e2d8ddea9d8efb573273e7594afcaca71f3f70bb9c489",
    "hi": "a6c31b6c5c5663084fa4193f0d5c0098f65882b814a92fa9e85cef940cf63b9c",
    "tw": "bb901eb5b1e98940c53b3ecaeccad2b8d410967952659f9902668de32c4524b0",
    "c8": "480925e58d28e7d318456703c6959548e9b9c33e375c3e0fefe688e844d37807",
}
FROZEN_KNOBS = {
    "c2": "-DBATCH=2 -DWORK_MUL=1 -DNDIV=1",
    "hi": "-DBATCH=3 -DWORK_MUL=1024 -DNDIV=4033",
    "tw": "-DBATCH=3 -DWORK_MUL=2048 -DNDIV=8066",
    "c8": "-DBATCH=8 -DWORK_MUL=1 -DNDIV=1",
}
INSTRUMENT_DIGEST = "a5e539f0ad1c5d732cda1eaa1cd2abb1aa4d1a66795c09c4ecb35ed2c3520556"
CORPUS_CENSUS_DIGEST = "eefba52e7be052d66eb7baae700b3f7583db7306f1a7d6b5a2201b862ac595a4"
CELLS_DIGEST = "873025d650afae2329ab2c05c2048931a5263976b9bfb585d3665b7018c32200"
CELL_LINE_COUNT = 24
CORPUS_FILE_COUNT = 16
RUN_COUNT = 78
VERIFY_PER_RUN = 24
VERIFY_TOTAL = RUN_COUNT * VERIFY_PER_RUN  # 1872

MATCH_NAMES = ("gpu-subgroup-reduce-anv-ndiv.c", "expected-corpus.sha256")

# The three committed 78-run windows (tag, evidence dir, manifest name).
WINDOWS = (
    ("s36", "anv-b3commonmode-20261028", "cases-s36-a.txt"),
    ("s51", "anv-b3levelrep-20261028", "cases-s51-a.txt"),
    ("s73", "anv-b3w5xdayrep-20261029", "cases-s73-a.txt"),
)

# Named artifact provenance (named, not hidden): the two chain-invariant
# artifacts (instrument source, expected-corpus census) are byte-copy
# identical across windows by the frozen chain digests; the W5 window dir
# committed NO copy of either (its host-verify record attests byte-copy
# == s36's / s51's).  When a window dir lacks one, the checker re-derives
# the local= digest from the NAMED canonical committed copy (the s51 dir)
# and prints an artifact-provenance line per fallback in --compat output.
# The manifest is window-specific (fresh header per window) and is NEVER
# resolved from a fallback -- its absence is a hard error.
CHAIN_ARTIFACT_FILES = {
    "gpu-subgroup-reduce-anv-ndiv.c": "gpu-subgroup-reduce-anv-ndiv.c.txt",
    "expected-corpus.sha256": "expected-corpus.sha256",
}
ARTIFACT_CANON_DIR = "anv-b3levelrep-20261028"

EVIDENCE_ROOT = Path(__file__).resolve().parent.parent

RE_MATCH = re.compile(r"^MATCH  (\S+): local=([0-9a-f]{64}) host=([0-9a-f]{64})\s*$")
RE_GO = re.compile(r"^GO stamp: (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\s*$")
RE_BUILD = re.compile(
    r"^build (\S+) \(([^)]*)\) rc=(-?\d+) @(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\s*$"
)
RE_DIGEST = re.compile(r"^([0-9a-f]{64})  (anv-bb-(\S+))\s*$")
RE_PINS = re.compile(r"^pins: (\d+)/(\d+) BYTE-IDENTICAL")
RE_CORPUS_RC = re.compile(r"^corpus_rc=(-?\d+)\s*$")
RE_CORPUS_SUM = re.compile(r"^(\d+)/(\d+) OK")
RE_STDERR_COUNT = re.compile(r"^(\d+) build-(\S+)\.err\s*$")
RE_STDERR_TOTAL = re.compile(r"^(\d+) total\s*$")
RE_RUN = re.compile(
    r"^\s+(\S+) rc=(-?\d+) host-date=(\S+) stderr_bytes=\d+ samples=\d+"
    r" verifies=\d+ cells=\d+ tail='"
)
RE_VERIFY = re.compile(r"^VERIFY .*mismatch=(\d+)")


# ---------------------------------------------------------------------------
# Parsers (text -> facts).  Every parser is total over its input: absent
# facts come back as None/empty and surface as row mismatches downstream.
# ---------------------------------------------------------------------------

def parse_host_verify(text):
    matches = []
    corpus_ok_files = 0
    corpus_ok_of16 = None
    corpus_rc = None
    summary = False
    go = None
    for line in text.splitlines():
        m = RE_MATCH.match(line)
        if m:
            matches.append((m.group(1), m.group(2), m.group(3)))
            continue
        m = RE_GO.match(line)
        if m:
            go = m.group(1)
            continue
        if line.rstrip().endswith(": OK"):
            corpus_ok_files += 1
            continue
        m = RE_CORPUS_SUM.match(line)
        if m:
            corpus_ok_of16 = int(m.group(1))
            continue
        m = RE_CORPUS_RC.match(line)
        if m:
            corpus_rc = int(m.group(1))
            continue
        if line.strip() == "== local-vs-host 3/3 MATCH; corpus 16/16 ==":
            summary = True
    corpus_ok = corpus_ok_files if corpus_ok_files else corpus_ok_of16
    return {
        "matches": matches,
        "corpus_ok": corpus_ok,
        "corpus_rc": corpus_rc,
        "summary": summary,
        "go": go,
    }


def parse_build_census(text):
    builds = []
    digests = {}
    pins = None
    stderr_total = None
    in_stderr_block = False
    for line in text.splitlines():
        m = RE_BUILD.match(line)
        if m:
            builds.append((m.group(1), m.group(2), int(m.group(3)), m.group(4)))
            continue
        m = RE_DIGEST.match(line)
        if m:
            digests[m.group(3)] = m.group(1)
            continue
        m = RE_PINS.match(line)
        if m:
            pins = "%s/%s" % (m.group(1), m.group(2))
            continue
        if line.strip() == "build stderr byte counts (host build-<tag>.err):":
            in_stderr_block = True
            continue
        if in_stderr_block:
            m = RE_STDERR_TOTAL.match(line)
            if m:
                stderr_total = int(m.group(1))
                in_stderr_block = False
                continue
            if not RE_STDERR_COUNT.match(line):
                in_stderr_block = False
    return {"builds": builds, "digests": digests, "pins": pins,
            "stderr_total": stderr_total}


def parse_run_window(text):
    runs = []
    for line in text.splitlines():
        m = RE_RUN.match(line)
        if m:
            runs.append((m.group(1), int(m.group(2)), m.group(3)))
    return {"runs": runs}


def cell_lines(manifest_bytes):
    """The 24 non-comment cell lines, byte-for-byte as they appear."""
    kept = []
    for line in manifest_bytes.splitlines(keepends=True):
        if line.startswith(b"#"):
            continue
        if not line.strip():
            continue
        kept.append(line)
    return kept


def sha(data):
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# The check itself.
# ---------------------------------------------------------------------------

def check_window(hv_text, bc_text, rw_text, artifacts, verify_lines,
                 verify_mismatch, chain=None):
    """One window's custody rows + its derived FLAG decision.

    artifacts: MATCH-name -> local artifact bytes (the committed files at
    --compat time; the fresh staged files at a live session).
    verify_lines / verify_mismatch: the window's aggregate VERIFY census
    (count of VERIFY lines across the 78 run logs; sum of their
    mismatch= fields).
    chain: the declared chain constants -- instrument / corpus_census /
    cells digests.  DEFAULTS ARE THE FROZEN CHAIN VALUES (the --compat
    path never passes anything else); the --self-test fixture suite
    passes fixture-derived values so its MOCK records are internally
    consistent (MOCK bytes are FIXTURES, never measurements).
    Returns (rows, flag) where rows is a list of
    (check, want, got, verdict) with verdict 'OK' or 'MISMATCH'.
    """
    if chain is None:
        chain = {"instrument": INSTRUMENT_DIGEST,
                 "corpus_census": CORPUS_CENSUS_DIGEST,
                 "cells": CELLS_DIGEST}
    hv = parse_host_verify(hv_text)
    bc = parse_build_census(bc_text)
    rw = parse_run_window(rw_text)
    rows = []

    def row(name, want, got, ok):
        rows.append((name, str(want), str(got), "OK" if ok else "MISMATCH"))

    match_by_name = {name: (local, host) for (name, local, host) in hv["matches"]}
    row("match-lines-3", 3, len(hv["matches"]), len(hv["matches"]) == 3)
    eq_host = sum(1 for (_, l, h) in hv["matches"] if l == h)
    row("match-local-eq-host", 3, eq_host, eq_host == 3 and len(hv["matches"]) == 3)
    eq_artifact = 0
    for name, local, _host in hv["matches"]:
        art = artifacts.get(name)
        if art is not None and sha(art) == local:
            eq_artifact += 1
    row("match-local-eq-artifact", 3, eq_artifact,
        eq_artifact == 3 and len(hv["matches"]) == 3)
    inst_local = match_by_name.get("gpu-subgroup-reduce-anv-ndiv.c", (None, None))[0]
    row("instrument-digest-chain", chain["instrument"],
        inst_local if inst_local is not None else "absent",
        inst_local == chain["instrument"])
    cor_local = match_by_name.get("expected-corpus.sha256", (None, None))[0]
    row("corpus-census-digest-chain", chain["corpus_census"],
        cor_local if cor_local is not None else "absent",
        cor_local == chain["corpus_census"])

    man = artifacts.get("__manifest__", b"")
    kept = cell_lines(man) if man else []
    row("manifest-cell-count", CELL_LINE_COUNT, len(kept), len(kept) == CELL_LINE_COUNT)
    cells_dig = sha(b"".join(kept)) if kept else "absent"
    row("manifest-cells-digest-chain", chain["cells"], cells_dig,
        cells_dig == chain["cells"])

    row("corpus-ok-16", CORPUS_FILE_COUNT,
        hv["corpus_ok"] if hv["corpus_ok"] is not None else "absent",
        hv["corpus_ok"] == CORPUS_FILE_COUNT)
    row("corpus-rc", 0,
        hv["corpus_rc"] if hv["corpus_rc"] is not None else "absent",
        hv["corpus_rc"] == 0)
    row("custody-summary-line", "present", "present" if hv["summary"] else "absent",
        hv["summary"])
    row("go-stamp", "present", hv["go"] if hv["go"] else "absent", hv["go"] is not None)

    build_times = [b[3] for b in bc["builds"]]
    run_times = [r[2] for r in rw["runs"]]
    if hv["go"] and build_times:
        go_vs_builds = "le" if hv["go"] <= min(build_times) else "gt"
    else:
        go_vs_builds = "na"
    row("go-not-after-builds", "le", go_vs_builds, go_vs_builds in ("le", "na")
        and hv["go"] is not None and bool(build_times))
    if hv["go"] and run_times:
        go_vs_runs = "lt" if hv["go"] < min(run_times) else "ge"
    else:
        go_vs_runs = "na"
    row("go-before-all-runs", "lt", go_vs_runs, go_vs_runs in ("lt", "na")
        and hv["go"] is not None and bool(run_times))
    if build_times and run_times:
        b_vs_r = "le" if max(build_times) <= min(run_times) else "gt"
    else:
        b_vs_r = "na"
    row("builds-before-first-run", "le", b_vs_r,
        b_vs_r in ("le", "na") and bool(build_times) and bool(run_times))

    row("build-lines", 4, len(bc["builds"]), len(bc["builds"]) == 4)
    knobs_ok = sum(1 for (t, k, _rc, _ts) in bc["builds"]
                   if FROZEN_KNOBS.get(t) == k)
    row("build-knobs", 4, knobs_ok, knobs_ok == 4 and len(bc["builds"]) == 4)
    rc_ok = sum(1 for (_t, _k, rc, _ts) in bc["builds"] if rc == 0)
    row("build-rc", 4, rc_ok, rc_ok == 4 and len(bc["builds"]) == 4)
    row("build-stderr-total", 0,
        bc["stderr_total"] if bc["stderr_total"] is not None else "absent",
        bc["stderr_total"] == 0)

    for tag in ("c2", "hi", "tw", "c8"):
        got = bc["digests"].get(tag, "absent")
        row("pin-%s" % tag, FROZEN_PINS[tag], got, got == FROZEN_PINS[tag])
    row("pins-verdict-line", "4/4",
        bc["pins"] if bc["pins"] is not None else "absent", bc["pins"] == "4/4")

    row("run-count", RUN_COUNT, len(rw["runs"]), len(rw["runs"]) == RUN_COUNT)
    row("verify-lines", VERIFY_TOTAL, verify_lines, verify_lines == VERIFY_TOTAL)
    row("verify-mismatch-total", 0, verify_mismatch, verify_mismatch == 0)

    by_name = {name: (want, got, verdict) for (name, want, got, verdict) in rows}
    if by_name["verify-mismatch-total"][2] == "MISMATCH":
        flag = "verify-mismatch"
    elif any(by_name["pin-%s" % t][2] == "MISMATCH" for t in ("c2", "hi", "tw", "c8")):
        flag = "build-pin-not-byte-identical"
    elif by_name["go-stamp"][1] == "absent":
        flag = "custody-go-missing"
    elif by_name["go-not-after-builds"][1] == "gt":
        flag = "custody-go-after-builds"
    elif any(verdict == "MISMATCH" for (_n, _w, _g, verdict) in rows):
        flag = "REFUSED-RECORD-INCONSISTENT"
    else:
        flag = "none"
    row("flag", "none", flag, flag == "none")
    return rows, flag


# ---------------------------------------------------------------------------
# Window loading (the --compat path over committed bytes).
# ---------------------------------------------------------------------------

def load_window(tag, dirname, manifest_name):
    d = EVIDENCE_ROOT / dirname
    hv_path = d / ("host-verify-%s.txt" % tag)
    bc_path = d / ("build-census-%s.txt" % tag)
    rw_path = d / "run-window.txt"
    hv_text = hv_path.read_text()
    bc_text = bc_path.read_text()
    rw_text = rw_path.read_text()
    provenance = []
    art = {}
    for key, fname in CHAIN_ARTIFACT_FILES.items():
        p = d / fname
        if p.is_file():
            art[key] = p.read_bytes()
        else:
            canon = EVIDENCE_ROOT / ARTIFACT_CANON_DIR / fname
            art[key] = canon.read_bytes()
            provenance.append(
                "artifact-provenance %s: absent in %s; local= re-derived"
                " from the named canonical committed copy in %s (byte-copy"
                " chain -- named, not hidden)" % (key, dirname,
                                                  ARTIFACT_CANON_DIR))
    art[manifest_name] = (d / manifest_name).read_bytes()
    art["__manifest__"] = art[manifest_name]
    verify_lines = 0
    verify_mismatch = 0
    for line in rw_text.splitlines():
        m = RE_RUN.match(line)
        if not m:
            continue
        run_tag = m.group(1)
        log_path = d / ("run-%s.txt" % run_tag)
        if not log_path.is_file():
            # fail-closed: a missing run log is a hard error (0 VERIFY
            # lines seen -> the verify-lines row mismatches downstream).
            continue
        for log_line in log_path.read_text().splitlines():
            vm = RE_VERIFY.match(log_line)
            if vm:
                verify_lines += 1
                verify_mismatch += int(vm.group(1))
    return hv_text, bc_text, rw_text, art, verify_lines, verify_mismatch, provenance


def run_compat():
    out = []
    out.append("JUN-59 custody-prego --compat: the PRE-GO CUSTODY CHECKER"
               " pre-build validated over the THREE committed 78-run"
               " run-window windows (s36/s51/W5).")
    out.append("LIVE-ONLY FIELDS (quoted from the committed records as"
               " INPUT, named not hidden): host= digests, GO stamp, build"
               " timestamps, per-run host dates; every other value is"
               " re-derived from committed bytes.")
    total = 0
    mismatched = 0
    flags = []
    for (tag, dirname, manifest_name) in WINDOWS:
        hv, bc, rw, arts, vl, vm, prov = load_window(tag, dirname, manifest_name)
        rows, flag = check_window(hv, bc, rw, arts, vl, vm)
        out.append("window=%s dir=%s manifest=%s" % (tag, dirname, manifest_name))
        for line in prov:
            out.append("  " + line)
        for (name, want, got, verdict) in rows:
            total += 1
            if verdict != "OK":
                mismatched += 1
            out.append("  check=%s want=%s got=%s verdict=%s"
                       % (name, want, got, verdict))
        flags.append(flag)
    out.append("TOTAL: %d rows, %d mismatched | windows %d | flags %s"
               % (total, mismatched, len(WINDOWS),
                  " ".join(flags)))
    text = "\n".join(out) + "\n"
    sys.stdout.write(text)
    return 0 if mismatched == 0 else 1


# ---------------------------------------------------------------------------
# The fixture suite (--self-test).  MOCK records only; no committed window
# is read in this mode.  MOCK bytes are FIXTURES, never measurements.
# ---------------------------------------------------------------------------

MOCK_ARTIFACTS = {
    "gpu-subgroup-reduce-anv-ndiv.c": b"mock instrument source bytes\n",
    "cases-s96-a.txt": (
        b"# mock manifest header\n"
        b"mock-cell-0 a b c\n"
        b"mock-cell-1 a b c\n"
        + b"".join(b"mock-cell-%d a b c\n" % i for i in range(2, 24))
    ),
    "expected-corpus.sha256": b"mock corpus census bytes\n",
}
MOCK_ARTIFACTS["__manifest__"] = MOCK_ARTIFACTS["cases-s96-a.txt"]

# The mock record's DECLARED chain constants (fixture-derived, never the
# frozen route values): the MOCK window is internally consistent by
# construction, so its chain rows must compare against these.
MOCK_CHAIN = {
    "instrument": sha(MOCK_ARTIFACTS["gpu-subgroup-reduce-anv-ndiv.c"]),
    "corpus_census": sha(MOCK_ARTIFACTS["expected-corpus.sha256"]),
    "cells": sha(b"".join(cell_lines(MOCK_ARTIFACTS["cases-s96-a.txt"]))),
}


def mock_host_verify(artifacts, go="2026-10-30T00:00:01Z", corpus_shape="sum",
                     summary=True, flip_host=False, drop_match=False,
                     bad_local=False, corpus_ok=16, corpus_rc=0):
    names = ["gpu-subgroup-reduce-anv-ndiv.c", "cases-s96-a.txt",
             "expected-corpus.sha256"]
    if drop_match:
        names = names[:-1]
    lines = ["== mock host-verify (FIXTURE, NEVER A MEASUREMENT) =="]
    for name in names:
        local = sha(artifacts[name])
        if bad_local and name == "cases-s96-a.txt":
            local = "0" * 64
        host = ("1" * 64) if (flip_host and name == "cases-s96-a.txt") else local
        lines.append("MATCH  %s: local=%s host=%s" % (name, local, host))
    lines.append("== corpus sha256sum -c (cwd = workdir root) ==")
    if corpus_shape == "sum":
        lines.append("%d/16 OK (mock files)" % corpus_ok)
    else:
        for i in range(corpus_ok):
            lines.append("shaders/mock-%d.spv: OK" % i)
    lines.append("corpus_rc=%d" % corpus_rc)
    if summary:
        lines.append("== local-vs-host 3/3 MATCH; corpus 16/16 ==")
    if go is not None:
        lines.append("GO stamp: %s" % go)
    return "\n".join(lines) + "\n"


def mock_build_census(go_time="2026-10-30T00:00:01Z", pins_override=None,
                      rc_override=None, knob_override=None, stderr_total=0,
                      pins_line="4/4", drop_digest=None, n_builds=4):
    base = "2026-10-30T00:00:02Z"
    order = ["c2", "hi", "tw", "c8"]
    lines = ["== mock build census (FIXTURE, NEVER A MEASUREMENT) ==",
             "== binary compiles: gcc -O2 -DBATCH=<B> -DWORK_MUL=<M> -DNDIV=<D> =="]
    for i, tag in enumerate(order[:n_builds]):
        knobs = FROZEN_KNOBS[tag]
        if knob_override and tag == knob_override[0]:
            knobs = knob_override[1]
        rc = 0
        if rc_override and tag == rc_override[0]:
            rc = rc_override[1]
        lines.append("build %s (%s) rc=%d @%s"
                     % (tag, knobs, rc, base))
    lines.append("build stderr byte counts (host build-<tag>.err):")
    for tag in order[:n_builds]:
        lines.append("0 build-%s.err" % tag)
    lines.append("%d total" % stderr_total)
    for tag in order[:n_builds]:
        if drop_digest == tag:
            continue
        dig = FROZEN_PINS[tag]
        if pins_override and tag in pins_override:
            dig = pins_override[tag]
        lines.append("%s  anv-bb-%s" % (dig, tag))
    if pins_line is not None:
        lines.append("pins: %s BYTE-IDENTICAL (mock)" % pins_line)
    return "\n".join(lines) + "\n"


def mock_run_window(n=RUN_COUNT, first="2026-10-30T00:01:00Z", last_prefix=None):
    lines = ["mock run window (FIXTURE, NEVER A MEASUREMENT)"]
    for i in range(n):
        tag = "mock-r%d" % (i + 1)
        ts = first
        lines.append("  %s rc=0 host-date=%s stderr_bytes=0 samples=450"
                     " verifies=24 cells=24 tail='# done cells=24'"
                     % (tag, ts))
    return "\n".join(lines) + "\n"


def self_test():
    out = ["JUN-59 custody-prego --self-test (MOCK FIXTURES, NEVER"
           " MEASUREMENTS; this mode reads NO committed window)"]
    n = [0]

    def ok(desc):
        n[0] += 1
        out.append("ok %d: %s" % (n[0], desc))

    def check(desc, cond):
        if not cond:
            raise AssertionError(desc)
        ok(desc)

    def rows_of(**kw):
        hv = mock_host_verify(MOCK_ARTIFACTS, **kw.get("hv", {}))
        bc = mock_build_census(**kw.get("bc", {}))
        rw = mock_run_window(**kw.get("rw", {}))
        vl = kw.get("vl", VERIFY_TOTAL)
        vm = kw.get("vm", 0)
        return check_window(hv, bc, rw, MOCK_ARTIFACTS, vl, vm, chain=MOCK_CHAIN)

    def verdict_of(rows, name):
        for (n_, _w, _g, v) in rows:
            if n_ == name:
                return v
        raise AssertionError("row %s absent" % name)

    def got_of(rows, name):
        for (n_, _w, g, _v) in rows:
            if n_ == name:
                return g
        raise AssertionError("row %s absent" % name)

    # -- the clean mock window -------------------------------------------
    rows, flag = rows_of()
    check("clean: flag is none", flag == "none")
    check("clean: every row OK", all(v == "OK" for (_a, _b, _c, v) in rows))
    check("clean: row count 27 (the eight named surfaces' 26 checks + flag)",
          len(rows) == 27)

    # -- deterministic: the same inputs give the same rows --------------
    rows2, flag2 = rows_of()
    check("determinism: rows byte-equal across calls", rows2 == rows)
    check("determinism: flag stable", flag2 == flag)

    # -- (i) custody MATCH lines ---------------------------------------
    rows, flag = rows_of(hv={"flip_host": True})
    check("host= flip: match-local-eq-host MISMATCH",
          verdict_of(rows, "match-local-eq-host") == "MISMATCH")
    check("host= flip: flag REFUSED-RECORD-INCONSISTENT",
          flag == "REFUSED-RECORD-INCONSISTENT")
    rows, flag = rows_of(hv={"drop_match": True})
    check("dropped MATCH line: match-lines-3 MISMATCH",
          verdict_of(rows, "match-lines-3") == "MISMATCH")
    check("dropped MATCH line: flag REFUSED-RECORD-INCONSISTENT",
          flag == "REFUSED-RECORD-INCONSISTENT")
    rows, flag = rows_of(hv={"bad_local": True})
    check("bad local= digest: match-local-eq-artifact MISMATCH",
          verdict_of(rows, "match-local-eq-artifact") == "MISMATCH")

    # -- (ii) manifest cell chain --------------------------------------
    rows, flag = rows_of(rw={}, hv={}, bc={}, )
    short = dict(MOCK_ARTIFACTS)
    short["cases-s96-a.txt"] = MOCK_ARTIFACTS["cases-s96-a.txt"].replace(
        b"mock-cell-23 a b c\n", b"")
    short["__manifest__"] = short["cases-s96-a.txt"]
    hv_s = mock_host_verify(short)
    rows, flag = check_window(hv_s, mock_build_census(), mock_run_window(),
                              short, VERIFY_TOTAL, 0, chain=MOCK_CHAIN)
    check("23 cell lines: manifest-cell-count MISMATCH",
          verdict_of(rows, "manifest-cell-count") == "MISMATCH")
    check("23 cell lines: manifest-cells-digest-chain MISMATCH",
          verdict_of(rows, "manifest-cells-digest-chain") == "MISMATCH")
    tampered = dict(MOCK_ARTIFACTS)
    tampered["cases-s96-a.txt"] = MOCK_ARTIFACTS["cases-s96-a.txt"].replace(
        b"mock-cell-23 a b c\n", b"mock-cell-23 a b CHANGED\n")
    tampered["__manifest__"] = tampered["cases-s96-a.txt"]
    hv_t = mock_host_verify(tampered)
    rows, flag = check_window(hv_t, mock_build_census(), mock_run_window(),
                              tampered, VERIFY_TOTAL, 0, chain=MOCK_CHAIN)
    check("tampered cell line: cells digest MISMATCH (count still 24)",
          verdict_of(rows, "manifest-cell-count") == "OK"
          and verdict_of(rows, "manifest-cells-digest-chain") == "MISMATCH")

    # -- (iii) corpus census -------------------------------------------
    rows, flag = rows_of(hv={"corpus_ok": 15})
    check("15/16 corpus: corpus-ok-16 MISMATCH",
          verdict_of(rows, "corpus-ok-16") == "MISMATCH")
    rows, flag = rows_of(hv={"corpus_shape": "files", "corpus_ok": 16})
    check("s36 per-file shape: corpus-ok-16 OK",
          verdict_of(rows, "corpus-ok-16") == "OK")
    rows, flag = rows_of(hv={"corpus_rc": 1})
    check("corpus_rc=1: corpus-rc MISMATCH",
          verdict_of(rows, "corpus-rc") == "MISMATCH")
    rows, flag = rows_of(hv={"summary": False})
    check("summary line absent: custody-summary-line MISMATCH",
          verdict_of(rows, "custody-summary-line") == "MISMATCH")

    # -- (iv) GO stamp and ordering ------------------------------------
    rows, flag = rows_of(hv={"go": None})
    check("GO absent: go-stamp MISMATCH",
          verdict_of(rows, "go-stamp") == "MISMATCH")
    check("GO absent: flag custody-go-missing (frozen criterion 4)",
          flag == "custody-go-missing")
    rows, flag = rows_of(hv={"go": "2026-10-30T00:00:09Z"})
    check("GO after builds: go-not-after-builds gt",
          got_of(rows, "go-not-after-builds") == "gt")
    check("GO after builds: flag custody-go-after-builds (frozen criterion 4)",
          flag == "custody-go-after-builds")
    rows, flag = rows_of(hv={"go": "2026-10-30T00:00:02Z"})
    check("GO == earliest build second: le (second granularity, named)",
          got_of(rows, "go-not-after-builds") == "le")
    check("GO == earliest build second: NOT flagged",
          flag == "none")
    rows, flag = rows_of(rw={"first": "2026-10-30T00:00:01Z"})
    check("first run before builds: builds-before-first-run gt",
          got_of(rows, "builds-before-first-run") == "gt")
    check("first run before builds: flag REFUSED-RECORD-INCONSISTENT"
          " (not a frozen criterion)",
          flag == "REFUSED-RECORD-INCONSISTENT")
    rows, flag = rows_of(hv={"go": "2026-10-30T00:02:00Z"})
    check("GO after first run: go-before-all-runs ge",
          got_of(rows, "go-before-all-runs") == "ge")

    # -- (v) pinned compiles -------------------------------------------
    rows, flag = rows_of(bc={"n_builds": 3})
    check("3 build lines: build-lines MISMATCH",
          verdict_of(rows, "build-lines") == "MISMATCH")
    rows, flag = rows_of(bc={"knob_override": ("hi", "-DBATCH=3 -DWORK_MUL=1")})
    check("wrong hi knobs: build-knobs MISMATCH",
          verdict_of(rows, "build-knobs") == "MISMATCH")
    rows, flag = rows_of(bc={"rc_override": ("tw", 1)})
    check("tw rc=1: build-rc MISMATCH",
          verdict_of(rows, "build-rc") == "MISMATCH")
    rows, flag = rows_of(bc={"stderr_total": 1})
    check("build stderr total 1: build-stderr-total MISMATCH",
          verdict_of(rows, "build-stderr-total") == "MISMATCH")

    # -- (vi) build pins -----------------------------------------------
    rows, flag = rows_of(bc={"pins_override": {"c2": "0" * 64}})
    check("c2 digest off pin: pin-c2 MISMATCH",
          verdict_of(rows, "pin-c2") == "MISMATCH")
    check("c2 digest off pin: flag build-pin-not-byte-identical"
          " (frozen criterion 3)",
          flag == "build-pin-not-byte-identical")
    rows, flag = rows_of(bc={"drop_digest": "hi"})
    check("hi digest line absent: pin-hi MISMATCH",
          verdict_of(rows, "pin-hi") == "MISMATCH")
    rows, flag = rows_of(bc={"pins_line": "3/4"})
    check("pins line 3/4: pins-verdict-line MISMATCH",
          verdict_of(rows, "pins-verdict-line") == "MISMATCH")
    rows, flag = rows_of(bc={"pins_line": None})
    check("pins line absent: pins-verdict-line MISMATCH",
          verdict_of(rows, "pins-verdict-line") == "MISMATCH")

    # -- (vii) run window ----------------------------------------------
    rows, flag = rows_of(rw={"n": RUN_COUNT - 1})
    check("77 runs: run-count MISMATCH",
          verdict_of(rows, "run-count") == "MISMATCH")

    # -- (viii) VERIFY -------------------------------------------------
    rows, flag = rows_of(vl=VERIFY_TOTAL - 24)
    check("1848 VERIFY lines: verify-lines MISMATCH",
          verdict_of(rows, "verify-lines") == "MISMATCH")
    rows, flag = rows_of(vm=3)
    check("verify mismatch 3: verify-mismatch-total MISMATCH",
          verdict_of(rows, "verify-mismatch-total") == "MISMATCH")
    check("verify mismatch 3: flag verify-mismatch (frozen criterion 2)",
          flag == "verify-mismatch")

    # -- precedence among the frozen criteria --------------------------
    rows, flag = rows_of(vm=1, bc={"pins_override": {"tw": "0" * 64}})
    check("verify + pin both bad: verify-mismatch wins (frozen order)",
          flag == "verify-mismatch")
    rows, flag = rows_of(hv={"go": None}, bc={"pins_override": {"c8": "0" * 64}})
    check("pin + GO both bad: build-pin-not-byte-identical wins (frozen order)",
          flag == "build-pin-not-byte-identical")
    rows, flag = rows_of(hv={"go": None}, rw={"n": 77})
    check("GO + record-shape both bad: custody-go-missing wins (frozen"
          " criteria before checker-level refusal)",
          flag == "custody-go-missing")

    out.append("TOTAL %d assertions passed 0 failed" % n[0])
    sys.stdout.write("\n".join(out) + "\n")
    return 0


def main():
    args = sys.argv[1:]
    if args == ["--self-test"]:
        return self_test()
    if args == ["--compat"]:
        return run_compat()
    sys.stderr.write("usage: custody-prego.py --self-test | --compat\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
