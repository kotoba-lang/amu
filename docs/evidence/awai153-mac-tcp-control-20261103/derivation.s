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
 b.cs fail
 cmp x0, #2
 b.ne fail
 mov x0, #2
 mov x1, #1
 mov x2, #0
 mov x16, #97
 movk x16, #0x200, lsl #16
 svc #0x80
 b.cs fail
 mov x19, x0
 mov x0, x19
 mov x1, sp
 mov x2, #16
 mov x16, #98
 movk x16, #0x200, lsl #16
 svc #0x80
 b.cs fail
 movz w8, #0x4950
 movk w8, #0x474e, lsl #16
 str w8, [sp, #16]
 mov x0, x19
 add x1, sp, #16
 mov x2, #4
 mov x16, #4
 movk x16, #0x200, lsl #16
 svc #0x80
 b.cs fail
 cmp x0, #4
 b.ne fail
 mov x0, x19
 add x1, sp, #20
 mov x2, #4
 mov x16, #3
 movk x16, #0x200, lsl #16
 svc #0x80
 b.cs fail
 cmp x0, #4
 b.ne fail
 ldr w9, [sp, #20]
 movz w8, #0x4f50
 movk w8, #0x474e, lsl #16
 cmp w9, w8
 b.ne fail
 mov x0, x19
 mov x16, #6
 movk x16, #0x200, lsl #16
 svc #0x80
 b.cs fail
 mov x0, #0
 b finish
fail:
 mov x0, #1
finish:
 mov x16, #1
 movk x16, #0x200, lsl #16
 svc #0x80
 brk #0
