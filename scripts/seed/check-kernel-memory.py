#!/usr/bin/env python3
"""Conformance of the x86_64-aiueos-kernel-v1 kernel memory windows (ADR 0373).

Compiles three one-function guests with a selfhost-built compiler, runs the emitted
x86-64 code in a small emulator of exactly the instruction forms the seed backend
emits, and compares every run with the specification:

  kernel-load-u32   (base length index)       length <= 512, base != 0, index < length,
                                              index + 4 <= length (all unsigned) else trap;
                                              the value is the u32 at base + index
  kernel-store-u32  (base length index value) the same checks; stores the u32; the value
  kernel-subregion  (base length offset n)    base != 0, offset <= length,
                                              n <= length - offset (unsigned) else trap;
                                              base + offset

A run that does not trap must touch only bytes inside [base, base + length) and must
have read or written nothing when it trapped. An instruction form the emulator does
not know is an error, never a pass. With --break NAME the named check byte of the
emitted code is flipped first and the run must then FAIL (a deliberate break seen red).

Python only orchestrates the compiler and the emulator; it compiles no Kotoba itself.
Run on arm64 Linux with the compiler's absolute path, for example
  python3 scripts/seed/check-kernel-memory.py --compiler OUT/S3.elf --work WORK
"""
import argparse
import os
import random
import struct
import subprocess
import sys
from pathlib import Path

MASK = (1 << 64) - 1

SOURCES = {
    "load": "(ns kload (:export [f]))\n(defn f [b :i64 n :i64 i :i64] :i64 (kernel-load-u32 b n i))\n",
    "store": "(ns kstore (:export [f]))\n(defn f [b :i64 n :i64 i :i64 v :i64] :i64 (kernel-store-u32 b n i v))\n",
    "sub": "(ns ksub (:export [f]))\n(defn f [b :i64 n :i64 o :i64 l :i64] :i64 (kernel-subregion b n o l))\n",
}


def compile_one(compiler, work, name, src):
    p = Path(work) / f"{name}.kotoba"
    p.write_text(src)
    out = Path(work) / f"{name}.o"
    if out.exists():
        out.unlink()
    env = dict(os.environ, KEXE_CAP_RESOURCES_35=str(work))
    r = subprocess.run([compiler, "compile", str(p), "--target", "x86_64-aiueos-kernel-v1", "--output", str(out)],
                       env=env, capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        raise SystemExit(f"compile {name} failed ({r.returncode}): {r.stdout.strip()} {r.stderr.strip()}")
    return out.read_bytes()


def elf_text(obj):
    """(.text bytes, entry offset of the public symbol). The object has exactly the seven
    sections of the aiueos kernel object ABI: "" .text .data .rela.text .symtab .strtab .shstrtab."""
    shoff, = struct.unpack_from("<Q", obj, 0x28)
    shentsize, shnum, shstrndx = struct.unpack_from("<HHH", obj, 0x3a)
    if shnum != 7:
        raise SystemExit(f"object has {shnum} sections, expected 7")
    sec = []
    for k in range(shnum):
        name, typ, flags, addr, off, size, link, info, align, entsize = struct.unpack_from(
            "<IIQQQQIIQQ", obj, shoff + k * shentsize)
        sec.append((typ, off, size))
    text, symtab = sec[1], sec[4]
    syms = [struct.unpack_from("<IBBHQQ", obj, symtab[1] + 24 * k) for k in range(symtab[2] // 24)]
    export = next(s for s in syms if s[1] == 0x12)       # GLOBAL FUNC
    return obj[text[1]:text[1] + text[2]], export[4]


class Trap(Exception):
    pass


class Unknown(Exception):
    pass


REG = {"rax": 0, "rcx": 1, "rdx": 2, "rbx": 3, "rsp": 4, "rbp": 5, "rsi": 6, "rdi": 7}


class Emu:
    """x86-64 subset: exactly the forms the seed's scalar backend and this slice emit."""

    def __init__(self, text, window_lo, window_hi, mem):
        self.text = text
        self.r = [0] * 16
        self.zf = self.sf = self.cf = self.of = 0
        self.mem = mem          # dict: address -> byte
        self.log = []           # (kind, address) of every access to the guest window region
        self.window = (window_lo, window_hi)
        self.steps = 0

    # -- memory --
    def rd(self, a, n):
        a &= MASK
        self.log.append(("r", a, n))
        return int.from_bytes(bytes(self.mem.get(a + k, 0) for k in range(n)), "little")

    def wr(self, a, n, v):
        a &= MASK
        self.log.append(("w", a, n))
        for k in range(n):
            self.mem[a + k] = (v >> (8 * k)) & 255

    def flags_sub(self, a, b, n=64):
        m = (1 << n) - 1
        res = (a - b) & m
        self.cf = 1 if (a & m) < (b & m) else 0
        self.zf = 1 if res == 0 else 0
        self.sf = (res >> (n - 1)) & 1
        sa, sb = (a >> (n - 1)) & 1, (b >> (n - 1)) & 1
        self.of = 1 if sa != sb and self.sf != sa else 0
        return res

    def run(self, entry, args):
        names = ["rdi", "rsi", "rdx", "rcx"]
        for k, v in enumerate(args[:4]):
            self.r[REG[names[k]]] = v & MASK
        if len(args) > 4:
            self.r[8] = args[4] & MASK            # r8
        stack_top = 0x7fff0000
        self.r[4] = stack_top
        self.r[REG["rax"]] = 0
        ret_marker = 0xdead0000
        self.wr(self.r[4] - 8, 8, ret_marker)
        self.r[4] -= 8
        pc = entry
        t = self.text
        while True:
            self.steps += 1
            if self.steps > 100000:
                raise Unknown("step limit")
            if pc == ret_marker:
                return self.r[REG["rax"]]
            pc = self.step(pc, t)

    def reg(self, n, rex_r=0):
        return n + (8 if rex_r else 0)

    def step(self, pc, t):
        b = t[pc:pc + 16]
        r = self.r
        if not b:
            raise Unknown(f"pc {pc} outside text")

        def i32(o):
            return struct.unpack_from("<i", b, o)[0]

        def u32(o):
            return struct.unpack_from("<I", b, o)[0]

        def u64(o):
            return struct.unpack_from("<Q", b, o)[0]

        def jcc(cond, ln, disp_at):
            return pc + ln + i32(disp_at) if cond else pc + ln

        # exact sequences first
        if b[0] == 0x55:
            r[4] -= 8; self.wr(r[4], 8, r[5])               # push rbp
            return pc + 1
        if b[:3] == b"\x48\x89\xe5":
            r[5] = r[4]; return pc + 3
        if b[:3] == b"\x48\x81\xec":
            r[4] = (r[4] - u32(3)) & MASK; return pc + 7
        if b[:4] == b"\x4c\x89\x4d\xf8":
            self.wr(r[5] - 8, 8, r[9]); return pc + 4
        if b[:4] == b"\x4c\x8b\x4d\xf8":
            r[9] = self.rd(r[5] - 8, 8); return pc + 4
        # mov [rbp+disp32], reg  /  mov reg, [rbp+disp32]   (REX.W 48 or 4c, opcode 89 / 8b, modrm 10 rrr 101)
        if b[0] in (0x48, 0x4c) and b[1] in (0x89, 0x8b) and (b[2] & 0xc7) == 0x85:
            reg = ((b[2] >> 3) & 7) + (8 if b[0] == 0x4c else 0)
            a = r[5] + i32(3)
            if b[1] == 0x89:
                self.wr(a, 8, r[reg])
            else:
                r[reg] = self.rd(a, 8)
            return pc + 7
        if b[:2] == b"\x48\xb8":
            r[0] = u64(2); return pc + 10
        if b[:3] == b"\x48\x01\xc8":
            r[0] = (r[0] + r[1]) & MASK; return pc + 3
        if b[:3] == b"\x48\x29\xc8":
            r[0] = self.flags_sub(r[0], r[1]); return pc + 3
        if b[:3] == b"\x48\x21\xc8":
            r[0] &= r[1]; return pc + 3
        if b[:3] == b"\x48\x09\xc8":
            r[0] |= r[1]; return pc + 3
        if b[:3] == b"\x48\x31\xc8":
            r[0] ^= r[1]; return pc + 3
        if b[:4] == b"\x48\x0f\xaf\xc1":
            r[0] = (r[0] * r[1]) & MASK; return pc + 4
        if b[:4] == b"\x48\x83\xf0\x01":
            r[0] ^= 1; return pc + 4
        if b[:3] == b"\x48\xf7\xd0":
            r[0] = (~r[0]) & MASK; return pc + 3
        if b[:3] == b"\x48\xf7\xd8":
            r[0] = (-r[0]) & MASK; return pc + 3
        if b[:3] == b"\x48\x39\xc8":                     # cmp rax,rcx
            self.flags_sub(r[0], r[1]); return pc + 3
        if b[:3] == b"\x48\x39\xcf":                     # cmp rdi,rcx
            self.flags_sub(r[7], r[1]); return pc + 3
        if b[:3] == b"\x48\x39\xce":                     # cmp rsi,rcx
            self.flags_sub(r[6], r[1]); return pc + 3
        if b[:3] == b"\x48\x81\xf9":                     # cmp rcx,imm32 (sign-extended)
            self.flags_sub(r[1], i32(3) & MASK); return pc + 7
        if b[:3] == b"\x48\x85\xd2":                     # test rdx,rdx
            self.zf = 1 if r[2] == 0 else 0; self.sf = (r[2] >> 63) & 1; self.cf = self.of = 0; return pc + 3
        if b[:3] == b"\x48\x85\xc0":                     # test rax,rax
            self.zf = 1 if r[0] == 0 else 0; self.sf = (r[0] >> 63) & 1; self.cf = self.of = 0; return pc + 3
        if b[:3] == b"\x48\x29\xf9":                     # sub rcx,rdi
            r[1] = self.flags_sub(r[1], r[7]); return pc + 3
        if b[:4] == b"\x48\x8d\x70\x04":                 # lea rsi,[rax+4]
            r[6] = (r[0] + 4) & MASK; return pc + 4
        if b[:4] == b"\x48\x8d\x77\x04":                 # lea rsi,[rdi+4]
            r[6] = (r[7] + 4) & MASK; return pc + 4
        if b[:4] == b"\x48\x8d\x04\x3a":                 # lea rax,[rdx+rdi]
            r[0] = (r[2] + r[7]) & MASK; return pc + 4
        if b[:3] == b"\x8b\x04\x02":                     # mov eax,[rdx+rax]
            r[0] = self.rd(r[2] + r[0], 4); return pc + 3
        if b[:3] == b"\x89\x04\x3a":                     # mov [rdx+rdi],eax
            self.wr(r[2] + r[7], 4, r[0] & 0xffffffff); return pc + 3
        # conditional jumps rel32: 0f 82 jb, 0f 84 jz, 0f 85 jnz, 0f 83 jae, 0f 87 ja
        if b[0] == 0x0f and b[1] in (0x82, 0x84, 0x85, 0x83, 0x87):
            cond = {0x82: self.cf == 1, 0x84: self.zf == 1, 0x85: self.zf == 0, 0x83: self.cf == 0,
                    0x87: self.cf == 0 and self.zf == 0}[b[1]]
            return jcc(cond, 6, 2)
        if b[:2] == b"\x7f\x02":                         # jg +2 (fuel)
            return pc + 4 if (self.zf == 0 and self.sf == self.of) else pc + 2
        if b[:2] == b"\xeb\x02":
            return pc + 4
        if b[:2] == b"\x0f\x0b":
            raise Trap("ud2")
        if b[0] == 0xe9:
            return pc + 5 + i32(1)
        if b[0] == 0xe8:
            r[4] -= 8; self.wr(r[4], 8, pc + 5); return pc + 5 + i32(1)
        if b[0] == 0xc9:                                  # leave
            r[4] = r[5]; r[5] = self.rd(r[4], 8); r[4] += 8; return pc + 1
        if b[0] == 0xc3:
            a = self.rd(r[4], 8); r[4] += 8; return a
        # fuel charge
        if b[:4] == b"\x49\x8b\x41\x08":
            r[0] = self.rd(r[9] + 8, 8); return pc + 4
        if b[:3] == b"\x48\xff\xc8":
            r[0] = self.flags_sub(r[0], 1); return pc + 3
        if b[:4] == b"\x49\x89\x41\x08":
            self.wr(r[9] + 8, 8, r[0]); return pc + 4
        # shim: lea r9,[rip+x] ; mov qword [r9+8],imm32 ; sub rsp,8 ; add rsp,8
        if b[:3] == b"\x4c\x8d\x0d":
            r[9] = 0x20000000; return pc + 7
        if b[:4] == b"\x49\xc7\x41\x08":
            self.wr(r[9] + 8, 8, u32(4)); return pc + 8
        if b[:4] == b"\x48\x83\xec\x08":
            r[4] -= 8; return pc + 4
        if b[:4] == b"\x48\x83\xc4\x08":
            r[4] += 8; return pc + 4
        raise Unknown(f"unknown instruction at {pc}: {b[:8].hex()}")


def spec(kind, args):
    """(trap?, value) by the specification; value is the u32 / v / base+offset."""
    if kind == "load":
        b, n, i = args
        if n > 512 or b == 0 or i >= n or i + 4 > n or i + 4 > MASK:
            return True, None
        return False, "read"
    if kind == "store":
        b, n, i, v = args
        if n > 512 or b == 0 or i >= n or i + 4 > n:
            return True, None
        return False, "write"
    b, n, o, l = args
    if b == 0 or o > n or l > n - o:
        return True, None
    return False, (b + o) & MASK


def vectors(kind, rng):
    base = 0x10000
    pick = [0, 1, 2, 3, 4, 5, 7, 8, 100, 508, 509, 510, 511, 512, 513, 1000, 4096, 1 << 31, (1 << 32) - 4,
            (1 << 32) - 1, 1 << 32, (1 << 63) - 1, 1 << 63, MASK - 3, MASK - 1, MASK]
    out = []
    for n in pick:
        for i in pick:
            if kind == "load":
                out.append((base, n, i))
            elif kind == "store":
                out.append((base, n, i, 0xA5A5A5A5))
            else:
                out.append((base, n, i, i))        # (base, length, offset, n) reuse the pick axes
                out.append((base, i, n, 4))
                out.append((base, n, 0, i))
    for _ in range(3000):
        n = rng.choice([rng.randrange(0, 600), rng.choice(pick)])
        i = rng.choice([rng.randrange(0, 600), rng.choice(pick), rng.getrandbits(64)])
        if kind == "load":
            out.append((rng.choice([0, base]), n, i))
        elif kind == "store":
            out.append((rng.choice([0, base]), n, i, rng.getrandbits(64)))
        else:
            out.append((rng.choice([0, base]), n, i, rng.choice([rng.randrange(0, 600), rng.getrandbits(64)])))
    return out


def check(kind, obj, rng, flip=None):
    text, entry = elf_text(obj)
    if flip is not None:
        text = bytearray(text)
        text[flip[0]] ^= flip[1]
        text = bytes(text)
    bad = []
    count = traps = 0
    for args in vectors(kind, rng):
        mem = {}
        base = 0x10000
        for k in range(0, 700):
            mem[base + k] = (k * 37 + 11) & 255
        lo = args[0]
        emu = Emu(text, lo, lo + args[1], mem)
        try:
            val = emu.run(entry, list(args))
            trapped = False
        except Trap:
            trapped, val = True, None
        want_trap, want = spec(kind, args)
        count += 1
        traps += trapped
        if trapped != want_trap:
            bad.append((args, "trap" if trapped else "no trap", "trap" if want_trap else "no trap"))
            continue
        if trapped:
            if any(a[0] == "w" and 0x10000 <= a[1] < 0x10000 + 1024 for a in emu.log):
                bad.append((args, "wrote before trapping", None))
            continue
        # no trap: every touch of the guest window must be inside [b, b+n)
        for kind_, a, n_ in emu.log:
            if 0x10000 <= a < 0x10000 + 4096 and not (args[0] <= a and a + n_ <= args[0] + args[1]):
                bad.append((args, f"touched {a:#x}+{n_} outside the window", None))
        if kind == "load":
            expect = int.from_bytes(bytes(mem[args[0] + args[2] + k] for k in range(4)), "little")
            if val != expect:
                bad.append((args, f"value {val:#x}", f"{expect:#x}"))
        elif kind == "store":
            got = int.from_bytes(bytes(mem[args[0] + args[2] + k] for k in range(4)), "little")
            if got != args[3] & 0xffffffff or val != args[3] & MASK:
                bad.append((args, f"stored {got:#x} returned {val:#x}", f"{args[3] & 0xffffffff:#x}"))
        else:
            if val != want:
                bad.append((args, f"value {val:#x}", f"{want:#x}"))
    return count, traps, bad


def admission(compiler, work, cases):
    """Rooted bases: the accepted shapes compile, the refused ones are E7106 and write no object."""
    bad = n = 0
    for src in sorted(cases.glob("*.kotoba")):
        out = work / (src.stem + ".o")
        if out.exists():
            out.unlink()
        env = dict(os.environ, KEXE_CAP_RESOURCES_35=str(src.parent), KEXE_CAP_RESOURCES_36=str(work))
        r = subprocess.run([compiler, "compile", str(src), "--target", "x86_64-aiueos-kernel-v1", "--output", str(out)],
                           env=dict(env, KEXE_CAP_RESOURCES_35=f"{src.parent}:{work}"), capture_output=True, text=True, timeout=600)
        want_ok = src.name.startswith("ok_")
        refused = r.returncode != 0 and "E7106" in r.stderr and not out.exists()
        good = (r.returncode == 0 and out.exists()) if want_ok else refused
        n += 1
        bad += 0 if good else 1
        print(f"{'ok ' if good else 'BAD'} {src.name}: rc={r.returncode} {'' if want_ok else ('E7106' if refused else r.stderr.strip()[:80])}")
    print("PASS_KERNEL_MEMORY_ADMISSION" if bad == 0 else "FAIL_KERNEL_MEMORY_ADMISSION", n, "cases")
    return 0 if bad == 0 else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--compiler", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--seed", type=int, default=20261023)
    ap.add_argument("--cases", default=None,
                    help="seed/tests/kernel-memory: every ok_*.kotoba must compile, every no_*.kotoba must be refused E7106")
    ap.add_argument("--break", dest="brk", default=None,
                    help="change one check's condition in the emitted code and expect FAIL: KIND-OP[-N] with KIND load|store|sub, OP ja|jae|jz")
    a = ap.parse_args()
    work = Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    if a.cases:
        sys.exit(admission(a.compiler, work, Path(a.cases)))
    rng = random.Random(a.seed)
    total_bad = 0
    for kind in ("load", "store", "sub"):
        obj = compile_one(a.compiler, work, f"k{kind}", SOURCES[kind])
        text, entry = elf_text(obj)
        flip = None
        if a.brk and a.brk.startswith(kind + "-"):
            # NAME is KIND-OP or KIND-OP-N (the Nth occurrence): OP is the conditional jump the check
            # is made of; its second opcode byte is changed to a different condition (ja -> jae,
            # jae -> jb, jz -> jnz), so the check no longer separates what it separated.
            parts = a.brk.split("-")
            op, xor = {"ja": (b"\x0f\x87", 0x04), "jae": (b"\x0f\x83", 0x01), "jz": (b"\x0f\x84", 0x01)}[parts[1]]
            nth = int(parts[2]) if len(parts) > 2 else 1
            at = -1
            for _ in range(nth):
                at = text.find(op, at + 1)
                if at < 0:
                    raise SystemExit(f"no {a.brk} in {kind}")
            flip = (at + 1, xor)
        count, traps, bad = check(kind, obj, rng, flip)
        total_bad += len(bad)
        print(f"{kind}: {count} runs, {traps} traps, {len(bad)} deviations" + (f" (broken: {a.brk})" if flip else ""))
        for b in bad[:3]:
            print("   ", b)
    if a.brk:
        print("EXPECTED-RED " + ("PASS (the break was seen)" if total_bad else "FAIL (the break was NOT seen)"))
        sys.exit(0 if total_bad else 1)
    print("PASS_KERNEL_MEMORY_CONFORMANCE" if total_bad == 0 else "FAIL_KERNEL_MEMORY_CONFORMANCE")
    sys.exit(0 if total_bad == 0 else 1)


if __name__ == "__main__":
    main()
