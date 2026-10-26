.section __TEXT,__text,regular,pure_instructions
.globl _main
.p2align 2
_main:
    cmp x0, #2
    b.ne Lusage
    ldr x1, [x1, #8]          // argv[1]: candidate relative path
    mov x0, #3                // root directory FD, supplied by parent
    mov x2, #0x1004           // O_RESOLVE_BENEATH | O_NONBLOCK
    movk x2, #0x2100, lsl #16 // O_NOFOLLOW_ANY | O_CLOEXEC
    mov x3, #0
    mov x16, #463             // SYS_openat
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cs Lrefused
    mov x19, x0
    sub sp, sp, #16
    mov x1, sp
    mov x2, #1
    mov x16, #3               // SYS_read
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cs Lread_fail
    cmp x0, #1
    b.ne Lread_fail
    ldrb w8, [sp]
    cmp w8, #75               // 'K'
    b.ne Lread_fail
    mov x0, x19
    mov x16, #6               // SYS_close
    movk x16, #0x2000, lsl #16
    svc #0x80
    b.cs Lread_fail
    mov x0, #42
    b Lexit
Lread_fail:
    mov x0, #4
    b Lexit
Lrefused:
    b Lexit
Lusage:
    mov x0, #2
Lexit:
    mov x16, #1               // SYS_exit
    movk x16, #0x2000, lsl #16
    svc #0x80
    brk #0
