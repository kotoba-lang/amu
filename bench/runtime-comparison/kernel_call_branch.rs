#[inline(never)]
#[no_mangle]
pub extern "C" fn kotoba_bench_step(x: i64) -> i64 {
    let value = x * 48_271 + 1;
    value - (value / 2_147_483_647) * 2_147_483_647
}

fn kernel(n: i64) -> i64 {
    let a = kotoba_bench_step(n);
    let b = kotoba_bench_step(n + 1);
    let c = kotoba_bench_step(n + 2);
    let d = kotoba_bench_step(n + 3);
    let e = kotoba_bench_step(a);
    let f = kotoba_bench_step(b);
    let g = kotoba_bench_step(c);
    let h = kotoba_bench_step(d);
    if n == 0 { 0 } else { a + b + c + d + e + f + g + h }
}

#[inline(never)]
#[no_mangle]
pub extern "C" fn kotoba_bench_kernel(n: i64, _a1: i64, _a2: i64, _a3: i64,
                                       _a4: i64, _a5: i64, _a6: i64, _a7: i64) -> i64 {
    kernel(n)
}
