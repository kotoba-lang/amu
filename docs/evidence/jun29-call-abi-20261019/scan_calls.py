#!/usr/bin/env python3
"""Pattern scan of kx64-v1 x86-64 guest code regions for call/dispatch sites
and the rdi/r9 context-reload discipline. Independent of the emitter source.
Every call-family site is classified; canonical emitter sequences are counted;
anything else is reported as a stray for the objdump reconciliation."""
import json, re, sys, hashlib, os

RELOAD_RDI = bytes.fromhex('488b7df8')   # mov rdi,[rbp-8]
RELOAD_R9  = bytes.fromhex('4c8b4df8')   # mov r9,[rbp-8]
LEAVE      = bytes.fromhex('c9')
RET        = bytes.fromhex('c3')
PROLOGUE_TAIL = bytes.fromhex('4c894df8')  # mov [rbp-8],r9 (end of prologue)

SLOTS = {48, 56, 64, 72, 112, 120, 128, 136, 144, 152, 160, 168, 176, 184,
         192, 200, 208, 216, 240, 352, 360, 368, 376}

def scan(path):
    code = open(path, 'rb').read()
    n = len(code)
    res = {'file': os.path.basename(path), 'bytes': n,
           'sha256': hashlib.sha256(code).hexdigest(),
           'host_dispatch': [], 'guest_call': [], 'guest_tail': [],
           'call_rax': [], 'jmp_rax': [], 'ret_leave': [],
           'prologues': [], 'strays': [], 'entry': None}

    # entry: xr-build emits jmp rel32 at code offset 0
    if code[0] == 0xe9:
        rel = int.from_bytes(code[1:5], 'little', signed=True)
        res['entry'] = {'offset': 0, 'opcode': 'jmp rel32', 'target': 5 + rel}
    else:
        res['entry'] = {'offset': 0, 'opcode_hex': code[:5].hex()}

    def add(k, off, **kw):
        d = {'offset': off}
        d.update(kw)
        res[k].append(d)

    # 1. host dispatch: mov rdi,[rbp-8]; call [rdi+disp32]; mov r9,[rbp-8]
    i = 0
    while True:
        i = code.find(RELOAD_RDI + b'\xff\x97', i)
        if i < 0:
            break
        disp = int.from_bytes(code[i+6:i+10], 'little')
        after = code[i+10:i+14] == RELOAD_R9
        add('host_dispatch', i, disp=disp, slot_admitted=disp in SLOTS,
            r9_restored_after=after)
        i += 1
    # 2. guest direct call / tail: mov r9,[rbp-8] then e8 rel32 | c9 e9 rel32
    i = 0
    while True:
        i = code.find(RELOAD_R9, i)
        if i < 0:
            break
        nxt = code[i+4:i+6]
        if nxt[:1] == b'\xe8':
            rel = int.from_bytes(code[i+5:i+9], 'little', signed=True)
            add('guest_call', i, target=i + 9 + rel)
        elif code[i+4] == 0xc9 and code[i+5] == 0xe9:
            rel = int.from_bytes(code[i+6:i+10], 'little', signed=True)
            add('guest_tail', i, target=i + 10 + rel)
        elif code[i+4] == 0xc9 and code[i+5] == 0xc3:
            add('ret_leave', i)
        elif code[i+4:i+6] == b'\xff\xd0':
            add('call_rax', i, r9_loaded_before=True)
        elif code[i+4] == 0xc9 and code[i+5:i+7] == b'\xff\xe0':
            add('jmp_rax', i, r9_loaded_before=True)
        i += 1
    # 3. prologues: push rbp; mov rbp,rsp; sub rsp,imm32; mov [rbp-8],r9
    pat = bytes.fromhex('554889e54881ec')
    i = 0
    while True:
        i = code.find(pat, i)
        if i < 0:
            break
        imm = int.from_bytes(code[i+7:i+11], 'little')
        ok = code[i+11:i+15] == PROLOGUE_TAIL
        add('prologues', i, frame=imm, frame_aligned16=(imm % 16 == 0),
            ctx_home_stored=ok)
        i += 1
    # 4. stray call-family opcode bytes (ff /2 call r/m64, ff /4 jmp r/m64,
    #    e8 call rel32) that are NOT part of a canonical sequence
    canon = []
    for k in ('host_dispatch', 'guest_call', 'guest_tail', 'call_rax', 'jmp_rax'):
        for d in res[k]:
            canon.append(d['offset'])
    def covered(off):
        return any(c - 8 <= off <= c + 16 for c in canon)
    for i in range(n - 1):
        b0, b1 = code[i], code[i+1]
        kind = None
        if b0 == 0xff:
            modrm = b1
            reg = (modrm >> 3) & 7
            if reg == 2 and (modrm & 0xc0) != 0xc0:
                kind = 'call_indirect_mem'
            elif reg == 2 and (modrm & 0xc0) == 0xc0:
                kind = 'call_reg'
            elif reg == 4:
                kind = 'jmp_indirect'
        elif b0 == 0xe8:
            kind = 'call_rel32'
        if kind and not covered(i):
            res['strays'].append({'offset': i, 'kind': kind,
                                  'context': code[max(0, i-8):i+10].hex()})
    return res

if __name__ == '__main__':
    out = {}
    for p in sys.argv[1:]:
        r = scan(p)
        out[os.path.basename(p)] = r
        print(json.dumps({k: (len(v) if isinstance(v, list) else v)
                          for k, v in r.items()}, sort_keys=True))
    json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     'scan-results.json'), 'w'), indent=1)
