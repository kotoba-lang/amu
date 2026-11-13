#!/usr/bin/env python3
"""JUN-59 session 102 -- the W6 ADOPTION-MANIFEST checker (pre-build).

Fails closed on the W6 adoption surface: every adoption contract named
in the s90/s95/s96/s97/s98/s99/s100/s101 pre-build records ("the W6
session adopts THIS file as ...") is prose distributed across eight
records, two of them carrying SUPERSESSION chains (reading:
reading-prego-fixed.py supersedes reading-s1001.py / reading-s1000.py /
reading-prego.py; custody: custody-check-prego.py supersedes
custody-prego.py).  Nothing in the tree binds those contracts to exact
committed bytes, so a wrong or superseded copy adopted under slot
pressure would run undetected.  This tool binds them: a frozen manifest
(adoption-manifest.txt, this directory) names, per adoption slot, the
canonical source path, its sha256, its adoption name (or SESSION-CHOSEN
where the frozen route names none) and its provenance; this checker
re-derives every digest from the committed bytes at --check time and
refuses (nonzero exit) on any mismatch.

INDEPENDENCE / HONESTY CONTRACT: pure stdlib; NO RNG, no clock; reads
committed bytes and emits text only; submits NOTHING to any GPU; it is
record-checking machinery, not a device measurement, and it moves no
Rule 4 row and no :measured? flag.

Usage:
  adoption-check-prego.py --check <manifest> <root>        (binding duty)
  adoption-check-prego.py --self-test <scratch-dir>        (MOCK battery)

Exit: 0 iff VERDICT CONSISTENT (or battery 0 failed); 1 otherwise.

Manifest grammar (fail-closed -- every non-comment line must parse):
  one row per line, space-separated k=v tokens, keys from the closed
  set {kind, slot, path, sha256, adopted, provenance, superseded,
  relation, derive, assoc}; '#' lines and blank lines are comments.
  kind=tool  requires slot, path, sha256, adopted, provenance
             (optional: superseded, relation);
  kind=frozen requires slot, path, sha256, provenance
             (optional: derive, assoc).
  provenance = computed-at-freeze | record-named:<record-path>
  superseded = comma-separated <path>@<sha256>
  relation   = lines-differ-only:<N>:<path>   (1-based line N)
  derive     = none | cell-lines-nl   (sha256 over the file's
               non-comment non-empty lines each terminated by \\n --
               the s91/s94 manifest-cell-lines chain construction,
               reproduced exactly at this tick)
  assoc      = the token that must appear in the record for the
               provenance-name sub-check (default: basename(path))

NAMED, NOT HIDDEN (limits of this checker):
  (a) record-named provenance is checked as TWO presence sub-checks
      (the digest appears in the record text; the assoc token appears
      in the record text) -- positional binding (the digest named FOR
      that token) is NOT enforced;
  (b) the manifest itself is only as trustworthy as its freeze: its
      digests were computed from committed bytes at session 102 and,
      where provenance=record-named, cross-checked against the record
      prose; a tampered manifest plus tampered source would pass --
      the binding guards adoption mistakes, not repository compromise;
  (c) adopted-name uniqueness is checked over literal manifest tokens;
      exactly one row may carry SESSION-CHOSEN (the frozen route names
      no run-window driver filename -- s95).
"""

import hashlib
import os
import shutil
import sys

KEYS = {"kind", "slot", "path", "sha256", "adopted", "provenance",
        "superseded", "relation", "derive", "assoc"}
HEX = "0123456789abcdef"
SLOT_CHARS = set("abcdefghijklmnopqrstuvwxyz0123456789-")
ADOPTED_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
                    "0123456789<>=._-+")


class ManifestError(Exception):
    pass


def is_hex64(s):
    return len(s) == 64 and all(c in HEX for c in s)


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def read_bytes(root, rel):
    path = os.path.join(root, rel)
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as fh:
        return fh.read()


def cell_lines_digest(data):
    out = []
    for line in data.split(b"\n"):
        if line.endswith(b"\r"):
            line = line[:-1]
        stripped = line.strip()
        if not stripped or stripped.startswith(b"#"):
            continue
        out.append(line + b"\n")
    return sha256_bytes(b"".join(out))


def hex_runs(text):
    runs = []
    cur = ""
    for ch in text:
        if ch in HEX:
            cur += ch
        else:
            if len(cur) >= 64:
                runs.append(cur)
            cur = ""
    if len(cur) >= 64:
        runs.append(cur)
    return runs


def parse_manifest(text):
    rows = []
    for lineno, raw in enumerate(text.split("\n"), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        toks = line.split(" ")
        kv = {}
        for tok in toks:
            if "=" not in tok:
                raise ManifestError("line %d: unparsed token %r" % (lineno, tok))
            k, v = tok.split("=", 1)
            if k not in KEYS:
                raise ManifestError("line %d: unknown key %r" % (lineno, k))
            if k in kv:
                raise ManifestError("line %d: duplicate key %r" % (lineno, k))
            if not v:
                raise ManifestError("line %d: empty value for %r" % (lineno, k))
            kv[k] = v
        kind = kv.get("kind")
        if kind not in ("tool", "frozen"):
            raise ManifestError("line %d: kind must be tool|frozen" % lineno)
        need = ["slot", "path", "sha256", "provenance"]
        if kind == "tool":
            need.append("adopted")
        for k in need:
            if k not in kv:
                raise ManifestError("line %d: missing %r" % (lineno, k))
        slot = kv["slot"]
        if not all(c in SLOT_CHARS for c in slot):
            raise ManifestError("line %d: bad slot token %r" % (lineno, slot))
        if kind == "tool" and not all(c in ADOPTED_CHARS for c in kv["adopted"]):
            raise ManifestError("line %d: bad adopted token %r" % (lineno, kv["adopted"]))
        if not is_hex64(kv["sha256"]):
            raise ManifestError("line %d: sha256 not 64 lowercase hex" % lineno)
        rel = kv["path"]
        if rel.startswith("/") or ".." in rel.split("/"):
            raise ManifestError("line %d: path escapes root: %r" % (lineno, rel))
        prov = kv["provenance"]
        if prov != "computed-at-freeze" and not prov.startswith("record-named:"):
            raise ManifestError("line %d: bad provenance %r" % (lineno, prov))
        if prov.startswith("record-named:"):
            rec = prov[len("record-named:"):]
            if not rec or rec.startswith("/") or ".." in rec.split("/"):
                raise ManifestError("line %d: bad record path in provenance" % lineno)
        sup_list = []
        if "superseded" in kv:
            if kind != "tool":
                raise ManifestError("line %d: superseded only on kind=tool" % lineno)
            for ent in kv["superseded"].split(","):
                if "@" not in ent:
                    raise ManifestError("line %d: bad superseded entry %r" % (lineno, ent))
                p, h = ent.rsplit("@", 1)
                if not p or p.startswith("/") or ".." in p.split("/"):
                    raise ManifestError("line %d: superseded path escapes root" % lineno)
                if not is_hex64(h):
                    raise ManifestError("line %d: superseded digest not 64 hex" % lineno)
                sup_list.append((p, h))
        rel_spec = None
        if "relation" in kv:
            if kind != "tool":
                raise ManifestError("line %d: relation only on kind=tool" % lineno)
            parts = kv["relation"].split(":")
            if len(parts) != 3 or parts[0] != "lines-differ-only":
                raise ManifestError("line %d: bad relation %r" % (lineno, kv["relation"]))
            if not parts[1].isdigit() or int(parts[1]) < 1:
                raise ManifestError("line %d: bad relation line number" % lineno)
            if not parts[2] or parts[2].startswith("/") or ".." in parts[2].split("/"):
                raise ManifestError("line %d: relation path escapes root" % lineno)
            rel_spec = (int(parts[1]), parts[2])
        derive = kv.get("derive", "none")
        if derive not in ("none", "cell-lines-nl"):
            raise ManifestError("line %d: bad derive %r" % (lineno, derive))
        if derive != "none" and kind != "frozen":
            raise ManifestError("line %d: derive only on kind=frozen" % lineno)
        rows.append({
            "line": lineno, "kind": kind, "slot": slot, "path": rel,
            "sha256": kv["sha256"], "adopted": kv.get("adopted"),
            "provenance": prov, "superseded": sup_list,
            "relation": rel_spec, "derive": derive,
            "assoc": kv.get("assoc", os.path.basename(rel)),
        })
    return rows


def check(root, rows, out):
    mismatched = 0
    matched = 0

    def row(text, ok):
        nonlocal matched, mismatched
        out.append(text + " verdict=" + ("MATCH" if ok else "MISMATCH"))
        if ok:
            matched += 1
        else:
            mismatched += 1

    def emit(text):
        out.append(text)

    for i, r in enumerate(rows, 1):
        data = read_bytes(root, r["path"])
        if data is None:
            emit("row %d slot=%s kind=%s digest path=%s want=%s got=MISSING"
                 " verdict=MISSING" % (i, r["slot"], r["kind"], r["path"], r["sha256"]))
            mismatched += 1
        else:
            if r["derive"] == "cell-lines-nl":
                got = cell_lines_digest(data)
            else:
                got = sha256_bytes(data)
            row("row %d slot=%s kind=%s digest path=%s derive=%s want=%s got=%s"
                % (i, r["slot"], r["kind"], r["path"], r["derive"], r["sha256"], got),
                got == r["sha256"])
        if r["provenance"].startswith("record-named:"):
            rec_rel = r["provenance"][len("record-named:"):]
            rec_data = read_bytes(root, rec_rel)
            if rec_data is None:
                emit("row %d slot=%s provenance record=%s digest-verdict=ABSENT"
                     " name-verdict=ABSENT token=%s verdict=MISMATCH"
                     % (i, r["slot"], rec_rel, r["assoc"]))
                mismatched += 1
            else:
                rec_text = rec_data.decode("utf-8", errors="replace")
                digest_ok = any(run == r["sha256"] for run in hex_runs(rec_text))
                name_ok = r["assoc"] in rec_text
                row("row %d slot=%s provenance record=%s digest-verdict=%s"
                    " name-verdict=%s token=%s"
                    % (i, r["slot"], rec_rel,
                       "PRESENT" if digest_ok else "ABSENT",
                       "PRESENT" if name_ok else "ABSENT", r["assoc"]),
                    digest_ok and name_ok)
        for p, h in r["superseded"]:
            sdata = read_bytes(root, p)
            if sdata is None:
                emit("row %d slot=%s superseded %s want=%s got=MISSING"
                     " verdict=MISSING" % (i, r["slot"], p, h))
                mismatched += 1
                continue
            got = sha256_bytes(sdata)
            ok = (got == h) and (p != r["path"])
            row("row %d slot=%s superseded %s want=%s got=%s"
                % (i, r["slot"], p, h, got), ok)
        if r["relation"] is not None:
            n, ref_rel = r["relation"]
            src = read_bytes(root, r["path"])
            ref = read_bytes(root, ref_rel)
            if src is None or ref is None or ref_rel == r["path"]:
                emit("row %d slot=%s relation lines-differ-only:%d want-diff=%d"
                     " got-diff=UNRESOLVED verdict=MISMATCH"
                     % (i, r["slot"], n, n))
                mismatched += 1
            else:
                sl = src.decode("utf-8", errors="replace").split("\n")
                rl = ref.decode("utf-8", errors="replace").split("\n")
                if len(sl) != len(rl):
                    got_desc = "LINE-COUNT"
                    ok = False
                else:
                    diffs = [j + 1 for j, (a, b) in enumerate(zip(sl, rl)) if a != b]
                    got_desc = ",".join(str(d) for d in diffs) if diffs else "none"
                    ok = diffs == [n]
                row("row %d slot=%s relation lines-differ-only:%d want-diff=%d"
                    " got-diff=%s" % (i, r["slot"], n, n, got_desc), ok)

    slots = [r["slot"] for r in rows]
    row("cross slots-unique want=%d got=%d"
        % (len(slots), len(set(slots))), len(set(slots)) == len(slots))
    tool_paths = [r["path"] for r in rows if r["kind"] == "tool"]
    row("cross tool-paths-unique want=%d got=%d"
        % (len(tool_paths), len(set(tool_paths))),
        len(set(tool_paths)) == len(tool_paths))
    adopted = [r["adopted"] for r in rows if r["kind"] == "tool"]
    row("cross adopted-unique want=%d got=%d"
        % (len(adopted), len(set(adopted))),
        len(set(adopted)) == len(adopted))
    return matched, mismatched


def run_check(manifest_path, root):
    with open(manifest_path, "r", encoding="utf-8") as fh:
        text = fh.read()
    out = []
    try:
        rows = parse_manifest(text)
    except ManifestError as exc:
        out.append("adoption-check-prego --check parse-error %s" % exc)
        out.append("VERDICT: INCONSISTENT (parse-error)")
        return 1, out
    out.append("adoption-check-prego --check rows=%d" % len(rows))
    matched, mismatched = check(root, rows, out)
    verdict = "CONSISTENT" if mismatched == 0 else "INCONSISTENT"
    out.append("VERDICT: %s (matched %d, mismatched %d)"
               % (verdict, matched, mismatched))
    return (0 if mismatched == 0 else 1), out


# ---------------------------------------------------------------- self-test

class Battery:
    def __init__(self):
        self.total = 0
        self.failed = 0
        self.lines = []

    def assert_(self, name, cond):
        self.total += 1
        if cond:
            self.lines.append("assert %d %s ok" % (self.total, name))
        else:
            self.failed += 1
            self.lines.append("assert %d %s FAIL" % (self.total, name))


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data)


def selftest(scratch):
    mock = os.path.join(scratch, "mock-adoption-check")
    if os.path.isdir(mock):
        shutil.rmtree(mock)
    os.makedirs(mock)
    b = Battery()

    # fixture bytes (FIXTURES, never measurements)
    a = b"P1\nP2Y\nP3\n"
    write(os.path.join(mock, "a.py"), a)
    a_hex = sha256_bytes(a)
    c_src = b"# comment\n\nCELL1 x\nCELL2 y\n# more\nCELL3 z"
    write(os.path.join(mock, "cells.txt"), c_src)
    cells_hex = cell_lines_digest(c_src)
    rec = ("record prose naming a.py (sha256 %s) and the token a.py here\n"
           % a_hex).encode()
    write(os.path.join(mock, "rec.txt"), rec)
    sup = b"superseded bytes\n"
    write(os.path.join(mock, "old.py"), sup)
    sup_hex = sha256_bytes(sup)
    ref = b"P1\nP2X\nP3\n"
    write(os.path.join(mock, "ref.txt"), ref)
    refsrc = b"L1\nL2X\nL3\n"
    write(os.path.join(mock, "refsrc.txt"), refsrc)
    src2 = b"L1\nL2Y\nL3\n"
    write(os.path.join(mock, "src2.py"), src2)

    def manifest(body):
        return body

    clean = manifest(
        "# mock manifest (FIXTURE)\n"
        "kind=tool slot=alpha path=a.py sha256=%s adopted=alpha-s1.py "
        "provenance=record-named:rec.txt superseded=old.py@%s "
        "relation=lines-differ-only:2:ref.txt\n" % (a_hex, sup_hex) +
        "kind=frozen slot=cells path=cells.txt sha256=%s provenance=computed-at-freeze "
        "derive=cell-lines-nl\n" % cells_hex)

    # 1. clean manifest -> CONSISTENT
    write(os.path.join(mock, "m-clean.txt"), clean.encode())
    rc, out = run_check(os.path.join(mock, "m-clean.txt"), mock)
    b.assert_("clean-rc-0", rc == 0)
    b.assert_("clean-verdict-consistent",
              out[-1] == "VERDICT: CONSISTENT (matched 8, mismatched 0)")
    b.assert_("clean-rows-header", out[0] == "adoption-check-prego --check rows=2")

    # 2. digest mismatch fires
    bad = clean.replace(a_hex, ("0" if a_hex[0] != "0" else "1") + a_hex[1:])
    write(os.path.join(mock, "m-bad.txt"), bad.encode())
    rc, out = run_check(os.path.join(mock, "m-bad.txt"), mock)
    b.assert_("bad-digest-rc-1", rc == 1)
    b.assert_("bad-digest-inconsistent",
              out[-1] == "VERDICT: INCONSISTENT (matched 6, mismatched 2)")
    b.assert_("bad-digest-row-named",
              any(l.startswith("row 1 slot=alpha") and "got=" + a_hex in l
                  for l in out))

    # 3. missing file fires
    missing = ("kind=tool slot=alpha path=none.py sha256=%s adopted=x.py "
               "provenance=computed-at-freeze\n" % a_hex)
    write(os.path.join(mock, "m-missing.txt"), missing.encode())
    rc, out = run_check(os.path.join(mock, "m-missing.txt"), mock)
    b.assert_("missing-rc-1", rc == 1)
    b.assert_("missing-verdict",
              any("got=MISSING verdict=MISSING" in l for l in out))

    # 4. derive=cell-lines-nl mismatch fires
    badcells = clean.replace(cells_hex, ("0" if cells_hex[0] != "0" else "1") + cells_hex[1:])
    write(os.path.join(mock, "m-badcells.txt"), badcells.encode())
    rc, out = run_check(os.path.join(mock, "m-badcells.txt"), mock)
    b.assert_("bad-cells-rc-1", rc == 1)
    b.assert_("bad-cells-named",
              any(l.startswith("row 2 slot=cells") and "MISMATCH" in l for l in out))

    # 5. provenance digest absent fires
    rec2 = "record prose naming the token a.py but no digest\n".encode()
    write(os.path.join(mock, "rec2.txt"), rec2)
    p_absent = ("kind=tool slot=alpha path=a.py sha256=%s adopted=alpha-s1.py "
                "provenance=record-named:rec2.txt\n" % a_hex)
    write(os.path.join(mock, "m-pabsent.txt"), p_absent.encode())
    rc, out = run_check(os.path.join(mock, "m-pabsent.txt"), mock)
    b.assert_("prov-digest-absent-rc-1", rc == 1)
    b.assert_("prov-digest-absent-named",
              any("digest-verdict=ABSENT" in l and "name-verdict=PRESENT" in l
                  for l in out))

    # 6. provenance name absent fires
    rec3 = ("record prose with the digest %s but a different token b.py\n"
            % a_hex).encode()
    write(os.path.join(mock, "rec3.txt"), rec3)
    p_name = ("kind=tool slot=alpha path=a.py sha256=%s adopted=alpha-s1.py "
              "provenance=record-named:rec3.txt\n" % a_hex)
    write(os.path.join(mock, "m-pname.txt"), p_name.encode())
    rc, out = run_check(os.path.join(mock, "m-pname.txt"), mock)
    b.assert_("prov-name-absent-rc-1", rc == 1)
    b.assert_("prov-name-absent-named",
              any("digest-verdict=PRESENT" in l and "name-verdict=ABSENT" in l
                  for l in out))

    # 7. superseded digest mismatch fires
    sup_bad = clean.replace(sup_hex, ("0" if sup_hex[0] != "0" else "1") + sup_hex[1:])
    write(os.path.join(mock, "m-supbad.txt"), sup_bad.encode())
    rc, out = run_check(os.path.join(mock, "m-supbad.txt"), mock)
    b.assert_("sup-mismatch-rc-1", rc == 1)
    b.assert_("sup-mismatch-named",
              any(" superseded old.py " in l and "MISMATCH" in l for l in out))

    # 8. superseded == source refuses
    sup_self = ("kind=tool slot=alpha path=a.py sha256=%s adopted=alpha-s1.py "
                "provenance=computed-at-freeze superseded=a.py@%s\n"
                % (a_hex, a_hex))
    write(os.path.join(mock, "m-supself.txt"), sup_self.encode())
    rc, out = run_check(os.path.join(mock, "m-supself.txt"), mock)
    b.assert_("sup-self-rc-1", rc == 1)
    b.assert_("sup-self-named",
              any(" superseded a.py " in l and "MISMATCH" in l for l in out))

    # 9. relation MATCH on the 1-line diff fixture
    rel_ok = ("kind=tool slot=beta path=src2.py sha256=%s adopted=beta-s1.py "
              "provenance=computed-at-freeze relation=lines-differ-only:2:refsrc.txt\n"
              % sha256_bytes(src2))
    write(os.path.join(mock, "m-relok.txt"), rel_ok.encode())
    rc, out = run_check(os.path.join(mock, "m-relok.txt"), mock)
    b.assert_("relation-match-rc-0", rc == 0)
    b.assert_("relation-match-row",
              any("relation lines-differ-only:2 want-diff=2 got-diff=2" in l
                  and "MATCH" in l for l in out))

    # 10. relation fires on 2-line diff
    ref2 = b"L1\nL2X\nL3X\n"
    write(os.path.join(mock, "ref2.txt"), ref2)
    rel_2 = ("kind=tool slot=beta path=src2.py sha256=%s adopted=beta-s1.py "
             "provenance=computed-at-freeze relation=lines-differ-only:2:ref2.txt\n"
             % sha256_bytes(src2))
    write(os.path.join(mock, "m-rel2.txt"), rel_2.encode())
    rc, out = run_check(os.path.join(mock, "m-rel2.txt"), mock)
    b.assert_("relation-2diff-rc-1", rc == 1)
    b.assert_("relation-2diff-row",
              any("got-diff=2,3" in l and "MISMATCH" in l for l in out))

    # 11. relation fires on line-count mismatch
    ref3 = b"L1\nL2X\nL3\nL4\n"
    write(os.path.join(mock, "ref3.txt"), ref3)
    rel_3 = ("kind=tool slot=beta path=src2.py sha256=%s adopted=beta-s1.py "
             "provenance=computed-at-freeze relation=lines-differ-only:2:ref3.txt\n"
             % sha256_bytes(src2))
    write(os.path.join(mock, "m-rel3.txt"), rel_3.encode())
    rc, out = run_check(os.path.join(mock, "m-rel3.txt"), mock)
    b.assert_("relation-count-rc-1", rc == 1)
    b.assert_("relation-count-row",
              any("got-diff=LINE-COUNT" in l and "MISMATCH" in l for l in out))

    # 12. cross: duplicate slot fires (single-fault fixture: row 3's own
    # digest MATCHes so only slots-unique fires)
    dup_slot = (clean + "kind=frozen slot=alpha path=a.py sha256=%s "
                "provenance=computed-at-freeze\n" % a_hex)
    write(os.path.join(mock, "m-dupslot.txt"), dup_slot.encode())
    rc, out = run_check(os.path.join(mock, "m-dupslot.txt"), mock)
    b.assert_("dup-slot-rc-1", rc == 1)
    b.assert_("dup-slot-row",
              any(l.startswith("cross slots-unique") and "MISMATCH" in l for l in out))

    # 13. cross: duplicate adopted fires
    dup_adopted = (clean + "kind=tool slot=gamma path=src2.py sha256=%s "
                   "adopted=alpha-s1.py provenance=computed-at-freeze\n"
                   % sha256_bytes(src2))
    write(os.path.join(mock, "m-dupadopted.txt"), dup_adopted.encode())
    rc, out = run_check(os.path.join(mock, "m-dupadopted.txt"), mock)
    b.assert_("dup-adopted-rc-1", rc == 1)
    b.assert_("dup-adopted-row",
              any(l.startswith("cross adopted-unique") and "MISMATCH" in l for l in out))

    # 14. cross: duplicate tool path fires
    dup_path = (clean + "kind=tool slot=gamma path=a.py sha256=%s "
                "adopted=gamma-s1.py provenance=computed-at-freeze\n" % a_hex)
    write(os.path.join(mock, "m-duppath.txt"), dup_path.encode())
    rc, out = run_check(os.path.join(mock, "m-duppath.txt"), mock)
    b.assert_("dup-path-rc-1", rc == 1)
    b.assert_("dup-path-row",
              any(l.startswith("cross tool-paths-unique") and "MISMATCH" in l
                  for l in out))

    # parse fail-closed cases (each must raise ManifestError)
    def parse_fails(name, text):
        try:
            parse_manifest(text)
            b.assert_(name, False)
        except ManifestError:
            b.assert_(name, True)

    parse_fails("parse-unknown-key",
                "kind=tool slot=a path=a.py sha256=%s adopted=x provenance="
                "computed-at-freeze bogus=1\n" % a_hex)
    parse_fails("parse-duplicate-key",
                "kind=tool slot=a path=a.py sha256=%s sha256=%s adopted=x "
                "provenance=computed-at-freeze\n" % (a_hex, a_hex))
    parse_fails("parse-bad-hex",
                "kind=tool slot=a path=a.py sha256=abc adopted=x provenance="
                "computed-at-freeze\n")
    parse_fails("parse-missing-adopted",
                "kind=tool slot=a path=a.py sha256=%s provenance="
                "computed-at-freeze\n" % a_hex)
    parse_fails("parse-bad-provenance",
                "kind=tool slot=a path=a.py sha256=%s adopted=x provenance="
                "record-claimed:rec.txt\n" % a_hex)
    parse_fails("parse-bad-relation",
                "kind=tool slot=a path=a.py sha256=%s adopted=x provenance="
                "computed-at-freeze relation=differs:2:ref.txt\n" % a_hex)
    parse_fails("parse-bad-derive",
                "kind=frozen slot=a path=cells.txt sha256=%s provenance="
                "computed-at-freeze derive=cell-lines\n" % cells_hex)
    parse_fails("parse-unparsed-token",
                "this line has no equals\n")
    parse_fails("parse-path-escapes",
                "kind=tool slot=a path=../a.py sha256=%s adopted=x provenance="
                "computed-at-freeze\n" % a_hex)
    parse_fails("parse-bad-kind",
                "kind=widget slot=a path=a.py sha256=%s adopted=x provenance="
                "computed-at-freeze\n" % a_hex)
    parse_fails("parse-bad-slot-chars",
                "kind=tool slot=A path=a.py sha256=%s adopted=x provenance="
                "computed-at-freeze\n" % a_hex)

    # grammar positive: comments and blank lines skipped
    try:
        rows = parse_manifest("# note\n\n" + clean)
        b.assert_("parse-comments-skipped", len(rows) == 2)
    except ManifestError:
        b.assert_("parse-comments-skipped", False)

    shutil.rmtree(mock)
    return b


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--self-test":
        b = selftest(sys.argv[2])
        for line in b.lines:
            print(line)
        print("TOTAL %d assertions passed %d failed" % (b.total, b.failed))
        return 0 if b.failed == 0 else 1
    if len(sys.argv) == 4 and sys.argv[1] == "--check":
        rc, out = run_check(sys.argv[2], sys.argv[3])
        for line in out:
            print(line)
        return rc
    print("usage: --check <manifest> <root> | --self-test <scratch-dir>")
    return 2


if __name__ == "__main__":
    sys.exit(main())
