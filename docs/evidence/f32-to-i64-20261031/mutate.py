"""Mutants of the native object (negative controls for the differential).

round:   cvttss2si (truncate) becomes cvtss2si, which rounds by MXCSR.RC: f3 48 0f 2c 85 -> f3 48 0f 2d 85.
noguard: the guard's jno over the trap becomes jmp: 71 0e -> eb 0e, so a NaN or an out-of-range operand returns the
         integer indefinite instead of reaching ud2.
exempt:  the in-range exemption compares the operand with 0xdf800000 instead of -2^63 (0xdf000000), so -2^63 traps.
"""
import sys
from pathlib import Path
SEQ = bytes.fromhex("48 89 c1 48 f7 d9 71 0e 81 bd")
MUTANTS = {
    "round": (bytes.fromhex("f3480f2c85"), bytes.fromhex("f3480f2d85")),
    "noguard": (bytes.fromhex("48f7d9710e"), bytes.fromhex("48f7d9eb0e")),
    "exempt": (bytes.fromhex("000000df7402"), bytes.fromhex("000080df7402")),
}
old, new = MUTANTS[sys.argv[1]]
for p in map(Path, sys.argv[2:]):
    b = p.read_bytes()
    n = b.count(old)
    if n != 1 or b.count(SEQ) != 1:
        raise SystemExit(f"{p.name}: {n} sites, guard {b.count(SEQ)}")
    p.write_bytes(b.replace(old, new))
    print(f"mutant {sys.argv[1]}: {p.name} {n} site patched")
