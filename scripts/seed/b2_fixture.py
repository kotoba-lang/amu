"""A small x86_64 shared object for testing route B2's ELF loader (tools/b2/50-elf.kotoba) without a C compiler.

build(variant) returns the bytes of an ET_DYN file written here, byte by byte (a test fixture, not a build of
anything: it is machine code assembled by hand below). It has what the loader must handle:
* two PT_LOAD segments (R+X; R+W with a zero tail: the file holds 0xAA bytes beyond the segment's file size, where
  the loader must put zeros), PT_DYNAMIC, PT_GNU_RELRO over the first page of the RW segment, PT_GNU_STACK;
* DT_NEEDED libc.so.6 and libm.so.6 (this image's), DT_SONAME, DT_INIT and DT_INIT_ARRAY;
* a GNU hash table (3 buckets) over ten exported functions and one object;
* imports: strlen at GLIBC_2.2.5 (JUMP_SLOT), stderr at GLIBC_2.2.5 (GLOB_DAT, a data object), a weak reference
  (GLOB_DAT, bound to 0) and an import nothing implements (JUMP_SLOT, bound to a refusing stub);
* RELATIVE (also the init_array entry, as in a real object) and R_X86_64_64 (symbol plus addend) relocations in .rela.dyn.
Variants add one thing the loader must refuse by name: see VARIANTS.
"""
import struct

BASE_FUNCS = ["fx_add", "fx_strlen", "fx_stderr", "fx_weak", "fx_flag", "fx_flag2", "fx_ptr", "fx_ref64", "fx_bss", "fx_missing"]
VARIANTS = {
    "base": None,
    "zero-file-bss": None,
    "etexec": "not ET_DYN (a shared object)",
    "tls": "PT_TLS: thread-local storage is slice 2",
    "irelative": "relocation type 37",
    "unknown-reloc": "relocation type 99",
    "needed": "needed library not available in slice 1: libnot-there.so.9",
    "textrel": "DT_TEXTREL",
    "relr": "DT_RELR",
    "version": "this image has it at another symbol version than GLIBC_2.99999",
    "not-elf": "not an ELF file",
    "short": "file shorter than an ELF header",
}
JUNK = 0xAA


def gnu_hash(name):
    h = 5381
    for c in name.encode():
        h = (h * 33 + c) & 0xFFFFFFFF
    return h


def elf_hash(name):
    h = 0
    for c in name.encode():
        h = ((h << 4) + c) & 0xFFFFFFFF
        g = h & 0xF0000000
        if g:
            h ^= g >> 24
        h &= ~g & 0xFFFFFFFF
    return h


def build(variant="base"):
    assert variant in VARIANTS, variant
    if variant == "short":
        return b"\x7fELF\x02\x01"
    # --- addresses (file offset = virtual address throughout)
    text = 0x500
    got_stderr, got_weak, gotplt_strlen, gotplt_missing = 0x1200, 0x1208, 0x1210, 0x1218
    flag, flag2, ptrcell, ref64, string, bss = 0x2000, 0x2008, 0x2010, 0x2018, 0x2020, 0x2800
    if variant == "zero-file-bss":
        bss = 0x4008  # valid p_filesz=0 segment, not page-aligned
    init_array, dynamic = 0x1000, 0x1008
    # --- machine code
    code, addr_of = bytearray(), {}

    def func(name, build_fn):
        while len(code) % 16:
            code.append(0xCC)
        addr_of[name] = text + len(code)
        code.extend(build_fn(text + len(code)))

    def store_imm(target, imm):  # mov qword [rip+disp], imm32 ; ret
        return lambda a: b"\x48\xc7\x05" + struct.pack("<i", target - (a + 11)) + struct.pack("<I", imm) + b"\xc3"

    def load(target):  # mov rax, [rip+disp] ; ret
        return lambda a: b"\x48\x8b\x05" + struct.pack("<i", target - (a + 7)) + b"\xc3"

    def jump(target):  # jmp [rip+disp]
        return lambda a: b"\xff\x25" + struct.pack("<i", target - (a + 6))
    func("_init", store_imm(flag2, 7))
    func("fx_init", store_imm(flag, 0x4242))
    func("fx_add", lambda a: b"\x48\x8d\x04\x37\xc3")
    func("fx_strlen", jump(gotplt_strlen))
    func("fx_stderr", load(got_stderr))
    func("fx_weak", load(got_weak))
    func("fx_flag", load(flag))
    func("fx_flag2", load(flag2))
    func("fx_ptr", load(ptrcell))
    func("fx_ref64", load(ref64))
    func("fx_bss", load(bss))
    func("fx_missing", jump(gotplt_missing))
    text_end = text + len(code)
    assert text_end < 0x1000
    # --- symbols: null, imports, then the definitions ordered by hash bucket
    nbuckets = 3
    imports = [("strlen", 2, 2, 1), ("no_such_import", 2, 0, 1), ("weak_thing", 0, 0, 2), ("stderr", 1, 1, 1)]  # name, type, versym, bind
    defs = [(n, 2, addr_of[n], 5) for n in BASE_FUNCS] + [("fx_datum", 1, string, 19)]
    defs.sort(key=lambda d: gnu_hash(d[0]) % nbuckets)
    names = ["", "libc.so.6", "libm.so.6", "libfixture.so.1", "GLIBC_2.2.5"] + ([] if variant != "needed" else ["libnot-there.so.9"]) \
        + (["GLIBC_2.99999"] if variant == "version" else []) + [i[0] for i in imports] + [d[0] for d in defs]
    strtab, off = bytearray(), {}
    for n in names:
        if n not in off:
            off[n] = len(strtab)
            strtab.extend(n.encode() + b"\0")
    syms = [(0, 0, 0, 0)]
    for n, typ, _, bind in imports:
        syms.append((off[n], (bind << 4) | typ, 0, 0))
    first_def = len(syms)
    for n, typ, value, size in defs:
        syms.append((off[n], (1 << 4) | typ, value, size))
    dynsym = b"".join(struct.pack("<IBBHQQ", st_name, info, 0, 0 if info >> 4 and value == 0 and n_i < first_def else 1, value, size)
                      for n_i, (st_name, info, value, size) in enumerate(syms))
    versym = struct.pack("<H", 0) + b"".join(struct.pack("<H", v) for _, _, v, _ in imports) + struct.pack("<H", 1) * len(defs)
    # --- GNU hash: buckets by hash % nbuckets, chain bit 0 ends a bucket's run
    hashes = [gnu_hash(d[0]) for d in defs]
    buckets, chain = [0] * nbuckets, []
    for k, h in enumerate(hashes):
        b = h % nbuckets
        if buckets[b] == 0:
            buckets[b] = first_def + k
        last = k + 1 == len(hashes) or hashes[k + 1] % nbuckets != b
        chain.append((h & ~1) | (1 if last else 0))
    gnuhash = struct.pack("<IIII", nbuckets, first_def, 1, 6) + struct.pack("<Q", 0xFFFFFFFFFFFFFFFF) \
        + struct.pack("<%dI" % nbuckets, *buckets) + struct.pack("<%dI" % len(chain), *chain)
    ver_name = "GLIBC_2.99999" if variant == "version" else "GLIBC_2.2.5"
    verneed = struct.pack("<HHIII", 1, 1, off["libc.so.6"], 16, 0) + struct.pack("<IHHII", elf_hash(ver_name), 0, 2, off[ver_name], 0)
    # --- relocations
    sym_index = {n: i for i, n in enumerate([""] + [i[0] for i in imports] + [d[0] for d in defs])}
    rela = [(ptrcell, 8, 0, string), (init_array, 8, 0, addr_of["fx_init"]), (ref64, 1, sym_index["fx_add"], 0x10),
            (got_stderr, 6, sym_index["stderr"], 0), (got_weak, 6, sym_index["weak_thing"], 0)]
    if variant == "irelative":
        rela.insert(0, (ptrcell, 37, 0, text))
    if variant == "unknown-reloc":
        rela.insert(0, (ptrcell, 99, 0, 0))
    pltrela = [(gotplt_strlen, 7, sym_index["strlen"], 0), (gotplt_missing, 7, sym_index["no_such_import"], 0)]
    rela_b = b"".join(struct.pack("<QQq", o, (s << 32) | t, a) for o, t, s, a in rela)
    plt_b = b"".join(struct.pack("<QQq", o, (s << 32) | t, a) for o, t, s, a in pltrela)
    # --- layout of the tables in page 0 (after the program headers)
    nph = 6 if variant in ("tls", "zero-file-bss") else 5
    pos = 64 + 56 * nph
    layout = {}
    for name, blob, align in (("gnuhash", gnuhash, 8), ("dynsym", dynsym, 8), ("dynstr", bytes(strtab), 1), ("versym", versym, 2),
                              ("verneed", verneed, 8), ("rela", rela_b, 8), ("plt", plt_b, 8)):
        pos = (pos + align - 1) & -align
        layout[name] = (pos, blob)
        pos += len(blob)
    assert pos <= text, hex(pos)
    # --- dynamic section
    dyn = [(1, off["libc.so.6"]), (1, off["libm.so.6"]), (14, off["libfixture.so.1"]), (12, addr_of["_init"]), (25, init_array), (27, 8),
           (0x6FFFFEF5, layout["gnuhash"][0]), (5, layout["dynstr"][0]), (6, layout["dynsym"][0]), (10, len(strtab)), (11, 24),
           (7, layout["rela"][0]), (8, len(rela_b)), (9, 24), (23, layout["plt"][0]), (2, len(plt_b)), (20, 7),
           (0x6FFFFFF0, layout["versym"][0]), (0x6FFFFFFE, layout["verneed"][0]), (0x6FFFFFFF, 1), (30, 8)]
    if variant == "needed":
        dyn.insert(2, (1, off["libnot-there.so.9"]))
    if variant == "textrel":
        dyn.insert(0, (22, 0))
    if variant == "relr":
        dyn.insert(0, (36, 0))
    dyn.append((0, 0))
    dyn_b = b"".join(struct.pack("<qQ", t, v) for t, v in dyn)
    assert dynamic + len(dyn_b) <= got_stderr
    # --- the file
    img = bytearray([0] * 0x2900)
    for i in range(0x2040, 0x2900):
        img[i] = JUNK
    e_type = 2 if variant == "etexec" else 3
    img[0:64] = b"\x7fELF\x02\x01\x01" + b"\0" * 9 + struct.pack("<HHIQQQIHHHHHH", e_type, 62, 1, 0, 64, 0, 0, 64, 56, nph, 64, 0, 0)
    ph = [(1, 5, 0, 0, text_end, text_end, 0x1000), (1, 6, 0x1000, 0x1000, 0x1040, 0x2000, 0x1000),
          (2, 6, dynamic, dynamic, len(dyn_b), len(dyn_b), 8), (0x6474E552, 4, 0x1000, 0x1000, 0x1000, 0x1000, 1), (0x6474E551, 6, 0, 0, 0, 0, 16)]
    if variant == "tls":
        ph.append((7, 4, flag, flag, 8, 8, 8))
    if variant == "zero-file-bss":
        ph.append((1, 6, 0x3008, bss, 0, 8, 0x1000))
    for i, (t, f, o, v, fs, ms, al) in enumerate(ph):
        img[64 + 56 * i:64 + 56 * (i + 1)] = struct.pack("<IIQQQQQQ", t, f, o, v, v, fs, ms, al)
    for pos, blob in layout.values():
        img[pos:pos + len(blob)] = blob
    img[text:text_end] = code
    img[init_array:init_array + 8] = struct.pack("<Q", 0)   # relocated by the RELATIVE entry
    img[dynamic:dynamic + len(dyn_b)] = dyn_b
    img[got_stderr:got_stderr + 32] = b"\0" * 32
    img[flag:string] = b"\0" * (string - flag)
    img[string:string + 19] = b"hello from fixture\0"
    img[string + 19:0x2040] = b"\0" * (0x2040 - string - 19)
    out = bytes(img)
    if variant == "not-elf":
        out = b"\x7fELG" + out[4:]
    return out


def symbols():
    """The names the loader's tests look up."""
    return BASE_FUNCS + ["fx_datum"]
