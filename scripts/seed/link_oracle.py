#!/usr/bin/env python3
"""scripts/seed/link_oracle.py <object-dir> <root-ns> <out.kseed> -- an independent linker of seed module objects (KSEEDO1).
BOOTSTRAP-TOOL (agent LINK, rung r6h, 2026-10-04): the reference `seed link` (60-proj pj-link-objects) is checked against.
Written from the object format of 60-proj's separate-mode header, not from its code:
  modules: the root, then depth first along R lines (a module's R lines are all registered before any is visited; a
           registered, unvisited dependency is visited from the first module whose own dependency loop reaches it);
           post-order = layout order
  layout:  each blob (C lines, hex) at the next 8-aligned image offset
  L <o>:   the movz/movk pair at base+o, base+o+4 holds a 32-bit offset in its imm16 fields (bits 5..20); add base
  S <o> <code>: the stub clause at base+o becomes `b` to clause (code & 7) of interface entry ((code // 8) & 4095) of the
           module on this module's require edge (code // 32768)
  E <n> <off>.. <name> ..: interface entry, clause offsets relative to the blob
  W <o>:   the module's keyword table at base+o; when the root has one, every other module's first table instruction
           becomes `b` to the root's
  X <name> <off> <arity>: the root's exports, in the container header at base+off
Container: "KSEED1 <image bytes> <exports>\\n", the X lines, "\\n", the image.
"""
import os
import sys


def load(objdir, ns):
    return open(os.path.join(objdir, ns + '.kso'), encoding='latin-1').read().split('\n')


def main():
    objdir, root, out = sys.argv[1], sys.argv[2], sys.argv[3]
    mods = []          # [name, lines, state, deps(module indexes in R order)]
    index = {}

    def add(name):
        index[name] = len(mods)
        mods.append([name, load(objdir, name), 0, []])
        return index[name]

    order = []

    def visit(m):
        mods[m][2] = 1
        for l in mods[m][1]:
            if l.startswith('R '):
                rn = l[2:]
                t = index.get(rn)
                if t is None:
                    t = add(rn)
                elif mods[t][2] == 1:
                    sys.exit('cycle at ' + rn)
                mods[m][3].append(t)
        for t in mods[m][3]:
            if mods[t][2] == 0:
                visit(t)
        mods[m][2] = 2
        order.append(m)

    visit(add(root))
    img = bytearray()
    base_of, entries, kwt = {}, {}, {}

    def get32(a):
        return int.from_bytes(img[a:a + 4], 'little')

    def put32(a, w):
        img[a:a + 4] = (w & 0xffffffff).to_bytes(4, 'little')

    def b_to(at, target):
        d = (target - at) // 4
        return 0x14000000 | (d & 0x3ffffff)

    for m in order:
        lines = mods[m][1]
        base = (len(img) + 7) & ~7
        img.extend(b'\0' * (base - len(img)))
        base_of[m] = base
        for l in lines:
            if l.startswith('C '):
                img.extend(bytes.fromhex(l[2:]))
        ents = []
        for l in lines:
            if l.startswith('E '):
                f = l[2:].split(' ')
                n = int(f[0])
                ents.append([base + int(x) for x in f[1:1 + n]])
        entries[m] = ents
        for l in lines:
            if l.startswith('L '):
                at = base + int(l[2:])
                w0, w1 = get32(at), get32(at + 4)
                v = base + ((w0 >> 5) & 0xffff) + 65536 * ((w1 >> 5) & 0xffff)
                put32(at, (w0 & 4292870175) | ((v & 0xffff) << 5))
                put32(at + 4, (w1 & 4292870175) | (((v >> 16) & 0xffff) << 5))
            elif l.startswith('W '):
                kwt[m] = base + int(l[2:])
            elif l.startswith('S '):
                o, code = l[2:].split(' ')
                at, code = base + int(o), int(code)
                dep = mods[m][3][code // 32768]
                target = entries[dep][(code // 8) & 4095][code & 7]
                put32(at, b_to(at, target))
    r = index[root]
    if r in kwt:
        for m, a in kwt.items():
            if m != r:
                put32(a, b_to(a, kwt[r]))
    xs = [l[2:].split(' ') for l in mods[r][1] if l.startswith('X ')]
    hdr = 'KSEED1 %d %d\n' % (len(img), len(xs)) + ''.join('%s %d %s\n' % (n, base_of[r] + int(o), a) for n, o, a in xs) + '\n'
    open(out, 'wb').write(hdr.encode('latin-1') + bytes(img))
    print('{:ok true :modules %d :image %d}' % (len(mods), len(img)))


if __name__ == '__main__':
    main()
