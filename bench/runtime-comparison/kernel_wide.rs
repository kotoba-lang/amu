use std::env;
use std::hint::black_box;
use std::time::Instant;

fn kernel(n: i64) -> i64 {
    let v_a0 = n * 48271 + 1;
    let a0 = v_a0 - (v_a0 / 2147483647) * 2147483647;
    let v_b0 = (n + 1) * 48271 + 1;
    let b0 = v_b0 - (v_b0 / 2147483647) * 2147483647;
    let v_c0 = (n + 2) * 48271 + 1;
    let c0 = v_c0 - (v_c0 / 2147483647) * 2147483647;
    let v_d0 = (n + 3) * 48271 + 1;
    let d0 = v_d0 - (v_d0 / 2147483647) * 2147483647;
    let v_e0 = (n + 4) * 48271 + 1;
    let e0 = v_e0 - (v_e0 / 2147483647) * 2147483647;
    let v_f0 = (n + 5) * 48271 + 1;
    let f0 = v_f0 - (v_f0 / 2147483647) * 2147483647;
    let v_g0 = (n + 6) * 48271 + 1;
    let g0 = v_g0 - (v_g0 / 2147483647) * 2147483647;
    let v_h0 = (n + 7) * 48271 + 1;
    let h0 = v_h0 - (v_h0 / 2147483647) * 2147483647;
    let v_a1 = a0 * 48271 + 1;
    let a1 = v_a1 - (v_a1 / 2147483647) * 2147483647;
    let v_b1 = b0 * 48271 + 1;
    let b1 = v_b1 - (v_b1 / 2147483647) * 2147483647;
    let v_c1 = c0 * 48271 + 1;
    let c1 = v_c1 - (v_c1 / 2147483647) * 2147483647;
    let v_d1 = d0 * 48271 + 1;
    let d1 = v_d1 - (v_d1 / 2147483647) * 2147483647;
    let v_e1 = e0 * 48271 + 1;
    let e1 = v_e1 - (v_e1 / 2147483647) * 2147483647;
    let v_f1 = f0 * 48271 + 1;
    let f1 = v_f1 - (v_f1 / 2147483647) * 2147483647;
    let v_g1 = g0 * 48271 + 1;
    let g1 = v_g1 - (v_g1 / 2147483647) * 2147483647;
    let v_h1 = h0 * 48271 + 1;
    let h1 = v_h1 - (v_h1 / 2147483647) * 2147483647;
    a1 + b1 + c1 + d1 + e1 + f1 + g1 + h1
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
