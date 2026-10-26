#!/usr/bin/env python3
# Identifiability analysis for the e_MF / e_FM cross-edge split in the
# edge-additive dependent-chain model (ADR-0361 twenty-ninth amendment).
#
# Model (the twenty-eighth amendment's own frame): the cost of a dependent
# chain is a sum of edge prices along the chain path. Node types: M =
# MUFU.RSQ-class op, F = FADD-class op (2-type families), U = a third
# same-accumulator op (3-type families). Variables per family:
#   e_{i,j}  : price of the edge from an op of type i to a consumer of type j
#              (self edges i==j included)
#   a_i      : entry edge (seed producer -> first op), only where the timed
#              region includes the chain's start
#   b_i      : exit edge (last op -> sink consumer)
#   f        : floor intercept
# Every measured quantity in every chain form is a PATH SUM over these
# variables (loop-carried bodies are cyclic path sums: consecutive edges
# plus the loop back edge).
#
# PRE-REGISTERED PREDICTIONS (written before the first run):
#   P1 family A (loop-carried bodies, alphabet {M,F}): rank 3 of 4 edge
#      variables; nullspace = the e_MF - e_FM direction -> the SPLIT is NOT
#      identifiable, the SUM e_MF+e_FM is (this reproduces the twenty-eighth
#      amendment's rotation-counting result mechanically).
#   P2 family B (open chains, entry edge INSIDE the timed region): the
#      nullspace is a potential gauge (dimension |types|) -> the SPLIT is NOT
#      identifiable even with open chains. The twenty-eighth amendment's
#      "an open-chain form would be needed" is therefore NOT sufficient in
#      this discipline.
#   P3 family C (open chains, entry EXCLUDED by timing discipline: first
#      operand ready before the timing boundary): full rank -> the split IS
#      identifiable, with the estimator e_MF = V(MF) - V(F), e_FM = V(FM) -
#      V(M), and the falsifiable closure V(MFM) == V(MF) + V(FM) - V(F).
#   P4 family A over {M,F,U}: nullspace = 2-dim potential gauge -> the split
#      is NOT identifiable in ANY cyclic alphabet; only cycle sums are.
#
# This script computes ranks and nullspaces EXACTLY (rational arithmetic,
# Gauss-Jordan). It contains no measurements: it is a design analysis of
# what chain forms can and cannot identify.

from fractions import Fraction
from itertools import product

def rref(rows, ncols):
    mat = [[Fraction(x) for x in r] for r in rows]
    pivots = []
    r = 0
    for c in range(ncols):
        piv = None
        for i in range(r, len(mat)):
            if mat[i][c] != 0:
                piv = i
                break
        if piv is None:
            continue
        mat[r], mat[piv] = mat[piv], mat[r]
        inv = mat[r][c]
        mat[r] = [x / inv for x in mat[r]]
        for i in range(len(mat)):
            if i != r and mat[i][c] != 0:
                fac = mat[i][c]
                mat[i] = [a - fac * b for a, b in zip(mat[i], mat[r])]
        pivots.append(c)
        r += 1
        if r == len(mat):
            break
    return mat, pivots

def nullspace(rows, ncols):
    mat, pivots = rref(rows, ncols)
    pset = set(pivots)
    basis = []
    for fc in range(ncols):
        if fc in pset:
            continue
        v = [Fraction(0)] * ncols
        v[fc] = Fraction(1)
        for i, pc in enumerate(pivots):
            v[pc] = -mat[i][fc]
        basis.append(v)
    return basis, pivots

def sparse(v, names):
    return "{" + ", ".join(f"{n}:{x}" for x, n in zip(v, names) if x != 0) + "}"

def family_rows(types, kind, max_len):
    """kind: 'A' cyclic bodies (no entry/exit), 'B' open chains with entry,
    'C' open chains with entry excluded. Returns (rows, var_names)."""
    edges = [(i, j) for i in types for j in types]
    names = [f"e_{i}{j}" for i, j in edges]
    if kind == "A":
        extra = []
    elif kind == "B":
        extra = [f"a_{i}" for i in types]
    else:
        extra = []
    extra = extra + [f"b_{i}" for i in types] + ["f"]
    names = names + extra
    idx = {n: k for k, n in enumerate(names)}
    rows = []
    for L in range(1, max_len + 1):
        for w in product(types, repeat=L):
            row = [0] * len(names)
            if kind == "A":
                seq = list(w) + [w[0]]          # loop back edge closes it
                for s, t in zip(seq, seq[1:]):
                    row[idx[f"e_{s}{t}"]] += 1
            else:
                seq = list(w)
                if kind == "B":
                    row[idx[f"a_{w[0]}"]] += 1
                for s, t in zip(seq, seq[1:]):
                    row[idx[f"e_{s}{t}"]] += 1
                row[idx[f"b_{w[-1]}"]] += 1
                row[idx["f"]] += 1
            rows.append(row)
    return rows, names

def verdict(rows, names, functional_name, coef):
    ncols = len(names)
    basis, pivots = nullspace(rows, ncols)
    ident = True
    witness = None
    for v in basis:
        d = sum(Fraction(c) * x for c, x in zip(coef, v))
        if d != 0:
            ident = False
            witness = (v, d)
            break
    return ident, witness, len(basis), len(pivots)

def coef_vec(names, terms):
    v = [0] * len(names)
    for t, c in terms:
        v[names.index(t)] = c
    return v

def analyze(label, types, kind, max_len, functionals):
    rows, names = family_rows(types, kind, max_len)
    ncols = len(names)
    basis, pivots = nullspace(rows, ncols)
    print(f"=== {label}")
    print(f"alphabet={{{','.join(types)}}} form={kind} max_body_len={max_len} "
          f"rows={len(rows)} vars={ncols} rank={len(pivots)} null_dim={len(basis)}")
    for v in basis:
        print(f"  null: {sparse(v, names)}")
    for fname, terms in functionals:
        coef = coef_vec(names, terms)
        ident, witness, ndim, rk = verdict(rows, names, fname, coef)
        if ident:
            print(f"  {fname}: IDENTIFIABLE")
        else:
            print(f"  {fname}: NOT IDENTIFIABLE -- witness null vector "
                  f"{sparse(witness[0], names)} (dot={witness[1]})")
    print()
    return rows, names, basis

print("mufu-split-identifiability -- exact rank/nullspace analysis of the")
print("edge-additive chain model; no measurements in this file.")
print("PRE-REGISTERED PREDICTIONS P1..P4 are in the script header.")
print()

twotype = ["M", "F"]
three = ["M", "F", "U"]

f2 = [
    ("e_MF",            [("e_MF", 1)]),
    ("e_FM",            [("e_FM", 1)]),
    ("e_MF+e_FM",       [("e_MF", 1), ("e_FM", 1)]),
    ("e_MF-e_FM",       [("e_MF", 1), ("e_FM", -1)]),
    ("e_MM",            [("e_MM", 1)]),
    ("e_FF",            [("e_FF", 1)]),
]

analyze("P1 family A: loop-carried cyclic bodies (as-built instruments)",
        twotype, "A", 6, f2)

analyze("P2 family B: open chains, entry edge INSIDE the timed region",
        twotype, "B", 6, f2)

f2c = f2 + [
    ("e_MF-e_FM (estimator check)", [("e_MF", 1), ("e_FM", -1)]),
]
analyze("P3 family C: open chains, entry EXCLUDED by timing discipline",
        twotype, "C", 6, f2c)

f3 = [
    ("e_MF",            [("e_MF", 1)]),
    ("e_FM",            [("e_FM", 1)]),
    ("e_MF+e_FM",       [("e_MF", 1), ("e_FM", 1)]),
    ("e_MF-e_FM",       [("e_MF", 1), ("e_FM", -1)]),
]
analyze("P4 family A over three node types: cyclic bodies",
        three, "A", 5, f3)

analyze("P4b family B over three node types: open chains, entry included",
        three, "B", 4, f3)

analyze("P3b family C over three node types: open chains, entry excluded",
        three, "C", 4, f3)

print("=== estimator identities for the P3 discipline (algebraic, verbatim)")
print("V(MF) = e_MF + b_F + f ; V(F) = b_F + f  =>  e_MF = V(MF) - V(F)")
print("V(FM) = e_FM + b_M + f ; V(M) = b_M + f  =>  e_FM = V(FM) - V(M)")
print("closure (falsifiable prediction for the future instrument):")
print("  V(MFM) = e_MF + e_FM + b_M + f = V(MF) + V(FM) - V(F)")
print("  V(FMF) = e_FM + e_MF + b_F + f = V(FM) + V(MF) - V(M)")
print("=== analysis complete")
