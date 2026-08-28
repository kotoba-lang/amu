@inline(__always) private func step(_ x: Int64) -> Int64 {
    let value = x * 48_271 + 1
    return value - (value / 2_147_483_647) * 2_147_483_647
}

// These two functions are compiled in a separate Swift dylib.  The benchmark
// dylib therefore cannot delete the semantic-twin calls by inspecting their
// bodies, while both sides remain Swift and cross an ordinary native call.
@_silgen_name("kotoba_bench_swift_step") private func opaqueStep(_ x: Int64) -> Int64
@_silgen_name("kotoba_bench_swift_id") private func opaqueId(_ x: Int64) -> Int64

@_cdecl("kotoba_bench_kernel")
public func kernel(_ n: Int64, _: Int64, _: Int64, _: Int64, _: Int64, _: Int64, _: Int64, _: Int64) -> Int64 {
    var x = n
    for _ in 0..<8 { x = step(x) }
    return x
}

@_cdecl("kotoba_bench_kernel_wide")
public func kernelWide(_ n: Int64, _: Int64, _: Int64, _: Int64, _: Int64, _: Int64, _: Int64, _: Int64) -> Int64 {
    let lanes = (0..<8).map { step(step(n + Int64($0))) }
    return lanes.reduce(0, +)
}

@_cdecl("kotoba_bench_kernel_deep")
public func kernelDeep(_ n: Int64, _: Int64, _: Int64, _: Int64, _: Int64, _: Int64, _: Int64, _: Int64) -> Int64 {
    var lanes = (0..<14).map { step(n + Int64($0)) }
    let shadowN = lanes[13]
    lanes += (14..<24).map { step(shadowN + Int64($0)) }
    return lanes.reduce(0, +)
}

@inline(never) private func callSum(_ n: Int64) -> Int64 {
    let a = opaqueStep(n), b = opaqueStep(n + 1), c = opaqueStep(n + 2), d = opaqueStep(n + 3)
    return a+b+c+d+opaqueStep(a)+opaqueStep(b)+opaqueStep(c)+opaqueStep(d)
}

@_cdecl("kotoba_bench_kernel_call")
public func kernelCall(_ n: Int64, _: Int64, _: Int64, _: Int64, _: Int64, _: Int64, _: Int64, _: Int64) -> Int64 { callSum(n) }

@_cdecl("kotoba_bench_kernel_call_branch")
public func kernelCallBranch(_ n: Int64, _: Int64, _: Int64, _: Int64, _: Int64, _: Int64, _: Int64, _: Int64) -> Int64 { n == 0 ? 0 : callSum(n) }

@_cdecl("kotoba_bench_kernel_loop_call")
public func kernelLoopCall(_ n: Int64, _: Int64, _: Int64, _: Int64, _: Int64, _: Int64, _: Int64, _: Int64) -> Int64 {
    var i = n, acc: Int64 = 0
    while i != 0 { acc += opaqueId(1); i -= 1 }
    return acc
}
