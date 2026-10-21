#!/usr/bin/env python3
"""JUN-29 vehicle (b) minimal verification: raw-ELF byte emitter probe.

Measurement/orchestration only. Emits a Linux x86-64 ELF64 whose machine code
is written directly as hand-audited byte strings (no assembler, no toolchain in
the artifact build), covering exactly the runner constructs that vehicle (a)
(the seed compiler's standalone elf64 route) refused in the 2026-10-19
expressiveness probes:

  - capability I/O via context vtable   call [rdi+0x30]   (cap_call @48)
  - pair vtable dispatch                call [rdi+0x38/0x40/0x48] (slots 56/64/72)
  - fn-ref / indirect dispatch          mov rax,[rdi+disp]; call rax
  - tail dispatch (OP-CALLI tail)       jmp rax
  - string literal                      lea rsi,[rip+disp32]
  - fuel@8 inline contract              mov rax,[rdi+8] / sub / mov [rdi+8],rax
  - refusal trap                        js trap -> ud2
  - Linux process exit path             xor edi,edi; mov eax,60; syscall

Then verifies the emitted bytes with an independently written parser and a
pattern scan against the hand-audit table. Outputs a receipt JSON binding the
runner-slice receipt fields (JUN-30/JUN-102 admission binding).
"""
import hashlib
import json
import struct
import sys
from pathlib import Path

OUT_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---- kexe_context_v11 slot displacements (surface doc §1) -------------------
SLOT_CAP_CALL = 0x30      # @48
SLOT_PAIR_NEW = 0x38      # @56
SLOT_PAIR_FIRST = 0x40    # @64
SLOT_PAIR_SECOND = 0x48   # @72
SLOT_STRING_EQUAL = 0x70  # @112
SLOT_STRING_CONCAT = 0x78 # @120
FUEL_OFF = 0x08           # @8

RODATA = b"runner-probe\x00"

# ---- hand-assembled instruction table (each entry: mnemonic, bytes) --------
code = bytearray()
table = []  # (offset, mnemonic, bytes)


def emit(mnem, bts):
    table.append((len(code), mnem, bytes(bts)))
    code.extend(bts)


def here():
    return len(code)


def fix_at(off, bts, mnem_note):
    code[off:off + len(bts)] = bts
    for i, (o, m, b) in enumerate(table):
        if o == off:
            table[i] = (o, m + " ; fixed " + mnem_note, bytes(bts))


emit("push rbp", [0x55])
emit("mov rbp, rsp", [0x48, 0x89, 0xE5])
emit("push rbx", [0x53])
emit("push r12", [0x41, 0x54])
emit("mov rbx, rdi", [0x48, 0x89, 0xFB])          # ctx -> rbx (callee-saved)
emit("xor r12, r12", [0x4D, 0x31, 0xE4])          # accumulator
# fuel@8 inline contract: read, decrement, write back (via rbx)
emit("mov rax, [rbx+8]", [0x48, 0x8B, 0x43, 0x08])
emit("sub rax, 1", [0x48, 0x83, 0xE8, 0x01])
emit("mov [rbx+8], rax", [0x48, 0x89, 0x43, 0x08])
js_off = here()
emit("js trap", [0x78, 0x00])                      # rel8 patched below
# string literal: lea rsi, [rip+disp32] -> rodata
lea_off = here()
emit("lea rsi, [rip+disp32]", [0x48, 0x8D, 0x35, 0, 0, 0, 0])
# capability I/O through the vtable. rdi is caller-saved: reload ctx
# from rbx before every dispatch (hand-audit finding, see docs).
emit("mov rdi, rbx", [0x48, 0x89, 0xDF])
emit("call [rdi+0x30]  ; cap_call", [0xFF, 0x57, SLOT_CAP_CALL])
emit("add r12, rax", [0x49, 0x01, 0xC4])
# pair vtable dispatch at the exact slots measured in the kx64-v1 payloads
emit("mov rdi, rbx", [0x48, 0x89, 0xDF])
emit("call [rdi+0x38]  ; pair_new", [0xFF, 0x57, SLOT_PAIR_NEW])
emit("add r12, rax", [0x49, 0x01, 0xC4])
emit("mov rdi, rbx", [0x48, 0x89, 0xDF])
emit("call [rdi+0x40]  ; pair_first", [0xFF, 0x57, SLOT_PAIR_FIRST])
emit("add r12, rax", [0x49, 0x01, 0xC4])
emit("mov rdi, rbx", [0x48, 0x89, 0xDF])
emit("call [rdi+0x48]  ; pair_second", [0xFF, 0x57, SLOT_PAIR_SECOND])
emit("add r12, rax", [0x49, 0x01, 0xC4])
# fn-ref / indirect dispatch
emit("mov rdi, rbx", [0x48, 0x89, 0xDF])
emit("mov rax, [rdi+0x70]  ; string_equal", [0x48, 0x8B, 0x47, SLOT_STRING_EQUAL])
emit("call rax", [0xFF, 0xD0])
emit("add r12, rax", [0x49, 0x01, 0xC4])
emit("mov rdi, rbx", [0x48, 0x89, 0xDF])
emit("mov rax, [rdi+0x78]  ; string_concat", [0x48, 0x8B, 0x47, SLOT_STRING_CONCAT])
emit("call rax", [0xFF, 0xD0])
emit("add r12, rax", [0x49, 0x01, 0xC4])
emit("mov rax, r12", [0x4C, 0x89, 0xE0])
emit("pop r12", [0x41, 0x5C])
emit("pop rbx", [0x5B])
emit("pop rbp", [0x5D])
emit("ret", [0xC3])

trap_off = here()
emit("ud2", [0x0F, 0x0B])

tail_off = here()
emit("mov rax, [rdi+0x38]  ; tail pair_new", [0x48, 0x8B, 0x47, SLOT_PAIR_NEW])
emit("jmp rax", [0xFF, 0xE0])

exit_off = here()
emit("xor edi, edi", [0x31, 0xFF])
emit("mov eax, 60", [0xB8, 0x3C, 0x00, 0x00, 0x00])
emit("syscall", [0x0F, 0x05])

rodata_off = here()
code.extend(RODATA)

# ---- patch rip-relative and rel8 displacements -----------------------------
disp = rodata_off - (lea_off + 7)
struct.pack_into("<i", code, lea_off + 3, disp)
fix_at(lea_off, bytes(code[lea_off:lea_off + 7]),
       "disp32=%d -> rodata@%d" % (disp, rodata_off))
rel8 = trap_off - (js_off + 2)
assert -128 <= rel8 <= 127
code[js_off + 1] = rel8 & 0xFF
fix_at(js_off, bytes(code[js_off:js_off + 2]), "rel8=%d -> trap@%d" % (rel8, trap_off))

# ---- ELF64 packaging (Linux x86-64, one RX PT_LOAD) -----------------------
LOAD_VADDR = 0x400000
EHSIZE, PHENTSIZE = 64, 56
phoff = EHSIZE
code_file_off = EHSIZE + PHENTSIZE  # 0x78
entry = LOAD_VADDR + code_file_off
total = code_file_off + len(code)


def elf_bytes():
    eh = struct.pack(
        "<4sBBBB8x"       # e_ident
        "HHIQQQIHHHHHH",  # rest
        b"\x7fELF", 2, 1, 1, 0,
        2,              # e_type ET_EXEC
        0x3E,           # e_machine EM_X86_64
        1,              # e_version
        entry,          # e_entry
        phoff,          # e_phoff
        0,              # e_shoff (no section headers)
        0,              # e_flags
        EHSIZE, PHENTSIZE, 1, 64, 0, 0)
    ph = struct.pack(
        "<IIQQQQQQ",
        1,              # p_type PT_LOAD
        5,              # p_flags PF_R|PF_X
        0,              # p_offset
        LOAD_VADDR, LOAD_VADDR,
        total, total,
        0x1000)         # p_align
    assert len(eh) == 64 and len(ph) == 56
    return eh + ph + bytes(code)


blob = elf_bytes()
elf_path = OUT_DIR / "raw_elf_runner_probe"
elf_path.write_bytes(blob)

# ---- independent verification: re-read the file with a fresh parser --------
raw = elf_path.read_bytes()
checks = []


def check(name, ok, detail):
    checks.append({"check": name, "ok": bool(ok), "detail": detail})


magic = raw[0:4]
check("elf.magic", magic == b"\x7fELF", magic.hex())
check("elf.class64", raw[4] == 2, "EI_CLASS=%d" % raw[4])
check("elf.lsb", raw[5] == 1, "EI_DATA=%d" % raw[5])
(e_type, e_machine, e_version, e_entry, e_phoff, e_shoff, e_flags,
 e_ehsize, e_phentsize, e_phnum, e_shentsize, e_shnum, e_shstrndx) = \
    struct.unpack_from("<HHIQQQIHHHHHH", raw, 16)
check("elf.type_exec", e_type == 2, "e_type=%d" % e_type)
check("elf.machine_x86_64", e_machine == 0x3E, "e_machine=%d" % e_machine)
check("elf.entry", e_entry == entry, "e_entry=0x%x" % e_entry)
check("elf.phoff", e_phoff == phoff, "e_phoff=%d" % e_phoff)
p_type, p_flags, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, p_align = \
    struct.unpack_from("<IIQQQQQQ", raw, e_phoff)
check("phdr.pt_load", p_type == 1, "p_type=%d" % p_type)
check("phdr.rx", p_flags == 5, "p_flags=%d" % p_flags)
check("phdr.covers_code",
      p_offset <= code_file_off and p_filesz >= total,
      "p_offset=%d p_filesz=%d total=%d" % (p_offset, p_filesz, total))
check("phdr.entry_inside", p_vaddr <= e_entry < p_vaddr + p_memsz,
      "0x%x in [0x%x,0x%x)" % (e_entry, p_vaddr, p_vaddr + p_memsz))

# pattern scan: every hand-audited sequence present at its recorded offset
code_region = raw[code_file_off:code_file_off + len(code)]
for off, mnem, bts in table:
    if "fixed" in mnem:
        continue
    check("code@0x%03x %s" % (off, mnem),
          code_region[off:off + len(bts)] == bts, bts.hex())

# slot scan: call [rdi+disp8] at exactly the enumerated vtable slots
scan = {}
for disp8 in (SLOT_CAP_CALL, SLOT_PAIR_NEW, SLOT_PAIR_FIRST, SLOT_PAIR_SECOND):
    pat = bytes([0xFF, 0x57, disp8])
    scan["call [rdi+0x%x]" % disp8] = [i for i in range(len(code_region) - 2)
                                       if code_region[i:i + 3] == pat]
check("slots.call_disp",
      all(len(v) == 1 for v in scan.values()),
      json.dumps({k: ["0x%x" % i for i in v] for k, v in scan.items()}))
pat_fuel = bytes([0x48, 0x8B, 0x43, 0x08, 0x48, 0x83, 0xE8, 0x01, 0x48, 0x89, 0x43, 0x08])
check("fuel.inline_contract", pat_fuel in code_region, "read/sub/write @8 present")
check("trap.ud2", bytes([0x0F, 0x0B]) in code_region,
      "ud2@0x%x" % code_region.index(bytes([0x0F, 0x0B])))
check("tail.jmp_rax", bytes([0xFF, 0xE0]) in code_region,
      "jmp rax@0x%x" % code_region.index(bytes([0xFF, 0xE0])))

sha = hashlib.sha256(raw).hexdigest()
code_sha = hashlib.sha256(code_region).hexdigest()

receipt = {
    "receipt": "jun29-raw-elf-runner-probe.v1",
    "vehicle": "b",
    "artifact": {
        "path": elf_path.name,
        "sha256": sha,
        "bytes": len(raw),
        "format": "elf64",
        "target": "x86_64-linux",
        "entry": "0x%x" % entry,
        "code_sha256": code_sha,
    },
    "runner_slice_binding": {
        "layout": ":sysv-ctx-v11",
        "wires": [35, 37, 38, 39],
        "vtable_slots": {
            "cap_call": SLOT_CAP_CALL,
            "pair_new": SLOT_PAIR_NEW,
            "pair_first": SLOT_PAIR_FIRST,
            "pair_second": SLOT_PAIR_SECOND,
            "string_equal": SLOT_STRING_EQUAL,
            "string_concat": SLOT_STRING_CONCAT,
        },
        "fuel_offset": FUEL_OFF,
        "trap": "ud2",
    },
    "source_graph": {
        "producer": "raw_elf_runner_probe.py (hand-audited byte emitter)",
        "emitter_sha256": hashlib.sha256(
            Path(__file__).read_bytes()).hexdigest(),
    },
    "hand_audit_table": [
        {"off": "0x%x" % o, "mnem": m, "bytes": b.hex()} for o, m, b in table],
    "checks": checks,
    "checks_ok": all(c["ok"] for c in checks),
}

(OUT_DIR / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({
    "elf": str(elf_path), "sha256": sha, "bytes": len(raw),
    "entry": "0x%x" % entry, "checks_ok": receipt["checks_ok"],
    "checks": len(checks)}, indent=2))
sys.exit(0 if receipt["checks_ok"] else 1)
