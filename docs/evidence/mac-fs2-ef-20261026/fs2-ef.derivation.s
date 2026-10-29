.section __TEXT,__text,regular,pure_instructions
.globl _fs2_ef
.p2align 2
_fs2_ef:
    cmp x1, #35
    b.ne Lfallback
    cmp x2, #1
    b.ne Lfallback
    cmp x3, #1
    b.ne Lfallback
    cbz x4, Lbad
    sub sp, sp, #320
    stp x29, x30, [sp]
    stp x19, x20, [sp, #16]
    stp x21, x22, [sp, #32]
    stp x23, x24, [sp, #48]
    stp x25, x26, [sp, #64]
    stp x27, x28, [sp, #80]
    mov x19, x0
    mov x20, x4
    ldr x8, [x19, #16]
    movz x9, #8, lsl #32
    tst x8, x9
    b.eq Lbad
    ldr x8, [x19, #288]
    ldr x8, [x8]
    cmp x20, x8
    b.hi Lbad
    ldr x8, [x19, #296]
    sub x9, x20, #1
    add x8, x8, x9, lsl #4
    ldp x1, x22, [x8]
    mov x0, x19
    mov x2, x22
    bl Lspan_stub
    mov x21, x0
    cmp x22, #9
    b.lo Lbad
    mov x8, #4102
    cmp x22, x8
    b.hi Lbad
    ldrb w8, [x21]
    cbnz w8, Lbad
    ldrb w8, [x21, #1]
    cmp w8, #70
    b.ne Lbad
    ldrb w8, [x21, #2]
    cmp w8, #83
    b.ne Lbad
    ldrb w8, [x21, #3]
    cmp w8, #50
    b.ne Lbad
    ldrb w8, [x21, #4]
    cbnz w8, Lbad
    ldrb w26, [x21, #5]
    cmp w26, #69
    b.eq Lscan_path
    cmp w26, #70
    b.ne Lfallback_frame
Lscan_path:
    mov x23, #6
Lpath_loop:
    cmp x23, x22
    b.hs Lbad
    ldrb w8, [x21, x23]
    cbz w8, Lpath_end
    add x23, x23, #1
    b Lpath_loop
Lpath_end:
    add x23, x23, #1
    cmp w26, #70
    b.ne Lparse_range
    cmp x23, x22
    b.ne Lbad
    b Lopen
Lparse_range:
    mov x24, #0
    mov x25, #0
    mov x27, #0
Loffset_digit:
    cmp x23, x22
    b.hs Lbad
    ldrb w8, [x21, x23]
    cmp w8, #58
    b.eq Loffset_end
    sub w8, w8, #48
    cmp w8, #9
    b.hi Lbad
    movz x9, #0x9999
    movk x9, #0x1999, lsl #16
    cmp x24, x9
    b.hi Lbad
    mov x9, #10
    madd x24, x24, x9, x8
    mov w9, #-1
    cmp x24, x9
    b.hi Lbad
    add x23, x23, #1
    add x27, x27, #1
    b Loffset_digit
Loffset_end:
    cbz x27, Lbad
    add x23, x23, #1
    mov x27, #0
Lcount_digit:
    cmp x23, x22
    b.hs Lcount_end
    ldrb w8, [x21, x23]
    sub w8, w8, #48
    cmp w8, #9
    b.hi Lbad
    mov x9, #10
    madd x25, x25, x9, x8
    mov x9, #262144
    cmp x25, x9
    b.hi Lbad
    add x23, x23, #1
    add x27, x27, #1
    b Lcount_digit
Lcount_end:
    cbz x27, Lbad
Lopen:
    add x1, x21, #6
    ldrb w8, [x1]
    cmp w8, #47
    b.ne Lopenat
    add x1, x1, #1
Lopenat:
    mov x0, #3
    mov x2, #0x1004
    movk x2, #0x2100, lsl #16
    mov x3, #0
    mov x16, #463
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cs Lopen_fail
    mov x20, x0
    mov x0, x20
    add x1, sp, #112
    mov x16, #339
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cs Lbad
    ldrh w8, [sp, #116]
    and w9, w8, #0xf000
    cmp w9, #0x8000
    b.ne Lbad
    cmp w26, #70
    b.eq Lmetadata
    ldr x8, [sp, #208]
    cmp x8, #0
    b.lt Lbad
    add x9, x24, x25
    cmp x9, x8
    b.hi Lbad
    ldr x23, [x19, #408]
    movz x8, #0x1000, lsl #16
    sub x8, x8, #5
    cmp x23, x8
    b.hi Lbad
    sub x8, x8, x23
    cmp x25, x8
    b.hi Lbad
    mov x0, x20
    mov x1, x24
    mov x2, #0
    mov x16, #199
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cs Lbad
    cmp x0, x24
    b.ne Lbad
    ldr x21, [x19, #400]
    add x21, x21, x23
    add x21, x21, #5
    mov x27, #0
Lread_loop:
    cmp x27, x25
    b.hs Lread_done
    mov x0, x20
    add x1, x21, x27
    sub x2, x25, x27
    mov x16, #3
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cs Lread_error
    cbz x0, Lbad
    add x27, x27, x0
    b Lread_loop
Lread_error:
    cmp x0, #4
    b.eq Lread_loop
    b Lbad
Lread_done:
    mov x0, x20
    mov x16, #6
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cs Lbad
    sub x21, x21, #5
    movz w8, #0x4600
    movk w8, #0x3253, lsl #16
    str w8, [x21]
    strb wzr, [x21, #4]
    add x8, x23, x25
    add x8, x8, #5
    str x8, [x19, #408]
    mov x0, x19
    mvn x1, x23
    add x2, x25, #5
    b Lmint
Lmetadata:
    ldr x23, [x19, #408]
    movz x8, #0x1000, lsl #16
    sub x8, x8, #96
    cmp x23, x8
    b.hi Lbad
    ldr x21, [x19, #400]
    add x21, x21, x23
    movz w8, #0x4600
    movk w8, #0x3253, lsl #16
    str w8, [x21]
    strb wzr, [x21, #4]
    add x1, x21, #5
    ldrh w0, [sp, #116]
    and w0, w0, #511
    bl Ldecimal
    mov w8, #32
    strb w8, [x1], #1
    ldr x0, [sp, #208]
    bl Ldecimal
    mov w8, #32
    strb w8, [x1], #1
    ldr x0, [sp, #160]
    bl Ldecimal
    mov w8, #32
    strb w8, [x1], #1
    mov w8, #48
    strb w8, [x1], #1
    sub x25, x1, x21
    add x8, x23, x25
    str x8, [x19, #408]
    mov x0, x20
    mov x16, #6
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cs Lbad
    mov x0, x19
    mvn x1, x23
    mov x2, x25
    b Lmint
Lopen_fail:
    cmp w26, #70
    b.ne Lbad
    ldr x23, [x19, #408]
    movz x8, #0x1000, lsl #16
    sub x8, x8, #5
    cmp x23, x8
    b.hi Lbad
    ldr x21, [x19, #400]
    add x21, x21, x23
    movz w8, #0x4600
    movk w8, #0x3253, lsl #16
    str w8, [x21]
    strb wzr, [x21, #4]
    add x8, x23, #5
    str x8, [x19, #408]
    mov x0, x19
    mvn x1, x23
    mov x2, #5
Lmint:
    ldr x16, [x19, #56]
    blr x16
    ldp x27, x28, [sp, #80]
    ldp x25, x26, [sp, #64]
    ldp x23, x24, [sp, #48]
    ldp x21, x22, [sp, #32]
    ldp x19, x20, [sp, #16]
    ldp x29, x30, [sp]
    add sp, sp, #320
    ret
Ldecimal:
    mov x2, #0
    mov x8, #10
Ldecimal_digit:
    udiv x9, x0, x8
    msub x10, x9, x8, x0
    add w10, w10, #48
    add x11, sp, #272
    strb w10, [x11, x2]
    add x2, x2, #1
    mov x0, x9
    cbnz x0, Ldecimal_digit
Ldecimal_copy:
    sub x2, x2, #1
    ldrb w10, [x11, x2]
    strb w10, [x1], #1
    cbnz x2, Ldecimal_copy
    ret
Lfallback:
    b Lda_stub
Lfallback_frame:
    mov x0, x19
    mov x1, #35
    mov x2, #1
    mov x3, #1
    mov x4, x20
    ldp x27, x28, [sp, #80]
    ldp x25, x26, [sp, #64]
    ldp x23, x24, [sp, #48]
    ldp x21, x22, [sp, #32]
    ldp x19, x20, [sp, #16]
    ldp x29, x30, [sp]
    add sp, sp, #320
    b Lda_stub
Lbad:
    brk #0x36
Lspan_stub:
    brk #0x101
Lda_stub:
    brk #0x102
