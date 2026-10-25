#!/usr/bin/env python3
"""Wrap a raw x86-64 code blob in a minimal ELF64 ET_EXEC (R+X, one PT_LOAD)
so llvm-objdump can linearly decode it. Measurement instrument only."""
import struct, sys

def wrap(code: bytes, out_path: str):
    e_entry = 0x400078
    eh = struct.pack('<16sHHIQQQIHHHHHH',
                     b'\x7fELF' + bytes([2, 1, 1, 0]) + bytes(8),  # e_ident
                     2, 62, 1, e_entry, 64, 0, 0,
                     64, 56, 1, 0, 0, 0)
    ph = struct.pack('<IIQQQQQQ',
                     1, 5, 0, 0x400000, 0x400000,
                     0x78 + len(code), 0x78 + len(code), 0x1000)
    blob = eh + ph + code
    assert len(eh) == 64 and len(ph) == 56
    open(out_path, 'wb').write(blob)
    return len(blob)

if __name__ == '__main__':
    code = open(sys.argv[1], 'rb').read()
    print(wrap(code, sys.argv[2]))
