.text
.globl _guard
_guard:
 mov x19, sp
 mov x0, #4
 mov x1, #0
 mov x2, #0
 mov x3, #0
 mov x4, #0
 mov x8, #167
 svc #0
 cmp x0, #0
 b.ne fail
 sub sp, sp, #32
 mov x8, #1
 str x8, [sp]
 stp xzr, xzr, [sp, #8]
 str xzr, [sp, #24]
 mov x0, #25
 mov x1, sp
 mov x2, #0
 mov x3, #8
 mov x8, #134
 svc #0
 cmp x0, #0
 b.ne fail
 str xzr, [sp]
 mov x2, sp
 add x1, x19, #8
 adr x0, curl_path
 str x0, [x19, #8]
 mov x8, #221
 svc #0
fail:
 mov x0, #127
 mov x8, #93
 svc #0
curl_path:
 .asciz "/usr/bin/curl"
