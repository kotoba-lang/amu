.section __TEXT,__text,regular,pure_instructions
.globl _ksl1_or_fs2
.p2align 2
_ksl1_or_fs2:
    cmp x1, #35
    b.ne Lbc
    cmp x2, #8
    b.ne Lbc
    cmp x3, #8
    b.ne Lbc
    cbz x4, Lbc
    ldr x8, [x0, #16008]
    cmp x4, x8
    b.hi Lbc
    ldr x8, [x0, #16000]
    sub x9, x4, #1
    add x8, x8, x9, lsl #4
    ldp x9, x10, [x8]
    cmp x10, #7
    b.lo Lbc
    mov x8, #4101
    cmp x10, x8
    b.hi Lbc
    ldr x8, [x0, #16024]
    cmp x9, x8
    b.hi Lbc
    sub x8, x8, x9
    cmp x10, x8
    b.hi Lbc
    ldr x8, [x0, #16016]
    add x12, x8, x9, lsl #3
    ldr x8, [x12]
    cbnz x8, Lbc
    ldr x8, [x12, #8]
    cmp x8, #75
    b.ne Lbc
    ldr x8, [x12, #16]
    cmp x8, #83
    b.ne Lbc
    ldr x8, [x12, #24]
    cmp x8, #76
    b.ne Lbc
    ldr x8, [x12, #32]
    cmp x8, #49
    b.ne Lbc
    ldr x8, [x12, #40]
    cbnz x8, Lbc
    sub sp, sp, #12288
    stp x29, x30, [sp]
    stp x19, x20, [sp, #16]
    stp x21, x22, [sp, #32]
    stp x23, x24, [sp, #48]
    stp x25, x26, [sp, #64]
    stp x27, x28, [sp, #80]
    mov x19, x0
    mov x20, x12
    mov x21, x10
    ldr x8, [x19, #16]
    movz x9, #8, lsl #32
    tst x8, x9
    b.eq Lbad
    mov x22, #6
    add x1, sp, #128
Lpath:
    cmp x22, x21
    b.hs Lpathdone
    ldr x8, [x20, x22, lsl #3]
    cbz x8, Lbad
    cmp x8, #255
    b.hi Lbad
    cmp x8, #47
    b.eq Lbad
    sub x9, x22, #6
    strb w8, [x1, x9]
    add x22, x22, #1
    b Lpath
Lpathdone:
    cmp x22, #6
    b.eq Lbad
    sub x22, x22, #6
    strb wzr, [x1, x22]
    mov x0, #3
    mov x2, #0x1004
    movk x2, #0x2100, lsl #16
    mov x3, #0
    mov x16, #463
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cs Lstatus0
    mov x23, x0
    mov x0, x23
    add x1, sp, #4096
    add x1, x1, #256
    mov x16, #339
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cs Lclosefail
    ldrh w8, [sp, #4356]
    and w8, w8, #0xf000
    cmp w8, #0x8000
    b.ne Lclosefail
    ldr x24, [sp, #4448]
    cmp x24, #1048576
    b.hi Lclosefail
    mov x0, x19
    add x1, x24, #1
    ldr x16, [x19, #200]
    blr x16
    mov x25, x0
    cbz x25, Lbad
    ldr x8, [x19, #16008]
    cmp x25, x8
    b.hi Lbad
    ldr x8, [x19, #16000]
    sub x9, x25, #1
    add x8, x8, x9, lsl #4
    ldp x9, x10, [x8]
    add x11, x24, #1
    cmp x10, x11
    b.ne Lbad
    ldr x8, [x19, #16016]
    add x26, x8, x9, lsl #3
    mov x8, #1
    str x8, [x26]
    mov x27, #0
Lchunk:
    cmp x27, x24
    b.hs Lprobe
    sub x2, x24, x27
    cmp x2, #4096
    b.ls Lread
    mov x2, #4096
Lread:
    mov x0, x23
    add x1, sp, #4096
    add x1, x1, #512
    mov x16, #3
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cs Lreaderr
    cbz x0, Lclosefail
    add x1, sp, #4096
    add x1, x1, #512
    mov x28, #0
Lcopy:
    cmp x28, x0
    b.hs Lcopied
    ldrb w8, [x1, x28]
    add x9, x27, x28
    add x9, x9, #1
    str x8, [x26, x9, lsl #3]
    add x28, x28, #1
    b Lcopy
Lcopied:
    add x27, x27, x0
    b Lchunk
Lreaderr:
    cmp x0, #4
    b.eq Lchunk
    b Lclosefail
Lprobe:
    mov x0, x23
    add x1, sp, #8192
    add x1, x1, #512
    mov x2, #1
    mov x16, #3
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cs Lprobeerr
    cbnz x0, Lclosefail
    mov x0, x23
    mov x16, #6
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cs Lstatus0
    mov x0, x25
    b Lreturn
Lprobeerr:
    cmp x0, #4
    b.eq Lprobe
Lclosefail:
    mov x0, x23
    mov x16, #6
    movk x16, #0x2000, lsl #16
    svc #0x80
Lstatus0:
    mov x0, x19
    mov x1, #1
    ldr x16, [x19, #200]
    blr x16
    cbz x0, Lbad
    mov x25, x0
    ldr x8, [x19, #16000]
    sub x9, x25, #1
    add x8, x8, x9, lsl #4
    ldp x9, x10, [x8]
    cmp x10, #1
    b.ne Lbad
    ldr x8, [x19, #16016]
    add x8, x8, x9, lsl #3
    str xzr, [x8]
    mov x0, x25
Lreturn:
    ldp x27, x28, [sp, #80]
    ldp x25, x26, [sp, #64]
    ldp x23, x24, [sp, #48]
    ldp x21, x22, [sp, #32]
    ldp x19, x20, [sp, #16]
    ldp x29, x30, [sp]
    add sp, sp, #12288
    ret
Lbad:
    brk #0x36
Lbc:
    b Lbc_stub
Lbc_stub:
    brk #0x103
