#!/usr/bin/env python3
"""mufu_entryexcl_verify.py -- deterministic body extraction over
`nvdisasm -c` output of the gpu-mufu-entryexcl-microbench cubin (v6 of
the interleaved-spelling row -- the ENTRY-EXCLUDED OPEN-CHAIN
instrument; scratch, never staged). Per function: the exact LOOP BODY
(label -> a BRA back to that label, inclusive) printed VERBATIM as an
ordered mnemonic list, the full static opcode histogram, and two
verdicts:
  1. CHAIN counts: the body must carry exactly the named word's chain
     opcodes (MUFU.RSQ / FADD*) at its named counts -- numbers are never
     attributed to a MUFU spelling the SASS does not carry.
  2. OVERHEAD-IDENTICAL: the multiset of every NON-chain instruction in
     the loop body must be IDENTICAL across all eight arms (the
     estimator/closure floor cancellation is structural only if the
     timed-region tails and heads are the same instructions).
No timing, no arithmetic beyond counts."""
import re, sys
from collections import Counter

path = sys.argv[1]
text = open(path).read().splitlines()

label_re = re.compile(r"^\.text\.(_Z\d+[A-Za-z0-9_]+)Py:\s*$")
ins_re = re.compile(r"^\s*/\*([0-9a-fA-F]+)\*/\s+(.*)$")
lbl_re = re.compile(r"^\.(\w+):\s*$")

EXPECTED = {
    "ee_M":   {"MUFU.RSQ": 1},
    "ee_F":   {"FADD*": 1},
    "ee_MM":  {"MUFU.RSQ": 2},
    "ee_FF":  {"FADD*": 2},
    "ee_MF":  {"MUFU.RSQ": 1, "FADD*": 1},
    "ee_FM":  {"MUFU.RSQ": 1, "FADD*": 1},
    "ee_MFM": {"MUFU.RSQ": 2, "FADD*": 1},
    "ee_FMF": {"MUFU.RSQ": 1, "FADD*": 2},
}
ORDER = ["ee_M", "ee_F", "ee_MM", "ee_FF", "ee_MF", "ee_FM", "ee_MFM", "ee_FMF"]


def demangle(sym):
    m = re.match(r"_Z(\d+)(\w+)", sym)
    if m:
        return m.group(2)[: int(m.group(1))]
    return sym


def mnemonic(body_item):
    # strip opcode suffixes for classification: FADD.FTZ.F32 -> FADD
    op = body_item.split()[0] if body_item.split() else "?"
    return op


funcs = {}
cur = None
for ln in text:
    m = label_re.match(ln)
    if m:
        cur = demangle(m.group(1))
        funcs.setdefault(cur, [])
        continue
    if cur is None:
        continue
    m = ins_re.match(ln)
    if m:
        funcs[cur].append(("ins", m.group(2).strip()))
        continue
    m = lbl_re.match(ln)
    if m:
        funcs[cur].append(("lbl", m.group(1)))


def loop_body(items):
    # find a BRA back to a label inside items; body = label..BRA inclusive
    labels = {}
    for i, (k, v) in enumerate(items):
        if k == "lbl":
            labels[v] = i
    for i, (k, v) in enumerate(items):
        if k != "ins":
            continue
        m = re.search(r"^\S+\s+.*\b(?:BRA|BRX)\b.*?\.(\w+)\s*$", v) or re.search(r"\b(?:BRA|BRX)\b\s+.*?(\w+)\s*$", v)
        if not m:
            continue
        tgt = m.group(1)
        if tgt in labels and labels[tgt] < i:
            return items[labels[tgt] : i + 1]
    return None


def classify(op):
    base = op.split()[0]
    if base.startswith("FADD") or base.startswith("FADD"):
        return "FADD*"
    return base


def chain_counts(body):
    c = Counter()
    for k, v in body:
        if k != "ins":
            continue
        b = classify(v)
        if b == "FADD*":
            c["FADD*"] += 1
        elif b.startswith("MUFU"):
            c[v.split()[0]] += 1
    return c


def nonchain_multiset(body):
    c = Counter()
    for k, v in body:
        if k != "ins":
            continue
        b = classify(v)
        if b == "FADD*" or b.startswith("MUFU"):
            continue
        c[v.split()[0]] += 1
    return c


print("=== per-function loop-body extraction (nvdisasm -c of the entry-excluded cubin)")
overheads = {}
all_ok = True
for name in ORDER:
    if name not in funcs:
        print(f"{name}: MISSING FUNCTION")
        all_ok = False
        continue
    body = loop_body(funcs[name])
    if body is None:
        print(f"{name}: NO-LOOP (body folded or loop-free) -- realized static histogram: "
              + str(Counter(classify(v) for k, v in funcs[name] if k == 'ins')))
        all_ok = False
        continue
    print(f"--- {name}: loop body ({len(body)} lines), verbatim mnemonics:")
    for k, v in body:
        if k == "ins":
            print(f"    {v}")
        else:
            print(f"    .{v}:")
    got = chain_counts(body)
    exp = EXPECTED[name]
    ok = all(got.get(k, 0) == v for k, v in exp.items()) and all(
        k in exp for k in got)
    print(f"    CHAIN-VERDICT {name}: expected {dict(exp)} realized {dict(got)} -> "
          + ("MATCH" if ok else "DIFFERENT"))
    if not ok:
        all_ok = False
    overheads[name] = nonchain_multiset(body)

print("=== non-chain overhead multiset per arm (the common floor's instructions)")
base = None
base_name = None
identical = True
for name in ORDER:
    if name not in overheads:
        continue
    print(f"    {name}: {dict(sorted(overheads[name].items()))}")
    if base is None:
        base = overheads[name]
        base_name = name
    elif overheads[name] != base:
        identical = False
        print(f"    OVERHEAD-DIFF vs {base_name}: {dict(overheads[name] - base)} / {dict(base - overheads[name])}")
print(f"OVERHEAD-VERDICT: " + ("IDENTICAL 8/8" if identical and len(overheads) == 8 else f"NOT IDENTICAL ({len(overheads)} arms compared)"))
print(f"CHAIN-VERDICT-ALL: " + ("MATCH 8/8" if all_ok else "NOT 8/8 MATCH"))
