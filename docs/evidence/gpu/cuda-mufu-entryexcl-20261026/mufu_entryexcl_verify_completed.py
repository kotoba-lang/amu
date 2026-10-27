#!/usr/bin/env python3
"""mufu_entryexcl_verify.py -- deterministic body extraction over
`nvdisasm -c` output of the gpu-mufu-entryexcl-microbench cubin (v6 of
the interleaved-spelling row -- the ENTRY-EXCLUDED OPEN-CHAIN
instrument; scratch, never staged). Per function: the exact LOOP BODY
(label -> a BRA back to that label, inclusive) printed VERBATIM as an
ordered mnemonic list, and three verdicts:
  1. CHAIN counts: the body must carry exactly the named word's chain
     opcodes (MUFU.RSQ / FADD*) at its named counts -- numbers are never
     attributed to a MUFU spelling the SASS does not carry.
  2. CLOCK-WRAP: exactly two CS2R SR_CLOCKLO reads in the body, with the
     chain's instructions strictly between them (the entry-excluded
     discipline's timed region).
  3. OVERHEAD-IDENTICAL: the multiset of every NON-chain instruction in
     the loop body must be IDENTICAL across all eight arms (the
     estimator/closure floor cancellation is structural only if the
     timed-region heads and tails are the same instructions).
No timing, no arithmetic beyond counts."""
import re, sys
from collections import Counter

path = sys.argv[1]
text = open(path).read().splitlines()

label_re = re.compile(r"^\.text\.(_Z\d+\w+):\s*$")
ins_re = re.compile(r"^\s*/\*([0-9a-fA-F]+)\*/\s+(.*?)\s*$")
lbl_re = re.compile(r"^\.(\w+):\s*$")
bra_re = re.compile(r"\bBRA\b\s+`\(\.(\w+)\)")

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


def strip_pred(op):
    # drop a leading execution predicate: @!PT / @P0 / @!P1 ...
    parts = op.split()
    if parts and parts[0].startswith("@"):
        parts = parts[1:]
    return " ".join(parts)


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
        funcs[cur].append(("ins", strip_pred(m.group(2))))
        continue
    m = lbl_re.match(ln)
    if m:
        funcs[cur].append(("lbl", m.group(1)))


def loop_body(items):
    labels = {}
    for i, (k, v) in enumerate(items):
        if k == "lbl":
            labels.setdefault(v, i)
    for i, (k, v) in enumerate(items):
        if k != "ins":
            continue
        m = bra_re.search(v)
        if not m:
            continue
        tgt = m.group(1)
        if tgt in labels and labels[tgt] < i:
            return items[labels[tgt] : i + 1]
    return None


def classify(op):
    base = op.split()[0]
    if base.startswith("FADD"):
        return "FADD*"
    return base


def chain_counts(body):
    c = Counter()
    for k, v in body:
        if k != "ins":
            continue
        b = classify(v)
        if b == "FADD*" or b.startswith("MUFU"):
            c[b if b == "FADD*" else v.split()[0]] += 1
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


def clock_wrap_check(body):
    # exactly two CS2R SR_CLOCKLO, chain ops strictly between them
    seq = [v for k, v in body if k == "ins"]
    idx = [i for i, v in enumerate(seq)
           if v.split()[0] == "CS2R" and "SR_CLOCKLO" in v]
    if len(idx) != 2:
        return f"WRAP-BAD ({len(idx)} SR_CLOCKLO reads in body)"
    lo, hi = idx
    between = seq[lo + 1 : hi]
    chain = [v for v in between
             if classify(v) == "FADD*" or classify(v).startswith("MUFU")]
    nonchain_between = [v for v in between if v not in chain]
    ok = len(chain) == len(between)
    return ("WRAP-OK (chain strictly between the two SR_CLOCKLO reads)"
            if ok else
            f"WRAP-MIXED (non-chain instructions inside the timed region: {nonchain_between})")


print("=== per-function loop-body extraction (nvdisasm -c of the entry-excluded cubin)")
overheads = {}
all_ok = True
wrap_ok = True
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
    w = clock_wrap_check(body)
    print(f"    {w}")
    if not w.startswith("WRAP-OK"):
        wrap_ok = False
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
        print(f"    OVERHEAD-DIFF vs {base_name}: +{dict(overheads[name] - base)} / -{dict(base - overheads[name])}")
print("OVERHEAD-VERDICT: " + ("IDENTICAL 8/8" if identical and len(overheads) == 8
                             else f"NOT IDENTICAL ({len(overheads)} arms compared)"))
print("CHAIN-VERDICT-ALL: " + ("MATCH 8/8" if all_ok else "NOT 8/8 MATCH"))
print("CLOCK-WRAP-VERDICT-ALL: " + ("WRAP-OK 8/8" if wrap_ok else "NOT 8/8 WRAP-OK"))
