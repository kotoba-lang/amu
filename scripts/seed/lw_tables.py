#!/usr/bin/env python3
"""scripts/seed/lw_tables.py SRC OUT -- BOOTSTRAP-TOOL (test-only, owner 30-lower).

Writes the TOK, NODE, LIT and LITB tables of SRC as decimal text for the 30-lower gate's reference front end
(seed/tests/unit/30-lower-refload.kotoba), from the Python reference lexer/reader scripts/seed/lexread_ref.py
(owner 10-lex/11-read). Used by lw-gate.sh LW_FRONT=ref while 10-lex/11-read are not buildable by stage-0.
Format: "<ntok> <nnode> <nlit> <nlitb>", then 4 words per token, 5 per node (NF-KIND FIRST NEXT TOK AUX),
4 per literal (LF-B LF-LEN 0 LF-TOK), then the LITB bytes. Index order from 1. A lex/read error writes "0 0 0 0".
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lexread_ref as LR

def tables(src):
    try:
        toks, lits = LR.lex(src)
        root = LR.read(toks)
    except LR.Err:
        return "0 0 0 0\n"
    nodes = LR.nodes_flat(root)
    littok = {}
    for i, t in enumerate(toks):
        if t[0] == LR.TK["STR"]:
            littok[t[3]] = i + 1
    out = ["%d %d %d %d" % (len(toks), len(nodes), len(lits), sum(len(l) for l in lits))]
    out += ["%d %d %d %d" % t for t in toks]
    out += ["%d %d %d %d %d" % n for n in nodes]
    b = 1  # LITB index 0 is the null record
    for k, l in enumerate(lits):
        out.append("%d %d 0 %d" % (b, len(l), littok[k + 1]))
        b += len(l)
    allb = b"".join(lits)
    for i in range(0, len(allb), 32):
        out.append(" ".join(str(x) for x in allb[i:i + 32]))
    return "\n".join(out) + "\n"

if __name__ == "__main__":
    open(sys.argv[2], "w").write(tables(open(sys.argv[1], "rb").read()))
