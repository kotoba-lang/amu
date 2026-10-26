.section __TEXT,__text
.org 2048
_pool_setup:
  ret
.org 2100
_bounded_span:
  ret
.org 6256
_mac_pure_setup:
  stp x29, x30, [sp, #-16]!
  adr x8, _mac_vector_conj
  str x8, [x19, #160]
  adr x8, _mac_vector_assoc
  str x8, [x19, #184]
  adr x8, _mac_string_index
  str x8, [x19, #216]
  adr x8, _mac_string_compare
  str x8, [x19, #240]
  bl _pool_setup
  ldp x29, x30, [sp], #16
  ret

// Persistent vector edit. x4=1 selects conj; x4=0 selects assoc.
_mac_vector_conj:
  mov x4, #1
  b _mac_vector_edit
_mac_vector_assoc:
  mov x4, #0
  b _mac_vector_edit
_mac_vector_edit:
  sub sp, sp, #96
  stp x29, x30, [sp]
  stp x19, x20, [sp, #16]
  stp x21, x22, [sp, #32]
  stp x23, x24, [sp, #48]
  stp x25, x26, [sp, #64]
  stp x27, x28, [sp, #80]
  mov x19, x0
  mov x20, x1
  mov x21, x4
  mov x22, x2
  mov x23, x3
  cbz x21, 1f
  mov x23, x2
1:
  ldr x8, [x19]
  cmp x8, #11
  b.ne _mac_pure_trap
  cmp x20, #1
  b.lo _mac_pure_trap
  ldr x8, [x19, #16008]
  cmp x20, x8
  b.hi _mac_pure_trap
  ldr x8, [x19, #16000]
  sub x9, x20, #1
  add x8, x8, x9, lsl #4
  ldp x24, x25, [x8]
  // Bounds for the old slice, with subtraction before addition.
  ldr x8, [x19, #16024]
  cmp x24, x8
  b.hi _mac_pure_trap
  sub x8, x8, x24
  cmp x25, x8
  b.hi _mac_pure_trap
  mov x8, #0x800000
  cmp x25, x8
  b.hi _mac_pure_trap
  cbz x21, 2f
  cmp x25, x8
  b.hs _mac_pure_trap
  mov x22, x25
  add x26, x25, #1
  b 3f
2:
  tbnz x22, #63, _mac_pure_trap
  cmp x22, x25
  b.hs _mac_pure_trap
  mov x26, x25
3:
  mov x0, x19
  mov x1, x26
  ldr x16, [x19, #200]
  blr x16
  mov x27, x0
  // The allocator checked item and descriptor limits; its new handle is live.
  ldr x8, [x19, #16000]
  sub x9, x27, #1
  add x8, x8, x9, lsl #4
  ldr x28, [x8]
  ldr x9, [x19, #16016]
  add x10, x9, x24, lsl #3
  add x11, x9, x28, lsl #3
  mov x12, x25
4:
  cbz x12, 5f
  ldr x13, [x10], #8
  str x13, [x11], #8
  sub x12, x12, #1
  b 4b
5:
  add x8, x28, x22
  str x23, [x9, x8, lsl #3]
  mov x0, x27
  ldp x29, x30, [sp]
  ldp x19, x20, [sp, #16]
  ldp x21, x22, [sp, #32]
  ldp x23, x24, [sp, #48]
  ldp x25, x26, [sp, #64]
  ldp x27, x28, [sp, #80]
  add sp, sp, #96
  ret

// Validate and resolve a string handle. Returns x0=address, x1=byte length.
_mac_string_span:
  sub sp, sp, #64
  stp x29, x30, [sp]
  stp x19, x20, [sp, #16]
  stp x21, x22, [sp, #32]
  mov x19, x0
  mov x20, x1
  ldr x8, [x19]
  cmp x8, #11
  b.ne _mac_pure_trap
  cmp x20, #1
  b.lo _mac_pure_trap
  ldr x8, [x19, #288]
  ldr x8, [x8]
  cmp x20, x8
  b.hi _mac_pure_trap
  ldr x8, [x19, #296]
  sub x9, x20, #1
  add x8, x8, x9, lsl #4
  ldp x21, x22, [x8]
  tbnz x22, #63, _mac_pure_trap
  cbz x22, 6f
  // The existing codepoint helper checks the entire canonical UTF-8 value.
  mov x0, x19
  mov x1, x20
  mov x2, #0
  ldr x16, [x19, #144]
  blr x16
6:
  mov x0, x19
  mov x1, x21
  mov x2, x22
  bl _bounded_span
  mov x1, x22
  ldp x29, x30, [sp]
  ldp x19, x20, [sp, #16]
  ldp x21, x22, [sp, #32]
  add sp, sp, #64
  ret

_mac_string_compare:
  sub sp, sp, #64
  stp x29, x30, [sp]
  stp x19, x20, [sp, #16]
  stp x21, x22, [sp, #32]
  stp x23, x24, [sp, #48]
  mov x19, x0
  mov x20, x2
  bl _mac_string_span
  mov x21, x0
  mov x22, x1
  mov x0, x19
  mov x1, x20
  bl _mac_string_span
  mov x23, x0
  mov x24, x1
  cmp x22, x24
  csel x8, x22, x24, lo
  mov x9, #0
7:
  cmp x9, x8
  b.hs 8f
  ldrb w10, [x21, x9]
  ldrb w11, [x23, x9]
  cmp w10, w11
  b.lo 9f
  b.hi 10f
  add x9, x9, #1
  b 7b
8:
  cmp x22, x24
  b.lo 9f
  b.hi 10f
  mov x0, #0
  b 11f
9:
  mov x0, #-1
  b 11f
10:
  mov x0, #1
11:
  ldp x29, x30, [sp]
  ldp x19, x20, [sp, #16]
  ldp x21, x22, [sp, #32]
  ldp x23, x24, [sp, #48]
  add sp, sp, #64
  ret

_mac_string_index:
  sub sp, sp, #64
  stp x29, x30, [sp]
  stp x19, x20, [sp, #16]
  stp x21, x22, [sp, #32]
  stp x23, x24, [sp, #48]
  mov x19, x0
  mov x20, x2
  bl _mac_string_span
  mov x21, x0
  mov x22, x1
  mov x0, x19
  mov x1, x20
  bl _mac_string_span
  mov x23, x0
  mov x24, x1
  cbz x24, _mac_pure_trap
  cmp x24, x22
  b.hi 15f
  sub x8, x22, x24
  mov x9, #0
12:
  cmp x9, x8
  b.hi 15f
  mov x10, #0
13:
  cmp x10, x24
  b.hs 14f
  add x11, x9, x10
  ldrb w12, [x21, x11]
  ldrb w13, [x23, x10]
  cmp w12, w13
  b.ne 16f
  add x10, x10, #1
  b 13b
14:
  mov x0, x9
  b 17f
16:
  add x9, x9, #1
  b 12b
15:
  mov x0, #-1
17:
  ldp x29, x30, [sp]
  ldp x19, x20, [sp, #16]
  ldp x21, x22, [sp, #32]
  ldp x23, x24, [sp, #48]
  add sp, sp, #64
  ret

_mac_pure_trap:
  brk #0
