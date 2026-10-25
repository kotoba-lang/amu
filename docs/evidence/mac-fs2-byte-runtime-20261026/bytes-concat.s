.text
.globl _bytes_concat
_bytes_concat:
    stp x29, x30, [sp, #-80]!
    stp x19, x20, [sp, #16]
    stp x21, x22, [sp, #32]
    stp x23, x24, [sp, #48]
    stp x25, x26, [sp, #64]
    mov x19, x0
    mov x20, x1
    mov x21, x2

    mov x0, x19
    mov x1, x20
    ldr x9, [x19, #168]
    blr x9
    mov x22, x0
    mov x0, x19
    mov x1, x21
    ldr x9, [x19, #168]
    blr x9
    mov x23, x0
    adds x26, x22, x23
    b.vs .Linvalid
    movz x8, #0x80, lsl #16
    cmp x26, x8
    b.hi .Linvalid

    mov x0, x19
    mov x1, x26
    ldr x9, [x19, #200]
    blr x9
    mov x24, x0
    mov x25, #0

.Lfirst:
    cmp x25, x22
    b.hs .Lsecond
    mov x0, x19
    mov x1, x20
    mov x2, x25
    ldr x9, [x19, #176]
    blr x9
    mov x3, x0
    mov x0, x19
    mov x1, x24
    mov x2, x25
    ldr x9, [x19, #208]
    blr x9
    add x25, x25, #1
    b .Lfirst

.Lsecond:
    cmp x25, x26
    b.hs .Ldone
    mov x0, x19
    mov x1, x21
    sub x2, x25, x22
    ldr x9, [x19, #176]
    blr x9
    mov x3, x0
    mov x0, x19
    mov x1, x24
    mov x2, x25
    ldr x9, [x19, #208]
    blr x9
    add x25, x25, #1
    b .Lsecond

.Ldone:
    mov x0, x24
    ldp x25, x26, [sp, #64]
    ldp x23, x24, [sp, #48]
    ldp x21, x22, [sp, #32]
    ldp x19, x20, [sp, #16]
    ldp x29, x30, [sp], #80
    ret

.Linvalid:
    brk #0x376
