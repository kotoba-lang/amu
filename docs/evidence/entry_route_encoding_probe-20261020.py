#!/usr/bin/env python3
"""JUN-29 entry-route measurement: encoding probe for Route A (entry-stub)
setup-syscall sites. Hand-audited byte strings; llvm-objdump is the
independent decode instrument (measurement only, not an artifact build).
Counts the byte cost the kernel-profile ELF entry stub would grow by if the
runner setup (mmap arenas / openat2 / prlimit64 / prctl / seccomp) is emitted
inline in guest code (Route A) vs kept in the supervisor (Route B)."""
import struct, sys, json, hashlib, subprocess, os

WRAP = os.path.expanduser("~/.hermes/cache/scratch/jun29-call-abi-20261019/wrap_elf.py")

# x86-64 Linux syscall encodings (hand-audited; verified by llvm-objdump decode)
def mov_eax(imm): return b"\xb8" + struct.pack("<I", imm)      # mov eax,imm32  5B
def mov_rax(imm): return b"\x48\xc7\xc0" + struct.pack("<i", imm)  # mov rax,imm32 7B
def mov_edi(imm): return b"\xbf" + struct.pack("<I", imm)      # 5B
def mov_esi(imm): return b"\xbe" + struct.pack("<I", imm)      # 5B
def mov_edx(imm): return b"\xba" + struct.pack("<I", imm)      # 5B
def mov_r10():    return b"\x49\x89\xfa"                       # mov r10,rdi   3B (5th arg)
def mov_r8():     return b"\x49\x89\xf8"                       # mov r8,rdi    3B (6th arg)
def mov_edi_r10():return b"\x44\x89\xd7"                       # mov edi,r10d  3B (arg4 <- r10)
def mov_esi_r8(): return b"\x44\x89\xc6"                       # mov esi,r8d   3B
def load_arg(idx_reg_from_rbp, tmp):  # mov tmp,[rbp-off] 4B shape
    return b"\x48\x8b\x7d\xf8"                                 # mov rdi,[rbp-8] 4B (measured shape)
def syscall():    return b"\x0f\x05"                           # 2B

sites = {}
# mmap(addr=0, len=KEXE_VECTORS*8, prot=3, flags=0x22, fd=-1, off=0)  6 args
mmap_site = (mov_eax(9) + mov_edi(0) + mov_esi(4194304) + mov_edx(3) +
             mov_eax(9)[:0] + mov_edx(0x22)[:0])  # placeholder replaced below
# build explicitly, 6-arg: rdi,rsi,rdx,r10,r8,r9
mmap_site = (mov_eax(9) + b"\x31\xff" +            # xor edi,edi        2B
             mov_esi(4194304) +                    # mov esi,imm        5B
             mov_edx(3) +                          # mov edx,3 (RW)     5B
             b"\x41\xba\x22\x00\x00\x00" +         # mov r10d,0x22      6B (MAP_PRIVATE|ANON)
             b"\x49\xc7\xc0\xff\xff\xff\xff" +     # mov r8,-1          7B
             b"\x4d\x31\xc9" +                     # xor r9,r9          3B
             syscall())                            #                    2B
sites["mmap-arena"] = mmap_site

# openat2(dirfd=scope_fd, path, &how(RESOLVE_BENEATH), 24)  4 args  (syscall 437)
openat2_site = (mov_eax(437) + load_arg(0,0) +     # mov eax,437; mov rdi,[rbp-8] (fd)
                mov_esi(0x1234000) +               # path ptr placeholder 5B
                mov_edx(0x5678000) +               # &how placeholder     5B
                b"\x41\xba\x18\x00\x00\x00" +      # mov r10d,24          6B
                syscall())
sites["openat2-resolve-beneath"] = openat2_site

# prlimit64(pid=0, RLIMIT_AS=9, &rlim, old=0)  4 args (syscall 302)
prlimit_site = (mov_eax(302) + mov_edi(0) + mov_esi(9) + mov_edx(0x1234000) +
                b"\x45\x31\xd2" +                  # xor r10d,r10d        3B
                syscall())
sites["prlimit64-rlimit-as"] = prlimit_site

# prctl(PR_SET_NO_NEW_PRIVS=38, 1, 0, 0, 0)  5 args (syscall 157)
prctl_site = (mov_eax(157) + mov_edi(38) + mov_esi(1) + mov_edx(0) +
              b"\x45\x31\xd2" + b"\x45\x31\xc0" +  # xor r10d; xor r8d    6B
              syscall())
sites["prctl-no-new-privs"] = prctl_site

# seccomp(SECCOMP_SET_MODE_FILTER=1, flags=0, &fprog)  3 args (syscall 317)
seccomp_site = (mov_eax(317) + mov_edi(1) + mov_esi(0) + mov_edx(0x1234000) + syscall())
sites["seccomp-set-mode-filter"] = seccomp_site

# measured control: the profile-0 stub's own exit site shape (1 arg)
exit_site = (mov_edi(0) + mov_eax(60) + syscall())
sites["control-exit-as-in-stub"] = exit_site

blob = b"\x90" + b"\xcc".join(sites.values())  # int3 separators, 1 nop prefix
open("/tmp/entry_route_setup_sites.bin", "wb").write(blob)
os.system(f"python3 {WRAP} /tmp/entry_route_setup_sites.bin /tmp/entry_route_setup_sites.elf > /dev/null")

total = {k: len(v) for k, v in sites.items()}
print(json.dumps({"site_bytes": total, "sites": len(sites),
                  "setup_sites_excl_control": len(sites)-1,
                  "blob_bytes_incl_5_separators": len(blob),
                  "sha256_blob": hashlib.sha256(blob).hexdigest()}, indent=1))
