use std::env;
use std::hint::black_box;
use std::time::Instant;

#[inline(never)]
#[no_mangle]
pub extern "C" fn kotoba_bench_batch(n: i64, iterations: u64) -> i64 {
    let mut remaining = iterations;
    let mut checksum = n;
    while remaining != 0 {
        let mixed = (checksum * 48_271) + 1;
        checksum = mixed - ((mixed / 2_147_483_647) * 2_147_483_647);
        remaining -= 1;
    }
    checksum
}

fn positive_arg(index: usize, name: &str) -> u64 {
    let value = env::args().nth(index).unwrap_or_else(|| panic!("missing {}", name));
    value.parse::<u64>().ok().filter(|v| *v > 0)
        .unwrap_or_else(|| panic!("{} must be a positive integer", name))
}

fn main() {
    let n = positive_arg(1, "n") as i64;
    let iterations = positive_arg(2, "iterations");
    let started = Instant::now();
    let checksum = black_box(kotoba_bench_batch(black_box(n), black_box(iterations)));
    let elapsed = started.elapsed().as_nanos();
    println!(
        "{{\"format\":\"kotoba.runtime-sample/v1\",\"calls\":1,\"warmupCalls\":0,\"iterations\":{iterations},\"hostCalls\":1,\"elapsedNanoseconds\":{elapsed},\"result\":{checksum}}}"
    );
}
