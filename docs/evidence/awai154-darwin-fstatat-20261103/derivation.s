.section __TEXT,__text,regular,pure_instructions
.globl _main
.p2align 2
_main:
    cmp x0, #2
    b.ne Lusage
    ldr x1, [x1, #8]
    mov x0, #3
    sub sp, sp, #160
    mov x2, sp
    mov x3, #0x2820
    mov x16, #470
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cs Lexit
    mov x0, #1
    add x1, sp, #4
    mov x2, #2
    mov x16, #4
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cs Lwrite_fail
    cmp x0, #2
    b.ne Lwrite_fail
    mov x0, #0
    b Lexit
Lwrite_fail:
    mov x0, #4
    b Lexit
Lusage:
    mov x0, #2
Lexit:
    mov x16, #1
    movk x16, #0x2000, lsl #16
    svc #0x80
    brk #0
