.text
.globl _main
_main:
 sub sp, sp, #64
 mov w8, #0x210
 strh w8, [sp]
 mov w8, #0x7f
 movk w8, #0x100, lsl #16
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
 mov w8, #1
 str w8, [sp, #16]
 mov x0, x19
 mov x1, #0xffff
 mov x2, #0x1022
 add x3, sp, #16
 mov x4, #4
 mov x16, #105
 movk x16, #0x200, lsl #16
 svc #0x80
 b.cs closefail
 mov x0, x19
 mov x1, sp
 mov x2, #16
 mov x16, #98
 movk x16, #0x200, lsl #16
 svc #0x80
 b.cs closefail
 mov x0, x19
 add x1, sp, #20
 mov x2, #1
 mov x16, #3
 movk x16, #0x200, lsl #16
 svc #0x80
 mov w8, #0x78
 strb w8, [sp, #20]
 mov x0, x19
 add x1, sp, #20
 mov x2, #1
 mov x16, #4
 movk x16, #0x200, lsl #16
 svc #0x80
 b.cc closefail
 cmp x0, #32
 b.ne closefail
 mov x0, x19
 mov x16, #6
 movk x16, #0x200, lsl #16
 svc #0x80
 b.cs fail
 mov x0, #0
 b exit
closefail:
 mov x0, x19
 mov x16, #6
 movk x16, #0x200, lsl #16
 svc #0x80
fail:
 mov x0, #1
exit:
 mov x16, #1
 movk x16, #0x200, lsl #16
 svc #0x80
 brk #0
