.section __TEXT,__text,regular,pure_instructions
.globl _codepoint_fast
.p2align 2
_codepoint_fast:
    stp x29, x30, [sp, #-64]!
    stp x19, x20, [sp, #16]
    stp x21, x22, [sp, #32]
    mov x19, x0
    mov x20, x1
    mov x21, x2
    cmp x20, #1
    b.lo Lslow
    ldr x8, [x19, #288]
    ldr x8, [x8]
    cmp x20, x8
    b.hi Lslow
    ldr x8, [x19, #296]
    sub x9, x20, #1
    add x8, x8, x9, lsl #4
    ldp x10, x11, [x8]
    tbnz x21, #63, Lslow
    cmp x21, x11
    b.hs Lslow
    ldr x22, [x19, #304]
    add x22, x22, x9
    ldrb w8, [x22]
    cmp w8, #1
    b.ne Lslow
    mov x0, x19
    mov x1, x10
    mov x2, x11
    bl Lspan_stub
    ldrb w8, [x0, x21]
    cmp w8, #128
    b.hs Lslow
    mov x0, x8
    b Ldone
Lslow:
    mov x0, x19
    mov x1, x20
    mov x2, x21
    bl Loriginal_stub
    ldr x8, [x19, #304]
    sub x9, x20, #1
    add x8, x8, x9
    mov w9, #1
    strb w9, [x8]
Ldone:
    ldp x21, x22, [sp, #32]
    ldp x19, x20, [sp, #16]
    ldp x29, x30, [sp], #64
    ret
Lspan_stub:
    brk #0x101
Loriginal_stub:
    brk #0x102
