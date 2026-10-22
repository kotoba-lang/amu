#!/usr/bin/env python3
"""T2 BOOTSTRAP-TOOL (not part of the seed): hand-encode an AArch64 kexe body against the runtime ABI v11
(context pointer in x7, helpers through slots, string literals as pair_new(offset, len) over code_base,
fuel at [x7,#8]). Independent of stage-0 and of the C loader's generated code; clang/otool are used only
as encoding oracles (--oracle).  usage: t2_asm.py <out.bin> [--oracle]   prints the offset of main."""
import re, struct, subprocess, sys, tempfile, os

SLOT = dict(pair_new=56, pair_second=72, string_equal=112, typed_cap_call=128, string_code_point_at=144,
            vector_count=168, vector_at=176, vector_alloc=200, vector_assoc_in_place=208, bytes_from_vector=360)
COND = dict(eq=0, ne=1, hs=2, lo=3, ge=10, lt=11, gt=12, le=13)

def X(r):  # register name -> number (sp/xzr = 31)
    return 31 if r in ('sp', 'xzr') else int(r[1:])

def enc(line, pc, labels):
    """one mnemonic -> one 32-bit word. pc = byte offset of this instruction."""
    t = line.strip()
    m = re.fullmatch(r'stp x29, x30, \[sp, #-(\d+)\]!', t)
    if m: return 0xa9800000 | (((-int(m[1]) // 8) & 0x7f) << 15) | (30 << 10) | (31 << 5) | 29
    m = re.fullmatch(r'ldp x29, x30, \[sp\], #(\d+)', t)
    if m: return 0xa8c00000 | ((int(m[1]) // 8) << 15) | (30 << 10) | (31 << 5) | 29
    m = re.fullmatch(r'mov (x\d+|sp), (x\d+|sp)', t)
    if m:
        d, s = X(m[1]), X(m[2])
        if 31 in (d, s): return 0x91000000 | (s << 5) | d          # add xd, xs, #0
        return 0xaa0003e0 | (s << 16) | d                           # orr xd, xzr, xs
    m = re.fullmatch(r'mov (x\d+), #(\d+)', t)
    if m:
        assert int(m[2]) < 65536; return 0xd2800000 | (int(m[2]) << 5) | X(m[1])
    m = re.fullmatch(r'(ldr|str) (x\d+), \[(x\d+|sp), #(\d+)\]', t)
    if m:
        assert int(m[4]) % 8 == 0
        return (0xf9400000 if m[1] == 'ldr' else 0xf9000000) | ((int(m[4]) // 8) << 10) | (X(m[3]) << 5) | X(m[2])
    m = re.fullmatch(r'(add|sub|subs) (x\d+), (x\d+), #(\d+)', t)
    if m:
        base = dict(add=0x91000000, sub=0xd1000000, subs=0xf1000000)[m[1]]
        assert int(m[4]) < 4096; return base | (int(m[4]) << 10) | (X(m[3]) << 5) | X(m[2])
    m = re.fullmatch(r'add (x\d+), (x\d+), (x\d+)', t)
    if m: return 0x8b000000 | (X(m[3]) << 16) | (X(m[2]) << 5) | X(m[1])
    m = re.fullmatch(r'mul (x\d+), (x\d+), (x\d+)', t)
    if m: return 0x9b007c00 | (X(m[3]) << 16) | (X(m[2]) << 5) | X(m[1])
    m = re.fullmatch(r'cmp (x\d+), (x\d+)', t)
    if m: return 0xeb00001f | (X(m[2]) << 16) | (X(m[1]) << 5)
    m = re.fullmatch(r'cmp (x\d+), #(\d+)', t)
    if m: return 0xf100001f | (int(m[2]) << 10) | (X(m[1]) << 5)
    m = re.fullmatch(r'blr (x\d+)', t)
    if m: return 0xd63f0000 | (X(m[1]) << 5)
    if t == 'ret': return 0xd65f03c0
    if t == 'brk #0': return 0xd4200000
    m = re.fullmatch(r'b\.(\w+) (\w+)', t)
    if m: return 0x54000000 | ((((labels[m[2]] - pc) // 4) & 0x7ffff) << 5) | COND[m[1]]
    m = re.fullmatch(r'(b|bl) (\w+)', t)
    if m: return (0x14000000 if m[1] == 'b' else 0x94000000) | (((labels[m[2]] - pc) // 4) & 0x3ffffff)
    raise SystemExit('unencodable: ' + t)

FUEL = ['ldr x16, [x7, #8]', 'subs x16, x16, #1', 'b.hs @ok', 'brk #0', '@ok:', 'str x16, [x7, #8]']
_n = [0]
def fuel():
    _n[0] += 1
    return [l.replace('@ok', 'fuel_ok%d' % _n[0]) for l in FUEL]

def call(slot, *args):
    """runtime helper call: ctx reloaded from [sp,#16]; args are 'xN := mnemonic-source' pairs already formed."""
    out = ['ldr x7, [sp, #16]', 'ldr x16, [x7, #%d]' % SLOT[slot], 'mov x0, x7']
    out += list(args)
    out += ['blr x16']
    return out

def ldl(r, off): return 'ldr %s, [sp, #%d]' % (r, off)
def stl(r, off): return 'str %s, [sp, #%d]' % (r, off)

V, I, SUM, RES, S, TMP, R2, LL = 24, 32, 40, 48, 56, 64, 72, 80    # frame slots (frame = 96)
STR1 = 'aé€x'                                             # 61 c3a9 e282ac 78 : 7 bytes, 4 code points
PATH = '/private/tmp/t23/d/t2.binWRITE_SEP'
LIT1_OFF = LIT2_OFF = 0                                             # patched after layout

def program(lit1, lit2, n1, n2):
    p = []
    # ---- spin(n): leaf guest function, ctx in x7 from the caller; counts n via fuel; returns n
    p += ['spin:'] + fuel() + ['mov x1, #0', 'spin_loop:'] + fuel() + ['cmp x1, x0', 'b.ge spin_done', 'add x1, x1, #1', 'b spin_loop', 'spin_done:', 'mov x0, x1', 'ret']
    # ---- main: arity 0, context in x7
    p += ['main:', 'stp x29, x30, [sp, #-96]!', 'mov x29, sp', stl('x7', 16)] + fuel()
    # A. vector_alloc / vector_assoc_in_place / vector_at : v[i] = i*i+1, sum
    p += call('vector_alloc', 'mov x1, #8') + [stl('x0', V), 'mov x1, #0', stl('x1', I), 'a1:'] + fuel()
    p += [ldl('x1', I), 'cmp x1, #8', 'b.ge a1_done', 'mul x3, x1, x1', 'add x3, x3, #1', stl('x3', TMP)]
    p += call('vector_assoc_in_place', ldl('x1', V), ldl('x2', I), ldl('x3', TMP))
    p += [stl('x0', V), ldl('x1', I), 'add x1, x1, #1', stl('x1', I), 'b a1', 'a1_done:']
    p += ['mov x1, #0', stl('x1', I), stl('x1', SUM), 'a2:'] + fuel()
    p += [ldl('x1', I), 'cmp x1, #8', 'b.ge a2_done']
    p += call('vector_at', ldl('x1', V), ldl('x2', I))
    p += [ldl('x1', SUM), 'add x1, x1, x0', stl('x1', SUM), ldl('x1', I), 'add x1, x1, #1', stl('x1', I), 'b a2', 'a2_done:']
    p += [ldl('x1', SUM), stl('x1', RES)]                                         # RES = 148
    # B. string literal = pair_new(offset_in_code, length); code_point_at / pair_second / string_equal
    p += call('pair_new', 'mov x1, #%d' % lit1, 'mov x2, #%d' % n1) + [stl('x0', S)]
    for off in (0, 1, 3, 6):                                                      # 'a' e9 20ac 'x'
        p += call('string_code_point_at', ldl('x1', S), 'mov x2, #%d' % off) + [ldl('x1', RES), 'add x1, x1, x0', stl('x1', RES)]
    p += call('pair_second', ldl('x1', S)) + [ldl('x1', RES), 'add x1, x1, x0', stl('x1', RES)]   # + 7
    p += call('pair_new', 'mov x1, #%d' % lit1, 'mov x2, #%d' % n1) + [stl('x0', TMP)]
    p += call('string_equal', ldl('x1', S), ldl('x2', TMP)) + [ldl('x1', RES), 'add x1, x1, x0', stl('x1', RES)]  # + 1
    # C. guest-to-guest call with fuel: spin(1000)
    p += ['ldr x7, [sp, #16]', 'mov x0, #1000', 'bl spin', ldl('x1', RES), 'add x1, x1, x0', stl('x1', RES)]
    # D. typed_cap_call kind 1 (string -> string) over wire 37 :io/write, result handle "7"
    p += call('typed_cap_call', 'mov x1, #37', 'mov x2, #1', 'mov x3, #1', ldl('x4', S))
    p += [stl('x0', R2)] + call('string_code_point_at', ldl('x1', R2), 'mov x2, #0') + [ldl('x1', RES), 'add x1, x1, x0', stl('x1', RES)]  # + '7' = 55
    # E. kind 8 (bytes -> bytes) over wire 35: request = path "WRITE_SEP" 0..255 built in a vector, bytes_from_vector
    L = n2
    p += call('vector_alloc', 'mov x1, #%d' % (L + 256)) + [stl('x0', V)]
    p += call('pair_new', 'mov x1, #%d' % lit2, 'mov x2, #%d' % L) + [stl('x0', S), 'mov x1, #0', stl('x1', I), 'e1:'] + fuel()
    p += [ldl('x1', I), 'cmp x1, #%d' % L, 'b.ge e1_done']
    p += call('string_code_point_at', ldl('x1', S), ldl('x2', I)) + [stl('x0', TMP)]
    p += call('vector_assoc_in_place', ldl('x1', V), ldl('x2', I), ldl('x3', TMP)) + [stl('x0', V), ldl('x1', I), 'add x1, x1, #1', stl('x1', I), 'b e1', 'e1_done:']
    p += ['mov x1, #0', stl('x1', I), 'e2:'] + fuel() + [ldl('x1', I), 'cmp x1, #256', 'b.ge e2_done', 'add x2, x1, #%d' % L, 'mov x3, x1', stl('x2', TMP), stl('x3', LL)]
    p += call('vector_assoc_in_place', ldl('x1', V), ldl('x2', TMP), ldl('x3', LL)) + [stl('x0', V), ldl('x1', I), 'add x1, x1, #1', stl('x1', I), 'b e2', 'e2_done:']
    p += call('bytes_from_vector', ldl('x1', V)) + [stl('x0', TMP)]
    p += call('typed_cap_call', 'mov x1, #35', 'mov x2, #8', 'mov x3, #8', ldl('x4', TMP)) + [stl('x0', R2)]
    p += call('vector_count', ldl('x1', R2)) + [ldl('x1', RES), 'add x1, x1, x0', stl('x1', RES)]             # + 256
    p += call('vector_at', ldl('x1', R2), 'mov x2, #255') + [ldl('x1', RES), 'add x1, x1, x0', stl('x1', RES)]  # + 255
    p += [ldl('x0', RES), 'ldp x29, x30, [sp], #96', 'ret']
    return p

def assemble(lines):
    labels, pc, insns = {}, 0, []
    for l in lines:
        if l.endswith(':'): labels[l[:-1]] = pc
        else: insns.append((pc, l)); pc += 4
    return labels, insns, pc

def build():
    # pass 1 sizes the code; the literal data follows the code (8-aligned), exactly where stage-0 places it
    size = assemble(program(0, 0, 0, 0))[2]
    s1 = STR1.encode(); s2 = PATH.encode()
    lit1 = (size + 7) & ~7; lit2 = lit1 + ((len(s1) + 7) & ~7)
    lines = program(lit1, lit2, len(s1), len(s2))
    labels, insns, end = assemble(lines)
    assert end == size
    code = b''.join(struct.pack('<I', enc(l, pc, labels)) for pc, l in insns)
    blob = code + b'\0' * (lit1 - len(code)) + s1 + b'\0' * (lit2 - lit1 - len(s1)) + s2
    return blob, labels, lines, insns

def oracle(lines, insns):
    src = '\n'.join(('' if l.endswith(':') and False else l) for l in lines) + '\n'
    with tempfile.TemporaryDirectory() as d:
        open(d + '/a.s', 'w').write('.text\n' + src)
        subprocess.check_call(['clang', '-c', '-target', 'arm64-apple-macos', '-x', 'assembler', d + '/a.s', '-o', d + '/a.o'])
        out = subprocess.check_output(['otool', '-t', '-X', d + '/a.o'], text=True)
    words = [int(w, 16) for line in out.splitlines() for w in line.split()[1:]]
    return words

if __name__ == '__main__':
    blob, labels, lines, insns = build()
    mine = [struct.unpack('<I', blob[pc:pc + 4])[0] for pc, _ in insns]
    if '--oracle' in sys.argv:
        ref = oracle(lines, insns)
        bad = [(pc, l, hex(a), hex(b)) for (pc, l), a, b in zip(insns, mine, ref) if a != b]
        print('instructions %d, oracle words %d, mismatches %d' % (len(mine), len(ref), len(bad)), file=sys.stderr)
        for b in bad[:10]: print('MISMATCH', b, file=sys.stderr)
        if bad or len(ref) != len(mine): sys.exit(1)
    open(sys.argv[1], 'wb').write(blob)
    print('main offset %d spin offset %d total bytes %d' % (labels['main'], labels['spin'], len(blob)))
