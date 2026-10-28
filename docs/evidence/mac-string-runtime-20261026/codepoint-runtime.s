.text
.p2align 2
.globl _codepoint
_codepoint:
    sub sp, sp, #96
    stp x29, x30, [sp, #0]
    stp x19, x20, [sp, #16]
    stp x21, x22, [sp, #32]
    stp x23, x24, [sp, #48]
    stp x25, x26, [sp, #64]
    mov x19, x0
    mov x20, x2
    cmp x1, #1
    b.lo Ltrap
    tbnz x20, #63, Ltrap
    ldr x8, [x19, #288]
    ldr x8, [x8]
    cmp x1, x8
    b.hi Ltrap
    ldr x9, [x19, #296]
    sub x10, x1, #1
    add x10, x9, x10, lsl #4
    ldp x3, x26, [x10]
    tbnz x26, #63, Ltrap
    cmp x20, x26
    b.hs Ltrap
    mov x0, x19
    mov x1, x3
    mov x2, x26
    bl Lresolve
    mov x21, x0
    mov x22, #-1
    mov x23, #0
Lscan:
    cmp x23, x26
    b.hs Ldone
    ldrb w8, [x21, x23]
    cmp w8, #0x80
    b.lo Lascii
    cmp w8, #0xc2
    b.lo Ltrap
    cmp w8, #0xe0
    b.lo Ltwo
    cmp w8, #0xf0
    b.lo Lthree
    cmp w8, #0xf5
    b.lo Lfour
    b Ltrap
Lascii:
    mov x24, x8
    mov x25, #1
    b Lpoint
Ltwo:
    add x9, x23, #1
    cmp x9, x26
    b.hs Ltrap
    ldrb w10, [x21, x9]
    and w11, w10, #0xc0
    cmp w11, #0x80
    b.ne Ltrap
    and w12, w8, #0x1f
    lsl w12, w12, #6
    and w10, w10, #0x3f
    orr w24, w12, w10
    mov x25, #2
    b Lpoint
Lthree:
    add x9, x23, #2
    cmp x9, x26
    b.hs Ltrap
    sub x9, x9, #1
    ldrb w10, [x21, x9]
    and w11, w10, #0xc0
    cmp w11, #0x80
    b.ne Ltrap
    cmp w8, #0xe0
    b.ne Lthree_not_e0
    cmp w10, #0xa0
    b.lo Ltrap
Lthree_not_e0:
    cmp w8, #0xed
    b.ne Lthree_not_ed
    cmp w10, #0xa0
    b.hs Ltrap
Lthree_not_ed:
    add x9, x9, #1
    ldrb w11, [x21, x9]
    and w12, w11, #0xc0
    cmp w12, #0x80
    b.ne Ltrap
    and w12, w8, #0x0f
    lsl w12, w12, #12
    and w10, w10, #0x3f
    lsl w10, w10, #6
    orr w12, w12, w10
    and w11, w11, #0x3f
    orr w24, w12, w11
    mov x25, #3
    b Lpoint
Lfour:
    add x9, x23, #3
    cmp x9, x26
    b.hs Ltrap
    sub x9, x9, #2
    ldrb w10, [x21, x9]
    and w11, w10, #0xc0
    cmp w11, #0x80
    b.ne Ltrap
    cmp w8, #0xf0
    b.ne Lfour_not_f0
    cmp w10, #0x90
    b.lo Ltrap
Lfour_not_f0:
    cmp w8, #0xf4
    b.ne Lfour_not_f4
    cmp w10, #0x90
    b.hs Ltrap
Lfour_not_f4:
    add x9, x9, #1
    ldrb w11, [x21, x9]
    and w12, w11, #0xc0
    cmp w12, #0x80
    b.ne Ltrap
    add x9, x9, #1
    ldrb w12, [x21, x9]
    and w13, w12, #0xc0
    cmp w13, #0x80
    b.ne Ltrap
    and w13, w8, #0x07
    lsl w13, w13, #18
    and w10, w10, #0x3f
    lsl w10, w10, #12
    orr w13, w13, w10
    and w11, w11, #0x3f
    lsl w11, w11, #6
    orr w13, w13, w11
    and w12, w12, #0x3f
    orr w24, w13, w12
    mov x25, #4
Lpoint:
    cmp x23, x20
    b.ne Ladvance
    mov x22, x24
Ladvance:
    add x23, x23, x25
    b Lscan
Ldone:
    tbnz x22, #63, Ltrap
    mov x0, x22
    ldp x29, x30, [sp, #0]
    ldp x19, x20, [sp, #16]
    ldp x21, x22, [sp, #32]
    ldp x23, x24, [sp, #48]
    ldp x25, x26, [sp, #64]
    add sp, sp, #96
    ret
Ltrap:
    brk #0
Lresolve:
    brk #1
