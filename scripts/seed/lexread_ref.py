#!/usr/bin/env python3
"""scripts/seed/lexread_ref.py -- BOOTSTRAP-TOOL: reference lexer + reader + dumps for seed modules 10-lex / 11-read.

Independent re-implementation of the contract in seed/HEADS (:tokens :nodes :errors) used ONLY to produce goldens
(never in the compiler's process tree). The Kotoba modules must produce byte-identical dumps.

  lexread_ref.py dump tok|tree|stat FILE     print the dump of one file (what seed/tests/lexread/dump.kotoba prints)
  lexread_ref.py gen                         (re)write seed/tests/lexread/golden/* and seed/tests/unit/{10-lex,11-read}.expected
  lexread_ref.py check                       self-checks: canonical print is a fixed point (read(print(read x)) == print)

Dump formats (every line ends with LF):
  tok:   "TOKENS <n>" then per token "T <i> <KIND> <start> <end> <val>" (+ ` "<escaped decoded bytes>"` for STR)
  tree:  one line per top-level form: the canonical print (lists "(a b)", vectors "[a b]", ints as decimals, strings
         re-escaped, symbols and keywords verbatim, one space between children)
  error: a single line "ERR <code> <pos> <a> <b> <n>"  (a lexical error hides every reader error: lex runs first)
"""
import os, sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
M64 = (1 << 64) - 1
MIN = -(1 << 63)

KIND = ["", "LPAREN", "RPAREN", "LBRACK", "RBRACK", "LBRACE", "RBRACE", "INT", "STR", "SYM", "KW"]
TK = {n: i for i, n in enumerate(KIND) if n}
ND_ROOT, ND_LIST, ND_VEC, ND_MAP, ND_INT, ND_STR, ND_SYM, ND_KW = 1, 2, 3, 4, 5, 6, 7, 8


class Err(Exception):
    def __init__(self, code, pos=-1, a=0, b=0, n=0):
        self.code, self.pos, self.a, self.b, self.n = code, pos, a, b, n

    def line(self):
        return "ERR %d %d %d %d %d\n" % (self.code, self.pos, self.a, self.b, self.n)


def symch(c):
    return (97 <= c <= 122 or 65 <= c <= 90 or 48 <= c <= 57 or c in b"*+!_?<>=/.-")


def lex(src):
    """src: bytes. Returns (tokens, lits). token = (kind, start, end, val); lit = bytes. Raises Err."""
    for i, b in enumerate(src):
        if b > 127:
            raise Err(1002, i, i, i + 1, b)
    toks, lits = [], []
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c in b" \t\n\r,":
            i += 1
        elif c == 59:
            while i < n and src[i] != 10:
                i += 1
        elif c in b"()[]{}":
            toks.append((TK["LPAREN"] + b"()[]{}".index(c), i, i + 1, 0))
            i += 1
        elif c == 34:
            j, buf = i + 1, bytearray()
            while True:
                if j >= n:
                    raise Err(1001, i, i, i + 1)
                d = src[j]
                if d == 34:
                    break
                if d == 92:
                    if j + 1 >= n:
                        raise Err(1001, i, i, i + 1)
                    k = {110: 10, 116: 9, 92: 92, 34: 34}.get(src[j + 1], -1)
                    if k < 0:
                        raise Err(1003, j, j, j + 2)
                    buf.append(k)
                    j += 2
                else:
                    buf.append(d)
                    j += 1
            lits.append(bytes(buf))
            toks.append((TK["STR"], i, j + 1, len(lits)))  # LIT index is 1-based (record 0 is null)
            i = j + 1
        elif c == 58:
            j = i + 1
            while j < n and symch(src[j]):
                j += 1
            if j == i + 1:
                raise Err(1005, i, i, i + 1)
            toks.append((TK["KW"], i, j, 0))
            i = j
        elif symch(c):
            j = i
            while j < n and symch(src[j]):
                j += 1
            w = src[i:j]
            body = w[1:] if w[:1] == b"-" else w
            if body and body.isdigit() and (w[:1] != b"-" or len(w) > 1):
                v = int(w)
                if not (MIN <= v < (1 << 63)):
                    raise Err(1004, i, i, j)
                toks.append((TK["INT"], i, j, v))
            else:
                toks.append((TK["SYM"], i, j, 0))
            i = j
        else:
            raise Err(1005, i, i, i + 1)
    return toks, lits


class Node:
    __slots__ = ("kind", "kids", "tok", "aux")

    def __init__(self, kind, tok=0, aux=0):
        self.kind, self.kids, self.tok, self.aux = kind, [], tok, aux


def read(toks):
    """toks 0-based list; node.tok is the 1-based token index (the Kotoba layout). Raises Err."""
    def tk(t):
        return toks[t - 1]

    def span_err(code, t):
        _, s, e, _ = tk(t)
        return Err(code, s, s, e)

    def items(t, parent):
        while True:
            if t > len(toks):
                if parent.kind == ND_ROOT:
                    return t
                raise span_err(1102, parent.tok)
            k = tk(t)[0]
            if k in (TK["RPAREN"], TK["RBRACK"], TK["RBRACE"]):
                if parent.kind == ND_ROOT:
                    raise span_err(1101, t)
                want = TK["RPAREN"] if parent.kind == ND_LIST else TK["RBRACK"]
                if k == want:
                    return t + 1
                raise span_err(1103, t)
            t, n = form(t)
            parent.kids.append(n)
            parent.aux += 1

    def form(t):
        k, s, e, v = tk(t)
        if k == TK["LPAREN"] or k == TK["LBRACK"]:
            n = Node(ND_LIST if k == TK["LPAREN"] else ND_VEC, t)
            return items(t + 1, n), n
        if k == TK["LBRACE"]:
            raise span_err(1105, t)
        if k in (TK["RPAREN"], TK["RBRACK"], TK["RBRACE"]):
            raise span_err(1101, t)
        if k == TK["INT"]:
            return t + 1, Node(ND_INT, t, v)
        if k == TK["STR"]:
            return t + 1, Node(ND_STR, t, v)
        return t + 1, Node(ND_SYM if k == TK["SYM"] else ND_KW, t, 0)

    root = Node(ND_ROOT, 0, 0)
    items(1, root)
    return root


def esc_byte(b):
    if b == 10: return "\\n"
    if b == 9: return "\\t"
    if b == 34: return '\\"'
    if b == 92: return "\\\\"
    if 32 <= b <= 126: return chr(b)
    return "\\x%02x" % b


def esc(bs):
    return "".join(esc_byte(b) for b in bs)


def dump_tok(src):
    try:
        toks, lits = lex(src)
    except Err as e:
        return e.line()
    out = ["TOKENS %d\n" % len(toks)]
    for i, (k, s, e, v) in enumerate(toks, 1):
        extra = ' "%s"' % esc(lits[v - 1]) if k == TK["STR"] else ""
        out.append("T %d %s %d %d %d%s\n" % (i, KIND[k], s, e, v, extra))
    return "".join(out)


def pnode(n, src, toks, lits):
    if n.kind == ND_INT: return str(n.aux)
    if n.kind == ND_STR: return '"%s"' % esc(lits[n.aux - 1])
    if n.kind in (ND_SYM, ND_KW):
        _, s, e, _ = toks[n.tok - 1]
        return src[s:e].decode("ascii")
    o, c = ("(", ")") if n.kind == ND_LIST else ("[", "]")
    return o + " ".join(pnode(k, src, toks, lits) for k in n.kids) + c


def dump_tree(src):
    try:
        toks, lits = lex(src)
        root = read(toks)
    except Err as e:
        return e.line()
    return "".join(pnode(k, src, toks, lits) + "\n" for k in root.kids)


def nodes_flat(root):
    """Nodes numbered as the Kotoba reader numbers them: the root is 1, then pre-order (a node is created before its
    children, siblings in order). Returns a list of (kind, first, next, tok, aux) with index = number-1."""
    order = []

    def walk(n):
        order.append(n)
        for k in n.kids:
            walk(k)
    walk(root)
    idx = {id(n): i + 1 for i, n in enumerate(order)}
    nxt = {}
    for n in order:
        for a, b in zip(n.kids, n.kids[1:]):
            nxt[id(a)] = idx[id(b)]
    return [(n.kind, idx[id(n.kids[0])] if n.kids else 0, nxt.get(id(n), 0), n.tok, n.aux) for n in order]


def w64(x):
    return x & M64


def fold(h, x):
    return w64((h ^ w64(x)) * 1099511628211)


def hash_tokens(toks):
    h = w64(-3750763034362895579)  # FNV-64 offset basis as a signed i64 literal
    for k, s, e, v in toks:
        for x in (k, s, e, v):
            h = fold(h, x)
    return h - (1 << 64) if h >= (1 << 63) else h


def hash_nodes(root):
    h = w64(-3750763034362895579)
    for rec in nodes_flat(root):
        for x in rec:
            h = fold(h, x)
    return h - (1 << 64) if h >= (1 << 63) else h


def dump_stat(src):
    try:
        toks, lits = lex(src)
        root = read(toks)
    except Err as e:
        return e.line()
    nn = len(nodes_flat(root))
    return "STAT bytes=%d toks=%d nodes=%d lits=%d litb=%d\n" % (len(src), len(toks), nn, len(lits), sum(len(x) for x in lits))


# ---------------------------------------------------------------------------------------------------------------
# test corpus
# ---------------------------------------------------------------------------------------------------------------
PORTS = ["aha-mont64", "crc32", "depthconv", "edn", "huffbench", "matmult-int", "md5sum", "nettle-aes", "nettle-sha256",
         "nsichneu", "picojpeg", "qrduino", "sglib-combined", "slre", "statemate", "tarfind", "ud", "wikisort", "xgboost"]
CASES = [  # (name, path relative to the repo)
    ("edge-tokens", "seed/tests/lexread/pos/edge-tokens.kotoba"),
    ("edge-crlf", "seed/tests/lexread/pos/edge-crlf.kotoba"),
    ("edge-nest", "seed/tests/lexread/pos/edge-nest.kotoba"),
    ("edge-empty", "seed/tests/lexread/pos/edge-empty.kotoba"),
    ("edge-comments", "seed/tests/lexread/pos/edge-comments.kotoba"),
    ("edge-ints", "seed/tests/lexread/pos/edge-ints.kotoba"),
] + [(os.path.splitext(f)[0], "seed/tests/lexread/neg/" + f)
     for f in sorted(os.listdir(os.path.join(REPO, "seed/tests/lexread/neg")))] \
    if os.path.isdir(os.path.join(REPO, "seed/tests/lexread/neg")) else []
FILES = [("port-" + p, "bench/embench/ports/%s.kotoba" % p) for p in PORTS] + CASES


def readf(rel):
    with open(os.path.join(REPO, rel), "rb") as f:
        return f.read()


def unit_line(name, src, tree):
    try:
        toks, lits = lex(src)
        root = read(toks) if tree else None
    except Err as e:
        return "%s %s" % (name, e.line())
    s = "%s toks=%d tokhash=%d" % (name, len(toks), hash_tokens(toks))
    if tree:
        s += " nodes=%d nodehash=%d" % (len(nodes_flat(root)), hash_nodes(root))
    return s + "\n"


def gen():
    gd = os.path.join(REPO, "seed/tests/lexread/golden")
    os.makedirs(gd, exist_ok=True)
    for name, rel in FILES:
        src = readf(rel)
        for mode, fn in (("tok", dump_tok), ("tree", dump_tree)):
            with open(os.path.join(gd, "%s.%s" % (name, mode)), "w") as f:
                f.write(fn(src))
    for mod, tree in (("10-lex", False), ("11-read", True)):
        out = "".join(unit_line(n, readf(r), tree) for n, r in FILES) + "exit=0\n"
        with open(os.path.join(REPO, "seed/tests/unit/%s.expected" % mod), "w") as f:
            f.write(out)
    gen_unit_tests()
    print("gen: %d files, goldens in %s" % (len(FILES), gd))


UNIT_TMPL = r''';; seed/tests/unit/@MOD@_t.kotoba -- GENERATED by scripts/seed/lexread_ref.py gen (do not edit). Unit test of seed/@MOD@.kotoba.
;; For each of the @N@ files (19 Embench ports + the lexread corpus) it prints one line: the token count and an FNV-style
;; hash of every (kind start end val) token@TREE1@, or the "ERR code pos a b n" line. The expected file is made by the
;; independent Python reference (scripts/seed/lexread_ref.py), not by this program.
;; deps: @DEPS@
(defn- t-digit [d :i64] :string
  (cond (= d 0) "0" (= d 1) "1" (= d 2) "2" (= d 3) "3" (= d 4) "4"
        (= d 5) "5" (= d 6) "6" (= d 7) "7" (= d 8) "8" :else "9"))
(defn- t-neg [n :i64] :string
  (if (> n -10)
    (t-digit (- 0 n))
    (string-concat (t-neg (quot n 10)) (t-digit (- 0 (- n (* 10 (quot n 10))))))))
(defn- t-dec [n :i64] :string
  (if (< n 0) (string-concat "-" (t-neg n)) (t-neg (- 0 n))))
(defn- t-w [s :string] :i64
  (let [o (typed-cap-call :io/write :string :string s)] 0))
(defn- t-wn [n :i64] :i64 (t-w (t-dec n)))
(defn- t-rel [k :i64] :string
  (cond
@RELS@
    :else ""))
(defn- t-nm [k :i64] :string
  (cond
@NAMES@
    :else ""))
;; a clean heap between files: fills back to 1, error cells cleared (regions are overwritten, never read before written)
(defn- t-reset [M :vector-i64] :vector-i64
  (let [M1 (vector-assoc! M MM-TOK-N 1)
        M2 (vector-assoc! M1 MM-NODE-N 1)
        M3 (vector-assoc! M2 MM-LIT-N 1)
        M4 (vector-assoc! M3 MM-LITB-N 1)
        M5 (vector-assoc! M4 MM-ERR 0)
        M6 (vector-assoc! M5 MM-ERR-POS 0)
        M7 (vector-assoc! M6 MM-ERR-A 0)
        M8 (vector-assoc! M7 MM-ERR-B 0)]
    (vector-assoc! M8 MM-ERR-N 0)))
(defn- t-fold [h :i64 x :i64] :i64 (* (bit-xor h x) 1099511628211))
(defn- t-tokf [M :vector-i64 i :i64 f :i64] :i64 (vector-at M (+ MM-TOK-BASE (* i MM-TOK-W) f)))
(defn- t-htok [M :vector-i64 i :i64 h :i64] :i64
  (if (>= i (vector-at M MM-TOK-N))
    h
    (t-htok M (+ i 1)
            (t-fold (t-fold (t-fold (t-fold h (t-tokf M i TF-KIND)) (t-tokf M i TF-START)) (t-tokf M i TF-END)) (t-tokf M i TF-VAL)))))
(defn- t-nodef [M :vector-i64 i :i64 f :i64] :i64 (vector-at M (+ MM-NODE-BASE (* i MM-NODE-W) f)))
(defn- t-hnode [M :vector-i64 i :i64 h :i64] :i64
  (if (>= i (vector-at M MM-NODE-N))
    h
    (t-hnode M (+ i 1)
             (t-fold (t-fold (t-fold (t-fold (t-fold h (t-nodef M i NF-KIND)) (t-nodef M i NF-FIRST)) (t-nodef M i NF-NEXT))
                             (t-nodef M i NF-TOK)) (t-nodef M i NF-AUX)))))
(defn- t-err [M :vector-i64] :i64
  (let [o (t-w "ERR ") o1 (t-wn (vector-at M MM-ERR)) o2 (t-w " ") o3 (t-wn (vector-at M MM-ERR-POS)) o4 (t-w " ")
        o5 (t-wn (vector-at M MM-ERR-A)) o6 (t-w " ") o7 (t-wn (vector-at M MM-ERR-B)) o8 (t-w " ")
        o9 (t-wn (vector-at M MM-ERR-N))]
    (t-w "\n")))
(defn- t-ok [M :vector-i64] :i64
  (let [o (t-w "toks=") o1 (t-wn (- (vector-at M MM-TOK-N) 1)) o2 (t-w " tokhash=") o3 (t-wn (t-htok M 1 -3750763034362895579))@TREE2@]
    (t-w "\n")))
(defn- t-report [M :vector-i64] :i64
  (if (= (vector-at M MM-ERR) 0) (t-ok M) (t-err M)))
(defn- t-after [M :vector-i64 root :string k :i64] :i64
  (let [o (t-w (t-nm k)) o1 (t-w " ") o2 (t-report M)]
    (t-loop M root (+ k 1))))
(defn- t-loop [M :vector-i64 root :string k :i64] :i64
  (if (>= k @N@)
    0
    (let [path (string-concat root (string-concat "/" (t-rel k)))
          S (typed-cap-call :fs/app-data :string :string path)]
      (t-after @RUN@ root k))))
(defn- seed-main [] :i64
  (let [root (typed-cap-call :cli/args :string :string "0")]
    (t-loop (vector-alloc MM-WORDS) root 0)))
'''


def gen_unit_tests():
    rels = "\n".join('    (= k %d) "%s"' % (i, r) for i, (_, r) in enumerate(FILES))
    names = "\n".join('    (= k %d) "%s"' % (i, n) for i, (n, _) in enumerate(FILES))
    for mod, tree, deps in (("10-lex", False, ""), ("11-read", True, "10-lex")):
        t = UNIT_TMPL
        run = "(lx-run (t-reset M) S)" if not tree else "(rd-run (lx-run (t-reset M) S) S)"
        t = t.replace("@MOD@", mod).replace("@N@", str(len(FILES))).replace("@DEPS@", deps).replace("@RELS@", rels).replace("@NAMES@", names)
        t = t.replace("@TREE1@", " and every node" if tree else "")
        t = t.replace("@TREE2@", "\n        o4 (t-w \" nodes=\") o5 (t-wn (- (vector-at M MM-NODE-N) 1)) o6 (t-w \" nodehash=\") o7 (t-wn (t-hnode M 1 -3750763034362895579))" if tree else "")
        t = t.replace("(t-after @RUN@ root k)", "(t-after %s root k)" % run)
        with open(os.path.join(REPO, "seed/tests/unit/%s_t.kotoba" % mod), "w") as f:
            f.write(t)


def check():
    bad = 0
    for name, rel in FILES:
        src = readf(rel)
        t1 = dump_tree(src)
        if t1.startswith("ERR"):
            continue
        t2 = dump_tree(t1.encode("ascii"))
        if t1 != t2:
            print("NOT A FIXED POINT:", name)
            bad += 1
    print("check: canonical print fixed point on all accepted files" if not bad else "check: %d failures" % bad)
    return bad


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "dump":
        sys.stdout.write({"tok": dump_tok, "tree": dump_tree, "stat": dump_stat}[sys.argv[2]](open(sys.argv[3], "rb").read()))
    elif cmd == "gen":
        gen()
    elif cmd == "check":
        sys.exit(1 if check() else 0)
    else:
        print(__doc__)
        sys.exit(2)
