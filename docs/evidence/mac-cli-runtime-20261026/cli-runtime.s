.text
.p2align 2
.globl _arg_setup
_arg_setup:
    str x0, [x19, #416]
    str x1, [x19, #424]
    ret
.p2align 5
.globl _cli_dispatch
_cli_dispatch:
    cmp x1, #38
    b.eq Lcli
    b Lstderr
Lcli:
    sub sp, sp, #144
    stp x29, x30, [sp, #0]
    stp x19, x20, [sp, #16]
    stp x21, x22, [sp, #32]
    stp x23, x24, [sp, #48]
    stp x25, x26, [sp, #64]
    stp x27, x28, [sp, #80]
    mov x19, x0
    cmp x2, #1
    b.ne Ltrap
    cmp x3, #1
    b.ne Ltrap
    ldr x8, [x19, #16]
    movz x9, #64, lsl #32
    tst x8, x9
    b.eq Ltrap
    cmp x4, #1
    b.lo Ltrap
    ldr x8, [x19, #288]
    ldr x8, [x8]
    cmp x4, x8
    b.hi Ltrap
    ldr x9, [x19, #296]
    sub x10, x4, #1
    add x10, x9, x10, lsl #4
    ldp x1, x2, [x10]
    mov x20, x2
    mov x0, x19
    bl Lresolve
    mov x21, x0
    cbz x20, Lcount
    cmp x20, #20
    b.hs Ltrap
    mov x22, #0
    mov x23, #0
    mov x24, #10
Lparse:
    ldrb w25, [x21, x23]
    cmp w25, #48
    b.lo Ltrap
    cmp w25, #57
    b.hi Ltrap
    sub w25, w25, #48
    madd x22, x22, x24, x25
    add x23, x23, #1
    cmp x23, x20
    b.lo Lparse
    ldr x8, [x19, #416]
    cmp x8, #1
    b.lo Ltrap
    sub x8, x8, #1
    cmp x22, x8
    b.hs Lempty
    ldr x9, [x19, #424]
    add x22, x22, #1
    ldr x21, [x9, x22, lsl #3]
    cbz x21, Ltrap
    mov x24, #0
    mov x8, #0x800000
Lstrlen:
    cmp x24, x8
    b.hi Ltrap
    ldrb w10, [x21, x24]
    cbz w10, Lreturn_span
    add x24, x24, #1
    b Lstrlen
Lcount:
    ldr x22, [x19, #416]
    cmp x22, #1
    b.lo Ltrap
    sub x22, x22, #1
    add x21, sp, #144
    mov x24, #10
Ldigit:
    udiv x25, x22, x24
    msub x26, x25, x24, x22
    add w26, w26, #48
    strb w26, [x21, #-1]!
    mov x22, x25
    cbnz x22, Ldigit
    add x24, sp, #144
    sub x24, x24, x21
    b Lreturn_span
Lempty:
    add x21, sp, #144
    mov x24, #0
Lreturn_span:
    ldr x22, [x19, #408]
    mov x8, #0x10000000
    cmp x22, x8
    b.hi Ltrap
    sub x8, x8, x22
    cmp x24, x8
    b.hi Ltrap
    ldr x9, [x19, #400]
    add x10, x9, x22
    mov x11, x24
Lcopy:
    cbz x11, Lmint
    ldrb w12, [x21], #1
    strb w12, [x10], #1
    sub x11, x11, #1
    b Lcopy
Lmint:
    add x8, x22, x24
    str x8, [x19, #408]
    mov x0, x19
    mvn x1, x22
    mov x2, x24
    ldr x16, [x19, #56]
    blr x16
    ldp x29, x30, [sp, #0]
    ldp x19, x20, [sp, #16]
    ldp x21, x22, [sp, #32]
    ldp x23, x24, [sp, #48]
    ldp x25, x26, [sp, #64]
    ldp x27, x28, [sp, #80]
    add sp, sp, #144
    ret
Ltrap:
    brk #0
Lstderr:
    brk #1
Lresolve:
    brk #2
