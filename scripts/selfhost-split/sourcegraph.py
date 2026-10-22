"""AST-level top-level form inventory + reference graph for a Clojure-family file.

Units are TOP-LEVEL FORMS (chunks).  A chunk may define several names when a reader
conditional gives each platform its own def; every branch is analysed.
"""
import re
from cljparse import parse, strip_meta, meta_of, walk, Node

DEF_HEADS = {"def", "defn", "defn-", "defonce", "defmacro", "defmulti", "defrecord", "deftype", "defprotocol"}
LET_LIKE = {"let", "loop", "when-let", "if-let", "when-some", "if-some", "with-open", "let*", "binding", "doseq", "for", "dotimes"}
SKIP_SYMS = {"&", "_"}

def sym_text(n):
    n = strip_meta(n)
    return n.text if n.kind == "sym" else None

def pattern_syms(n, out):
    """All binder symbols in a destructuring pattern (vectors, maps, reader conditionals)."""
    k = n.kind
    if k == "sym":
        if n.text not in SKIP_SYMS and "/" not in n.text:
            out.add(n.text)
    elif k == "meta":
        pattern_syms(n.kids[1], out)
    elif k == "map":
        kids = n.kids
        i = 0
        while i < len(kids):
            key, val = kids[i], kids[i + 1] if i + 1 < len(kids) else None
            if key.kind == "kw" and key.text in (":keys", ":strs", ":syms") and val is not None:
                for s in val.kids:
                    if s.kind == "sym":
                        out.add(s.text.split("/")[-1])
            elif key.kind == "kw" and key.text == ":as" and val is not None:
                pattern_syms(val, out)
            elif key.kind == "kw" and key.text == ":or":
                pass  # defaults are expressions, not binders
            elif key.kind != "kw":
                pattern_syms(key, out)
            i += 2
    elif k in ("vec", "rc", "rcs", "list"):
        for c in n.kids:
            pattern_syms(c, out)

class Chunk:
    def __init__(self, idx, node, src, prev_end):
        self.idx = idx
        self.node = node
        self.start, self.end = node.start, node.end
        self.lead_start = prev_end            # includes comments between forms
        self.text = src[node.start:node.end]
        self.names = []                       # defined names (all branches)
        self.kinds = {}                       # name -> def head
        self.plats = {}                       # name -> {feature key or None}
        self.defnodes = {}
        self.private = {}
        self.dynamic = {}
        self.declares = []
        self.doc = {}
        self.refs = {}                        # name -> {"call":n, "value":n}
        self.binds = set()                    # dynamic vars rebound with `binding`
        self.platform_only = None             # e.g. {:kotoba}
        self.is_ns = False

def find_defs(node, found, plat=None):
    """Collect (name, head, defnode, platform-key) for def forms at the chunk's top, descending through
    reader conditionals/do.  platform-key is the reader-conditional feature the def sits under (None = all)."""
    n = strip_meta(node)
    if n.kind == "list" and n.kids and n.kids[0].kind == "sym":
        h = n.kids[0].text
        if h in DEF_HEADS and len(n.kids) > 1:
            nm = strip_meta(n.kids[1])
            if nm.kind == "sym":
                found.append((nm.text, h, n, plat))
            return
        if h == "declare":
            found.append(("*declare*", h, n, plat))
            return
        if h == "do":
            for c in n.kids[1:]:
                find_defs(c, found, plat)
            return
    if n.kind in ("rc", "rcs"):
        for i in range(0, len(n.kids) - 1, 2):
            find_defs(n.kids[i + 1], found, n.kids[i].text)

class Analyzer:
    def __init__(self, src):
        self.src = src
        tops = parse(src)
        self.chunks = []
        prev = 0
        for i, t in enumerate(tops):
            ch = Chunk(i, t, src, prev)
            prev = t.end
            self.chunks.append(ch)
        self.tail_start = prev
        self.def_chunks = {}  # name -> [chunk idx]
        for ch in self.chunks:
            self._classify(ch)
        self.top_names = set(self.def_chunks)
        for ch in self.chunks:
            if not ch.is_ns:
                self._refs(ch)

    # ---- classification
    def _classify(self, ch):
        n = strip_meta(ch.node)
        if n.kind == "list" and n.kids and n.kids[0].kind == "sym" and n.kids[0].text == "ns":
            ch.is_ns = True
            return
        found = []
        find_defs(ch.node, found)
        for name, head, d, plat in found:
            if name == "*declare*":
                ch.declares += [sym_text(x) for x in d.kids[1:] if sym_text(x)]
                continue
            if name not in ch.names:
                ch.names.append(name)
            ch.kinds[name] = head
            ch.plats.setdefault(name, set()).add(plat)
            ch.defnodes.setdefault(name, []).append(d)
            mets = meta_of(d.kids[1])
            txt = " ".join(self.src[m.start:m.end] for m in mets)
            ch.private[name] = head == "defn-" or ":private" in txt
            ch.dynamic[name] = ":dynamic" in txt
            doc = None
            for x in d.kids[2:4]:
                if x.kind == "str":
                    doc = x.text
                    break
            if doc:
                ch.doc[name] = doc
            lst = self.def_chunks.setdefault(name, [])
            if ch.idx not in lst:
                lst.append(ch.idx)
        if ch.node.kind == "rc":
            keys = {k.text for i, k in enumerate(ch.node.kids) if i % 2 == 0 and k.kind == "kw"}
            ch.platform_only = sorted(keys)
        # kotoba-only branch noted for the dual-runtime porting work
        ch.has_kotoba_branch = ":kotoba" in ch.text

    # ---- scoped reference walk
    def _refs(self, ch):
        refs = ch.refs
        own = set(ch.names)
        names = self.top_names

        def add(name, role):
            d = refs.setdefault(name, {"call": 0, "value": 0})
            d[role] += 1

        def sym(n, env, role):
            t = n.text
            if t in names and t not in env:
                add(t, role)

        def body(forms, env):
            for f in forms:
                visit(f, env, "value")

        def bindings(vec, env, consume_names=True):
            """process a let-style binding vector sequentially; return extended env"""
            env = set(env)
            kids = vec.kids
            i = 0
            while i + 1 < len(kids) + 0 and i < len(kids):
                pat, val = kids[i], (kids[i + 1] if i + 1 < len(kids) else None)
                if pat.kind == "kw":      # for/doseq modifiers :let :when :while
                    if pat.text == ":let" and val is not None and val.kind == "vec":
                        env = bindings(val, env)
                    elif val is not None:
                        visit(val, env, "value")
                    i += 2
                    continue
                if val is not None:
                    visit(val, env, "value")
                p = set()
                pattern_syms(pat, p)
                # defaults inside map patterns may reference earlier names
                env |= p
                i += 2
            return env

        def fn_arity(params, rest, env):
            p = set()
            pattern_syms(params, p)
            body(rest, env | p)

        def visit(n, env, role):
            k = n.kind
            if k == "sym":
                sym(n, env, role)
            elif k in ("kw", "str", "num", "char", "regex", "other", "discard"):
                return
            elif k == "meta":
                visit(n.kids[0], env, "value"); visit(n.kids[1], env, role)
            elif k == "quote":
                if n.text == "'":
                    return
                visit(n.kids[0], env, "value")
            elif k == "list":
                if not n.kids:
                    return
                h = n.kids[0]
                ht = h.text if h.kind == "sym" else None
                rest = n.kids[1:]
                if ht is None:
                    visit(h, env, "call"); body(rest, env); return
                if ht == "quote":
                    return
                if ht in ("declare", "ns"):
                    return
                if ht in ("def", "defonce"):
                    # name is a definition, not a reference
                    body(rest[1:], env); return
                if ht in LET_LIKE:
                    if rest and rest[0].kind == "vec":
                        if ht == "binding":
                            # targets are VAR references (dynamic rebinding), values are exprs
                            kids = rest[0].kids
                            e2 = set(env)
                            for i in range(0, len(kids) - 1, 2):
                                t = sym_text(kids[i])
                                if t and t in names:
                                    ch.binds.add(t)
                                    add(t, "value")
                                visit(kids[i + 1], env, "value")
                            body(rest[1:], env)
                        elif ht == "dotimes":
                            e2 = bindings(rest[0], env); body(rest[1:], e2)
                        else:
                            e2 = bindings(rest[0], env); body(rest[1:], e2)
                        return
                if ht in ("fn", "fn*"):
                    r = list(rest)
                    e2 = set(env)
                    if r and r[0].kind == "sym":
                        e2.add(r[0].text); r = r[1:]
                    if r and r[0].kind == "vec":
                        fn_arity(r[0], r[1:], e2)
                    else:
                        for a in r:
                            if a.kind == "list" and a.kids and a.kids[0].kind in ("vec",):
                                fn_arity(a.kids[0], a.kids[1:], e2)
                            else:
                                visit(a, e2, "value")
                    return
                if ht in ("defn", "defn-"):
                    r = list(rest)
                    if r:
                        r = r[1:]  # name
                    while r and (r[0].kind in ("str", "map") or r[0].kind == "meta"):
                        if r[0].kind == "map":
                            visit(r[0], env, "value")
                        r = r[1:]
                    if r and r[0].kind == "vec":
                        fn_arity(r[0], r[1:], env)
                    else:
                        for a in r:
                            if a.kind == "list" and a.kids and a.kids[0].kind == "vec":
                                fn_arity(a.kids[0], a.kids[1:], env)
                            else:
                                visit(a, env, "value")
                    return
                if ht == "letfn":
                    if rest and rest[0].kind == "vec":
                        e2 = set(env)
                        for f in rest[0].kids:
                            if f.kind == "list" and f.kids and f.kids[0].kind == "sym":
                                e2.add(f.kids[0].text)
                        for f in rest[0].kids:
                            if f.kind == "list" and len(f.kids) > 2 and f.kids[1].kind == "vec":
                                fn_arity(f.kids[1], f.kids[2:], e2)
                        body(rest[1:], e2); return
                if ht == "catch" and len(rest) >= 2:
                    e2 = set(env); t = sym_text(rest[1])
                    if t: e2.add(t)
                    body(rest[2:], e2); return
                if ht == "as->" and len(rest) >= 2:
                    visit(rest[0], env, "value")
                    t = sym_text(rest[1]); e2 = set(env)
                    if t: e2.add(t)
                    body(rest[2:], e2); return
                if ht == "case" and rest:
                    visit(rest[0], env, "value")
                    cl = rest[1:]
                    for i in range(0, len(cl) - 1, 2):
                        visit(cl[i + 1], env, "value")
                    if len(cl) % 2 == 1:
                        visit(cl[-1], env, "value")
                    return
                if ht == "condp" and rest:
                    body(rest, env); return
                # ordinary call
                if ht in names and ht not in env:
                    add(ht, "call")
                elif ht not in names:
                    pass
                body(rest, env)
            else:  # vec map set fn rc rcs tagged nsmap
                for c in n.kids:
                    visit(c, env, "value")

        visit(ch.node, set(), "value")
        # a definition does not "use" itself
        for nm in own:
            refs.pop(nm, None)
        refs_decl = {}  # (declared forwards are not dependencies)

def line_of(src, off):
    return src.count("\n", 0, off) + 1
