"""Minimal Clojure/ClojureScript/Kotoba source parser (stdlib only).

Produces a concrete tree with exact source offsets so a file can be cut into
top-level forms and re-emitted byte-for-byte.  Reader conditionals (#?, #?@)
are kept as ordinary nodes so EVERY branch is visible to the analyses.

Node: Node(kind, children, start, end, text)
  kind in: list vec map set fn rc rcs sym kw str num char regex other
           meta (^x y)  quote (' ` ~ ~@ @ #')  discard (#_ x)  nsmap (#:a{})
"""
import re

class Node:
    __slots__ = ("kind", "kids", "start", "end", "text")
    def __init__(self, kind, kids, start, end, text=None):
        self.kind, self.kids, self.start, self.end, self.text = kind, kids, start, end, text
    def __repr__(self):
        return f"<{self.kind} {self.text if self.text is not None else len(self.kids)} @{self.start}>"

CLOSERS = {"(": ")", "[": "]", "{": "}"}
WS = " \t\r\n,\f"
DELIM = WS + "()[]{}\";"

class ParseError(Exception):
    pass

def parse(src):
    """Return (top_level_nodes, src).  Comments/whitespace are trivia (kept via offsets)."""
    n = len(src)
    pos = 0

    def skip_trivia(i):
        while i < n:
            c = src[i]
            if c in WS:
                i += 1
            elif c == ";":
                while i < n and src[i] != "\n":
                    i += 1
            else:
                break
        return i

    def read_form(i):
        i = skip_trivia(i)
        if i >= n:
            raise ParseError("eof")
        c = src[i]
        s = i
        if c in "([{":
            kind = {"(": "list", "[": "vec", "{": "map"}[c]
            return read_seq(i + 1, CLOSERS[c], kind, s)
        if c == '"':
            j = i + 1
            while j < n and src[j] != '"':
                j += 2 if src[j] == "\\" else 1
            return Node("str", [], s, j + 1, src[s:j + 1])
        if c == "\\":
            j = i + 2
            while j < n and src[j] not in DELIM:
                j += 1
            return Node("char", [], s, j, src[s:j])
        if c in "'`@":
            k = read_form(i + 1)
            return Node("quote", [k], s, k.end, c)
        if c == "~":
            j = i + 1
            if j < n and src[j] == "@":
                j += 1
            k = read_form(j)
            return Node("quote", [k], s, k.end, src[s:j])
        if c == "^":
            m = read_form(i + 1)
            k = read_form(m.end)
            return Node("meta", [m, k], s, k.end)
        if c == "#":
            nx = src[i + 1] if i + 1 < n else ""
            if nx == "{":
                return read_seq(i + 2, "}", "set", s)
            if nx == "(":
                return read_seq(i + 2, ")", "fn", s)
            if nx == "?":
                j = i + 2
                kind = "rc"
                if j < n and src[j] == "@":
                    kind = "rcs"
                    j += 1
                if src[j] != "(":
                    raise ParseError(f"bad reader conditional at {i}")
                return read_seq(j + 1, ")", kind, s)
            if nx == '"':
                j = i + 2
                while j < n and src[j] != '"':
                    j += 2 if src[j] == "\\" else 1
                return Node("regex", [], s, j + 1, src[s:j + 1])
            if nx == "_":
                k = read_form(i + 2)
                return Node("discard", [k], s, k.end)
            if nx == "'":
                k = read_form(i + 2)
                return Node("quote", [k], s, k.end, "#'")
            if nx == ":":  # namespaced map #:ns{...} / #::{...}
                j = i + 2
                while j < n and src[j] not in DELIM:
                    j += 1
                k = read_form(j)
                return Node("nsmap", [k], s, k.end, src[s:j])
            if nx == "#":  # ##Inf
                j = i + 2
                while j < n and src[j] not in DELIM:
                    j += 1
                return Node("other", [], s, j, src[s:j])
            # tagged literal  #inst "..." / #js {...}
            j = i + 1
            while j < n and src[j] not in DELIM:
                j += 1
            k = read_form(j)
            return Node("tagged", [k], s, k.end, src[s:j])
        j = i
        while j < n and src[j] not in DELIM:
            j += 1
        if j == i:
            raise ParseError(f"unexpected {c!r} at {i}")
        t = src[i:j]
        if t[0] == ":":
            kind = "kw"
        elif re.match(r"^[-+]?\d", t):
            kind = "num"
        else:
            kind = "sym"
        return Node(kind, [], s, j, t)

    def read_seq(i, closer, kind, s):
        kids = []
        while True:
            i = skip_trivia(i)
            if i >= n:
                raise ParseError(f"unterminated {kind} starting at {s}")
            if src[i] == closer:
                return Node(kind, kids, s, i + 1)
            if src[i] in ")]}":
                raise ParseError(f"mismatched {src[i]} at {i} (open {kind} at {s})")
            k = read_form(i)
            kids.append(k)
            i = k.end

    tops = []
    while True:
        pos = skip_trivia(pos)
        if pos >= n:
            break
        k = read_form(pos)
        tops.append(k)
        pos = k.end
    return tops

def strip_meta(node):
    """Skip ^meta wrappers: return the underlying form."""
    while node.kind == "meta":
        node = node.kids[1]
    return node

def meta_of(node):
    """Meta nodes attached in front of `node` (returned as a list of meta-expression nodes)."""
    out = []
    while node.kind == "meta":
        out.append(node.kids[0])
        node = node.kids[1]
    return out

def walk(node):
    yield node
    for k in node.kids:
        yield from walk(k)
