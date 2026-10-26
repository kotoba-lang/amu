.text
.p2align 2
vector_install:
    mov x8, #11
    str x8, [x19]
    adr x8, vector_alloc
    str x8, [x19, #200]
    adr x8, vector_count
    str x8, [x19, #168]
    adr x8, vector_at
    str x8, [x19, #176]
    adr x8, vector_assoc_in_place
    str x8, [x19, #208]
    add x8, x19, #3, lsl #12
    add x8, x8, #3720
    str x8, [x19, #312]
    adr x8, bytes_from_vector
    str x8, [x19, #360]
    ret

.org 64
vector_setup:
    mov x0, xzr
    movz x1, #0x400, lsl #16
    mov x2, #3
    mov x3, #0x1002
    mov x4, #-1
    mov x5, xzr
    mov x16, #0xc5
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cs setup_trap
    str x0, [x19, #16000]
    str x0, [x19, #320]
    mov x0, xzr
    movz x1, #0x800, lsl #16
    mov x2, #3
    mov x3, #0x1002
    mov x4, #-1
    mov x5, xzr
    mov x16, #0xc5
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cs setup_trap
    str x0, [x19, #16016]
    str x0, [x19, #328]
    ret
setup_trap:
    brk #0

.org 256
vector_alloc:
    ldr x8, [x0]
    cmp x8, #11
    b.ne alloc_trap
    cmp x1, #0
    b.lt alloc_trap
    movz x8, #0x100, lsl #16
    cmp x1, x8
    b.hi alloc_trap
    ldr x9, [x0, #16024]
    cmp x9, x8
    b.hi alloc_trap
    sub x10, x8, x9
    cmp x1, x10
    b.hi alloc_trap
    ldr x11, [x0, #16008]
    movz x12, #0x40, lsl #16
    cmp x11, x12
    b.hs alloc_trap
    ldr x13, [x0, #16000]
    cbz x13, alloc_trap
    add x14, x13, x11, lsl #4
    str x9, [x14]
    str x1, [x14, #8]
    add x9, x9, x1
    str x9, [x0, #16024]
    add x11, x11, #1
    str x11, [x0, #16008]
    mov x0, x11
    ret
alloc_trap:
    brk #0

.org 384
vector_count:
    ldr x8, [x0]
    cmp x8, #11
    b.ne count_trap
    cmp x1, #0
    b.le count_trap
    ldr x8, [x0, #16008]
    cmp x1, x8
    b.hi count_trap
    ldr x8, [x0, #16000]
    sub x9, x1, #1
    add x8, x8, x9, lsl #4
    ldr x0, [x8, #8]
    ret
count_trap:
    brk #0

.org 448
vector_at:
    ldr x8, [x0]
    cmp x8, #11
    b.ne at_trap
    cmp x1, #0
    b.le at_trap
    ldr x8, [x0, #16008]
    cmp x1, x8
    b.hi at_trap
    cmp x2, #0
    b.lt at_trap
    ldr x8, [x0, #16000]
    sub x9, x1, #1
    add x9, x8, x9, lsl #4
    ldp x10, x11, [x9]
    cmp x2, x11
    b.hs at_trap
    adds x10, x10, x2
    b.cs at_trap
    ldr x11, [x0, #16024]
    cmp x10, x11
    b.hs at_trap
    ldr x11, [x0, #16016]
    ldr x0, [x11, x10, lsl #3]
    ret
at_trap:
    brk #0

.org 576
vector_assoc_in_place:
    ldr x8, [x0]
    cmp x8, #11
    b.ne assoc_trap
    cmp x1, #0
    b.le assoc_trap
    ldr x8, [x0, #16008]
    cmp x1, x8
    b.hi assoc_trap
    cmp x2, #0
    b.lt assoc_trap
    ldr x8, [x0, #16000]
    sub x9, x1, #1
    add x9, x8, x9, lsl #4
    ldp x10, x11, [x9]
    cmp x2, x11
    b.hs assoc_trap
    adds x10, x10, x2
    b.cs assoc_trap
    ldr x11, [x0, #16024]
    cmp x10, x11
    b.hs assoc_trap
    ldr x11, [x0, #16016]
    str x3, [x11, x10, lsl #3]
    mov x0, x1
    ret
assoc_trap:
    brk #0

.org 704
bytes_from_vector:
    ldr x8, [x0]
    cmp x8, #11
    b.ne bytes_trap
    cmp x1, #0
    b.le bytes_trap
    ldr x8, [x0, #16008]
    cmp x1, x8
    b.hi bytes_trap
    ldr x8, [x0, #16000]
    sub x9, x1, #1
    add x9, x8, x9, lsl #4
    ldp x10, x11, [x9]
    movz x12, #0x80, lsl #16
    cmp x11, x12
    b.hi bytes_trap
    ldr x13, [x0, #16024]
    cmp x10, x13
    b.hi bytes_trap
    sub x14, x13, x10
    cmp x11, x14
    b.hi bytes_trap
    ldr x15, [x0, #16016]
    add x16, x15, x10, lsl #3
    mov x17, x11
validate_item:
    cbz x17, validated
    ldr x12, [x16], #8
    cmp x12, #255
    b.hi bytes_trap
    sub x17, x17, #1
    b validate_item
validated:
    movz x12, #0x100, lsl #16
    sub x14, x12, x13
    cmp x11, x14
    b.hi bytes_trap
    ldr x9, [x0, #16008]
    movz x12, #0x40, lsl #16
    cmp x9, x12
    b.hs bytes_trap
    add x14, x15, x13, lsl #3
    add x16, x15, x10, lsl #3
    mov x17, x11
copy_item:
    cbz x17, copied
    ldr x12, [x16], #8
    str x12, [x14], #8
    sub x17, x17, #1
    b copy_item
copied:
    ldr x8, [x0, #16000]
    add x8, x8, x9, lsl #4
    str x13, [x8]
    str x11, [x8, #8]
    add x13, x13, x11
    str x13, [x0, #16024]
    add x9, x9, #1
    str x9, [x0, #16008]
    mov x0, x9
    ret
bytes_trap:
    brk #0
