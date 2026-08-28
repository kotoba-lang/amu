@inline(__always) private func step(_ x: Int64) -> Int64 {
    let value = x * 48_271 + 1
    return value - (value / 2_147_483_647) * 2_147_483_647
}

@_cdecl("kotoba_bench_swift_step")
@inline(never)
public func kotobaBenchSwiftStep(_ x: Int64) -> Int64 { step(x) }

@_cdecl("kotoba_bench_swift_id")
@inline(never)
public func kotobaBenchSwiftID(_ x: Int64) -> Int64 { x }
