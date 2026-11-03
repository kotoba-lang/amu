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
    sub sp, sp, #2432
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
    cmp x22, #8
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
    b.eq Lscan_path
    cmp w26, #79
    b.eq Lscan_path
    cmp w26, #85
    b.eq Lscan_path
    cmp w26, #72
    b.eq Lscan_path
    cmp w26, #77
    b.eq Lscan_path
    cmp w26, #73
    b.eq Lscan_path
    cmp w26, #76
    b.eq Lscan_path
    cmp w26, #84
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
    cmp w26, #69
    b.eq Lparse_range
    cmp w26, #72
    b.eq Lparse_mode
    cmp w26, #76
    b.eq Lrename
    cmp w26, #84
    b.eq Lrename
    cmp x23, x22
    b.ne Lbad
    cmp w26, #73
    b.eq Lmkdir
    b Lopen
Lparse_mode:
    mov x24, #0
    mov x27, #0
Lmode_loop:
    cmp x23, x22
    b.eq Lmode_end
    ldrb w8, [x21, x23]
    sub w8, w8, #48
    cmp w8, #7
    b.hi Lbad
    cmp x27, #6
    b.hs Lbad
    lsl x24, x24, #3
    add x24, x24, x8
    add x27, x27, #1
    add x23, x23, #1
    b Lmode_loop
Lmode_end:
    cbz x27, Lbad
    and x24, x24, #511
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
    cmp w26, #79
    b.eq Lnofollow
    cmp w26, #85
    b.eq Lnofollow
    ldrb w8, [x1]
    cbnz w8, Lopen_scoped
    cmp w26, #72
    b.eq Ldup_root
    cmp w26, #77
    b.ne Lopen_scoped
Ldup_root:
    mov x0, #3
    mov x16, #41
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cs Lopen_fail
    b Lopened
Lopen_scoped:
    mov x0, #3
    mov x2, #0x1004
    movk x2, #0x2100, lsl #16
    mov x3, #0
    mov x16, #463
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cs Lopen_fail
Lopened:
    mov x20, x0
    cmp w26, #72
    b.eq Lmutation
    cmp w26, #77
    b.eq Lmutation
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
// L/T: prepare two scoped parents; T uses atomic RENAME_EXCL.
Lrename:
    ldr x8, [x19, #408]
    movz x9, #0x1000, lsl #16
    sub x9, x9, #6
    cmp x8, x9
    b.hi Lbad
    add x0, x21, #6
    sub x1, x23, #7
    add x2, sp, #320
    bl Lrename_prepare
    cmn x0, #1
    b.eq Lbool_zero
    mov x24, x0
    str x1, [sp, #112]
    add x0, x21, x23
    sub x1, x22, x23
    add x2, sp, #1344
    bl Lrename_prepare
    cmn x0, #1
    b.eq Lrename_second_failed
    mov x25, x0
    mov x3, x1
    mov x0, x24
    ldr x1, [sp, #112]
    mov x2, x25
    mov x4, #0x10
    cmp w26, #84
    b.ne Lrename_call
    mov x4, #0x14
Lrename_call:
    mov x16, #488
    movk x16, #0x2000, lsl #16
    svc #0x80
    cset x28, cc
    mov x0, x24
    mov x16, #6
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cs Lbad
    mov x0, x25
    mov x16, #6
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cs Lbad
    mov x24, x28
    b Lbool_reply
Lrename_second_failed:
    mov x0, x24
    mov x16, #6
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cs Lbad
    b Lbool_zero
// x0 path bytes, x1 length, x2 output buffer; returns fd and basename.
// Paths are copied, strictly validated and parents opened beneath FD3.
Lrename_prepare:
    str x30, [sp, #264]
    mov x3, x0
    mov x4, x1
    cbz x4, Lrename_prepare_bad
    ldrb w8, [x3]
    cmp w8, #47
    b.ne Lrename_prepare_start
    add x3, x3, #1
    sub x4, x4, #1
Lrename_prepare_start:
    cbz x4, Lrename_prepare_bad
    cmp x4, #1023
    b.hi Lrename_prepare_bad
    mov x5, #0
    mov x28, #0
    mov x27, #-1
Lrename_prepare_loop:
    cmp x5, x4
    b.eq Lrename_prepare_end
    ldrb w8, [x3, x5]
    cbz w8, Lrename_prepare_bad
    cmp w8, #47
    b.ne Lrename_prepare_store
    sub x9, x5, x28
    bl Lmkdir_component
    cbnz x0, Lrename_prepare_bad
    mov x27, x5
    add x28, x5, #1
Lrename_prepare_store:
    strb w8, [x2, x5]
    add x5, x5, #1
    b Lrename_prepare_loop
Lrename_prepare_end:
    sub x9, x5, x28
    bl Lmkdir_component
    cbnz x0, Lrename_prepare_bad
    strb wzr, [x2, x5]
    mov x6, x2
    cmn x27, #1
    b.ne Lrename_open_parent
    mov x0, #3
    mov x16, #41
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cs Lrename_prepare_bad
    mov x1, x6
    ldr x30, [sp, #264]
    ret
Lrename_open_parent:
    strb wzr, [x6, x27]
    mov x0, #3
    mov x1, x6
    movz x2, #0x1004
    movk x2, #0x2110, lsl #16
    mov x3, #0
    mov x16, #463
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cs Lrename_prepare_bad
    add x1, x6, x27
    add x1, x1, #1
    ldr x30, [sp, #264]
    ret
Lrename_prepare_bad:
    mov x0, #-1
    ldr x30, [sp, #264]
    ret
// I: validate a relative path, open its parent beneath FD3, mkdirat once.
// Fail closed on dot, empty or oversized components. No existing entry is changed.
Lmkdir:
    ldr x23, [x19, #408]
    movz x8, #0x1000, lsl #16
    sub x8, x8, #6
    cmp x23, x8
    b.hi Lbad
    add x1, x21, #6
    ldrb w8, [x1]
    cmp w8, #47
    b.ne Lmkdir_copy_start
    add x1, x1, #1
Lmkdir_copy_start:
    add x2, sp, #320
    mov x25, #0
    mov x28, #0
    mov x27, #-1
Lmkdir_copy:
    ldrb w8, [x1, x25]
    cbz w8, Lmkdir_end
    cmp x25, #1023
    b.hs Lbool_zero
    cmp w8, #47
    b.ne Lmkdir_store
    sub x9, x25, x28
    bl Lmkdir_component
    cbnz x0, Lbool_zero
    mov x27, x25
    add x28, x25, #1
Lmkdir_store:
    strb w8, [x2, x25]
    add x25, x25, #1
    b Lmkdir_copy
Lmkdir_end:
    sub x9, x25, x28
    bl Lmkdir_component
    cbnz x0, Lbool_zero
    strb wzr, [x2, x25]
    mov x20, #3
    mov x28, #0
    cmn x27, #1
    b.eq Lmkdir_root_parent
    strb wzr, [x2, x27]
    mov x0, #3
    mov x1, x2
    movz x2, #0x1004
    movk x2, #0x2110, lsl #16
    mov x3, #0
    mov x16, #463
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cs Lbool_zero
    mov x20, x0
    mov x28, #1
    add x1, sp, #320
    add x1, x1, x27
    add x1, x1, #1
    b Lmkdir_call
Lmkdir_root_parent:
    add x1, sp, #320
Lmkdir_call:
    mov x0, x20
    mov x2, #511
    mov x16, #475
    movk x16, #0x2000, lsl #16
    svc #0x80
    cset x24, cc
    cbz x28, Lbool_reply
    mov x0, x20
    mov x16, #6
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cs Lbad
    b Lbool_reply
// Input x9 length, x28 component start, x2 destination buffer. x0=0 valid.
Lmkdir_component:
    cbz x9, Lmkdir_component_bad
    cmp x9, #255
    b.hi Lmkdir_component_bad
    cmp x9, #1
    b.eq Lmkdir_dot_check
    cmp x9, #2
    b.ne Lmkdir_component_ok
Lmkdir_dot_check:
    ldrb w10, [x2, x28]
    cmp w10, #46
    b.ne Lmkdir_component_ok
    cmp x9, #1
    b.eq Lmkdir_component_bad
    add x10, x28, #1
    ldrb w10, [x2, x10]
    cmp w10, #46
    b.eq Lmkdir_component_bad
Lmkdir_component_ok:
    mov x0, #0
    ret
Lmkdir_component_bad:
    mov x0, #1
    ret
Lmutation:
    // Check response arena before any external side effect.
    ldr x23, [x19, #408]
    movz x8, #0x1000, lsl #16
    sub x8, x8, #6
    cmp x23, x8
    b.hi Lbad
    mov x0, x20
    cmp w26, #72
    b.ne Ldo_sync
    mov x1, x24
    mov x16, #124
    b Ldo_mutation
Ldo_sync:
    mov x16, #95
Ldo_mutation:
    movk x16, #0x2000, lsl #16
    svc #0x80
    cset x24, cc
    mov x0, x20
    mov x16, #6
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cs Lbad
    b Lbool_reply
Lnofollow:
    ldrb w8, [x1]
    cbnz w8, Lnofollow_child
    mov x0, #3
    add x1, sp, #112
    mov x16, #339
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cs Lopen_fail
    b Lmetadata
Lnofollow_child:
    mov x0, #3
    add x2, sp, #112
    mov x3, #0x2820
    mov x16, #470
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cs Lopen_fail
    b Lmetadata
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
    cmp w26, #85
    b.ne Lmode_legacy
    and w0, w0, #4095
    b Lmode_ready
Lmode_legacy:
    and w0, w0, #511
Lmode_ready:
    bl Ldecimal
    mov w8, #32
    strb w8, [x1], #1
    ldr x0, [sp, #208]
    bl Ldecimal
    mov w8, #32
    strb w8, [x1], #1
    cmp w26, #70
    b.ne Lmetadata_blocks
    ldr x0, [sp, #160]
    b Lmetadata_third
Lmetadata_blocks:
    ldr x0, [sp, #216]
Lmetadata_third:
    bl Ldecimal
    mov w8, #32
    strb w8, [x1], #1
    ldrh w8, [sp, #116]
    and w8, w8, #0xf000
    cmp w8, #0x4000
    b.eq Ltype_dir
    cmp w8, #0xa000
    b.eq Ltype_link
    cmp w8, #0x8000
    b.eq Ltype_file
    mov w8, #51
    b Ltype_write
Ltype_dir:
    mov w8, #49
    b Ltype_write
Ltype_link:
    mov w8, #50
    b Ltype_write
Ltype_file:
    mov w8, #48
Ltype_write:
    strb w8, [x1], #1
    sub x25, x1, x21
    add x8, x23, x25
    str x8, [x19, #408]
    cmp w26, #79
    b.eq Lmetadata_done
    cmp w26, #85
    b.eq Lmetadata_done
    mov x0, x20
    mov x16, #6
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cs Lbad
Lmetadata_done:
    mov x0, x19
    mvn x1, x23
    mov x2, x25
    b Lmint
Lopen_fail:
    cmp w26, #69
    b.eq Lbad
    cmp w26, #72
    b.eq Lbool_zero
    cmp w26, #77
    b.eq Lbool_zero
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
    b Lmint
Lbool_zero:
    mov x24, #0
Lbool_reply:
    ldr x23, [x19, #408]
    movz x8, #0x1000, lsl #16
    sub x8, x8, #6
    cmp x23, x8
    b.hi Lbad
    ldr x21, [x19, #400]
    add x21, x21, x23
    movz w8, #0x4600
    movk w8, #0x3253, lsl #16
    str w8, [x21]
    strb wzr, [x21, #4]
    add w8, w24, #48
    strb w8, [x21, #5]
    add x8, x23, #6
    str x8, [x19, #408]
    mov x0, x19
    mvn x1, x23
    mov x2, #6
Lmint:
    ldr x16, [x19, #56]
    blr x16
    ldp x27, x28, [sp, #80]
    ldp x25, x26, [sp, #64]
    ldp x23, x24, [sp, #48]
    ldp x21, x22, [sp, #32]
    ldp x19, x20, [sp, #16]
    ldp x29, x30, [sp]
    add sp, sp, #2432
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
    add sp, sp, #2432
    b Lda_stub
Lbad:
    brk #0x36
Lspan_stub:
    brk #0x101
Lda_stub:
    brk #0x102
