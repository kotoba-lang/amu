inline fn step(x: i64) i64 {
    const value = x * 48271 + 1;
    return value - @divTrunc(value, 2147483647) * 2147483647;
}

noinline fn opaqueStep(x: i64) i64 {
    const held = asm volatile (""
        : [ret] "={x0}" (-> i64),
        : [arg] "{x0}" (x),
    );
    return step(held);
}
noinline fn opaqueId(x: i64) i64 {
    return asm volatile (""
        : [ret] "={x0}" (-> i64),
        : [arg] "{x0}" (x),
    );
}

export fn kotoba_bench_kernel(n: i64, _: i64, _: i64, _: i64, _: i64, _: i64, _: i64, _: i64) callconv(.c) i64 {
    var x = n;
    inline for (0..8) |_| x = step(x);
    return x;
}

export fn kotoba_bench_kernel_wide(n: i64, _: i64, _: i64, _: i64, _: i64, _: i64, _: i64, _: i64) callconv(.c) i64 {
    var lanes: [8]i64 = undefined;
    inline for (0..8) |i| lanes[i] = step(step(n + @as(i64, i)));
    var sum: i64 = 0;
    inline for (lanes) |lane| sum += lane;
    return sum;
}

export fn kotoba_bench_kernel_deep(n: i64, _: i64, _: i64, _: i64, _: i64, _: i64, _: i64, _: i64) callconv(.c) i64 {
    var lanes: [24]i64 = undefined;
    inline for (0..14) |i| lanes[i] = step(n + @as(i64, i));
    const shadow_n = lanes[13];
    inline for (14..24) |i| lanes[i] = step(shadow_n + @as(i64, i));
    var sum: i64 = 0;
    inline for (lanes) |lane| sum += lane;
    return sum;
}

fn callSum(n: i64) i64 {
    const a = opaqueStep(n); const b = opaqueStep(n + 1);
    const c = opaqueStep(n + 2); const d = opaqueStep(n + 3);
    return a + b + c + d + opaqueStep(a) + opaqueStep(b) + opaqueStep(c) + opaqueStep(d);
}

export fn kotoba_bench_kernel_call(n: i64, _: i64, _: i64, _: i64, _: i64, _: i64, _: i64, _: i64) callconv(.c) i64 { return callSum(n); }
export fn kotoba_bench_kernel_call_branch(n: i64, _: i64, _: i64, _: i64, _: i64, _: i64, _: i64, _: i64) callconv(.c) i64 { return if (n == 0) 0 else callSum(n); }
export fn kotoba_bench_kernel_loop_call(n: i64, _: i64, _: i64, _: i64, _: i64, _: i64, _: i64, _: i64) callconv(.c) i64 {
    var i = n; var acc: i64 = 0;
    while (i != 0) : (i -= 1) acc += opaqueId(1);
    return acc;
}
