package main

/*
#include <stdint.h>
*/
import "C"

func step(x int64) int64 {
	value := x*48271 + 1
	return value - (value/2147483647)*2147483647
}

//go:noinline
func opaqueStep(x int64) int64 { return step(x) }

//go:noinline
func opaqueID(x int64) int64 { return x }

//export kotoba_bench_kernel
func kotoba_bench_kernel(n, a1, a2, a3, a4, a5, a6, a7 C.int64_t) C.int64_t {
	_, _, _, _, _, _, _ = a1, a2, a3, a4, a5, a6, a7
	x := int64(n)
	for i := 0; i < 8; i++ {
		x = step(x)
	}
	return C.int64_t(x)
}

//export kotoba_bench_kernel_wide
func kotoba_bench_kernel_wide(n, a1, a2, a3, a4, a5, a6, a7 C.int64_t) C.int64_t {
	_, _, _, _, _, _, _ = a1, a2, a3, a4, a5, a6, a7
	var lanes [8]int64
	for i := range lanes {
		lanes[i] = step(step(int64(n) + int64(i)))
	}
	var sum int64
	for _, lane := range lanes {
		sum += lane
	}
	return C.int64_t(sum)
}

//export kotoba_bench_kernel_deep
func kotoba_bench_kernel_deep(n, a1, a2, a3, a4, a5, a6, a7 C.int64_t) C.int64_t {
	_, _, _, _, _, _, _ = a1, a2, a3, a4, a5, a6, a7
	var lanes [24]int64
	for i := 0; i < 14; i++ {
		lanes[i] = step(int64(n) + int64(i))
	}
	shadowN := lanes[13]
	for i := 14; i < 24; i++ {
		lanes[i] = step(shadowN + int64(i))
	}
	var sum int64
	for _, lane := range lanes {
		sum += lane
	}
	return C.int64_t(sum)
}

func callSum(n int64) int64 {
	a, b, c, d := opaqueStep(n), opaqueStep(n+1), opaqueStep(n+2), opaqueStep(n+3)
	return a + b + c + d + opaqueStep(a) + opaqueStep(b) + opaqueStep(c) + opaqueStep(d)
}

//export kotoba_bench_kernel_call
func kotoba_bench_kernel_call(n, a1, a2, a3, a4, a5, a6, a7 C.int64_t) C.int64_t {
	_, _, _, _, _, _, _ = a1, a2, a3, a4, a5, a6, a7
	return C.int64_t(callSum(int64(n)))
}

//export kotoba_bench_kernel_call_branch
func kotoba_bench_kernel_call_branch(n, a1, a2, a3, a4, a5, a6, a7 C.int64_t) C.int64_t {
	_, _, _, _, _, _, _ = a1, a2, a3, a4, a5, a6, a7
	if n == 0 {
		return 0
	}
	return C.int64_t(callSum(int64(n)))
}

//export kotoba_bench_kernel_loop_call
func kotoba_bench_kernel_loop_call(n, a1, a2, a3, a4, a5, a6, a7 C.int64_t) C.int64_t {
	_, _, _, _, _, _, _ = a1, a2, a3, a4, a5, a6, a7
	i, acc := int64(n), int64(0)
	for i != 0 {
		acc += opaqueID(1)
		i--
	}
	return C.int64_t(acc)
}

func main() {}
