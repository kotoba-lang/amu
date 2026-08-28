// Keep the call opaque to rustc/LLVM without adding a runtime operation to
// the identity body on supported targets. `inline(never)` alone is not enough:
// LLVM can otherwise prove that the complete loop returns `n` and delete it.
#[inline(never)]
#[no_mangle]
pub extern "C" fn kotoba_bench_id(x: i64) -> i64 {
    let mut value = x;
    // Zero emitted instructions, but an opaque ABI value: this preserves the
    // semantic-twin call without charging Rust a comparator-only operation.
    unsafe {
        core::arch::asm!("", inout("x0") value, options(nomem, nostack, preserves_flags));
    }
    value
}

fn kernel(n: i64) -> i64 {
    let mut i = n;
    let mut acc = 0_i64;
    while i != 0 {
        let stepped = kotoba_bench_id(1);
        acc += stepped;
        i -= 1;
    }
    acc
}

#[inline(never)]
#[no_mangle]
pub extern "C" fn kotoba_bench_kernel(n: i64, _a1: i64, _a2: i64, _a3: i64,
                                       _a4: i64, _a5: i64, _a6: i64, _a7: i64) -> i64 {
    kernel(n)
}
