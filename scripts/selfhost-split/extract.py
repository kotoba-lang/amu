#!/usr/bin/env python3
"""selfhost-split step 2: cut a big namespace into modules according to a partition, plus a facade.

  extract.py SRC.cljk PARTITION.json OUT-DIR [--ns kotoba.compiler.frontend]

Writes, under OUT-DIR (a SCRATCH directory, never the repo src):
  <ns path>.cljk                     thin facade: same ns name + :kotoba/export attr map, re-exports every name
  <ns path>/<module>.cljk            one file per module: ns + :require (dependency order, only what is used),
                                     (declare ...) for forward references inside the module, then the original
                                     forms byte-for-byte (docstrings and the comments before each form preserved)
Only two textual edits are made to a form: `defn-` -> `defn` and `^:private` dropped (cross-module access).
Reader conditionals are respected: a name that exists on only some platforms is :refer'd / re-exported only there.
"""
import argparse, collections, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cljparse
from cljparse import strip_meta, meta_of, walk
import analyze as an
import sourcegraph as sg

def ident(s):
    return re.sub(r"[^A-Za-z0-9-]", "-", s)

def plat_wrap(keys, body_for_branch, nothing="nil"):
    """Reader-conditional expression for 'exists under feature keys' (None in keys = unconditional)."""
    if None in keys or {":kotoba", ":default"} <= set(keys):
        return body_for_branch
    return None

def parse_ns(a, src):
    ns = next(c for c in a.chunks if c.is_ns)
    kids = ns.node.kids            # (ns name [doc] [attr-map] clauses...)
    info = {"name": kids[1].text, "doc": None, "attr": None, "requires": [], "other": [], "node": ns.node}
    i = 2
    if kids[i].kind == "str": info["doc"] = src[kids[i].start:kids[i].end]; i += 1
    if kids[i].kind in ("map", "nsmap"): info["attr"] = src[kids[i].start:kids[i].end]; i += 1
    for k in kids[i:]:
        t = strip_meta(k)
        if t.kind == "list" and t.kids and t.kids[0].kind == "kw" and t.kids[0].text == ":require":
            info["requires"] = t.kids[1:]
        else:
            info["other"].append(src[k.start:k.end])
    return info

def spec_alias(vec, src):
    """alias (or ns name) of one [ns :as x ...] require spec"""
    ks = vec.kids
    for j, k in enumerate(ks):
        if k.kind == "kw" and k.text == ":as" and j + 1 < len(ks): return ks[j + 1].text
    return ks[0].text

def used_aliases(chunks):
    u = set()
    for c in chunks:
        for n in walk(c.node):
            if n.kind == "sym" and "/" in n.text and n.text != "/":
                u.add(n.text.split("/")[0].lstrip("'`~@#^"))
    return u

def build_requires(info, src, used):
    """Filter the ORIGINAL require specs (including their #? wrappers) down to the aliases a module uses."""
    out = []
    def keep(vec): return spec_alias(vec, src) in used
    for e in info["requires"]:
        t = strip_meta(e)
        if t.kind == "vec":
            if keep(t): out.append(src[e.start:e.end])
        elif t.kind in ("rc", "rcs"):
            branches = []
            for i in range(0, len(t.kids) - 1, 2):
                key, val = t.kids[i], t.kids[i + 1]
                specs = [x for x in (val.kids if val.kind == "vec" else [val]) if x.kind == "vec" and keep(x)]
                if specs: branches.append(key.text + " [" + " ".join(src[x.start:x.end] for x in specs) + "]")
            if branches:
                out.append(("#?@(" if t.kind == "rcs" else "#?(") + " ".join(branches) + ")")
    return out

def chunk_edits(c, src):
    """textual edits making a form importable from another module: defn- -> defn, drop ^:private."""
    ed = []
    for name, ds in c.defnodes.items():
        for d in ds:
            h = d.kids[0]
            if h.text == "defn-": ed.append((h.start, h.end, "defn"))
            nm = d.kids[1]
            while nm.kind == "meta":
                m = nm.kids[0]
                if m.kind == "kw" and m.text == ":private":
                    ed.append((nm.start, nm.kids[1].start, ""))
                nm = nm.kids[1]
    return ed

def apply_edits(text, base, edits):
    for s, e, r in sorted(edits, reverse=True):
        text = text[:s - base] + r + text[e - base:]
    return text

def keyset_expr(names_plats, make):
    """Group (name, platkeys) into reader-conditional expressions. `make(names)` -> text for those names."""
    always, groups = [], collections.defaultdict(list)
    for n, ps in names_plats:
        if None in ps or {":kotoba", ":default"} <= set(ps): always.append(n)
        else: groups[frozenset(ps)].append(n)
    return always, groups

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("partition"); ap.add_argument("out")
    ap.add_argument("--ns", default="kotoba.compiler.frontend")
    ns = ap.parse_args()
    src = open(ns.src).read()
    a, adj = an.build(src)
    part = json.load(open(ns.partition))
    assign = {int(k): v for k, v in part["assign"].items()}
    order = part["order"]
    info = parse_ns(a, src)
    base_dir = os.path.join(ns.out, *[p.replace("-", "_") for p in ns.ns.split(".")[:-1]])
    mod_dir = os.path.join(ns.out, *[p.replace("-", "_") for p in ns.ns.split(".")])
    os.makedirs(mod_dir, exist_ok=True)
    modns = lambda m: f"{ns.ns}.{ident(m)}"
    mods = {m: [] for m in order}
    for c in a.chunks:
        if c.idx in assign and c.names: mods[assign[c.idx]].append(c)
    owner = {}                       # name -> module
    for m, cs in mods.items():
        for c in cs:
            for n in c.names: owner[n] = m
    # carry comments of dropped (declare) forms to the next kept form of the same module
    trivia = {}
    pend = ""
    for c in a.chunks:
        lead = src[c.lead_start:c.start]
        if c.is_ns: pend = ""; continue
        if c.idx not in assign or not c.names:      # (declare ...) forms are regenerated per module
            if lead.strip(): pend += lead
            continue
        trivia[c.idx] = pend + lead if pend.strip() else lead
        pend = ""
    stats = {}
    schema_clause = [o for o in info["other"] if ":schemas" in o]
    schema_keys = set(re.findall(r":([a-z]+)/", " ".join(schema_clause)))
    for m, cs in mods.items():
        names_here = {n for c in cs for n in c.names}
        pos = {}
        for i, c in enumerate(cs):
            for n in c.names: pos.setdefault(n, i)
        # cross-module deps
        need = collections.defaultdict(dict)       # dep module -> {name: platkeys}
        for c in cs:
            for r in c.refs:
                o = owner.get(r)
                if o and o != m:
                    ps = set()
                    for ci in a.def_chunks[r]:
                        for p in a.chunks[ci].plats.get(r, ()): ps.add(p)
                    need[o][r] = ps
        # forward references inside the module need a declare
        fwd, dyn = [], set()
        for i, c in enumerate(cs):
            for r in c.refs:
                if r in names_here and pos[r] >= i and r not in c.names and r not in fwd:
                    fwd.append(r)
        for c in cs:
            for n in c.names:
                if c.dynamic.get(n): dyn.add(n)
        used = used_aliases(cs)
        reqs = build_requires(info, src, used)
        rq = list(reqs)
        for dep in sorted(need, key=lambda d: order.index(d)):
            names = sorted(need[dep].items())
            always, groups = keyset_expr([(n, p) for n, p in names], None)
            items = list(always)
            for ks, ns_ in groups.items():
                keys = sorted(k for k in ks if k)
                body = []
                for k in keys:
                    body.append(f"{k} [{' '.join(ns_)}]")
                if ":kotoba" not in keys and ":default" in keys: body.insert(0, ":kotoba []")
                items.append("#?@(" + " ".join(body) + ")")
            rq.append(f"[{modns(dep)} :refer [{' '.join(items)}]]")
        head = [f"(ns {modns(m)}"]
        n_forms = len(cs); n_lines = sum(c.text.count(chr(10)) + 1 for c in cs)
        head.append(f'  "Module `{m}` of {ns.ns}, cut from the original namespace by scripts/selfhost-split '
                    f'({n_forms} forms, {n_lines} lines). Depends on: {", ".join(sorted(need, key=lambda d: order.index(d))) or "nothing in this split"}."')
        if rq: head.append("  (:require " + ("\n            ".join(rq)) + ")")
        text_all = " ".join(c.text for c in cs)
        for sc in schema_clause:
            if any(f":{k}/" in text_all for k in schema_keys): head.append("  " + sc)
        out = "\n".join(head) + ")\n"
        if fwd or dyn:
            ds = []
            for r in fwd:
                ds.append(("^:dynamic " if r in dyn else "") + r)
            out += "\n;; forward references inside this module (the cut keeps the original form order)\n(declare " + " ".join(ds) + ")\n"
        for c in cs:
            lead = trivia.get(c.idx, "")
            body = apply_edits(c.text, c.start, chunk_edits(c, src))
            out += lead + body
        out += "\n"
        path = os.path.join(mod_dir, ident(m).replace("-", "_") + ".cljk")
        open(path, "w").write(out)
        stats[m] = {"forms": n_forms, "lines": n_lines, "declares": len(fwd), "requires": sorted(need)}
    # ---- facade ------------------------------------------------------------------
    fh = [f"(ns {ns.ns}"]
    if info["doc"]: fh.append("  " + info["doc"])
    if info["attr"]: fh.append("  " + info["attr"])
    fh.append("  (:require " + "\n            ".join(f"[{modns(m)} :as {ident(m)}]" for m in order) + ")")
    for o in info["other"]:
        if ":schemas" in o: fh.append("  " + o)
    fout = "\n".join(fh) + ")\n\n;; Facade over the split modules (scripts/selfhost-split). Each name is re-exported as a value;\n" \
           ";; a ^:dynamic var is a SNAPSHOT here: rebind it through its owning module (see split-report.edn).\n"
    rows = []
    for c in a.chunks:
        for n in c.names:
            if owner.get(n) is None: continue
        pass
    seen = set()
    for c in a.chunks:
        for n in c.names:
            if n in seen or n not in owner: continue
            seen.add(n)
            ps = set()
            for ci in a.def_chunks[n]:
                ps |= a.chunks[ci].plats.get(n, set())
            private = all(a.chunks[ci].private.get(n) for ci in a.def_chunks[n])
            dynamic = any(a.chunks[ci].dynamic.get(n) for ci in a.def_chunks[n])
            meta = ("^:dynamic " if dynamic else "") + ("^:private " if private else "")
            form = f"(def {meta}{n} {ident(owner[n])}/{n})"
            if None in ps or {":kotoba", ":default"} <= ps: rows.append(form)
            else:
                branches = []
                for k in sorted(k for k in ps if k):
                    branches.append(f"{k} {form}")
                if ":kotoba" not in ps and ":default" in ps: branches.insert(0, ":kotoba nil")
                rows.append("#?(" + " ".join(branches) + ")")
    fout += "\n".join(rows) + "\n"
    open(os.path.join(base_dir, ns.ns.split(".")[-1].replace("-", "_") + ".cljk"), "w").write(fout)
    json.dump({"modules": stats, "owner": owner}, open(os.path.join(ns.out, "split-report.json"), "w"), indent=1)
    print(f"wrote {len(mods)} modules + facade ({len(rows)} re-exports) under {ns.out}")

if __name__ == "__main__":
    main()
