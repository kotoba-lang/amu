"""Mutants of the aarch64 payload (negative controls for the differential).

noguard: the guard's brk #0 becomes nop, so a NaN or out-of-range operand falls through to fcvtzs's saturated answer.
round:   the guard's fcvtzs (toward zero) becomes fcvtns (to nearest, ties to even): 9e38.... -> 9e20.....
edge:    the first range check's b.lt becomes b.le (5400008b -> 5400008d), so -2^63 itself traps.
"""
import struct
import sys
from pathlib import Path
TAIL = struct.pack("<3I", 0x1E202020, 0x5400004C, 0xD4200000)
p = Path(sys.argv[2])
b = bytearray(p.read_bytes())
if b.count(TAIL) != 1:
    raise SystemExit("guard not found exactly once")
at = b.find(TAIL)
word = lambda i: struct.unpack_from("<I", b, i)[0]
if sys.argv[1] == "noguard":
    struct.pack_into("<I", b, at + 8, 0xD503201F)
elif sys.argv[1] == "round":
    w = word(at + 12); assert w & 0xFFFFFC00 == 0x9E380000, hex(w)
    struct.pack_into("<I", b, at + 12, (w & 0x3FF) | 0x9E200000)
elif sys.argv[1] == "edge":
    assert word(at - 8) == 0x5400008B, hex(word(at - 8))
    struct.pack_into("<I", b, at - 8, 0x5400008D)
else:
    raise SystemExit("unknown mutant")
p.write_bytes(bytes(b))
print(f"mutant {sys.argv[1]}: {p.name} guard at +{at + 8:#x} patched")
