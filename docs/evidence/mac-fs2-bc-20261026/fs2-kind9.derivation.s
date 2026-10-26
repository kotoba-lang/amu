.section __TEXT,__text,regular,pure_instructions
.globl _fs2_kind9
.p2align 2
_fs2_kind9:
    cmp x2, #9
    b.ne Lda
    cmp x3, #9
    b.ne Lda
    sub sp, sp, #80
    stp x29, x30, [sp]
    stp x19, x20, [sp, #16]
    stp x21, x22, [sp, #32]
    stp x23, x24, [sp, #48]
    stp x25, x26, [sp, #64]
    mov x19, x0
    mov x2, #1
    mov x3, #1
    bl Lda_stub
    mov x20, x0
    cbz x20, Lbad
    ldr x8, [x19, #288]
    ldr x8, [x8]
    cmp x20, x8
    b.hi Lbad
    ldr x8, [x19, #296]
    sub x9, x20, #1
    add x8, x8, x9, lsl #4
    ldp x1, x21, [x8]
    mov x0, x19
    mov x2, x21
    bl Lspan_stub
    mov x22, x0
    mov x0, x19
    mov x1, x21
    ldr x16, [x19, #200]
    blr x16
    mov x23, x0
    cbz x23, Lbad
    ldr x8, [x19, #16008]
    cmp x23, x8
    b.hi Lbad
    ldr x8, [x19, #16000]
    sub x9, x23, #1
    add x8, x8, x9, lsl #4
    ldp x9, x10, [x8]
    cmp x10, x21
    b.ne Lbad
    ldr x8, [x19, #16016]
    add x24, x8, x9, lsl #3
    mov x25, #0
Lcopy:
    cmp x25, x21
    b.hs Ldone
    ldrb w8, [x22, x25]
    str x8, [x24, x25, lsl #3]
    add x25, x25, #1
    b Lcopy
Ldone:
    mov x0, x23
    ldp x25, x26, [sp, #64]
    ldp x23, x24, [sp, #48]
    ldp x21, x22, [sp, #32]
    ldp x19, x20, [sp, #16]
    ldp x29, x30, [sp]
    add sp, sp, #80
    ret
Lda:
    b Lda_stub
Lbad:
    brk #0x36
Lda_stub:
    brk #0x102
Lspan_stub:
    brk #0x101
