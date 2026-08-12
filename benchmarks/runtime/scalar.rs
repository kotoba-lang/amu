use std::env;
use std::hint::black_box;
use std::time::Instant;

#[inline(never)]
fn multiply(left: i64, right: i64) -> i64 {
    black_box(left).wrapping_mul(black_box(right))
}

fn checksum(iterations: u64) -> i64 {
    let mut total = 0_i64;
    for _ in 0..iterations {
        total = black_box(total.wrapping_add(multiply(6, 7)));
    }
    total
}

fn branch_checksum(iterations: u64) -> i64 {
    let half = iterations / 2;
    let mut total = 0_i64;
    for index in 0..iterations {
        total = black_box(total.wrapping_add(if black_box(index) < half { 41 } else { 43 }));
    }
    total
}

fn xorshift32_checksum(iterations: u64) -> i64 {
    let mut state = 2_463_534_242_u32;
    for _ in 0..iterations {
        state ^= state << 13;
        state ^= state >> 17;
        state ^= state << 5;
    }
    i64::from(state)
}

fn vector_allocation_checksum(iterations: u64) -> i64 {
    let mut state = 2_463_534_242_u32;
    let mut total = 0_i64;
    for _ in 0..iterations {
        let values = black_box([3_i64, 5, 8, 13, 21, 34, 55, 89]);
        state ^= state << 13;
        state ^= state >> 17;
        state ^= state << 5;
        total = total.wrapping_add(values[(state & 7) as usize]);
    }
    total
}

#[inline(never)]
fn retain_vector(values: [i64; 8]) -> [i64; 8] {
    black_box(values)
}

fn vector_materialization_checksum(iterations: u64) -> i64 {
    let mut state = 2_463_534_242_u32;
    let mut total = 0_i64;
    for index in 0..iterations {
        let values = black_box([3_i64, 5, 8, 13, 21, 34, 55, 89]);
        state ^= state << 13;
        state ^= state >> 17;
        state ^= state << 5;
        let selected = if index & 511 == 0 {
            retain_vector(values)[(state & 7) as usize]
        } else {
            values[(state & 7) as usize]
        };
        total = total.wrapping_add(selected);
    }
    total
}

fn main() {
    let args: Vec<String> = env::args().skip(1).collect();
    let workload = args.first().map(String::as_str).unwrap_or("scalar");
    let once = args.get(1).map(String::as_str) == Some("--once");
    let iterations = args.get(2).and_then(|value| value.parse().ok()).unwrap_or(1);
    let warmup_iterations = args
        .get(3)
        .and_then(|value| value.parse().ok())
        .unwrap_or(iterations.min(1_000));
    let run = |count| match workload {
        "scalar" => checksum(count),
        "branch" => branch_checksum(count),
        "mix" => xorshift32_checksum(count),
        "vector" => vector_allocation_checksum(count),
        "vector-materialize" => vector_materialization_checksum(count),
        _ => panic!("unknown benchmark workload"),
    };
    if once {
        println!("{{\"checksum\":{}}}", run(iterations));
        return;
    }
    black_box(run(warmup_iterations));
    let started = Instant::now();
    let result = black_box(run(iterations));
    let elapsed = started.elapsed().as_nanos();
    println!(
        "{{\"iterations\":{},\"warmupIterations\":{},\"checksum\":{},\"elapsedNanoseconds\":{}}}",
        iterations, warmup_iterations, result, elapsed
    );
}
