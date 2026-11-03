# Multiboot (a.out kludge) flat image at 0x100000, long mode, an IDT whose #UD (vector 6) gate abandons the faulting
# call and returns 1 from trapcall, then test_main(). The same file as docs/evidence/fused-dot-20261031/entry.S (JUN-633).
.section .text.entry, "ax"
.code32
.globl hdr
hdr:
  .long 0x1BADB002
  .long 0x00010000
  .long -(0x1BADB002 + 0x00010000)
  .long hdr
  .long hdr
  .long _edata
  .long _end
  .long entry
entry:
  cli
  movl $stack_top, %esp
  movl $(pdpt + 3), pml4
  xorl %ecx, %ecx
1: movl %ecx, %eax
  shll $12, %eax
  addl $(pd + 3), %eax
  movl %eax, pdpt(,%ecx,8)
  incl %ecx
  cmpl $4, %ecx
  jb 1b
  xorl %ecx, %ecx
2: movl %ecx, %eax
  shll $21, %eax
  orl $0x83, %eax
  movl %eax, pd(,%ecx,8)
  incl %ecx
  cmpl $2048, %ecx
  jb 2b
  movl $pml4, %eax
  movl %eax, %cr3
  movl %cr4, %eax
  orl $0x620, %eax          # PAE, OSFXSR, OSXMMEXCPT
  movl %eax, %cr4
  movl $0xC0000080, %ecx
  rdmsr
  orl $0x100, %eax
  wrmsr
  movl %cr0, %eax
  andl $0xFFFFFFFB, %eax    # clear EM
  orl $0x80000003, %eax     # PG, PE, MP
  movl %eax, %cr0
  lgdt gdtr
  ljmp $0x08, $long
.code64
long:
  movw $0x10, %ax
  movw %ax, %ds
  movw %ax, %es
  movw %ax, %ss
  movq $stack_top, %rsp
  # IDT gate 6 -> ud_handler (64-bit interrupt gate, selector 8, present, DPL 0)
  leaq ud_handler(%rip), %rax
  leaq idt(%rip), %rdi
  movw %ax, 96(%rdi)
  movw $0x08, 98(%rdi)
  movw $0x8E00, 100(%rdi)
  shrq $16, %rax
  movw %ax, 102(%rdi)
  shrq $16, %rax
  movl %eax, 104(%rdi)
  movl $0, 108(%rdi)
  lidt idtr(%rip)
  call test_main
  movw $0xf4, %dx
  xorl %eax, %eax
  outl %eax, %dx
3: hlt
  jmp 3b
# int64_t trapcall(fn, a, b, c, d, e, int64_t *result): 0 when fn returned (result stored), 1 when it raised #UD
.globl trapcall
trapcall:
  push %rbx
  push %rbp
  push %r12
  push %r13
  push %r14
  push %r15
  movq 56(%rsp), %rax
  movq %rax, trap_result_ptr(%rip)
  movq %rsp, trap_saved_rsp(%rip)
  movq %rdi, %rax
  movq %rsi, %rdi
  movq %rdx, %rsi
  movq %rcx, %rdx
  movq %r8, %rcx
  movq %r9, %r8
  subq $8, %rsp
  call *%rax
  addq $8, %rsp
  movq trap_result_ptr(%rip), %rcx
  movq %rax, (%rcx)
  xorl %eax, %eax
  jmp 4f
ud_handler:
  movq trap_saved_rsp(%rip), %rsp
  movl $1, %eax
4: pop %r15
  pop %r14
  pop %r13
  pop %r12
  pop %rbp
  pop %rbx
  ret
.balign 16
gdt:
  .quad 0
  .quad 0x00AF9A000000FFFF
  .quad 0x00CF92000000FFFF
gdtr:
  .word 23
  .long gdt
.balign 16
idtr:
  .word 4095
  .quad idt
.section .bss.boot, "aw", @nobits
.balign 4096
pml4: .skip 4096
pdpt: .skip 4096
pd: .skip 16384
idt: .skip 4096
trap_saved_rsp: .skip 8
trap_result_ptr: .skip 8
.balign 16
.skip 262144
stack_top:
