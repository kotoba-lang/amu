#!/usr/bin/env python3
"""seed/tests/text/gen.py -- the kotoba.lang.text differential: inputs, driver, digests (agent TEXT, 2026-10-04).
BOOTSTRAP-TOOL (python, host only: it writes the driver and the input table and folds answers; every answer it compares is
computed by the host library or by native code).

  gen.py gen <out-dir> [group-size]   writes <out-dir>/main.kotoba (a driver requiring kotoba.lang.text :as t: one arity-0
                                      export gK per group of cases, each folding the digests of its cases into one i64),
                                      <out-dir>/cases.json ([[group, fn, args..] ..], read by host.cljk), and prints the count
  gen.py fold <out-dir> <host.json>   the expected value of every group from the HOST library's answers (host.json, written
                                      by host.cljk: one answer per case, in order) as "gK value" lines

Digests (the same fold in the driver and here, i64 wrap-around): a string is its UTF-8 bytes folded h = len; h = h*31 + b;
a list of strings h = count; h = h*31 + digest(item); a bool 0/1; an option i64 the value or -1 when absent; a group
h = 0; h = h*1000003 + digest(case). The input table is the one of kotoba-lang test/kotoba/lang/kotoba_lang_text_compat_test
(multi-byte, astral, every Java whitespace, empty) plus split / split-lines / join tables.
"""
import json, os, sys

STRINGS = ["", "a", "ab", "hello", "ababa", "あいう", "aあb", "日本語", "a😀b", "😀😀", "aあ😀",
           " ", "\t", "\n", " a ", "\t\ta\n", "　a　", " a ", " a",
           " a ", "\u0085a\u0085", " a ", " a ", " あ ",
           "😀 ", " 😀", "\u000b\u000c", "\u001c\u001f a", "x ", "日本語　", "\r\n", "á", "🇯🇵"]
NEEDLES = ["", "a", "b", "ab", "he", "lo", "ba", "z", "あ", "い", "いう", "aあ", "あb", "本", "語", "😀", "😀b", " ",
           "　", "abc"]
REPLACE_S = ["", "a", "abc", "a.b.c", "ababa", "aaa", "あいう", "a/b/c", "日本語日本", "a😀b😀", "x$1y", "--a--"]
REPLACE_M = [".", "a", "ab", "aa", "/", "あ", "本", "😀", "-", "z", "$1", "abc"]
REPLACE_R = ["", "x", "/", "$1", "\\\\", "あ", "😀", "xyz"]
SPLIT_S = ["", "a", "a,b", "a,,b,,", ",a", "a::b::", "aあbあ", "😀x😀", "a/b/c/", "..a..b..", "abc", "a,b,c,d,e",
           ",,,", "x\ny\n"]
SPLIT_SEP = [",", "::", "/", ".", "あ", "😀", "x", "ab", "\n", "", "a,"]
SPLIT_LIMIT = [None, 1, 2, 3, -1]
LINES = ["", "a", "a\n", "a\r\nb", "a\rb", "\n\n", "a\n\nb\n", "\r\n", "あ\r\nい\r\n\r\n", "x\r", "\r", "a\r\r\nb",
         "\n", "\na", "😀\n😀\r\n"]
JOIN_SEP = ["", ",", ", ", "あ", "😀"]
JOIN_LISTS = [[], ["a"], ["a", "bb"], ["a", "", "日本"], ["😀", "あ", "b"]]

M64 = (1 << 64) - 1


def wrap(x):
    x &= M64
    return x - (1 << 64) if x >> 63 else x


def lit(s):
    out = ['"']
    for ch in s:
        o = ord(ch)
        if ch == '"': out.append('\\"')
        elif ch == '\\': out.append('\\\\')
        elif ch == '\n': out.append('\\n')
        elif ch == '\t': out.append('\\t')
        elif ch == '\r': out.append('\\r')
        elif o < 0x20 or o == 0x7f: out.append('\\u%04x' % o)
        else: out.append(ch)
    out.append('"')
    return ''.join(out)


def cases():
    c = []
    pairs = [(s, n) for s in STRINGS for n in NEEDLES]
    for f in ("starts-with?", "ends-with?", "includes?", "index-of", "last-index-of"):
        c += [[f, s, n] for s, n in pairs]
    for f in ("blank?", "trim", "triml", "trimr", "reverse"):
        c += [[f, s] for s in STRINGS]
    c += [["replace", s, m, r] for s in REPLACE_S for m in REPLACE_M for r in REPLACE_R]
    for s in SPLIT_S:
        for sep in SPLIT_SEP:
            # an EMPTY separator over an astral character: the nbb host (the oracle run here) splits between UTF-16 units and
            # answers lone surrogates, which no UTF-8 :string can hold; the twin splits between code points (its header).
            # Not comparable, so not generated (measured 2026-10-04: every such case answered a lone surrogate).
            if sep == "" and any(ord(ch) > 0xffff for ch in s):
                continue
            for lim in SPLIT_LIMIT:
                c.append(["split", s, sep] if lim is None else ["split", s, sep, lim])
    c += [["split-lines", s] for s in LINES]
    c += [["join", sep, xs] for sep in JOIN_SEP for xs in JOIN_LISTS]
    return c


KIND = {"starts-with?": "bool", "ends-with?": "bool", "includes?": "bool", "blank?": "bool",
        "index-of": "opt", "last-index-of": "opt", "split": "list", "split-lines": "list",
        "trim": "str", "triml": "str", "trimr": "str", "reverse": "str", "replace": "str", "join": "str"}

PRELUDE = '''(defn- dbytes [b :bytes] :i64 (loop [i 0 h (bytes-count b)] (if (>= i (bytes-count b)) h (recur (+ i 1) (+ (* h 31) (bytes-at b i))))))
(defn- dstr [s :string] :i64 (dbytes (string-to-utf8 s)))
(defn- dlist [xs [:list :string]] :i64 (loop [i 0 h (vector-count xs)] (if (>= i (vector-count xs)) h (recur (+ i 1) (+ (* h 31) (dstr (typed-list-nth [:list :string] xs i)))))))
(defn- dbool [b :bool] :i64 (if b 1 0))
(defn- dopt [o [:option :i64]] :i64 (option-or o -1))
(defn- mix [h :i64 d :i64] :i64 (+ (* h 1000003) d))
'''


def call(case):
    f, args = case[0], case[1:]
    if f == "join":
        xs = args[1]
        items = ' '.join(lit(x) for x in xs)
        a = '%s (typed-list-new [:list :string]%s)' % (lit(args[0]), (' ' + items) if items else '')
    else:
        a = ' '.join(str(x) if isinstance(x, int) else lit(x) for x in args)
    d = {"bool": "dbool", "opt": "dopt", "list": "dlist", "str": "dstr"}[KIND[f]]
    return '(%s (t/%s %s))' % (d, f, a)


def gen(out, size):
    cs = cases()
    groups = [cs[i:i + size] for i in range(0, len(cs), size)]
    names = ['g%d' % k for k in range(len(groups))]
    src = ['(ns text-diff\n  (:require [kotoba.lang.text :as t])\n  (:export [%s]))\n' % ' '.join(names), PRELUDE]
    table = []
    for k, g in enumerate(groups):
        e = '0'
        for c in g:
            e = '(mix %s %s)' % (e, call(c))
            table.append(['g%d' % k] + c)
        src.append('(defn g%d [] :i64 %s)\n' % (k, e))
    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, 'main.kotoba'), 'w', encoding='utf-8').write(''.join(src))
    json.dump(table, open(os.path.join(out, 'cases.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    print('%d cases in %d groups' % (len(cs), len(groups)))


def digest(kind, v):
    if kind == 'bool': return 1 if v else 0
    if kind == 'opt': return -1 if v is None else v
    if kind == 'str':
        b = v.encode('utf-8'); h = len(b)
        for x in b: h = wrap(h * 31 + x)
        return h
    if kind == 'list':
        h = len(v)
        for x in v: h = wrap(h * 31 + digest('str', x))
        return h


def fold(out, hostjson):
    table = json.load(open(os.path.join(out, 'cases.json'), encoding='utf-8'))
    answers = json.load(open(hostjson, encoding='utf-8'))
    assert len(answers) == len(table), (len(answers), len(table))
    acc = {}
    order = []
    for row, v in zip(table, answers):
        g, f = row[0], row[1]
        if g not in acc: acc[g] = 0; order.append(g)
        acc[g] = wrap(acc[g] * 1000003 + digest(KIND[f], v))
    for g in order: print(g, acc[g])


if __name__ == '__main__':
    if sys.argv[1] == 'gen': gen(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 40)
    elif sys.argv[1] == 'fold': fold(sys.argv[2], sys.argv[3])
