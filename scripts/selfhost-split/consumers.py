#!/usr/bin/env python3
"""Find (and optionally retarget) consumers of the split namespace that a value-copying facade cannot serve.

A facade `(def x mod/x)` is a different Var from `mod/x`.  Reads and calls are fine; WRITES are not:
`binding`, `with-redefs`, `with-redefs-fn`, `alter-var-root`, `set!` on `facade/x` never reach the code in the
module that owns x.  This tool AST-scans consumer files for exactly those write positions.

  consumers.py --report FILE_OR_DIR...  --split-report W/split/split-report.json [--ns kotoba.compiler.frontend]
  consumers.py --rewrite OUT-DIR --root ROOT FILE_OR_DIR...  ...
        writes patched COPIES (path relative to ROOT) in which each unsafe `alias/x` becomes `fe-<module>/x`
        and the module is required; used only as a verification overlay, never applied in place.
"""
import argparse, glob, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cljparse
from cljparse import walk

WRITE_HEADS = {"binding", "with-redefs", "with-redefs-fn", "alter-var-root", "set!", "with-bindings", "push-thread-bindings"}

def files_of(paths):
    for p in paths:
        if os.path.isdir(p):
            for root, _, fs in os.walk(p):
                if "node_modules" in root: continue
                for f in fs:
                    if f.endswith((".cljk", ".cljc", ".clj", ".cljs")): yield os.path.join(root, f)
        else:
            yield p

def frontend_aliases(tops, src, ns):
    al = {}
    for t in tops:
        if t.kind == "list" and t.kids and t.kids[0].text == "ns":
            for n in walk(t):
                if n.kind == "vec" and n.kids and n.kids[0].kind == "sym" and n.kids[0].text == ns:
                    for j, k in enumerate(n.kids):
                        if k.kind == "kw" and k.text == ":as": al[n.kids[j + 1].text] = n
            return al
    return al

def unsafe_uses(tops, src, aliases, ns):
    """-> list of (symbol node, alias, name, head)"""
    out = []
    prefixes = {a + "/" for a in aliases} | {ns + "/"}
    def is_target(n):
        return n.kind == "sym" and any(n.text.startswith(p) for p in prefixes)
    for t in tops:
        for n in walk(t):
            if n.kind != "list" or not n.kids or n.kids[0].kind != "sym" or n.kids[0].text not in WRITE_HEADS: continue
            head = n.kids[0].text
            region = []
            if head in ("binding", "with-redefs") and len(n.kids) > 1 and n.kids[1].kind == "vec":
                kv = n.kids[1].kids
                region = [kv[i] for i in range(0, len(kv), 2)]
            else:
                region = n.kids[1:2] if head in ("alter-var-root", "set!") else n.kids[1:]
            for r in region:
                for s in walk(r):
                    if is_target(s):
                        pre = next(p for p in prefixes if s.text.startswith(p))
                        out.append((s, pre[:-1], s.text[len(pre):], head))
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--split-report", required=True)
    ap.add_argument("--ns", default="kotoba.compiler.frontend")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--rewrite")
    ap.add_argument("--root")
    ns = ap.parse_args()
    owner = json.load(open(ns.split_report))["owner"]
    total = 0; patched = 0; unsafe_vars = {}
    for f in files_of(ns.paths):
        try: src = open(f).read()
        except Exception: continue
        if ns.ns not in src: continue
        try: tops = cljparse.parse(src)
        except Exception as e:
            print(f"SKIP {f}: {e}", file=sys.stderr); continue
        al = frontend_aliases(tops, src, ns.ns)
        uses = unsafe_uses(tops, src, set(al), ns.ns)
        if not uses: continue
        total += len(uses)
        for s, a, name, head in uses:
            unsafe_vars.setdefault(name, []).append(f"{f}:{src.count(chr(10), 0, s.start) + 1} ({head})")
        if ns.rewrite:
            edits, mods = [], {}
            for s, a, name, head in uses:
                m = owner.get(name)
                if not m: continue
                alias = "fe-" + re.sub(r"[^a-z0-9-]", "-", m)
                mods[m] = alias
                edits.append((s.start, s.end, f"{alias}/{name}"))
            for m, alias in mods.items():
                vec = next(iter(al.values()))
                edits.append((vec.end, vec.end, f"\n            [{ns.ns}.{m} :as {alias}]"))
            for st, en, r in sorted(edits, reverse=True):
                src = src[:st] + r + src[en:]
            rel = os.path.relpath(f, ns.root)
            dest = os.path.join(ns.rewrite, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            open(dest, "w").write(src)
            patched += 1
    print(f"unsafe write-position uses of the facade: {total}  ({len(unsafe_vars)} distinct vars)")
    for n, w in sorted(unsafe_vars.items()):
        print(f"  {n:<40} owner={owner.get(n)}  {'; '.join(w[:3])}")
    if ns.rewrite: print(f"patched copies written: {patched} -> {ns.rewrite}")

if __name__ == "__main__":
    main()
