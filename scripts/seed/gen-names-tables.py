#!/usr/bin/env python3
"""scripts/seed/gen-names-tables.py -- regenerate the spelling tables of seed/20-names.kotoba (nm-head-code,
nm-kw-code) between the markers ';; BEGIN GENERATED SPELLINGS' / ';; END GENERATED SPELLINGS'. BOOTSTRAP-TOOL.

A spelling is packed little-endian, 8 bytes per word (nm-pack: byte k of word j at bits 8k), zero beyond the end;
spellings longer than 24 bytes are not recognised (nm-spelling-code). The tables nest by w2, then w1, then w0.
The head and keyword lists are seed/HEADS (:heads codes and spellings, :keywords). Run after editing them;
`--check` exits 1 when the file differs.
"""
import sys, pathlib

HEADS = [  # (spelling, constant)
    ("ns", "HD-NS"), ("defn", "HD-DEFN"), ("defn-", "HD-DEFN-PRIV"), ("def", "HD-DEF"), ("let", "HD-LET"),
    ("loop", "HD-LOOP"), ("recur", "HD-RECUR"), ("if", "HD-IF"), ("and", "HD-AND"), ("or", "HD-OR"),
    ("not", "HD-NOT"), ("=", "HD-EQ"), ("<", "HD-LT"), (">", "HD-GT"), ("<=", "HD-LE"), (">=", "HD-GE"),
    ("+", "HD-ADD"), ("-", "HD-SUB"), ("*", "HD-MUL"), ("quot", "HD-QUOT"), ("bit-and", "HD-BIT-AND"),
    ("bit-or", "HD-BIT-OR"), ("bit-xor", "HD-BIT-XOR"), ("bit-not", "HD-BIT-NOT"),
    ("u64-shift-right", "HD-USHR"), ("i64-shift-left", "HD-SHL"), ("i64-shift-right", "HD-SSHR"),
    ("vector-at", "HD-VECTOR-AT"), ("vector-conj", "HD-VECTOR-CONJ"), ("vector-assoc", "HD-VECTOR-ASSOC"),
    ("vector-assoc!", "HD-VECTOR-ASSOC-BANG"), ("vector-alloc", "HD-VECTOR-ALLOC"),
    ("string-code-point-at", "HD-STRING-CODE-POINT-AT"), ("string-length", "HD-STRING-LENGTH"),
    ("typed-cap-call", "HD-TYPED-CAP-CALL"), ("bytes-from-vector-i64", "HD-BYTES-FROM-VECTOR-I64"),
    ("string-concat", "HD-STRING-CONCAT"), ("cond", "HD-COND"), ("vector-i64-from-bytes", "HD-VECTOR-I64-FROM-BYTES"),
    # R1
    ("do", "HD-DO"), ("when", "HD-WHEN"), ("when-not", "HD-WHEN-NOT"), ("if-not", "HD-IF-NOT"), ("case", "HD-CASE"),
    ("condp", "HD-CONDP"), ("->", "HD-THREAD-FIRST"), ("->>", "HD-THREAD-LAST"), ("as->", "HD-AS-THREAD"),
    ("cond->", "HD-COND-THREAD"), ("cond->>", "HD-COND-THREAD-LAST"), ("dotimes", "HD-DOTIMES"),
    ("doseq", "HD-DOSEQ"), ("range", "HD-RANGE"), ("inc", "HD-INC"), ("dec", "HD-DEC"), ("zero?", "HD-ZERO"),
    ("pos?", "HD-POS"), ("neg?", "HD-NEG"), ("not=", "HD-NOT-EQ"), ("assert", "HD-ASSERT"), ("true", "HD-TRUE"),
    ("false", "HD-FALSE"), ("vector-count", "HD-VECTOR-COUNT"), ("record-new", "HD-RECORD-NEW"),
    ("record", "HD-RECORD"), ("record-get", "HD-RECORD-GET"), ("defrecord", "HD-DEFRECORD"), ("get", "HD-GET"),
    ("assoc", "HD-ASSOC"),
]
KWS = [
    (":i64", "KW-I64"), (":bool", "KW-BOOL"), (":string", "KW-STRING"), (":vector-i64", "KW-VECTOR-I64"),
    (":export", "KW-EXPORT"), (":else", "KW-ELSE"), (":bytes", "KW-BYTES"), (":fs/app-data", "KW-FS-APP-DATA"),
    (":cli/args", "KW-CLI-ARGS"), (":io/write-error", "KW-IO-WRITE-ERROR"), (":io/write", "KW-IO-WRITE"),
    (":fs/app-data-bytes", "KW-FS-APP-DATA-BYTES"),
    (":keyword", "KW-KEYWORD"), (":record", "KW-RECORD"), (":let", "KW-LET"), (":when", "KW-WHEN"),
    (":while", "KW-WHILE"),
]


def pack(s, j):
    w = 0
    for k in range(7, -1, -1):
        i = 8 * j + k
        w = (w << 8) | (ord(s[i]) if i < len(s) else 0)
    return w - (1 << 64) if w >= (1 << 63) else w


def table(name, entries, doc):
    assert all(len(s) <= 24 for s, _ in entries)
    # R1: the tables are written with `case` (the seed is compiled by an R1 seed from rung 1 on)
    out = [doc, f"(defn- {name} [w0 :i64 w1 :i64 w2 :i64] :i64", "  (case w2"]
    by2 = {}
    for s, c in entries:
        by2.setdefault(pack(s, 2), {}).setdefault(pack(s, 1), []).append((pack(s, 0), c, s))
    for w2, by1 in by2.items():
        out.append(f"    {w2}")
        out.append("    (case w1")
        for w1, rows in by1.items():
            out.append(f"      {w1}")
            out.append("      (case w0")
            for w0, c, s in rows:
                out.append(f"        {w0} {c}  ; {s}")
            out.append("        0)")
        out.append("      0)")
    out.append("    0))")
    return "\n".join(out)


def main():
    p = pathlib.Path(__file__).resolve().parents[2] / "seed" / "20-names.kotoba"
    src = p.read_text()
    a = src.index(";; BEGIN GENERATED SPELLINGS\n") + len(";; BEGIN GENERATED SPELLINGS\n")
    b = src.index(";; END GENERATED SPELLINGS")
    body = table("nm-head-code", HEADS,
                 ";; head code of a symbol spelling (seed/HEADS :spellings) from its packed words w0 w1 w2, 0 if none.") \
        + "\n\n" + table("nm-kw-code", KWS,
                         ";; KW-* code of a keyword spelling (the ':' included) from its packed words, 0 if none.") + "\n"
    new = src[:a] + body + src[b:]
    if "--check" in sys.argv:
        sys.exit(0 if new == src else 1)
    p.write_text(new)
    print(f"gen-names-tables: {len(HEADS)} heads, {len(KWS)} keywords -> {p}")


if __name__ == "__main__":
    main()
