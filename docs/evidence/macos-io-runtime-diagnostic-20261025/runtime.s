.section __TEXT,__text,regular,pure_instructions
.globl _main
_main:
  sub sp, sp, #1024
  mov x7, sp
  str xzr, [x7]
  mov x8, #1000
  str x8, [x7, #8]
  movz x8, #32, lsl #32
  str x8, [x7, #16]
  adr x8, guest
  str x8, [x7, #384]
  mov x8, #135
  str x8, [x7, #392]
  adr x8, pair_new
  str x8, [x7, #56]
  adr x8, typed_cap
  str x8, [x7, #128]
  bl guest
  mov x16, #1
  movk x16, #0x2000, lsl #16
  svc #0x80
  brk #1

guest:
  .incbin "macos-io-main-v2.raw"
  .p2align 2

pair_new:
  ldr x5, [x0]
  cmp x5, #4
  b.hs denied
  add x6, x0, #512
  add x6, x6, x5, lsl #4
  str x1, [x6]
  str x2, [x6, #8]
  add x5, x5, #1
  str x5, [x0]
  mov x0, x5
  ret

typed_cap:
  stp x19, x30, [sp, #-16]!
  mov x19, x0
  cmp x1, #37
  b.ne denied
  cmp x2, #1
  b.ne denied
  cmp x3, #1
  b.ne denied
  ldr x5, [x0, #16]
  movz x6, #32, lsl #32
  cmp x5, x6
  b.ne denied
  cbz x4, denied
  ldr x5, [x0]
  cmp x4, x5
  b.hi denied
  sub x4, x4, #1
  add x5, x0, #512
  add x5, x5, x4, lsl #4
  ldr x1, [x5]
  ldr x2, [x5, #8]
  cmp x2, #64
  b.hi denied
  ldr x5, [x0, #392]
  cmp x1, x5
  b.hi denied
  sub x5, x5, x1
  cmp x2, x5
  b.hi denied
  ldr x5, [x0, #384]
  add x1, x5, x1
  mov x0, #1
  mov x16, #4
  movk x16, #0x2000, lsl #16
  svc #0x80
  b.cs denied
  cmp x0, #9
  b.hi denied
  add x1, x0, #48
  strb w1, [x19, #768]
  mov x0, x19
  mov x1, #-1
  mov x2, #1
  bl pair_new
  ldp x19, x30, [sp], #16
  ret

denied:
  brk #1
