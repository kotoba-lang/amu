.text
.globl _main
_main:
 sub sp, sp, #64
 mov w8, #0x210
 strh w8, [sp]
 movz w8, #0x007f
 movk w8, #0x0100, lsl #16
 str w8, [sp, #4]
 mov x0, #0
 add x1, sp, #2
 mov x2, #2
 mov x16, #3
 movk x16, #0x200, lsl #16
 svc #0x80
 b.cs fail_before
 cmp x0, #2
 b.ne fail_before
 mov x0, #2
 mov x1, #1
 mov x2, #0
 mov x16, #97
 movk x16, #0x200, lsl #16
 svc #0x80
 b.cs fail_before
 mov x19, x0
 mov x0, x19
 mov x1, #4
 mov x2, #4
 mov x16, #92
 movk x16, #0x200, lsl #16
 svc #0x80
 b.cs fail
 mov x0, x19
 mov x1, sp
 mov x2, #16
 mov x16, #98
 movk x16, #0x200, lsl #16
 svc #0x80
 b.cc connected
 cmp x0, #36
 b.ne fail
 str w19, [sp, #16]
 mov w8, #4
 strh w8, [sp, #20]
 strh wzr, [sp, #22]
 add x0, sp, #16
 mov x1, #1
 mov x2, #200
 mov x16, #230
 movk x16, #0x200, lsl #16
 svc #0x80
 b.cs fail
 cbz x0, timed_out
 cmp x0, #1
 b.ne fail
 ldrh w8, [sp, #22]
 tst w8, #4
 b.eq fail
 str wzr, [sp, #24]
 mov w8, #4
 str w8, [sp, #28]
 mov x0, x19
 mov x1, #0xffff
 mov x2, #0x1007
 add x3, sp, #24
 add x4, sp, #28
 mov x16, #118
 movk x16, #0x200, lsl #16
 svc #0x80
 b.cs fail
 ldr w8, [sp, #28]
 cmp w8, #4
 b.ne fail
 ldr w8, [sp, #24]
 cbnz w8, fail
connected:
 mov x20, #0
 b close_fd
timed_out:
 mov x20, #2
 b close_fd
fail:
 mov x20, #1
close_fd:
 mov x0, x19
 mov x16, #6
 movk x16, #0x200, lsl #16
 svc #0x80
 b.cc finish
 mov x20, #1
finish:
 mov x0, x20
 b exit
fail_before:
 mov x0, #1
exit:
 mov x16, #1
 movk x16, #0x200, lsl #16
 svc #0x80
 brk #0
