#!/usr/bin/env python3
"""Embedding check for the static runtime sources (JUN-19, seed/76 seed/77).

seed/76-x86_64-static-rt.kotoba (xs-rt-src) and seed/77-aarch64-static-rt.kotoba
(xa-rt-src) hold their whole runtime source INSIDE a Kotoba string literal:
the wrapper (defn- xs-rt-src [] :string) is followed by a line that is a bare
quote, the runtime text, and a closing quote before the final ')'. The unity
build (scripts/seed/selfhost-bootstrap.py) concatenates the files verbatim, so
any raw '"' in the embedded text TERMINATES the string early and the rest of
the runtime is parsed as code (measured 2026-10-23: one raw-quote pair in a
comment broke the string at unity byte 670744 and the next compile failed
with E2102 'unknown symbol' at the byte after the premature close).

Invariants this script enforces per file:
  1. exactly two '"' bytes: the wrapper's open and close;
  2. the embedded region between them contains no '"' and no '\\' (an escape
     introducer) — comments describe token shapes without quoting them;
  3. the embedded region is paren-balanced: depth ends at 0 with no negative
     dip, scanning ';' comments to end-of-line (the runtime has no strings).

Exit 0 when all hold. A paren-balance scan alone is NOT enough: comments with
quotes are fine as code and fatal as embedded text.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RT = ["seed/76-x86_64-static-rt.kotoba", "seed/77-aarch64-static-rt.kotoba"]
PAIRS = {0x28: 0x29, 0x5B: 0x5D, 0x7B: 0x7D}


def check(path):
    data = (ROOT / path).read_bytes()
    quotes = [i for i, c in enumerate(data) if c == 0x22]
    errs = []
    if len(quotes) != 2:
        errs.append(f"{path}: expected exactly 2 quote bytes (the wrapper's), found {len(quotes)} at {quotes}")
        # still scan what we can below around the first quote
    open_q = quotes[0] if quotes else None
    close_q = quotes[-1] if len(quotes) >= 2 else None
    if open_q is not None:
        ls = data.rfind(b"\n", 0, open_q) + 1
        if data[ls:open_q].strip():
            errs.append(f"{path}: wrapper quote at {open_q} is not alone on its line")
    if close_q is not None:
        tail = data[close_q + 1:]
        if tail.strip() not in (b")", b""):
            errs.append(f"{path}: wrapper close at {close_q} is not at end of form: {tail[:20]!r}")
    if open_q is not None and close_q is not None and close_q > open_q:
        region = data[open_q + 1:close_q]
        for name, b in (('"', 0x22), ("\\", 0x5C)):
            hits = [i for i, c in enumerate(region) if c == b]
            if hits:
                errs.append(f"{path}: {len(hits)} raw {name} byte(s) in the embedded runtime text at {hits[:8]}")
        depth, dip = 0, 0
        i = 0
        while i < len(region):
            c = region[i]
            if c == 0x3B:  # ';' comment to end of line
                j = region.find(b"\n", i)
                i = len(region) if j < 0 else j
                continue
            if c in PAIRS:
                depth += 1
            elif c in (0x29, 0x5D, 0x7D):
                depth -= 1
                dip = min(dip, depth)
            i += 1
        if depth != 0 or dip < 0:
            errs.append(f"{path}: embedded paren balance depth={depth} dip={dip} (want 0 / 0)")
    return errs


def main():
    errs = [e for p in RT for e in check(p)]
    for e in errs:
        print("FAIL", e)
    if errs:
        return 1
    print("OK", ", ".join(RT), ": wrapper quotes only, no raw quote/backslash, paren-balanced")
    return 0


if __name__ == "__main__":
    sys.exit(main())
