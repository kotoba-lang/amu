.text
.p2align 2
.globl _pool_setup
_pool_setup:
    mov x0, xzr
    mov x1, #0x10000000
    mov x2, #3
    mov x3, #0x1002
    mov x4, #-1
    mov x5, xzr
    mov x16, #197
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cs Ltrap
    str x0, [x19, #400]
    str xzr, [x19, #408]
    ret

.p2align 2
.globl _resolve
_resolve:
    tbnz x2, #63, Ltrap
    tbnz x1, #63, Lpool
    ldr x8, [x0, #392]
    cmp x1, x8
    b.hi Ltrap
    sub x8, x8, x1
    cmp x2, x8
    b.hi Ltrap
    ldr x8, [x0, #384]
    add x0, x8, x1
    ret
Lpool:
    mvn x9, x1
    ldr x8, [x0, #408]
    cmp x9, x8
    b.hi Ltrap
    sub x8, x8, x9
    cmp x2, x8
    b.hi Ltrap
    ldr x8, [x0, #400]
    add x0, x8, x9
    ret

.p2align 2
.globl _concat
_concat:
    sub sp, sp, #96
    stp x29, x30, [sp, #0]
    stp x19, x20, [sp, #16]
    stp x21, x22, [sp, #32]
    stp x23, x24, [sp, #48]
    stp x25, x26, [sp, #64]
    stp x27, x28, [sp, #80]
    mov x19, x0
    cmp x1, #1
    b.lo Ltrap
    cmp x2, #1
    b.lo Ltrap
    ldr x8, [x19, #288]
    ldr x8, [x8]
    cmp x1, x8
    b.hi Ltrap
    cmp x2, x8
    b.hi Ltrap
    ldr x9, [x19, #296]
    sub x10, x1, #1
    add x10, x9, x10, lsl #4
    ldp x21, x22, [x10]
    sub x10, x2, #1
    add x10, x9, x10, lsl #4
    ldp x23, x24, [x10]
    tbnz x22, #63, Ltrap
    tbnz x24, #63, Ltrap
    adds x25, x22, x24
    b.vs Ltrap
    mov x0, x19
    mov x1, x21
    mov x2, x22
    bl _resolve
    mov x26, x0
    mov x0, x19
    mov x1, x23
    mov x2, x24
    bl _resolve
    mov x27, x0
    ldr x28, [x19, #408]
    mov x20, x25
    mov x14, #0
    tbnz x21, #63, Lcheck_tail
    b Lcheck_room
Lcheck_tail:
    mvn x8, x21
    add x8, x8, x22
    cmp x8, x28
    b.ne Lcheck_room
    mov x20, x24
    mov x14, #1
Lcheck_room:
    mov x8, #0x10000000
    cmp x28, x8
    b.hi Ltrap
    sub x8, x8, x28
    cmp x20, x8
    b.hi Ltrap
    ldr x9, [x19, #400]
    cbnz x14, Ltail_copy
    add x10, x9, x28
    mov x11, x26
    mov x12, x22
Lcopy_a:
    cbz x12, Lcopy_b_begin
    ldrb w13, [x11], #1
    strb w13, [x10], #1
    sub x12, x12, #1
    b Lcopy_a
Lcopy_b_begin:
    mov x11, x27
    mov x12, x24
Lcopy_b:
    cbz x12, Lfinish_copy
    ldrb w13, [x11], #1
    strb w13, [x10], #1
    sub x12, x12, #1
    b Lcopy_b
Ltail_copy:
    mvn x28, x21
    add x10, x9, x28
    add x10, x10, x22
    b Lcopy_b_begin
Lfinish_copy:
    ldr x8, [x19, #408]
    add x8, x8, x20
    str x8, [x19, #408]
    mov x0, x19
    mvn x1, x28
    mov x2, x25
    ldr x16, [x19, #56]
    blr x16
    ldp x29, x30, [sp, #0]
    ldp x19, x20, [sp, #16]
    ldp x21, x22, [sp, #32]
    ldp x23, x24, [sp, #48]
    ldp x25, x26, [sp, #64]
    ldp x27, x28, [sp, #80]
    add sp, sp, #96
    ret

.p2align 2
.globl _equal
_equal:
    sub sp, sp, #80
    stp x29, x30, [sp, #0]
    stp x19, x20, [sp, #16]
    stp x21, x22, [sp, #32]
    stp x23, x24, [sp, #48]
    stp x25, x26, [sp, #64]
    mov x19, x0
    cmp x1, #1
    b.lo Ltrap
    cmp x2, #1
    b.lo Ltrap
    ldr x8, [x19, #288]
    ldr x8, [x8]
    cmp x1, x8
    b.hi Ltrap
    cmp x2, x8
    b.hi Ltrap
    ldr x9, [x19, #296]
    sub x10, x1, #1
    add x10, x9, x10, lsl #4
    ldp x20, x21, [x10]
    sub x10, x2, #1
    add x10, x9, x10, lsl #4
    ldp x22, x23, [x10]
    mov x0, x19
    mov x1, x20
    mov x2, x21
    bl _resolve
    mov x24, x0
    mov x0, x19
    mov x1, x22
    mov x2, x23
    bl _resolve
    mov x25, x0
    cmp x21, x23
    b.ne Lnot_equal
Lcompare:
    cbz x21, Lyes_equal
    ldrb w8, [x24], #1
    ldrb w9, [x25], #1
    cmp w8, w9
    b.ne Lnot_equal
    sub x21, x21, #1
    b Lcompare
Lyes_equal:
    mov x0, #1
    b Lequal_done
Lnot_equal:
    mov x0, #0
Lequal_done:
    ldp x29, x30, [sp, #0]
    ldp x19, x20, [sp, #16]
    ldp x21, x22, [sp, #32]
    ldp x23, x24, [sp, #48]
    ldp x25, x26, [sp, #64]
    add sp, sp, #80
    ret
Ltrap:
    brk #0
