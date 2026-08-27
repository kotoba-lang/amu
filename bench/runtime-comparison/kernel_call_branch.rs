use std::env;
use std::hint::black_box;
use std::time::Instant;

#[inline(never)]
#[no_mangle]
pub extern "C" fn kotoba_bench_step(x: i64) -> i64 {
    let x = black_box(x);
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
    if black_box(n) == 0 { 0 } else { a + b + c + d + e + f + g + h }
}

fn positive_arg(index: usize, name: &str) -> u64 {
    let value = env::args().nth(index).unwrap_or_else(|| panic!("missing {}", name));
    value.parse::<u64>().ok().filter(|v| *v > 0)
        .unwrap_or_else(|| panic!("{} must be a positive integer", name))
}

fn main() {
    let n = positive_arg(1, "n") as i64;
    let calls = positive_arg(2, "calls");
    let warmup = positive_arg(3, "warmup");
    let mut result = 0_i64;
    for _ in 0..warmup { result = black_box(kernel(black_box(n))); }
    let started = Instant::now();
    for _ in 0..calls { result = black_box(kernel(black_box(n))); }
    println!("{{\"format\":\"kotoba.runtime-sample/v1\",\"calls\":{calls},\"warmupCalls\":{warmup},\"elapsedNanoseconds\":{},\"result\":{result}}}", started.elapsed().as_nanos());
}
