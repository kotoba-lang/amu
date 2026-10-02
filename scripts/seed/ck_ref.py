#!/usr/bin/env python3
"""scripts/seed/ck_ref.py -- BOOTSTRAP-TOOL (owner 20-names/21-check): reference model of seed modules 20-names and
21-check, written independently of the Kotoba code from seed/HEADS, seed/MEMORY-MAP and the rules documented at the
top of seed/21-check.kotoba. Used ONLY to cross-check scripts/seed/ck-gate.sh results (never in the compiler's
process tree). Lexing and reading come from scripts/seed/lexread_ref.py (the 10-lex/11-read reference).

  ck_ref.py FILE...          print the ck-dump result line of each file ("ok fns= syms= nodes= digest=" or
                             "E<code> pos= n= '<span>'"), exactly what seed/tests/check/ck-dump.kotoba prints in mode r
  ck_ref.py --gate           print "<label> <line>" for the ck-gate.sh list (same labels and order) on stdout
"""
import os, sys, glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lexread_ref as LR

REPO = LR.REPO
M64 = (1 << 64) - 1
S24 = 1 << 24
ND_ROOT, ND_LIST, ND_VEC, ND_MAP, ND_INT, ND_STR, ND_SYM, ND_KW = 1, 2, 3, 4, 5, 6, 7, 8
I64, BOOL, STR, VEC, BYTES = 1, 2, 3, 4, 5
POISON = 7
RES_LOCAL, RES_FN, RES_DEF, RES_HEAD = 1, 2, 3, 4
SPELL = ["", "ns", ":export", "defn", "defn-", "def", "let", "loop", "recur", "if", "and", "or", "not", "=", "<", ">",
         "<=", ">=", "+", "-", "*", "quot", "bit-and", "bit-or", "bit-xor", "bit-not", "u64-shift-right",
         "i64-shift-left", "i64-shift-right", "vector-at", "vector-conj", "vector-assoc", "vector-assoc!",
         "vector-alloc", "string-code-point-at", "string-length", "[", "(call)", "typed-cap-call",
         "bytes-from-vector-i64", "string-concat", "cond"]
HD = {s: i for i, s in enumerate(SPELL) if i not in (0, 2, 36, 37)}
(NS, EXPORT, DEFN, DEFNP, DEF, LET, LOOP, RECUR, IF, AND, OR, NOT, EQ, LT, GT, LE, GE, ADD, SUB, MUL, QUOT, BAND, BOR,
 BXOR, BNOT, USHR, SHL, SSHR, VAT, VCONJ, VASSOC, VASSOCB, VALLOC, SCPA, SLEN, VECLIT, CALL, CAP, BYTESF, SCAT,
 COND) = range(1, 42)
KW = {":i64": 1, ":bool": 2, ":string": 3, ":vector-i64": 4, ":export": 5, ":else": 6, ":bytes": 7,
      ":fs/app-data": 8, ":cli/args": 9, ":io/write-error": 10, ":io/write": 11}
FK_DEFN, FK_PRIV, FK_DEF = 1, 2, 3


class Fail(Exception):
    pass


def s64(x):
    x &= M64
    return x - (1 << 64) if x >= (1 << 63) else x


class Model:
    def __init__(self, src):
        self.src = src
        toks, lits = LR.lex(src)
        root = LR.read(toks)
        self.toks = toks
        order = []

        def walk(n):
            order.append(n)
            for k in n.kids:
                walk(k)
        walk(root)
        idx = {id(n): i + 1 for i, n in enumerate(order)}
        self.N = len(order) + 1
        self.kind = [0] * self.N
        self.first = [0] * self.N
        self.next = [0] * self.N
        self.tok = [0] * self.N
        self.kids = [[] for _ in range(self.N)]
        for n in order:
            i = idx[id(n)]
            self.kind[i], self.tok[i] = n.kind, n.tok
            self.kids[i] = [idx[id(k)] for k in n.kids]
            if n.kids:
                self.first[i] = self.kids[i][0]
            for a, b in zip(n.kids, n.kids[1:]):
                self.next[idx[id(a)]] = idx[id(b)]
        self.ntype = [0] * self.N
        self.nres = [0] * self.N
        self.nsym = [0] * self.N
        self.err = None
        # symbols
        self.syms = [None]          # spelling bytes
        self.symid = {}
        self.shead = [0]
        self.sfn = [0]
        self.sbind = [0]
        self.scope = []             # (sym, prev)
        self.fns = [None]           # dict per FN

    # ---- helpers
    def span(self, n):
        t = self.tok[n]
        if t == 0:
            return -1, 0
        _, s, e, _ = self.toks[t - 1]
        return s, e

    def fail(self, code, node, n=0):
        if self.err is None:
            a, b = self.span(node) if node > 0 else (-1, 0)
            self.err = (code, a, max(a, 0), b, n)
        raise Fail()

    def nth(self, n, k):
        ks = self.kids[n]
        return ks[k] if k < len(ks) else 0

    def count(self, n):
        return len(self.kids[n])

    def head_of(self, n):
        return self.shead[self.nsym[n]] if self.kind[n] in (ND_SYM, ND_KW) else 0

    def mark(self, n, ty, res):
        self.ntype[n], self.nres[n] = ty, res
        return ty

    # ---- 20-names
    def intern_all(self):
        for n in range(1, self.N):
            if self.kind[n] in (ND_SYM, ND_KW):
                s, e = self.span(n)
                sp = self.src[s:e]
                if sp not in self.symid:
                    self.symid[sp] = len(self.syms)
                    self.syms.append(sp)
                    txt = sp.decode()
                    self.shead.append(KW.get(txt, 0) if txt.startswith(":") else HD.get(txt, 0))
                    self.sfn.append(0)
                    self.sbind.append(0)
                self.nsym[n] = self.symid[sp]

    def ns_ok(self, n):
        if n == 0:
            return False
        if not (self.kind[n] == ND_LIST and self.kind[self.first[n]] == ND_SYM and self.head_of(self.first[n]) == NS
                and self.kind[self.nth(n, 1)] == ND_SYM):
            return False
        c = self.count(n)
        if c == 2:
            return True
        if c != 3:
            return False
        x = self.nth(n, 2)
        v = self.nth(x, 1)
        return (self.kind[x] == ND_LIST and self.count(x) == 2 and self.kind[self.first[x]] == ND_KW
                and self.head_of(self.first[x]) == KW[":export"] and self.kind[v] == ND_VEC
                and all(self.kind[k] == ND_SYM for k in self.kids[v]))

    def names(self):
        self.intern_all()
        root = 1
        ns = self.first[root]
        if not self.ns_ok(ns):
            self.fail(2004, ns)
        for n in self.kids[root][1:]:
            hd = self.head_of(self.first[n]) if (self.kind[n] == ND_LIST and self.kind[self.first[n]] == ND_SYM) else 0
            fk = {DEFN: FK_DEFN, DEFNP: FK_PRIV, DEF: FK_DEF}.get(hd, 0)
            nn = n if self.first[n] == 0 else (self.first[n] if self.kind[n] == ND_LIST else n)
            if hd == NS:
                self.fail(2004, n)
            if fk == 0:
                self.fail(2003, nn)
            nm = self.nth(n, 1)
            if self.kind[nm] != ND_SYM:
                self.fail(2003, nn)
            s = self.nsym[nm]
            if self.sfn[s] > 0 or self.shead[s] > 0:
                self.fail(2001, nm)
            p = self.nth(n, 2)
            np_ = 0 if fk == FK_DEF else (self.count(p) // 2 if self.kind[p] == ND_VEC else 0)
            self.fns.append(dict(sym=s, node=n, kind=fk, np=np_, rt=0, pt=[0] * 5, nslots=0, fuel=0, export=0))
            self.sfn[s] = len(self.fns) - 1
        if self.count(ns) == 3:
            for c in self.kids[self.nth(self.nth(ns, 2), 1)]:
                f = self.sfn[self.nsym[c]]
                if f == 0 or self.fns[f]["kind"] == FK_DEF:
                    self.fail(2005, c)
                self.fns[f]["export"] = 1

    # scope
    def bind(self, s, slot, ty):
        self.scope.append((s, self.sbind[s]))
        self.sbind[s] = slot + 1 + ty * S24

    def unbind(self, h):
        while len(self.scope) > h:
            s, prev = self.scope.pop()
            self.sbind[s] = prev

    def local_slot(self, s):
        v = self.sbind[s]
        return -1 if v == 0 else (v & (S24 - 1)) - 1

    def local_type(self, s):
        return self.sbind[s] // S24

    def bound_since(self, s, h):
        return any(x == s for x, _ in self.scope[h:])

    # ---- 21-check
    def kw_type(self, n):
        return self.head_of(n) if self.kind[n] == ND_KW and self.head_of(n) in (1, 2, 3, 4) else 0

    def check(self):
        for f in range(1, len(self.fns)):
            (self.sig_def if self.fns[f]["kind"] == FK_DEF else self.sig_defn)(f)
        for f in range(1, len(self.fns)):
            if self.fns[f]["kind"] != FK_DEF:
                self.body(f)

    def sig_defn(self, f):
        F = self.fns[f]
        n = F["node"]
        nm, p, r = self.nth(n, 1), self.nth(n, 2), self.nth(n, 3)
        rt = self.kw_type(r)
        if self.kind[p] != ND_VEC or self.count(p) % 2:
            self.fail(2119, nm)
        if self.count(p) > 10:
            self.fail(2108, nm)
        if self.kind[r] != ND_KW:
            self.fail(2119, nm)
        if rt == 0:
            self.fail(2105, r)
        if self.count(n) != 5:
            self.fail(2118, nm)
        ks = self.kids[p]
        for k in range(0, len(ks), 2):
            b, t = ks[k], ks[k + 1]
            if self.kind[b] != ND_SYM:
                self.fail(2119, b)
            if self.kind[t] != ND_KW:
                self.fail(2119, t)
            if self.kw_type(t) == 0:
                self.fail(2105, t)
            F["pt"][k // 2] = self.kw_type(t)
        F["rt"] = rt
        self.nres[nm] = RES_FN * S24 + f
        if F["export"]:
            if any(F["pt"][k] != I64 for k in range(F["np"])) or rt not in (I64, BOOL):
                self.fail(2104, nm, I64)

    def sig_def(self, f):
        F = self.fns[f]
        n = F["node"]
        nm, v = self.nth(n, 1), self.nth(n, 2)
        k = self.kind[v]
        if self.count(n) != 3:
            self.fail(2124, nm)
        if k == ND_INT:
            F["rt"] = self.mark(v, I64, 0)
        elif k == ND_STR:
            F["rt"] = self.mark(v, STR, 0)
        elif k == ND_VEC and self.count(v) <= 64 and all(self.kind[c] == ND_INT for c in self.kids[v]):
            for c in self.kids[v]:
                self.mark(c, I64, 0)
            F["rt"] = self.mark(v, VEC, VECLIT)
        else:
            self.fail(2124, nm)

    def use_slot(self, f, slot):
        if slot > self.fns[f]["nslots"]:
            self.fns[f]["nslots"] = slot

    def bindnode(self, b, slot, ty, f):
        self.bind(self.nsym[b], slot, ty)
        self.ntype[b], self.nres[b] = ty, RES_LOCAL * S24 + slot
        self.use_slot(f, slot)

    def binder_ok(self, b, h0):
        if self.kind[b] != ND_SYM:
            self.fail(2111, b)
        if self.head_of(b) > 0:
            self.fail(2111, b)
        if self.bound_since(self.nsym[b], h0):
            self.fail(2112, b)

    def body(self, f):
        F = self.fns[f]
        n = F["node"]
        nm, p, body = self.nth(n, 1), self.nth(n, 2), self.nth(n, 4)
        F["nslots"], F["fuel"] = F["np"], 0
        h0 = len(self.scope)
        ks = self.kids[p]
        for k in range(0, len(ks), 2):
            self.binder_ok(ks[k], h0)
            self.bindnode(ks[k], k // 2 + 1, F["pt"][k // 2], f)
        ty = self.expr(body, f, F["np"] + 1, p, 1)
        self.unbind(h0)
        if ty != 0 and ty != F["rt"]:
            self.fail(2121, nm, F["rt"])

    # expr returns its type; (f, nxt) = function and next free slot; (tgt, tail) = recur target and tail flag
    def expr(self, n, f, nxt, tgt, tail):
        k = self.kind[n]
        if k == ND_INT:
            return self.mark(n, I64, 0)
        if k == ND_STR:
            return self.mark(n, STR, 0)
        if k == ND_KW:
            self.fail(2114, n)
        if k == ND_SYM:
            s = self.nsym[n]
            ty, slot, fi = self.local_type(s), self.local_slot(s), self.sfn[s]
            if ty == POISON:
                self.fail(2111, n)
            if slot >= 0:
                return self.mark(n, ty, RES_LOCAL * S24 + slot)
            if fi and self.fns[fi]["kind"] == FK_DEF:
                return self.mark(n, self.fns[fi]["rt"], RES_DEF * S24 + fi)
            self.fail(2102, n)
        if k == ND_VEC:
            if self.count(n) > 64:
                self.fail(2116, n)
            for c in self.kids[n]:
                if self.expr(c, f, nxt, 0, 0) != I64:
                    self.fail(2116, c)
            return self.mark(n, VEC, VECLIT)
        if k != ND_LIST:
            self.fail(2101, n)
        h = self.first[n]
        if h == 0:
            self.fail(2101, n)
        if self.kind[h] != ND_SYM:
            self.fail(2101, h)
        s = self.nsym[h]
        if self.local_slot(s) >= 0:
            self.fail(2101, h)
        hd, fi = self.shead[s], self.sfn[s]
        args = self.kids[n][1:]
        if hd > 0:
            self.nres[h] = RES_HEAD * S24 + hd
            return self.head(n, h, hd, args, f, nxt, tgt, tail)
        if fi and self.fns[fi]["kind"] != FK_DEF:
            self.nres[h] = RES_FN * S24 + fi
            F = self.fns[fi]
            if len(args) != F["np"]:
                self.fail(2103, h, F["np"])
            for i, a in enumerate(args):
                if self.expr(a, f, nxt, 0, 0) != F["pt"][i]:
                    self.fail(2104, h, F["pt"][i])
            self.fns[f]["fuel"] = 1
            return self.mark(n, F["rt"], CALL)
        self.fail(2101, h)

    def unify(self, ta, tb, h):
        if ta == 0:
            return tb
        if tb == 0 or ta == tb:
            return ta
        self.fail(2104, h, ta)

    def head(self, n, h, hd, args, f, nxt, tgt, tail):
        na = len(args)
        if hd == LET or hd == LOOP:
            v = self.nth(n, 1)
            nb = self.count(v)
            maxp = 1000 if hd == LET else 10
            if self.kind[v] != ND_VEC or nb % 2 or nb > 2 * maxp or (hd == LOOP and nb == 0):
                self.fail(2111, h)
            if self.count(n) != 3:
                self.fail(2118, h)
            h0 = len(self.scope)
            ks = self.kids[v]
            for i in range(0, nb, 2):
                b, e = ks[i], ks[i + 1]
                slot = nxt + i // 2
                self.binder_ok(b, h0)
                ty = self.expr(e, f, slot, 0, 0)
                if slot > 255:
                    self.fail(2120, b, slot)
                if ty == 0 or (hd == LOOP and ty == BYTES):
                    self.fail(2111, b)
                self.bindnode(b, slot, POISON if hd == LOOP else ty, f)
                self.ntype[b] = ty
            if hd == LOOP:
                self.unbind(h0)
                for i in range(0, nb, 2):
                    b = ks[i]
                    self.bindnode(b, self.nres[b] - RES_LOCAL * S24, self.ntype[b], f)
                ty = self.expr(self.nth(n, 2), f, nxt + nb // 2, v, 1)
            else:
                ty = self.expr(self.nth(n, 2), f, nxt + nb // 2, tgt, tail)
            self.unbind(h0)
            return self.mark(n, ty, hd)
        if hd == RECUR:
            nb = self.count(tgt) // 2
            if tail == 0 or tgt == 0:
                self.fail(2106, h)
            if na != nb:
                self.fail(2107, h, nb)
            bs = self.kids[tgt][0::2]
            for a, b in zip(args, bs):
                if self.expr(a, f, nxt, 0, 0) != self.ntype[b]:
                    self.fail(2104, h, self.ntype[b])
            return self.mark(n, 0, RECUR)
        if hd == IF:
            if self.count(n) != 4:
                self.fail(2110, h)
            if self.expr(args[0], f, nxt, 0, 0) != BOOL:
                self.fail(2104, h, BOOL)
            ta = self.expr(args[1], f, nxt, tgt, tail)
            tb = self.expr(args[2], f, nxt, tgt, tail)
            return self.mark(n, self.unify(ta, tb, h), IF)
        if hd == COND:
            if na < 2 or na % 2:
                self.fail(2109, h)
            acc = 0
            for i in range(0, na, 2):
                c, e = args[i], args[i + 1]
                last = i + 2 == na
                if self.kind[c] == ND_KW:
                    if not last or self.head_of(c) != KW[":else"]:
                        self.fail(2109, h)
                    acc = self.unify(acc, self.expr(e, f, nxt, tgt, tail), h)
                    break
                if last:
                    self.fail(2109, h)
                if self.expr(c, f, nxt, 0, 0) != BOOL:
                    self.fail(2104, h, BOOL)
                acc = self.unify(acc, self.expr(e, f, nxt, tgt, tail), h)
            return self.mark(n, acc, COND)
        if hd in (AND, OR):
            if na < 1:
                self.fail(2103, h, 1)
            for i, a in enumerate(args):
                last = i + 1 == na
                ty = self.expr(a, f, nxt, tgt if last else 0, tail if last else 0)
                if ty not in (BOOL, 0):
                    self.fail(2104, h, BOOL)
            return self.mark(n, BOOL, hd)
        if hd == EQ:
            if na != 2:
                self.fail(2103, h, 2)
            ta = self.expr(args[0], f, nxt, 0, 0)
            tb = self.expr(args[1], f, nxt, 0, 0)
            if ta not in (I64, BOOL) or tb not in (I64, BOOL):
                self.fail(2123, h)
            if ta != tb:
                self.fail(2104, h, ta)
            return self.mark(n, BOOL, EQ)
        if hd == CAP:
            if self.count(n) != 5:
                self.fail(2115, h)
            w, q, r, x = args
            wk, r1, r2 = self.head_of(w), self.head_of(q), self.head_of(r)
            ty = 0 if r1 != r2 else (STR if r1 == KW[":string"] else
                                     (BYTES if r1 == KW[":bytes"] and wk == KW[":fs/app-data"] else 0))
            if self.kind[w] != ND_KW or wk not in (8, 9, 10, 11):
                self.fail(2115, w)
            if self.kind[q] != ND_KW:
                self.fail(2115, q)
            if self.kind[r] != ND_KW:
                self.fail(2115, r)
            if ty == 0:
                self.fail(2115, q)
            if self.expr(x, f, nxt, 0, 0) != ty:
                self.fail(2104, h, ty)
            self.fns[f]["fuel"] = 1
            return self.mark(n, ty, CAP)
        if NOT <= hd <= SLEN or hd in (BYTESF, SCAT):
            arity = 1 if hd in (NOT, BNOT, VALLOC, SLEN, BYTESF) else (3 if hd in (VASSOC, VASSOCB) else 2)
            ok = na >= arity if hd in (ADD, SUB, MUL) else na == arity
            if not ok:
                self.fail(2103, h, arity)
            for k, a in enumerate(args):
                if hd == NOT:
                    want = BOOL
                elif hd in (VAT, VCONJ, VASSOC, VASSOCB):
                    want = VEC if k == 0 else I64
                elif hd == BYTESF:
                    want = VEC
                elif hd == SCPA:
                    want = STR if k == 0 else I64
                elif hd in (SLEN, SCAT):
                    want = STR
                else:
                    want = I64
                if self.expr(a, f, nxt, 0, 0) != want:
                    self.fail(2104, h, want)
            if VAT <= hd <= SLEN or hd in (BYTESF, SCAT):
                self.fns[f]["fuel"] = 1
            res = (BOOL if hd in (NOT, LT, GT, LE, GE) else VEC if hd in (VCONJ, VASSOC, VASSOCB, VALLOC)
                   else BYTES if hd == BYTESF else STR if hd == SCAT else I64)
            return self.mark(n, res, hd)
        self.fail(2101, self.first[n])

    def digest(self):
        h = M64 & -3750763034362895579

        def mix(h, v):
            return ((h ^ (v & M64)) * 1099511628211) & M64
        for n in range(1, self.N):
            h = mix(mix(h, self.ntype[n]), self.nres[n])
        for F in self.fns[1:]:
            pt = F["pt"]
            for v in (F["rt"], F["nslots"], F["fuel"], pt[0], pt[1], pt[2], pt[3], pt[4], F["export"], F["np"],
                      F["kind"]):
                h = mix(h, v)
        return s64(h)


def result(path):
    src = open(path, "rb").read()
    try:
        m = Model(src)
    except LR.Err as e:
        a, b = e.a, e.b
        return "E%d pos=%d n=%d '%s'" % (e.code, e.pos, e.n, src[a:b].decode("latin-1") if a < b else "")
    try:
        m.names()
        m.check()
    except Fail:
        code, pos, a, b, n = m.err
        return "E%d pos=%d n=%d '%s'" % (code, pos, n, src[a:b].decode() if a < b else "")
    return "ok fns=%d syms=%d nodes=%d digest=%d" % (len(m.fns) - 1, len(m.syms) - 1, m.N - 1, m.digest())


def gate_list(conf, accept, selfsrc):
    out = []
    for f in sorted(glob.glob(REPO + "/bench/embench/ports/*.kotoba")):
        out.append(("port/" + os.path.basename(f)[:-7], f))
    for f in sorted(glob.glob(REPO + "/seed/tests/corpus/*.kotoba")):
        out.append(("corpus/" + os.path.basename(f)[:-7], f))
    out.append(("self/unity", selfsrc))
    for pat in ("ok-*", "err-*"):
        for f in sorted(glob.glob(REPO + "/seed/tests/check/cases/" + pat + ".kotoba")):
            out.append(("case/" + os.path.basename(f)[:-7], f))
    for f in sorted(glob.glob(REPO + "/seed/tests/neg/*.kotoba")):
        out.append(("neg/" + os.path.basename(f)[:-7], f))
    for f in sorted(glob.glob(conf + "/*/*.kotoba")):
        out.append(("conf/%s/%s" % (os.path.basename(os.path.dirname(f)), os.path.basename(f)[:-7]), f))
    return out


if __name__ == "__main__":
    if sys.argv[1:2] == ["--gate"]:
        conf = os.environ.get("CK_CONFORMANCE", "/private/tmp/wt-K-kotoba-lang/lang/conformance")
        selfsrc = os.environ.get("CK_SELF", REPO + "/build/seed/check/self.kotoba")
        for lab, f in gate_list(conf, None, selfsrc):
            print(lab, result(f))
    else:
        for f in sys.argv[1:]:
            print(result(f))
