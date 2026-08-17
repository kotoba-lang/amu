"""Same kernel as kernel.rs: eight Lehmer steps, printed as one
kotoba.runtime-sample/v1 line. Python integers are arbitrary precision, but
every intermediate here stays below 2**47, so the result is identical."""
import sys
import time


def kernel(n):
    v1 = n * 48271 + 1
    x1 = v1 - (v1 // 2147483647) * 2147483647
    v2 = x1 * 48271 + 1
    x2 = v2 - (v2 // 2147483647) * 2147483647
    v3 = x2 * 48271 + 1
    x3 = v3 - (v3 // 2147483647) * 2147483647
    v4 = x3 * 48271 + 1
    x4 = v4 - (v4 // 2147483647) * 2147483647
    v5 = x4 * 48271 + 1
    x5 = v5 - (v5 // 2147483647) * 2147483647
    v6 = x5 * 48271 + 1
    x6 = v6 - (v6 // 2147483647) * 2147483647
    v7 = x6 * 48271 + 1
    x7 = v7 - (v7 // 2147483647) * 2147483647
    v8 = x7 * 48271 + 1
    return v8 - (v8 // 2147483647) * 2147483647


def positive_arg(index, name):
    if len(sys.argv) <= index:
        raise SystemExit("missing " + name)
    value = int(sys.argv[index])
    if value <= 0:
        raise SystemExit(name + " must be a positive integer")
    return value


def main():
    n = positive_arg(1, "n")
    calls = positive_arg(2, "calls")
    warmup = positive_arg(3, "warmup")
    result = 0
    for _ in range(warmup):
        result = kernel(n)
    started = time.perf_counter_ns()
    for _ in range(calls):
        result = kernel(n)
    elapsed = time.perf_counter_ns() - started
    print('{"format":"kotoba.runtime-sample/v1","calls":%d,"warmupCalls":%d,'
          '"elapsedNanoseconds":%d,"result":%d}' % (calls, warmup, elapsed, result))


main()
