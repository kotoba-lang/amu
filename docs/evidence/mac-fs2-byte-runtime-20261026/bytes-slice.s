.text
.globl _bytes_slice
_bytes_slice:
    stp x29, x30, [sp, #-80]!
    stp x19, x20, [sp, #16]
    stp x21, x22, [sp, #32]
    stp x23, x24, [sp, #48]
    stp x25, x26, [sp, #64]
    mov x19, x0
    mov x20, x1
    mov x21, x2
    mov x22, x3
    tbnz x21, #63, .Linvalid
    cmp x22, x21
    b.lo .Linvalid
    mov x0, x19
    mov x1, x20
    ldr x9, [x19, #168]
    blr x9
    cmp x22, x0
    b.hi .Linvalid
    sub x24, x22, x21
    mov x0, x19
    mov x1, x24
    ldr x9, [x19, #200]
    blr x9
    mov x25, x0
    mov x26, #0
.Lloop:
    cmp x26, x24
    b.hs .Ldone
    mov x0, x19
    mov x1, x20
    add x2, x21, x26
    ldr x9, [x19, #176]
    blr x9
    mov x3, x0
    mov x0, x19
    mov x1, x25
    mov x2, x26
    ldr x9, [x19, #208]
    blr x9
    add x26, x26, #1
    b .Lloop
.Ldone:
    mov x0, x25
    ldp x25, x26, [sp, #64]
    ldp x23, x24, [sp, #48]
    ldp x21, x22, [sp, #32]
    ldp x19, x20, [sp, #16]
    ldp x29, x30, [sp], #80
    ret
.Linvalid:
    brk #0x368
