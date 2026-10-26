.section __TEXT,__text,regular,pure_instructions
.globl _fs2_dispatch
.p2align 2
_fs2_dispatch:
    cmp x1, #35
    b.ne Llegacy
    stp x29, x30, [sp, #-256]!
    stp x19, x20, [sp, #16]
    stp x21, x22, [sp, #32]
    stp x23, x24, [sp, #48]
    mov x19, x0
    mov x20, x4
    ldr x8, [x19, #16]
    movz x9, #8, lsl #32
    tst x8, x9
    b.eq Lbad
    cmp x2, #1
    b.ne Lunsupported
    cmp x3, #1
    b.ne Lunsupported
    cbz x20, Lbad
    ldr x8, [x19, #288]
    ldr x8, [x8]
    cmp x20, x8
    b.hi Lbad
    ldr x8, [x19, #296]
    sub x9, x20, #1
    add x8, x8, x9, lsl #4
    ldp x1, x2, [x8]
    mov x22, x2
    mov x0, x19
    bl Lspan_stub
    mov x21, x0
    cmp x22, #8
    b.lo Lbad
    mov x8, #4102
    cmp x22, x8
    b.hi Lbad
    ldrb w8, [x21]
    cbnz w8, Lbad
    ldrb w8, [x21, #1]
    cmp w8, #70
    b.ne Lbad
    ldrb w8, [x21, #2]
    cmp w8, #83
    b.ne Lbad
    ldrb w8, [x21, #3]
    cmp w8, #50
    b.ne Lbad
    ldrb w8, [x21, #4]
    cbnz w8, Lbad
    ldrb w8, [x21, #5]
    cmp w8, #68
    b.eq Lpath
    cmp w8, #65
    b.ne Lunsupported
Lpath:
    mov x9, #6
Lscan:
    cmp x9, x22
    b.hs Lbad
    ldrb w8, [x21, x9]
    cbz w8, Lend
    add x9, x9, #1
    b Lscan
Lend:
    add x9, x9, #1
    cmp x9, x22
    b.ne Lbad
    add x1, x21, #6
    ldrb w8, [x1]
    cmp w8, #47
    b.ne Lopen
    add x1, x1, #1
Lopen:
    mov x0, #3
    mov x2, #0x1004
    movk x2, #0x2100, lsl #16
    mov x3, #0
    mov x16, #463
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cs Lopenfail
    mov x20, x0
    ldrb w8, [x21, #5]
    cmp w8, #65
    b.eq Lread
    mov x0, x20
    mov x16, #6
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cs Lbad
    mov w22, #49
    b Lanswer
Lopenfail:
    ldrb w8, [x21, #5]
    cmp w8, #65
    b.eq Lbad
Labsent:
    mov w22, #48
Lanswer:
    ldr x8, [x19, #408]
    movz x9, #0x1000, lsl #16
    sub x9, x9, #6
    cmp x8, x9
    b.hi Lbad
    ldr x9, [x19, #400]
    add x9, x9, x8
    movz w10, #0x4600
    movk w10, #0x3253, lsl #16
    str w10, [x9]
    strb wzr, [x9, #4]
    strb w22, [x9, #5]
    add x11, x8, #6
    str x11, [x19, #408]
    mov x0, x19
    mvn x1, x8
    mov x2, #6
    b Lmint
Lread:
    mov x0, x20
    add x1, sp, #80
    mov x16, #339
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cs Lbad
    ldrh w8, [sp, #84]
    and w8, w8, #0xf000
    cmp w8, #0x8000
    b.ne Lbad
    ldr x23, [x19, #408]
    movz x8, #0x1000, lsl #16
    sub x8, x8, #5
    cmp x23, x8
    b.hi Lbad
    sub x24, x8, x23
    movz x8, #0x80, lsl #16
    sub x8, x8, #5
    cmp x24, x8
    csel x24, x8, x24, hi
    ldr x21, [x19, #400]
    add x21, x21, x23
    add x21, x21, #5
    mov x22, #0
Lreadloop:
    sub x2, x24, x22
    cbz x2, Lprobe
    mov x0, x20
    add x1, x21, x22
    mov x16, #3
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cs Lreaderr
    cbz x0, Lreaddone
    add x22, x22, x0
    b Lreadloop
Lprobe:
    mov x0, x20
    add x1, sp, #64
    mov x2, #1
    mov x16, #3
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cs Lreaderr
    cbnz x0, Lbad
    b Lreaddone
Lreaderr:
    cmp x0, #4
    b.eq Lreadloop
    b Lbad
Lreaddone:
    mov x0, x20
    mov x16, #6
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cs Lbad
    sub x9, x21, #5
    movz w10, #0x4600
    movk w10, #0x3253, lsl #16
    str w10, [x9]
    strb wzr, [x9, #4]
    add x11, x23, x22
    add x11, x11, #5
    str x11, [x19, #408]
    mov x0, x19
    mvn x1, x23
    add x2, x22, #5
Lmint:
    ldr x16, [x19, #56]
    blr x16
    ldp x23, x24, [sp, #48]
    ldp x21, x22, [sp, #32]
    ldp x19, x20, [sp, #16]
    ldp x29, x30, [sp], #256
    ret
Llegacy:
    cmp x1, #38
    b Llegacy_stub
Lunsupported:
    brk #0x35
Lbad:
    brk #0x36
Lspan_stub:
    brk #0x101
Llegacy_stub:
    brk #0x102
