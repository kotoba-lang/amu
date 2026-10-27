.text
.p2align 2
.globl _typed_dispatch
_typed_dispatch:
    cmp x1, #39
    b.eq Lstderr
    b Llegacy
Lstderr:
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
    movz x9, #128, lsl #32
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
    mov x22, #0
Lwrite:
    cmp x22, x20
    b.eq Ldecimal
    mov x0, #2
    add x1, x21, x22
    sub x2, x20, x22
    mov x23, x2
    mov x16, #4
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cs Lwrite_error
    cbz x0, Ltrap
    cmp x0, x23
    b.hi Ltrap
    add x22, x22, x0
    b Lwrite
Lwrite_error:
    cmp x0, #4
    b.eq Lwrite
    b Ltrap
Ldecimal:
    mov x22, x20
    add x23, sp, #144
    mov x24, #10
Ldigit:
    udiv x25, x22, x24
    msub x26, x25, x24, x22
    add w26, w26, #48
    strb w26, [x23, #-1]!
    mov x22, x25
    cbnz x22, Ldigit
    add x24, sp, #144
    sub x24, x24, x23
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
Lcopy_digits:
    cbz x11, Lmint
    ldrb w12, [x23], #1
    strb w12, [x10], #1
    sub x11, x11, #1
    b Lcopy_digits
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
Llegacy:
    brk #1
Lresolve:
    brk #2
