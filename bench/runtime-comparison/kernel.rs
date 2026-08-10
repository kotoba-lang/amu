use std::env;
use std::hint::black_box;
use std::time::Instant;

fn kernel(n: i64) -> i64 {
    let v1 = n * 48_271 + 1; let x1 = v1 - (v1 / 2_147_483_647) * 2_147_483_647;
    let v2 = x1 * 48_271 + 1; let x2 = v2 - (v2 / 2_147_483_647) * 2_147_483_647;
    let v3 = x2 * 48_271 + 1; let x3 = v3 - (v3 / 2_147_483_647) * 2_147_483_647;
    let v4 = x3 * 48_271 + 1; let x4 = v4 - (v4 / 2_147_483_647) * 2_147_483_647;
    let v5 = x4 * 48_271 + 1; let x5 = v5 - (v5 / 2_147_483_647) * 2_147_483_647;
    let v6 = x5 * 48_271 + 1; let x6 = v6 - (v6 / 2_147_483_647) * 2_147_483_647;
    let v7 = x6 * 48_271 + 1; let x7 = v7 - (v7 / 2_147_483_647) * 2_147_483_647;
    let v8 = x7 * 48_271 + 1;
    v8 - (v8 / 2_147_483_647) * 2_147_483_647
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
    for _ in 0..warmup {
        result = black_box(kernel(black_box(n)));
    }
    let started = Instant::now();
    for _ in 0..calls {
        result = black_box(kernel(black_box(n)));
    }
    let elapsed = started.elapsed().as_nanos();
    println!(
        "{{\"format\":\"kotoba.runtime-sample/v1\",\"calls\":{calls},\"warmupCalls\":{warmup},\"elapsedNanoseconds\":{elapsed},\"result\":{result}}}"
    );
}
