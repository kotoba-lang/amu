/* a64call(fn, arg, ctx, &result, &spslot): call the extracted Amu payload function fn with x0 = arg and x7 = ctx (the
   seed's context register), as the aarch64 runner does. Returns 0 and stores x0 in *result, or, when the signal
   handler resumes at a64resume after a trap, returns 1. The handler restores sp from *spslot. */
#ifdef __APPLE__
#define SYM(x) _##x
#else
#define SYM(x) x
#endif
        .text
        .globl SYM(a64call)
        .globl SYM(a64resume)
        .p2align 2
SYM(a64call):
        sub sp, sp, #112
        stp x29, x30, [sp, #0]
        stp x19, x20, [sp, #16]
        stp x21, x22, [sp, #32]
        stp x23, x24, [sp, #48]
        stp x25, x26, [sp, #64]
        stp x27, x28, [sp, #80]
        str x3, [sp, #96]
        mov x9, sp
        str x9, [x4]
        mov x16, x0
        mov x0, x1
        mov x7, x2
        blr x16
        ldr x3, [sp, #96]
        str x0, [x3]
        mov x0, #0
        b 1f
SYM(a64resume):
        mov x0, #1
1:      ldp x29, x30, [sp, #0]
        ldp x19, x20, [sp, #16]
        ldp x21, x22, [sp, #32]
        ldp x23, x24, [sp, #48]
        ldp x25, x26, [sp, #64]
        ldp x27, x28, [sp, #80]
        add sp, sp, #112
        ret
