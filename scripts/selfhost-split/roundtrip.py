#!/usr/bin/env python3
"""Structural check of an extraction: every original top-level form (except ns and (declare ..)) occurs in
exactly one module, byte-identical apart from the two allowed edits (defn- -> defn, ^:private dropped),
and the facade re-exports every defined name.   roundtrip.py SRC.cljk SPLIT-DIR [--ns kotoba.compiler.frontend]"""
import argparse, collections, glob, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cljparse, sourcegraph as sg

def norm(t):
    t = re.sub(r"\(defn- ", "(defn ", t)
    t = re.sub(r"\^:private\s+", "", t)
    return t

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("src"); ap.add_argument("split"); ap.add_argument("--ns", default="kotoba.compiler.frontend")
    ns = ap.parse_args()
    a = sg.Analyzer(open(ns.src).read())
    want = collections.Counter(norm(c.text) for c in a.chunks if not c.is_ns and c.names)
    d = os.path.join(ns.split, *[p.replace("-", "_") for p in ns.ns.split(".")])
    got = collections.Counter(); files = sorted(glob.glob(d + "/*.cljk"))
    for f in files:
        mod = sg.Analyzer(open(f).read())
        for c in mod.chunks:
            if not c.is_ns and c.names: got[norm(c.text)] += 1
    facade = sg.Analyzer(open(d + ".cljk").read())
    exported = {n for c in facade.chunks for n in c.names}
    defined = {n for c in a.chunks for n in c.names}
    ok = want == got and exported == defined
    print(f"modules={len(files)} forms: original={sum(want.values())} split={sum(got.values())} "
          f"missing={sum((want - got).values())} extra={sum((got - want).values())} "
          f"facade-names={len(exported)}/{len(defined)}")
    print("ROUNDTRIP-OK" if ok else "ROUNDTRIP-FAILED")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
