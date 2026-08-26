use std::env;
use std::hint::black_box;
use std::time::Instant;

#[inline(never)]
fn id(x: i64) -> i64 {
    x
}

fn kernel(n: i64) -> i64 {
    let mut i = n;
    let mut acc = 0_i64;
    while i != 0 {
        let stepped = id(1);
        acc += stepped;
        i -= 1;
    }
    acc
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
