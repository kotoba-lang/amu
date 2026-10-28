.section __TEXT,__text,regular,pure_instructions
.globl _fs2_bc_dispatch
.p2align 2
_fs2_bc_dispatch:
    cmp x1, #35
    b.ne Lda
    cmp x2, #8
    b.ne Lda
    cmp x3, #8
    b.ne Lda
    sub sp, sp, #8192
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
    cbz x20, Lbad
    ldr x8, [x19, #16008]
    cmp x20, x8
    b.hi Lbad
    ldr x8, [x19, #16000]
    sub x9, x20, #1
    add x8, x8, x9, lsl #4
    ldp x9, x22, [x8]
    cmp x22, #8
    b.lo Lbad
    movz x8, #0x80, lsl #16
    cmp x22, x8
    b.hi Lbad
    ldr x8, [x19, #16024]
    cmp x9, x8
    b.hi Lbad
    sub x8, x8, x9
    cmp x22, x8
    b.hi Lbad
    ldr x8, [x19, #16016]
    add x21, x8, x9, lsl #3
    ldr x8, [x21]
    cbnz x8, Lbad
    ldr x8, [x21, #8]
    cmp x8, #70
    b.ne Lbad
    ldr x8, [x21, #16]
    cmp x8, #83
    b.ne Lbad
    ldr x8, [x21, #24]
    cmp x8, #50
    b.ne Lbad
    ldr x8, [x21, #32]
    cbnz x8, Lbad
    ldr x28, [x21, #40]
    cmp x28, #66
    b.eq Lpath
    cmp x28, #67
    b.ne Lbad
Lpath:
    mov x9, #6
    add x10, sp, #128
Lpathloop:
    cmp x9, x22
    b.hs Lbad
    sub x11, x9, #6
    cmp x11, #255
    b.hs Lbad
    ldr x8, [x21, x9, lsl #3]
    cbz x8, Lpathend
    cmp x8, #33
    b.lo Lbad
    cmp x8, #126
    b.hi Lbad
    cmp x8, #47
    b.eq Lbad
    strb w8, [x10, x11]
    add x9, x9, #1
    b Lpathloop
Lpathend:
    cmp x9, #6
    b.eq Lbad
    strb wzr, [x10, x11]
    add x23, x9, #1
    sub x27, x22, x23
    mov x9, x23
Lvalidate:
    cmp x9, x22
    b.hs Lalloc
    ldr x8, [x21, x9, lsl #3]
    cmp x8, #255
    b.hi Lbad
    add x9, x9, #1
    b Lvalidate
Lalloc:
    add x1, x27, #5
    mov x0, x19
    ldr x16, [x19, #200]
    blr x16
    mov x26, x0
    cbz x26, Lbad
    ldr x8, [x19, #16008]
    cmp x26, x8
    b.hi Lbad
    ldr x8, [x19, #16000]
    sub x9, x26, #1
    add x8, x8, x9, lsl #4
    ldp x9, x10, [x8]
    add x11, x27, #5
    cmp x10, x11
    b.ne Lbad
    ldr x8, [x19, #16016]
    add x25, x8, x9, lsl #3
    str xzr, [x25]
    mov x8, #70
    str x8, [x25, #8]
    mov x8, #83
    str x8, [x25, #16]
    mov x8, #50
    str x8, [x25, #24]
    str xzr, [x25, #32]
    mov x9, #0
Lreplyloop:
    cmp x9, x27
    b.hs Lopen
    add x10, x23, x9
    ldr x8, [x21, x10, lsl #3]
    add x10, x25, #40
    str x8, [x10, x9, lsl #3]
    add x9, x9, #1
    b Lreplyloop
Lopen:
    mov x0, #3
    add x1, sp, #128
    mov x2, #0x1605
    movk x2, #0x2100, lsl #16
    cmp x28, #66
    b.eq Lsysopen
    mov x2, #0x100d
    movk x2, #0x2100, lsl #16
Lsysopen:
    mov x3, #420
    mov x16, #463
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cs Lbad
    mov x24, x0
    mov x20, #0
Lchunk:
    cmp x20, x27
    b.hs Lclose
    sub x22, x27, x20
    cmp x22, #4096
    b.ls Lfill
    mov x22, #4096
Lfill:
    mov x9, #0
    add x10, sp, #512
Lfillloop:
    cmp x9, x22
    b.hs Lwrite
    add x11, x23, x20
    add x11, x11, x9
    ldr x8, [x21, x11, lsl #3]
    strb w8, [x10, x9]
    add x9, x9, #1
    b Lfillloop
Lwrite:
    mov x9, #0
Lwriteloop:
    cmp x9, x22
    b.hs Lchunkdone
    mov x0, x24
    add x1, x10, x9
    sub x2, x22, x9
    mov x16, #4
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cs Lwriteerr
    cbz x0, Lwritebad
    add x9, x9, x0
    b Lwriteloop
Lwriteerr:
    cmp x0, #4
    b.eq Lwriteloop
Lwritebad:
    mov x0, x24
    mov x16, #6
    movk x16, #0x2000, lsl #16
    svc #0x80
    b Lbad
Lchunkdone:
    add x20, x20, x22
    b Lchunk
Lclose:
    mov x0, x24
    mov x16, #6
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cs Lbad
    mov x0, x26
    ldp x27, x28, [sp, #80]
    ldp x25, x26, [sp, #64]
    ldp x23, x24, [sp, #48]
    ldp x21, x22, [sp, #32]
    ldp x19, x20, [sp, #16]
    ldp x29, x30, [sp]
    add sp, sp, #8192
    ret
Lda:
    b Lda_stub
Lbad:
    brk #0x36
Lda_stub:
    brk #0x102
