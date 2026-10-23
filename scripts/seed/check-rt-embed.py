#!/usr/bin/env python3
"""Embedding check for the static runtime sources (JUN-19, seed/76 seed/77).

seed/76-x86_64-static-rt.kotoba (xs-rt-*) and seed/77-aarch64-static-rt.kotoba
(xa-rt-*) hold their whole runtime source INSIDE Kotoba string literals: one
wrapper (defn- <name> [] :string) per literal, the wrapper's defn line, an
open quote (bare on its line, or followed by the first embedded line), the
runtime text, and a closing quote before the wrapper's closing ')'. seed/76
carries four wrappers (core / start / launch / pstart), seed/77 three
(core / start / launch — platform-linked is x86_64 only, seed/78). The unity
build (scripts/seed/selfhost-bootstrap.py) concatenates the files verbatim, so
any raw '"' in an embedded region TERMINATES that string early and the rest of
the runtime is parsed as code (measured 2026-10-23: one raw-quote pair in a
comment broke the string at unity byte 670744 and the next compile failed
with E2102 'unknown symbol' at the byte after the premature close).

Invariants this script enforces per file:
  1. the quote bytes pair up into exactly one literal per wrapper defn, in the
     expected order (76: core/start/launch/pstart, 77: core/start/launch);
  2. each embedded region contains no '"' and no '\' (an escape introducer) —
     comments describe token shapes without quoting them;
  3. each embedded region is paren-balanced: depth ends at 0 with no negative
     dip, scanning ';' comments to end-of-line (the runtime has no strings);
  4. the file outside the literals stays balanced too: every literal sits in
     the body of its own (defn- <name> [] :string) and each closing quote is
     followed by that form's ')' on the same line.

Exit 0 when all hold. A paren-balance scan alone is NOT enough: comments with
quotes are fine as code and fatal as embedded text.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WRAPPERS = {
    "seed/76-x86_64-static-rt.kotoba": ["xs-rt-core", "xs-rt-start", "xs-rt-launch", "xs-rt-pstart"],
    "seed/77-aarch64-static-rt.kotoba": ["xa-rt-core", "xa-rt-start", "xa-rt-launch"],
}
PAIRS = {0x28: 0x29, 0x5B: 0x5D, 0x7B: 0x7D}
CLOSES = {0x29, 0x5D, 0x7D}
DEFN = re.compile(rb"^\((?:defn|defn-)\s+(\S+)\s+\[\]\s+:string\s*$")


def line_bounds(data, off):
    """(start, end) of the line containing off; end excludes the newline."""
    ls = data.rfind(b"\n", 0, off) + 1
    le = data.find(b"\n", off)
    return ls, len(data) if le < 0 else le


def balance(region, label, errs):
    depth = dip = 0
    i = 0
    while i < len(region):
        c = region[i]
        if c == 0x3B:  # ';' comment to end of line
            j = region.find(b"\n", i)
            i = len(region) if j < 0 else j
            continue
        if c in PAIRS:
            depth += 1
        elif c in CLOSES:
            depth -= 1
            dip = min(dip, depth)
        i += 1
    if depth != 0 or dip < 0:
        errs.append(f"{label}: paren balance depth={depth} dip={dip} (want 0 / 0)")


def check(name, data):
    """Check one runtime source's embedded literals. Returns a list of errors."""
    expected = WRAPPERS[name]
    errs = []
    quotes = [i for i, c in enumerate(data) if c == 0x22]
    if len(quotes) != 2 * len(expected):
        errs.append(
            f"{name}: expected {2 * len(expected)} quote bytes ({len(expected)} wrapper literal(s)), "
            f"found {len(quotes)} at {quotes[:12]}"
        )
        return errs  # pairing below would pair the wrong bytes
    for k in range(len(expected)):
        open_q, close_q = quotes[2 * k], quotes[2 * k + 1]
        where = f"{name} wrapper {k + 1}/{len(expected)} ({expected[k]})"
        if close_q < open_q:
            errs.append(f"{where}: close quote {close_q} precedes open quote {open_q}")
            continue
        # invariant 4a: the open quote starts its line, after a bare defn line
        ls, le = line_bounds(data, open_q)
        if data[ls:open_q].strip():
            errs.append(f"{where}: open quote at {open_q} is not the first byte on its line")
        prev = data[:ls].rstrip()
        pl = prev.rfind(b"\n") + 1
        m = DEFN.match(prev[pl:])
        if not m:
            errs.append(f"{where}: line before the open quote is not a (defn- <name> [] :string): {prev[pl:][:60]!r}")
        elif m.group(1).decode() != expected[k]:
            errs.append(f"{where}: literal body belongs to {m.group(1).decode()!r}, want {expected[k]!r}")
        # invariant 4b: the close quote ends its line except for the form's ')'
        cl, ce = line_bounds(data, close_q)
        if data[cl:close_q].strip():
            errs.append(f"{where}: close quote at {close_q} is not the first byte on its line")
        tail = data[close_q + 1:ce]
        if tail.strip() != b")":
            errs.append(f"{where}: close quote at {close_q} is not followed by the wrapper's ')': {tail[:20]!r}")
        # invariant 2: no raw quote/backslash inside the embedded region
        region = data[open_q + 1:close_q]
        for label, b in (("quote", 0x22), ("backslash", 0x5C)):
            hits = [i for i, c in enumerate(region) if c == b]
            if hits:
                errs.append(f"{where}: {len(hits)} raw {label} byte(s) in the embedded text at {hits[:8]}")
        # invariant 3: the embedded region is paren-balanced
        balance(region, where, errs)
    # invariant 4c: the file outside the literals is balanced as code
    outside = bytearray()
    i = 0
    in_lit = False
    while i < len(data):
        c = data[i]
        if c == 0x22:
            in_lit = not in_lit
            i += 1
            continue
        if not in_lit:
            outside.append(c)
        i += 1
    if in_lit:
        errs.append(f"{name}: unbalanced string literal at end of file")
    balance(bytes(outside), f"{name} outside literals", errs)
    return errs


def main():
    errs = []
    for name in WRAPPERS:
        errs += check(name, (ROOT / name).read_bytes())
    for e in errs:
        print("FAIL", e)
    if errs:
        return 1
    for name, wrappers in WRAPPERS.items():
        print("OK", name, ":", " ".join(wrappers), "- one literal each, no raw quote/backslash, paren-balanced")
    return 0


if __name__ == "__main__":
    sys.exit(main())
