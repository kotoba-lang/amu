// Same kernel as kernel.rs, kernel.clj and kernel.kotoba: eight Lehmer steps,
// i64 throughout, printed as one kotoba.runtime-sample/v1 line.
package main

import (
	"fmt"
	"os"
	"strconv"
	"time"
)

func kernel(n int64) int64 {
	v1 := n*48271 + 1
	x1 := v1 - (v1/2147483647)*2147483647
	v2 := x1*48271 + 1
	x2 := v2 - (v2/2147483647)*2147483647
	v3 := x2*48271 + 1
	x3 := v3 - (v3/2147483647)*2147483647
	v4 := x3*48271 + 1
	x4 := v4 - (v4/2147483647)*2147483647
	v5 := x4*48271 + 1
	x5 := v5 - (v5/2147483647)*2147483647
	v6 := x5*48271 + 1
	x6 := v6 - (v6/2147483647)*2147483647
	v7 := x6*48271 + 1
	x7 := v7 - (v7/2147483647)*2147483647
	v8 := x7*48271 + 1
	return v8 - (v8/2147483647)*2147483647
}

func positiveArg(index int, name string) int64 {
	if len(os.Args) <= index {
		panic("missing " + name)
	}
	value, err := strconv.ParseInt(os.Args[index], 10, 64)
	if err != nil || value <= 0 {
		panic(name + " must be a positive integer")
	}
	return value
}

var sink int64

func main() {
	n := positiveArg(1, "n")
	calls := positiveArg(2, "calls")
	warmup := positiveArg(3, "warmup")
	var result int64
	for i := int64(0); i < warmup; i++ {
		result = kernel(n)
		sink = result
	}
	started := time.Now()
	for i := int64(0); i < calls; i++ {
		result = kernel(n)
		sink = result
	}
	elapsed := time.Since(started).Nanoseconds()
	fmt.Printf("{\"format\":\"kotoba.runtime-sample/v1\",\"calls\":%d,\"warmupCalls\":%d,\"elapsedNanoseconds\":%d,\"result\":%d}\n",
		calls, warmup, elapsed, result)
}
