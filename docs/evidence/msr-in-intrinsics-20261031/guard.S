# A trap guard for the hand check: guarded_call(fn, a0, a1) calls fn(a0, a1); a #UD (vector 6) or #GP (vector 13) in it
# resumes at `recover` on the saved stack with guard_vector set to the vector, and guarded_call returns 0.
.text
.globl guarded_call
guarded_call:
  pushq %rbx; pushq %rbp; pushq %r12; pushq %r13; pushq %r14; pushq %r15
  subq $8, %rsp
  movq %rsp, guard_rsp(%rip)
  movq $0, guard_vector(%rip)
  movq %rdi, %rax
  movq %rsi, %rdi; movq %rdx, %rsi
  call *%rax
resume:
  addq $8, %rsp
  popq %r15; popq %r14; popq %r13; popq %r12; popq %rbp; popq %rbx
  ret
recover:
  movq guard_rsp(%rip), %rsp
  xorl %eax, %eax
  jmp resume
isr_gp:
  addq $8, %rsp                # the error code
  movq $13, guard_vector(%rip)
  jmp frame
isr_ud:
  movq $6, guard_vector(%rip)
frame:
  pushq %rax
  leaq recover(%rip), %rax
  movq %rax, 8(%rsp)           # rip
  movq guard_rsp(%rip), %rax
  movq %rax, 32(%rsp)          # rsp
  popq %rax
  iretq
gate:                          # rax = handler, rcx = descriptor
  movw %ax, (%rcx)
  movw $0x08, 2(%rcx)
  movw $0x8e00, 4(%rcx)
  shrq $16, %rax
  movw %ax, 6(%rcx)
  shrq $16, %rax
  movl %eax, 8(%rcx)
  movl $0, 12(%rcx)
  ret
.globl guard_init
guard_init:
  leaq isr_ud(%rip), %rax
  leaq guard_idt+96(%rip), %rcx
  call gate
  leaq isr_gp(%rip), %rax
  leaq guard_idt+208(%rip), %rcx
  call gate
  leaq guard_idt(%rip), %rax
  movq %rax, guard_idtr+2(%rip)
  lidt guard_idtr(%rip)
  ret
.data
.balign 16
guard_idtr: .word 32 * 16 - 1
  .quad 0
.globl guard_vector
.balign 8
guard_vector: .quad 0
guard_rsp: .quad 0
.bss
.balign 16
guard_idt: .skip 32 * 16
