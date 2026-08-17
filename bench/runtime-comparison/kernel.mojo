# Same kernel as kernel.rs: eight Lehmer steps over Int64, printed as one
# kotoba.runtime-sample/v1 line.
from std.sys import argv
from std.time import perf_counter_ns
from std.benchmark import black_box, keep

def kernel(n: Int64) -> Int64:
    var v1 = n * 48271 + 1
    var x1 = v1 - (v1 // 2147483647) * 2147483647
    var v2 = x1 * 48271 + 1
    var x2 = v2 - (v2 // 2147483647) * 2147483647
    var v3 = x2 * 48271 + 1
    var x3 = v3 - (v3 // 2147483647) * 2147483647
    var v4 = x3 * 48271 + 1
    var x4 = v4 - (v4 // 2147483647) * 2147483647
    var v5 = x4 * 48271 + 1
    var x5 = v5 - (v5 // 2147483647) * 2147483647
    var v6 = x5 * 48271 + 1
    var x6 = v6 - (v6 // 2147483647) * 2147483647
    var v7 = x6 * 48271 + 1
    var x7 = v7 - (v7 // 2147483647) * 2147483647
    var v8 = x7 * 48271 + 1
    return v8 - (v8 // 2147483647) * 2147483647

def main() raises:
    var args = argv()
    var n = Int64(atol(String(args[1])))
    var calls = Int64(atol(String(args[2])))
    var warmup = Int64(atol(String(args[3])))
    var result = Int64(0)
    for _ in range(Int(warmup)):
        result = kernel(black_box(n))
        keep(result)
    var started = perf_counter_ns()
    for _ in range(Int(calls)):
        result = kernel(black_box(n))
        keep(result)
    var elapsed = perf_counter_ns() - started
    print('{"format":"kotoba.runtime-sample/v1","calls":', calls,
          ',"warmupCalls":', warmup, ',"elapsedNanoseconds":', elapsed,
          ',"result":', result, '}', sep="")
