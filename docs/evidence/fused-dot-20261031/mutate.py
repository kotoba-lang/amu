"""Summation-order mutants of the native objects (negative controls for the differential).

scalar-reduction: (l0+l1)+(l2+l3) becomes ((l0+l1)+l2)+l3 in the scalar arms: addss xmm0,xmm1; addss xmm2,xmm3;
                  addss xmm0,xmm2 -> addss xmm0,xmm1; addss xmm0,xmm2; addss xmm0,xmm3.
avx-halves:       each block adds its upper half before its lower half in the AVX2 arms: the two vaddps swapped.
"""
import sys
from pathlib import Path
MUTANTS = {
    "scalar-reduction": (bytes.fromhex("f30f58c1f30f58d3f30f58c2"), bytes.fromhex("f30f58c1f30f58c2f30f58c3")),
    "avx-halves": (bytes.fromhex("c5f858c1c5f858c2"), bytes.fromhex("c5f858c2c5f858c1")),
}
old, new = MUTANTS[sys.argv[1]]
for p in map(Path, sys.argv[2:]):
    b = p.read_bytes()
    n = b.count(old)
    if n == 0:
        raise SystemExit(f"{p.name}: pattern absent")
    p.write_bytes(b.replace(old, new))
    print(f"mutant {sys.argv[1]}: {p.name} {n} site(s) patched")
