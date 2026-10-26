.text
.p2align 2
.globl _substring
_substring:
    sub sp, sp, #80
    stp x29, x30, [sp, #0]
    stp x19, x20, [sp, #16]
    stp x21, x22, [sp, #32]
    stp x23, x24, [sp, #48]
    stp x25, x26, [sp, #64]
    mov x19, x0
    mov x20, x1
    mov x21, x2
    mov x22, x3
    cmp x20, #1
    b.lo Ltrap
    tbnz x21, #63, Ltrap
    tbnz x22, #63, Ltrap
    ldr x8, [x19, #288]
    ldr x8, [x8]
    cmp x20, x8
    b.hi Ltrap
    ldr x9, [x19, #296]
    sub x10, x20, #1
    add x10, x9, x10, lsl #4
    ldp x23, x24, [x10]
    tbnz x24, #63, Ltrap
    cmp x21, x22
    b.hi Ltrap
    cmp x22, x24
    b.hi Ltrap
    mov x0, x19
    mov x1, x23
    mov x2, x24
    bl Lresolve
    mov x25, x0
    cbz x24, Lstart
    mov x0, x19
    mov x1, x20
    mov x2, #0
    bl Lcodepoint
Lstart:
    cmp x21, x24
    b.eq Lend
    ldrb w8, [x25, x21]
    and w8, w8, #0xc0
    cmp w8, #0x80
    b.eq Ltrap
Lend:
    cmp x22, x24
    b.eq Lnew
    ldrb w8, [x25, x22]
    and w8, w8, #0xc0
    cmp w8, #0x80
    b.eq Ltrap
Lnew:
    tbnz x23, #63, Lnegative
    add x1, x23, x21
    b Lpair
Lnegative:
    sub x1, x23, x21
Lpair:
    mov x0, x19
    sub x2, x22, x21
    bl Lpairnew
    ldp x29, x30, [sp, #0]
    ldp x19, x20, [sp, #16]
    ldp x21, x22, [sp, #32]
    ldp x23, x24, [sp, #48]
    ldp x25, x26, [sp, #64]
    add sp, sp, #80
    ret
Ltrap:
    brk #0
Lresolve:
    brk #1
Lcodepoint:
    brk #2
Lpairnew:
    brk #3
