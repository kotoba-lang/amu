# ADR-0405 -- macOS programs reach Metal through dyld and one boot function

- Status: **implemented, first slice** (JUN-819). One kernel on one host; no model runs on it yet.
- Date: 2026-11-04
- Owner decision, 2026-11-04: 「dyld で進める」, on the choice below.
- Amends: ADR 0375 step 5 (macOS route B).
- Evidence: `docs/evidence/macos-metal-20261104/`; gate `scripts/seed/check-macos-metal.py`.

## Context

ADR 0375 sends GPU execution through Amu selfhost and calls the macOS route "a Kotoba Mach-O loader for libSystem and
Metal.framework". Its decision 1 says the executor is not the system's dynamic loader.

Two facts decide the macOS route:

- `Metal.framework` has no image on disk (`Versions/A` holds only `Libraries`, `Resources`, `XPCServices` and
  `_CodeSignature`). Its code exists only in the dyld shared cache, whose format is private and whose code uses arm64e
  pointer authentication. A loader that maps Metal itself would depend on all of that.
- Every Amu Mac binary already starts through dyld (LC_LOAD_DYLINKER), then uses direct system calls.

The owner chose dyld over a shared-cache loader and over route W alone.

## Decision

1. **dyld resolves OS frameworks for an Amu-built Mach-O.** There is no C compiler, linker, C source or C loader on the
   path. The packager writes the load commands and the bind stream itself.
2. **A new packager profile, `amu-program-metal`.** It adds LC_LOAD_DYLIB for libSystem and LC_DYLD_INFO_ONLY, which binds
   one import, `dlsym`, at `__DATA + 16384`. `bin/amu compile FILE --runtime-profile amu-program-metal` selects it.
3. **Wire 42 returns one fn value.** In this profile, `(typed-cap-call :gpu/compute :string :string "")` returns a fn value
   whose code is `boot(op, a, b)`, and the program retypes it with `__r6-as`:

   | op | effect |
   | ---: | --- |
   | 0 | load the word at `a` |
   | 1 | store `b` at `a` |
   | 2 | store byte `b` at `a` |
   | 3 | call `a` with x0..x7 from the eight words at `b` |
   | 4 | the address of `__DATA + 16384`: the bound `dlsym`, then 16 KiB less one word for the program |

   These 38 words are the only new machine code. Each `boot` call is an ordinary closure call, which reloads the context
   register afterwards.
4. **Everything else is Kotoba.** `dlopen`, `objc_msgSend`, the device, queue, library, pipeline, buffers and dispatch are
   ordinary Kotoba in `seed/tests/macos-metal/q8_metal.kotoba.in`.

No module in `seed/MANIFEST` changes, so this needs no core re-adoption, and the CDCI pins do not move.

## What the profile grants

A program built with this profile has the whole authority of its process: arbitrary loads, stores and C calls. That is the
price of one small primitive, and why the profile is an explicit build choice:

- The default profile is unchanged. The same program traps at wire 42 there (gate row `ordinary`), and its image names no
  dylib.
- Images in the other modes are byte-identical to the previous packager's (`amu-program`, `amu-program-fs35`,
  `fs2-cli-stdio-general`, one program, 2026-11-04).
- This is not an end-user app route. An app under the workspace's client-runtime contract gets no access through it.
- It does not serve wire 42's text protocol (ADR 0371). That protocol stays the provider's; a Metal device layer under
  `tools/gpu_provider.kotoba` can later be written on this primitive.

## Result

The Q8_0 matvec of the inference roadmap (S0), integer fixed point, one thread per row. Rows are independent, so execution
order cannot change the answer.

- **Exact.** Metal equals the Kotoba CPU twin and the C twin at 4,864 rows, and equals the C twin at 77,824 rows. A kernel
  with one changed operator gives a different answer. A kernel Metal cannot compile prints the compiler's error and traps.
- **Speed, diagnostic only** (M1 Max, load average 19 to 24). See the evidence README for the table. One 4,864 x 896 product
  takes about 300 us against 2.42 ms CPU for the Kotoba scalar kernel and 1.40 ms for C. About 275 us of that is the floor of
  one command buffer (`commit` to `waitUntilCompleted`); above the floor, throughput is about 50 G MACs/s.

## Not covered

- The kernel is MSL text in a Kotoba string, not transpiled. ADR 0375 decision 2 wants KIR v2 as the source; the
  `tools/spirv_to_wgsl.kotoba` pattern (ADR 0379) is the likely route.
- No model, no tokens, no f16 scales (the bench kernel uses integer scales), no threads on the CPU side.
- One command buffer per dispatch. A decode step runs many kernels, so its cost depends on batching them, which is not
  measured here.
- The friendly spelling `(gpu/compute "")` is refused by `bin/amu compile` with `EABI` (`pj-qualified?`,
  `seed/60-proj.kotoba:1153`, reads a slash name as a module reference). `bin/amu check` accepts it. The program uses
  `typed-cap-call`.
- The gate runs on a Mac GPU host, outside mandatory CDCI, as ADR 0375 step 1 does for its GPU hosts.

## Consequences

- Metal's own compiler and driver run in the process, as a vendor driver does under route B on Linux. A failure is a named
  error or a trap, never a fallback.
- `dlsym` by name means an OS update that removes a symbol traps at startup, not at build time.
- macOS keeps two ways of reaching the OS in one image: direct system calls in the runtime and libSystem through `boot`.
