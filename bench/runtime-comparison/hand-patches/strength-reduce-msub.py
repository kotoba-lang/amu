# Strength-reduce every `MOV xM,#2147483647 ; ... ; MSUB xD,xN,xM,xA` site.
#
#   MOV  xM, #2147483647      ->  SUB xM, xN, xN, LSL #31    ; xM = -q*(2^31-1)
#   MSUB xD, xN, xM, xA       ->  ADD xD, xA, xM             ; xD = v - q*(2^31-1)
#
# xN (the quotient) is preserved -- the scratch is xM, which held the constant
# and is dead after the MSUB. Clobbering xN instead would be wrong wherever the
# quotient is live past the site, and at 24 sites that cannot be assumed.
import struct, sys
src, dst = sys.argv[1], sys.argv[2]
b = bytearray(open(src, "rb").read())
n = len(b)//4
def rd(i): return struct.unpack("<I", b[i*4:i*4+4])[0]
def wr(i, v): b[i*4:i*4+4] = struct.pack("<I", v)
def is_mov_const(x):      # ORR xM, xzr, #2147483647  (0xb2407be0 | Rd)
    return (x & 0xffffffe0) == 0xb2407be0
def is_msub(x): return (x & 0xffe08000) == 0x9b008000
patched = 0; skipped = []
for i in range(n):
    x = rd(i)
    if not is_msub(x): continue
    D, N, M, A = x & 31, (x>>5) & 31, (x>>16) & 31, (x>>10) & 31
    # the nearest preceding MOV that defines xM
    j = None
    for k in range(i-1, max(-1, i-12), -1):
        y = rd(k)
        if is_mov_const(y) and (y & 31) == M: j = k; break
    if j is None: skipped.append((i, "no MOV #2147483647 defining x%d" % M)); continue
    if M in (N, A, 31) or N == 31: skipped.append((i, "scratch conflicts")); continue
    wr(j, 0xCB000000 | (N<<16) | (31<<10) | (N<<5) | M)   # SUB xM, xN, xN, LSL #31
    wr(i, 0x8B000000 | (M<<16) | (A<<5) | D)              # ADD xD, xA, xM
    patched += 1
open(dst, "wb").write(bytes(b))
print("  %s -> %s : %d site(s) strength-reduced, %d skipped" % (src, dst, patched, len(skipped)))
for i, why in skipped[:4]: print("     skipped @%d: %s" % (i*4, why))
