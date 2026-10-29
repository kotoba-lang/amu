// JUN-593: wire-35 legacy text requests (the Linux kxrt-fs grammar) for the
// Mac fs2-cli-stdio-general runtime. One-time derivation record: the words are
// emitted by seed/macos-fs2-runtime-packager.kotoba; this file is not a build input.
//
// Entry: x0 ctx, x1 wire, x2 in-kind, x3 out-kind, x4 request pair handle, x30 LR.
// Anything that is not wire 35, string->string, granted, with a non-NUL first
// byte goes unchanged to the existing FS2 chain (Lchain, patched).
//
// Paths are "/c1/c2/..." beneath FD 3: each component non-empty, not "." or
// "..", no NUL; at most 1023 bytes. Opens use O_NOFOLLOW_ANY|O_RESOLVE_BENEATH|
// O_CLOEXEC on fd 3; rename uses renameatx_np(..., RENAME_NOFOLLOW_ANY).
//   <path>                read: file bytes (trap if it cannot be opened/read)
//   <path>EXISTS_SEP      "1" | "0"
//   <path>WRITE_SEP<data> create/truncate, write all; reply <data> (trap on failure)
//   <path>FSYNC_SEP       "1" | "0"
//   <from>RENAME_SEP<to>  "1" | "0"
//   <path>FLOCK_SEP       "1" | "0"  one nonblocking exclusive lock per process
//   <path>UNLOCK_SEP      "1" | "0"  only the held lock's path
// Any other *_SEP token traps (brk #0x37). Lock state: ctx+13312 fd+1,
// ctx+13320 path length, ctx+13328 path bytes (<= 1023).
.section __TEXT,__text,regular,pure_instructions
.globl _fs35
.p2align 2
_fs35:
    cmp x1, #35
    b.ne Lchain
    cmp x2, #1
    b.ne Lchain
    cmp x3, #1
    b.ne Lchain
    ldr x9, [x0, #16]
    movz x10, #8, lsl #32
    tst x9, x10
    b.eq Lchain
    cbz x4, Lchain
    ldr x9, [x0, #288]
    ldr x9, [x9]
    cmp x4, x9
    b.hi Lchain
    sub sp, sp, #2560
    stp x29, x30, [sp]
    stp x19, x20, [sp, #16]
    stp x21, x22, [sp, #32]
    stp x23, x24, [sp, #48]
    stp x25, x26, [sp, #64]
    stp x27, x28, [sp, #80]
    stp x0, x1, [sp, #96]
    stp x2, x3, [sp, #112]
    str x4, [sp, #128]
    mov x19, x0
    ldr x8, [x19, #296]
    sub x9, x4, #1
    add x8, x8, x9, lsl #4
    ldp x1, x2, [x8]
    mov x22, x2
    cbz x22, Lpass
    mov x0, x19
    bl Lspan                       // patched: bounded string-span resolver
    mov x21, x0
    ldrb w8, [x21]
    cbz w8, Lpass
    // find the first "_SEP"
    mov x23, #0
Lfind:
    add x9, x23, #4
    cmp x9, x22
    b.hi Lread
    ldr w9, [x21, x23]
    movz w10, #0x535f
    movk w10, #0x5045, lsl #16
    cmp w9, w10
    b.eq Lfound
    add x23, x23, #1
    b Lfind
Lfound:
    add x24, x23, #4               // x24 = end of token
    cmp x23, #6
    b.lo Lfive
    sub x25, x23, #6
    ldr w9, [x21, x25]
    add x10, x25, #4
    ldrh w11, [x21, x10]
    movz w12, #0x5845
    movk w12, #0x5349, lsl #16     // "EXIS"
    cmp w9, w12
    b.ne 1f
    movz w12, #0x5354              // "TS"
    cmp w11, w12
    b.eq Lexists
1:  movz w12, #0x4552
    movk w12, #0x414e, lsl #16     // "RENA"
    cmp w9, w12
    b.ne 2f
    movz w12, #0x454d              // "ME"
    cmp w11, w12
    b.eq Lrename
2:  movz w12, #0x4e55
    movk w12, #0x4f4c, lsl #16     // "UNLO"
    cmp w9, w12
    b.ne Lfive
    movz w12, #0x4b43              // "CK"
    cmp w11, w12
    b.eq Lunlock
Lfive:
    cmp x23, #5
    b.lo Lunknown
    sub x25, x23, #5
    ldr w9, [x21, x25]
    add x10, x25, #4
    ldrb w11, [x21, x10]
    movz w12, #0x5257
    movk w12, #0x5449, lsl #16     // "WRIT"
    cmp w9, w12
    b.ne 3f
    cmp w11, #0x45                 // "E"
    b.eq Lwrite
3:  movz w12, #0x5346
    movk w12, #0x4e59, lsl #16     // "FSYN"
    cmp w9, w12
    b.ne 4f
    cmp w11, #0x43                 // "C"
    b.eq Lfsync
4:  movz w12, #0x4c46
    movk w12, #0x434f, lsl #16     // "FLOC"
    cmp w9, w12
    b.ne Lunknown
    cmp w11, #0x4b                 // "K"
    b.eq Lflock
Lunknown:
    brk #0x37

// ---- path validation: x0 src, x1 len, x2 dst -> x0 0 ok / -1; dst = relative C string
Lvalidate:
    cmp x1, #2
    b.lt Lvbad
    cmp x1, #1023
    b.gt Lvbad
    ldrb w9, [x0]
    cmp w9, #47
    b.ne Lvbad
    mov x3, #1                     // i
    mov x4, #1                     // component start
Lvloop:
    cmp x3, x1
    b.eq Lvend
    ldrb w9, [x0, x3]
    cbz w9, Lvbad
    cmp w9, #47
    b.eq Lvslash
    sub x10, x3, #1
    strb w9, [x2, x10]
    add x3, x3, #1
    b Lvloop
Lvslash:
    sub x10, x3, x4                // component length
    cbz x10, Lvbad
    cmp x10, #1
    b.ne 5f
    ldrb w9, [x0, x4]
    cmp w9, #46
    b.eq Lvbad
5:  cmp x10, #2
    b.ne 6f
    ldrb w9, [x0, x4]
    add x11, x4, #1
    ldrb w12, [x0, x11]
    cmp w9, #46
    b.ne 6f
    cmp w12, #46
    b.eq Lvbad
6:  sub x10, x3, #1
    mov w9, #47
    strb w9, [x2, x10]
    add x3, x3, #1
    mov x4, x3
    b Lvloop
Lvend:
    sub x10, x3, x4
    cbz x10, Lvbad
    cmp x10, #1
    b.ne 7f
    ldrb w9, [x0, x4]
    cmp w9, #46
    b.eq Lvbad
7:  cmp x10, #2
    b.ne 8f
    ldrb w9, [x0, x4]
    add x11, x4, #1
    ldrb w12, [x0, x11]
    cmp w9, #46
    b.ne 8f
    cmp w12, #46
    b.eq Lvbad
8:  sub x10, x1, #1
    strb wzr, [x2, x10]
    mov x0, #0
    ret
Lvbad:
    movn x0, #0
    ret

// path [0, x23) -> buf1 at sp+512; x0 = 0 ok / -1 bad
Lpath1:
    mov x26, x30
    mov x0, x21
    mov x1, x23
    add x2, sp, #512
    bl Lvalidate
    mov x30, x26
    ret

// openat(3, buf1, x2 flags, x3 mode) -> x0 fd, carry on error
Lopen1:
    mov x0, #3
    add x1, sp, #512
    mov x16, #463
    movk x16, #0x2000, lsl #16
    svc #0x80
    ret

Lclose:
    mov x16, #6
    movk x16, #0x2000, lsl #16
    svc #0x80
    ret

// ---- read
Lread:
    mov x23, x22
    bl Lpath1
    cbnz x0, Lfail
    movz x2, #0x1004
    movk x2, #0x2100, lsl #16
    mov x3, #0
    bl Lopen1
    b.cs Lfail
    mov x20, x0
    ldr x23, [x19, #408]
    movz x8, #0x1000, lsl #16
    sub x8, x8, #1
    cmp x23, x8
    b.hi Lfail
    sub x24, x8, x23               // room
    ldr x25, [x19, #400]
    add x25, x25, x23              // destination
    mov x26, #0                    // bytes read
Lrloop:
    sub x2, x24, x26
    cbz x2, Lrprobe
    mov x0, x20
    add x1, x25, x26
    mov x16, #3
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cs Lrerr
    cbz x0, Lrdone
    add x26, x26, x0
    b Lrloop
Lrprobe:
    mov x0, x20
    add x1, sp, #256
    mov x2, #1
    mov x16, #3
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cs Lrerr
    cbnz x0, Lfail                 // larger than the pool
    b Lrdone
Lrerr:
    cmp x0, #4
    b.eq Lrloop
    b Lfail
Lrdone:
    mov x0, x20
    bl Lclose
    b.cs Lfail
    add x11, x23, x26
    str x11, [x19, #408]
    mov x0, x19
    mvn x1, x23
    mov x2, x26
    b Lmint

// ---- exists / fsync
Lexists:
    cmp x24, x22
    b.ne Lunknown
    mov x23, x25
    bl Lpath1
    cbnz x0, Lzero
    movz x2, #0x1004
    movk x2, #0x2100, lsl #16
    mov x3, #0
    bl Lopen1
    b.cs Lzero
    bl Lclose
    b.cs Lzero
    b Lone
Lfsync:
    cmp x24, x22
    b.ne Lunknown
    mov x23, x25
    bl Lpath1
    cbnz x0, Lzero
    movz x2, #0x1004
    movk x2, #0x2100, lsl #16
    mov x3, #0
    bl Lopen1
    b.cs Lzero
    mov x20, x0
    mov x16, #95
    movk x16, #0x2000, lsl #16
    svc #0x80
    cset x27, cc
    mov x0, x20
    bl Lclose
    b.cs Lzero
    cbz x27, Lzero
    b Lone

// ---- write
Lwrite:
    mov x23, x25
    bl Lpath1
    cbnz x0, Lfail
    movz x2, #0x1605
    movk x2, #0x2100, lsl #16
    mov x3, #420
    bl Lopen1
    b.cs Lfail
    mov x20, x0
    add x25, x21, x24              // data
    sub x26, x22, x24              // data length
    mov x27, #0
Lwloop:
    cmp x27, x26
    b.eq Lwdone
    mov x0, x20
    add x1, x25, x27
    sub x2, x26, x27
    mov x16, #4
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cs Lwerr
    cbz x0, Lfail
    add x27, x27, x0
    b Lwloop
Lwerr:
    cmp x0, #4
    b.eq Lwloop
    b Lfail
Lwdone:
    mov x0, x20
    bl Lclose
    b.cs Lfail
    // reply: a copy of the data
    ldr x23, [x19, #408]
    movz x8, #0x1000, lsl #16
    sub x8, x8, x26
    cmp x23, x8
    b.hi Lfail
    ldr x9, [x19, #400]
    add x9, x9, x23
    mov x10, #0
Lwcopy:
    cmp x10, x26
    b.eq Lwminted
    ldrb w11, [x25, x10]
    strb w11, [x9, x10]
    add x10, x10, #1
    b Lwcopy
Lwminted:
    add x11, x23, x26
    str x11, [x19, #408]
    mov x0, x19
    mvn x1, x23
    mov x2, x26
    b Lmint

// ---- rename
Lrename:
    mov x23, x25
    bl Lpath1
    cbnz x0, Lzero
    add x0, x21, x24
    sub x1, x22, x24
    add x2, sp, #1536
    bl Lvalidate
    cbnz x0, Lzero
    mov x0, #3
    add x1, sp, #512
    mov x2, #3
    add x3, sp, #1536
    mov x4, #0x10                  // RENAME_NOFOLLOW_ANY
    mov x16, #488                  // renameatx_np
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cs Lzero
    b Lone

// ---- flock / unlock
Lflock:
    cmp x24, x22
    b.ne Lunknown
    mov x23, x25
    bl Lpath1
    cbnz x0, Lzero
    ldr x8, [x19, #13312]
    cbnz x8, Lzero
    movz x2, #0x1206
    movk x2, #0x2100, lsl #16
    mov x3, #384
    bl Lopen1
    b.cs Lzero
    mov x20, x0
    mov x1, #6                     // LOCK_EX|LOCK_NB
    mov x16, #131
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cc 9f
    mov x0, x20
    bl Lclose
    b Lzero
9:  add x8, x20, #1
    str x8, [x19, #13312]
    sub x9, x23, #1                // relative length
    str x9, [x19, #13320]
    mov x10, #13328
    add x10, x19, x10
    add x11, sp, #512
    mov x12, #0
10: cmp x12, x9
    b.eq Lone
    ldrb w13, [x11, x12]
    strb w13, [x10, x12]
    add x12, x12, #1
    b 10b
Lunlock:
    cmp x24, x22
    b.ne Lunknown
    mov x23, x25
    bl Lpath1
    cbnz x0, Lzero
    ldr x8, [x19, #13312]
    cbz x8, Lzero
    sub x9, x23, #1
    ldr x10, [x19, #13320]
    cmp x9, x10
    b.ne Lzero
    mov x10, #13328
    add x10, x19, x10
    add x11, sp, #512
    mov x12, #0
11: cmp x12, x9
    b.eq 12f
    ldrb w13, [x11, x12]
    ldrb w14, [x10, x12]
    cmp w13, w14
    b.ne Lzero
    add x12, x12, #1
    b 11b
12: sub x20, x8, #1
    mov x0, x20
    mov x1, #8                     // LOCK_UN
    mov x16, #131
    movk x16, #0x2000, lsl #16
    svc #0x80
    cset x27, cc
    mov x0, x20
    bl Lclose
    cset x28, cc
    str xzr, [x19, #13312]
    and x27, x27, x28
    cbz x27, Lzero
    b Lone

// ---- replies
Lzero:
    mov w22, #48
    b Lbyte
Lone:
    mov w22, #49
Lbyte:
    ldr x8, [x19, #408]
    movz x9, #0x1000, lsl #16
    sub x9, x9, #1
    cmp x8, x9
    b.hi Lfail
    ldr x9, [x19, #400]
    strb w22, [x9, x8]
    add x11, x8, #1
    str x11, [x19, #408]
    mov x0, x19
    mvn x1, x8
    mov x2, #1
Lmint:
    ldr x16, [x19, #56]
    blr x16
    ldp x27, x28, [sp, #80]
    ldp x25, x26, [sp, #64]
    ldp x23, x24, [sp, #48]
    ldp x21, x22, [sp, #32]
    ldp x19, x20, [sp, #16]
    ldp x29, x30, [sp]
    add sp, sp, #2560
    ret
Lpass:
    ldp x0, x1, [sp, #96]
    ldp x2, x3, [sp, #112]
    ldr x4, [sp, #128]
    ldp x27, x28, [sp, #80]
    ldp x25, x26, [sp, #64]
    ldp x23, x24, [sp, #48]
    ldp x21, x22, [sp, #32]
    ldp x19, x20, [sp, #16]
    ldp x29, x30, [sp]
    add sp, sp, #2560
Lchain:
    b Lchain                       // patched: the existing FS2 chain entry
Lfail:
    brk #0x36
Lspan:
    brk #0x101                     // never reached: the bl above is patched
