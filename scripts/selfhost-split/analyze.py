#!/usr/bin/env python3
"""selfhost-split step 1: dependency graph + partition proposal for a big .cljk namespace.

  analyze.py graph     SRC.cljk  OUT-DIR     -> graph.edn (nodes, edges, SCCs, dynamic vars)
  analyze.py partition SRC.cljk  OUT-DIR [--modules N] -> partition.edn (+ graph.edn)

Everything is derived from the AST (cljparse/sourcegraph): top-level forms are the nodes, every
reader-conditional branch is seen, references are scope-aware (let/fn/loop/destructuring shadowing).
"""
import argparse, json, os, re, sys, collections, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sourcegraph as sg
from edn import dumps, Sym

# ---------------------------------------------------------------------------- graph
def build(src):
    a = sg.Analyzer(src)
    n = len(a.chunks)
    adj = [dict() for _ in range(n)]   # u -> {v: weight(distinct names)}
    for c in a.chunks:
        for r in c.refs:
            for t in a.def_chunks.get(r, []):
                if t != c.idx:
                    adj[c.idx][t] = adj[c.idx].get(t, 0) + 1
    for name, idxs in a.def_chunks.items():          # one name defined by several chunks => keep together
        for i in idxs:
            for j in idxs:
                if i != j: adj[i][j] = adj[i].get(j, 0) + 1
    return a, adj

def tarjan(n, adj, skip):
    sys.setrecursionlimit(20000)
    idx, low, st, on, comps, cnt = {}, {}, [], set(), [], [0]
    def go(v):
        idx[v] = low[v] = cnt[0]; cnt[0] += 1; st.append(v); on.add(v)
        for w in adj[v]:
            if w not in idx:
                go(w); low[v] = min(low[v], low[w])
            elif w in on:
                low[v] = min(low[v], idx[w])
        if low[v] == idx[v]:
            comp = []
            while True:
                w = st.pop(); on.discard(w); comp.append(w)
                if w == v: break
            comps.append(sorted(comp))
    for v in range(n):
        if v not in idx and v not in skip:
            go(v)
    return comps   # reverse topological: dependencies first

def chunk_label(c):
    if c.names: return c.names[0]
    if c.declares: return "declare:" + c.declares[0]
    return "ns" if c.is_ns else f"form#{c.idx}"

def graph_edn(a, adj, comps, src):
    nodes = []
    for c in a.chunks:
        nodes.append({
            "id": c.idx, "names": [Sym(f'"{x}"')[0:0] or x for x in c.names] if False else list(c.names),
            "head": sorted(set(c.kinds.values())), "line": sg.line_of(src, c.start),
            "lines": c.text.count("\n") + 1,
            "private": any(c.private.values()) if c.names else False,
            "dynamic": [x for x in c.names if c.dynamic.get(x)],
            "declares": c.declares,
            "kotoba-branch": bool(getattr(c, "has_kotoba_branch", False)),
            "binds-dynamic": sorted(c.binds),
        })
    edges = [[u, v, w] for u in range(len(adj)) for v, w in sorted(adj[u].items())]
    scc = [c for c in comps if len(c) > 1]
    dyn = {}
    for c in a.chunks:
        for x in c.names:
            if c.dynamic.get(x):
                dyn[x] = {"defined-in": c.idx,
                          "read-by": sorted(d.idx for d in a.chunks if x in d.refs and x not in d.binds),
                          "bound-by": sorted(d.idx for d in a.chunks if x in d.binds)}
    return {"source-forms": len(a.chunks), "names": len(a.top_names), "edges": len(edges),
            "nodes": nodes, "edge-list": edges,
            "sccs": [{"size": len(c), "lines": sum(a.chunks[i].text.count("\n") + 1 for i in c), "members": c} for c in scc],
            "dynamic-vars": dyn}

# ---------------------------------------------------------------------------- clustering (Louvain, stdlib)
def louvain(nodes, wedges, resolution=1.0, seed=7):
    """nodes: list; wedges: {(u,v): w} undirected. Returns {node: community}."""
    rnd = random.Random(seed)
    comm = {v: v for v in nodes}
    nbr = collections.defaultdict(dict)
    for (u, v), w in wedges.items():
        if u == v: continue
        nbr[u][v] = nbr[u].get(v, 0) + w
        nbr[v][u] = nbr[v].get(u, 0) + w
    deg = {v: sum(nbr[v].values()) for v in nodes}
    m2 = sum(deg.values()) or 1.0
    # level-0 only local moving followed by aggregation passes
    cur_nodes = list(nodes); cur_nbr = nbr; cur_deg = deg
    member = {v: [v] for v in nodes}
    while True:
        c = {v: v for v in cur_nodes}
        tot = {v: cur_deg[v] for v in cur_nodes}
        improved = True; moved_any = False
        while improved:
            improved = False
            order = cur_nodes[:]; rnd.shuffle(order)
            for v in order:
                cv = c[v]
                links = collections.defaultdict(float)
                for u, w in cur_nbr[v].items():
                    links[c[u]] += w
                tot[cv] -= cur_deg[v]
                best, bestgain = cv, links.get(cv, 0) - resolution * tot[cv] * cur_deg[v] / m2
                for cc, w in links.items():
                    gain = w - resolution * tot[cc] * cur_deg[v] / m2
                    if gain > bestgain + 1e-12:
                        best, bestgain = cc, gain
                tot[best] += cur_deg[v]
                if best != cv:
                    c[v] = best; improved = True; moved_any = True
        if not moved_any:
            break
        groups = collections.defaultdict(list)
        for v in cur_nodes: groups[c[v]].append(v)
        new_member = {}
        for g, vs in groups.items():
            new_member[g] = [x for v in vs for x in member[v]]
        newnbr = collections.defaultdict(dict)
        for v in cur_nodes:
            for u, w in cur_nbr[v].items():
                a_, b_ = c[v], c[u]
                newnbr[a_][b_] = newnbr[a_].get(b_, 0) + w
        cur_nodes = list(groups); cur_nbr = newnbr
        cur_deg = {g: sum(newnbr[g].values()) for g in cur_nodes}
        member = new_member
        if len(cur_nodes) == 1: break
    out = {}
    for g, vs in member.items():
        for v in vs: out[v] = g
    return out

# ---------------------------------------------------------------------------- partition
def token_of(c):
    """The author's own 'pass' vocabulary: the leading word of the form's name."""
    if not c.names:
        return None
    t = c.names[0].lstrip("*").lstrip("-")
    t = t.split("-")[0].rstrip("?!*")
    return t or c.names[0]

def condense(a, adj, comps):
    comp_of = {}
    for ci, comp in enumerate(comps):
        for v in comp: comp_of[v] = ci
    cadj = [collections.defaultdict(int) for _ in comps]
    for c in a.chunks:
        if c.is_ns: continue
        for v, w in adj[c.idx].items():
            if comp_of[c.idx] != comp_of[v]:
                cadj[comp_of[c.idx]][comp_of[v]] += w
    return comp_of, cadj

def layerize(a, comps, cadj, modof, M):
    """Order modules (dependencies first, min back-edge weight), then make every edge point
    downward-or-same by pushing offending atoms UP, then give atoms back DOWN to their module."""
    w = [[0] * M for _ in range(M)]
    for u in modof:
        for v, ww in cadj[u].items():
            if modof[u] != modof[v]: w[modof[u]][modof[v]] += ww      # module u depends on module v
    order = sorted(range(M), key=lambda m: sum(w[m]) - sum(w[x][m] for x in range(M)))
    def back(o):
        pos = {m: i for i, m in enumerate(o)}
        return sum(w[x][y] for x in range(M) for y in range(M) if x != y and pos[x] < pos[y])
    improved = True
    while improved:
        improved = False
        for i in range(M):
            for j in range(M):
                if i == j: continue
                t = order[:]; m = t.pop(i); t.insert(j, m)
                if back(t) < back(order): order = t; improved = True
    rank = {m: i for i, m in enumerate(order)}
    layer = {x: rank[modof[x]] for x in modof}
    moved = set()
    changed = True
    while changed:
        changed = False
        for u in range(len(comps)):                 # comps: dependencies first
            if u not in layer: continue
            need = max([layer[v] for v in cadj[u]] + [layer[u]])
            if need > layer[u]:
                layer[u] = need; moved.add(u); changed = True
    dependents = collections.defaultdict(list)
    for u in modof:
        for v in cadj[u]: dependents[v].append(u)
    changed = True
    while changed:
        changed = False
        for u in reversed(range(len(comps))):
            if u not in layer or not dependents[u]: continue
            hi = min(layer[d] for d in dependents[u])
            lo = max([layer[v] for v in cadj[u]] + [0])
            tgt = max(lo, min(rank[modof[u]], hi))
            if tgt != layer[u] and lo <= tgt <= hi:
                layer[u] = tgt; changed = True
    return layer, rank, moved

def closures(cadj):
    n = len(cadj)
    cl = [0] * n
    for x in range(n):          # atoms come dependencies-first
        m = 1 << x
        for v in cadj[x]: m |= cl[v]
        cl[x] = m
    return cl

def bits(m):
    i = 0
    while m:
        if m & 1: yield i
        m >>= 1; i += 1

def find_driver(a, comps, cadj, lines, cl, min_root):
    """The pass driver = the largest-closure atom that directly calls >= 3 big, distinct passes."""
    best = None
    for x in range(len(comps)):
        big = [v for v in cadj[x] if sum(lines[y] for y in bits(cl[v])) >= min_root]
        if len(big) >= 3 and (best is None or len(cl[x].__str__()) > 0 and bin(cl[x]).count("1") > bin(cl[best]).count("1")):
            best = x
    return best

def partition(a, adj, comps, src, target, driver_name=None, min_root=100, cap_factor=1.7, min_lines=450):
    """Pass-ownership partition.

    1. atoms = SCCs of the reference graph (never split);
    2. DRIVER = the analyzer that calls the passes; ROOTS = its direct callees (the pass entry points);
    3. each atom gets its OWNER SET = the roots whose transitive closure contains it;
       the distinct owner sets are the initial modules (dependencies always have a superset
       owner set, so the quotient graph is a DAG by construction);
    4. modules are merged greedily (strongest connection, size-capped) while the quotient stays acyclic,
       until `target` remain.
    """
    comp_of, cadj = condense(a, adj, comps)
    n = len(comps)
    lines = [sum(a.chunks[v].text.count("\n") + 1 for v in comp) for comp in comps]
    is_ns = [a.chunks[comp[0]].is_ns for comp in comps]
    cl = closures(cadj)
    drv = None
    if driver_name:
        for x, comp in enumerate(comps):
            if any(driver_name in a.chunks[v].names for v in comp): drv = x
    else:
        drv = find_driver(a, comps, cadj, lines, cl, min_root)
    roots = [v for v in cadj[drv] if sum(lines[y] for y in bits(cl[v])) >= min_root]
    ancestors = {x for x in range(n) if (cl[x] >> drv) & 1}          # driver, analyze, lint ...
    mask = [0] * n
    for ri, r in enumerate(roots):
        for y in bits(cl[r]): mask[y] |= 1 << ri
    DR = 1 << len(roots)
    for x in range(n):
        if is_ns[x]: continue
        if x in ancestors: mask[x] = DR
        elif mask[x] == 0: mask[x] = DR | 0         # reached only from the driver itself
    live = [x for x in range(n) if not is_ns[x]]
    # initial modules
    key2mod, modof = {}, {}
    for x in live:
        modof[x] = key2mod.setdefault(mask[x], len(key2mod))
    members = collections.defaultdict(set)
    for x, m in modof.items(): members[m].add(x)
    total = sum(lines[x] for x in live)
    cap = cap_factor * total / target
    def msize(m): return sum(lines[x] for x in members[m])
    def edges_between():
        w = collections.defaultdict(int)       # (a,b) a depends on b
        for x in live:
            for v, ww in cadj[x].items():
                if modof[x] != modof[v]: w[(modof[x], modof[v])] += ww
        return w
    def reaches(w, src_m, dst_m, skip_direct):
        seen, st = {src_m}, [src_m]
        out = collections.defaultdict(list)
        for (p, q) in w: out[p].append(q)
        while st:
            u = st.pop()
            for v in out[u]:
                if u == src_m and v == dst_m and skip_direct: continue
                if v == dst_m: return True
                if v not in seen: seen.add(v); st.append(v)
        return False
    initial = len(members)
    def tokvec(m):
        v = collections.Counter()
        for x in members[m]:
            for c in comps[x]:
                t = token_of(a.chunks[c])
                if t: v[t] += a.chunks[c].text.count("\n") + 1
        return v
    def cosine(u, v):
        d = sum(u[k] * v[k] for k in u if k in v)
        nu = sum(x * x for x in u.values()) ** .5; nv = sum(x * x for x in v.values()) ** .5
        return d / (nu * nv) if nu and nv else 0.0
    while True:
        small = [m for m in members if msize(m) < min_lines]
        if len(members) <= target and not small: break
        if len(members) <= 2: break
        w = edges_between()
        pair = collections.defaultdict(int)
        for (p, q), ww in w.items(): pair[(min(p, q), max(p, q))] += ww
        cands = []
        for (p, q), ww in pair.items():
            sz = msize(p) + msize(q)
            score = ww / (min(msize(p), msize(q)) + 20) * (1 + 3 * cosine(tokvec(p), tokvec(q)))
            tiny = min(msize(p), msize(q)) < min_lines
            cands.append((not tiny, sz > cap, -score, p, q))
        cands.sort()
        done = False
        for _tiny, over, ns_, p, q in cands:
            # acyclic only if no path p->...->q (or q->...->p) other than the direct edge
            if reaches(w, p, q, True) or reaches(w, q, p, True): continue
            for x in members[q]: modof[x] = p
            members[p] |= members.pop(q)
            done = True
            break
        if not done:
            # unconnected small modules: fold into the neighbour in file order
            ms = sorted(members, key=msize)
            p, q = ms[0], ms[1]
            for x in members[q]: modof[x] = p
            members[p] |= members.pop(q)
    # dependencies first: topological order of the quotient
    w = edges_between()
    deps = collections.defaultdict(set)
    for (p, q) in w: deps[p].add(q)
    order, seen = [], set()
    def topo(m):
        if m in seen: return
        seen.add(m)
        for d in sorted(deps[m], key=msize): topo(d)
        order.append(m)
    for m in sorted(members, key=msize, reverse=True): topo(m)
    rank = {m: i for i, m in enumerate(order)}
    chunk_mod = {}
    for x, comp in enumerate(comps):
        if x in modof:
            for v in comp:
                if a.chunks[v].names: chunk_mod[v] = rank[modof[x]]     # (declare ...) forms are not placed
    info = {"driver": [a.chunks[v].names[0] for v in comps[drv]][:3],
            "roots": [[a.chunks[v].names[0] for v in comps[r]][0] for r in roots],
            "initial-modules": initial}
    return chunk_mod, len(order), info

def name_modules(a, chunk_mod, k):
    """Name = most characteristic leading tokens of the member names (weighted by lines)."""
    byname = collections.defaultdict(collections.Counter)
    tot = collections.Counter()
    for c in a.chunks:
        if c.idx not in chunk_mod or not c.names: continue
        tok = c.names[0].strip("*").lstrip("-").split("-")[0]
        byname[chunk_mod[c.idx]][tok] += c.text.count("\n") + 1
        tot[tok] += c.text.count("\n") + 1
    names = {}
    used = set()
    for m in range(k):
        cands = sorted(byname[m].items(), key=lambda kv: -kv[1] * kv[1] / (tot[kv[0]] or 1))
        nm = None
        for tok, _ in cands:
            if tok not in used and len(tok) > 2: nm = tok; break
        nm = nm or f"part{m}"
        used.add(nm)
        names[m] = nm
    return names

def partition_edn(a, adj, chunk_mod, k, names, src, moves):
    mods = []
    lines_total = 0
    for m in range(k):
        cs = [c for c in a.chunks if chunk_mod.get(c.idx) == m]
        ln = sum(c.text.count("\n") + 1 for c in cs)
        lines_total += ln
        deps = collections.Counter()
        for c in cs:
            for v in adj[c.idx]:
                if chunk_mod.get(v) is not None and chunk_mod[v] != m:
                    deps[names[chunk_mod[v]]] += 1
        mods.append({"module": names[m], "order": m, "forms": len(cs), "lines": ln,
                     "defs": sum(len(c.names) for c in cs), "requires": dict(sorted(deps.items(), key=lambda kv: -kv[1])),
                     "chunks": [c.idx for c in cs]})
    cross = sum(1 for u in chunk_mod for v in adj[u] if v in chunk_mod and chunk_mod[u] != chunk_mod[v])
    back = sum(1 for u in chunk_mod for v in adj[u] if v in chunk_mod and chunk_mod[v] > chunk_mod[u])
    total_edges = sum(len(adj[u]) for u in chunk_mod)
    cyc = [[names[chunk_mod[u]], chunk_label(a.chunks[u]), names[chunk_mod[v]], chunk_label(a.chunks[v])]
           for u in chunk_mod for v in adj[u] if v in chunk_mod and chunk_mod[v] > chunk_mod[u]]
    return {"modules": mods, "edges-total": total_edges, "edges-cross-module": cross,
            "edges-backward-blocking": back, "blocking-edges": cyc, "forms": len(chunk_mod), "lines": lines_total,
            "atoms-pushed": moves}

def scc_report(a, adj, comps, chunk_mod, names):
    """Cycles that bound how fine the split can get, and the cheapest late-binding set that would open the big one."""
    rep = []
    lines = lambda m: sum(a.chunks[v].text.count("\n") + 1 for v in m)
    for comp in sorted((c for c in comps if len(c) > 1), key=lambda c: -lines(c)):
        rep.append({"size": len(comp), "lines": lines(comp),
                    "module": names[chunk_mod[comp[0]]] if comp[0] in chunk_mod else None,
                    "forms": [chunk_label(a.chunks[v]) for v in comp][:8]})
    big = max((c for c in comps if len(c) > 1), key=lines)
    members = set(big)
    cut = []                        # forms whose INCOMING intra-cycle edges would become late-bound calls
    work = {u: {v: 1 for v in adj[u] if v in members} for u in members}
    steps = []
    for _ in range(40):
        sub = tarjan(len(adj), [work.get(u, {}) if u in members else {} for u in range(len(adj))], set(range(len(adj))) - members)
        cyc = [c for c in sub if len(c) > 1]
        if not cyc: break
        worst = max(cyc, key=lines)
        indeg = collections.Counter(v for u in worst for v in work[u] if v in set(worst))
        hub, k = indeg.most_common(1)[0]
        cut.append(chunk_label(a.chunks[hub]))
        for u in members:
            work[u] = {v: w for v, w in work[u].items() if v != hub}
        sub2 = tarjan(len(adj), [work.get(u, {}) if u in members else {} for u in range(len(adj))], set(range(len(adj))) - members)
        steps.append({"late-bind": chunk_label(a.chunks[hub]), "incoming-edges-cut": k,
                      "largest-remaining-cycle-lines": max([lines(c) for c in sub2 if len(c) > 1] or [0])})
    return {"cycles": rep, "big-cycle-opening-plan": steps,
            "note": "every cycle is kept inside ONE module (a require cycle cannot exist); to split the biggest one the listed forms "
                    "would have to be called through a late-bound hook (declare + registry), in order"}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["graph", "partition"])
    ap.add_argument("src"); ap.add_argument("out")
    ap.add_argument("--modules", type=int, default=12)
    ap.add_argument("--driver", help="a form name inside the driver SCC (default: auto-detected)")
    ap.add_argument("--names", help="JSON {form-name: module-label}: label the module containing that form")
    ns = ap.parse_args()
    src = open(ns.src).read()
    os.makedirs(ns.out, exist_ok=True)
    a, adj = build(src)
    live_skip = {c.idx for c in a.chunks if c.is_ns}
    comps = tarjan(len(a.chunks), adj, live_skip)
    g = graph_edn(a, adj, comps, src)
    open(os.path.join(ns.out, "graph.edn"), "w").write(dumps(g) + "\n")
    print(f"graph: {g['source-forms']} forms, {g['names']} names, {g['edges']} edges, "
          f"{len(comps)} SCCs, cyclic SCC sizes {[s['size'] for s in g['sccs']][:8]}")
    if ns.cmd == "graph": return
    chunk_mod, k, info = partition(a, adj, comps, src, ns.modules, ns.driver)
    names = name_modules(a, chunk_mod, k)
    if ns.names:
        for nm, lab in json.load(open(ns.names)).items():           # {"form-name": "module-label"}
            for c in a.chunks:
                if nm in c.names and c.idx in chunk_mod: names[chunk_mod[c.idx]] = lab
    p = partition_edn(a, adj, chunk_mod, k, names, src, 0)
    p["method"] = info
    p["cycles"] = scc_report(a, adj, comps, chunk_mod, names)
    open(os.path.join(ns.out, "partition.edn"), "w").write(dumps(p) + "\n")
    json.dump({"source": os.path.abspath(ns.src), "assign": {str(c): names[m] for c, m in chunk_mod.items()},
               "order": [names[m] for m in range(k)]}, open(os.path.join(ns.out, "partition.json"), "w"), indent=1)
    for m in p["modules"]:
        print(f"  {m['order']:2d} {m['module']:<14} forms={m['forms']:4d} lines={m['lines']:6d}  requires={m['requires']}")
    print(f"edges total={p['edges-total']} cross-module={p['edges-cross-module']} backward(blocking)={p['edges-backward-blocking']}")

if __name__ == "__main__":
    main()
