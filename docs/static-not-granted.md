# An ungranted wire is refused by name in the static runtimes (JUN-354)

A static image may call a capability wire that `KEXE_ALLOW` does not grant.
The runtime then stops it as before, but it now says which wire it refused:

```text
KEXE_CAP {:wire 41 :refused :not-granted}
KEXE_TRAP {:kind :signal :signal :SIGILL}
```

The change is in `kxrt-typed-cap-call` of `seed/76-x86_64-static-rt.kotoba`
and `seed/77-aarch64-static-rt.kotoba`. Its first branch, `(not
(kxrt-admitted? id))`, called `kxrt-fail`, the generic trap that every
runtime refusal shares, so the stderr of an ungranted wire was the same as
for any other refusal. It now calls `kxrt-not-granted`, which:
1. flushes stdout;
2. writes the `KEXE_CAP` line;
3. takes the same trap: SIGILL, exit 120, and the structured report when
   `KEXE_STRUCTURED_REPORT` is set.

Only the line is new. The exit code, the trap and the report stay the same,
so a caller that matched them still does.

- **One shape for both hosts.** The line is the one the wasm32-browser
  runtime (`seed/82`, `kxrt-cap-refused`) writes for a wire that its host does
  not provide: `KEXE_CAP {:wire 41 :refused :wasm32-browser}`. The two runtimes
  differ only in the reason.
- **No change to what is refused.** Other refusals of a granted wire, such as
  a malformed request, a request over a bound or an answer that is not
  UTF-8, still take the trap without the line.
- **Not shared with seed/82.** `kxrt-not-granted` sits next to
  `kxrt-typed-cap-call`, outside the sections that seed/82 copies from seed/77.
  The wasm runtime keeps its own refusal.
- **The string table.** The two runtimes are string literals of the
  compiler, so the new function has no double quote in it, comments included.

## Verification

Measured on 2026-10-23, and again on 2026-10-24 after the rebase onto main
6deb9969 (after #1510, #1539 and #1548), on arm64 Linux in the podman machine
(Fedora CoreOS, rootless podman, the arm64 Python image `255f49222a74`). No C compiler or loader and no hosted compiler were used.
Only the x86_64 run under "Both targets" is emulated (qemu-user). Receipts are in
[`evidence/static-not-granted-20261023/`](evidence/static-not-granted-20261023/).

- **The root** (`root-chain.json`).
  1. The previous root (`c95b8441…`, main at 6deb9969) compiled
     `seed/FULL-MANIFEST` from this source to F1 and packed it.
  2. F1 rebuilt itself to F2. The container is the same (F1.kseed = F2.kseed);
     the runtime wrapper is new, because the previous runtime packed F1.
  3. F2 rebuilt itself to F3 = F2. F2 is the pinned root, `f70486914…`
     (`seed/bootstrap/aarch64-linux-static-root.json`). Before the rebase
     the same change gave `2cedcaea…` from main 3c2207f4's root.
- **`selfhost-bootstrap.py --tier pr`** (`selfhost-bootstrap-pr.json`) and
  **`--tier main`** (`selfhost-bootstrap-main.json`) pass from the new root:
  - the root reproduces the adoption image;
  - the 24 runtime cases pass, and so does the wasm32-browser compile;
  - the capability step's ungranted wire 3 now writes
    `KEXE_CAP {:wire 3 :refused :not-granted}` before the trap.
- **`check-one-compiler.py`** (`one-compiler.json`) passes from the new
  root: the combined compiler's fixed point, the core route, the 24 cases on
  both compilers, and its x86_64 compiler and CDCI images.
  - Re-pinned with it:
    - the Amu selfhost gate (`seed/cdci/policy.json`), which is the core
      compiled with seed/76's runtime: `e6dcf618…` to `63701105…`;
    - the complete24 gate fixture (`seed/cdci/kotoba-gate.kotoba`). Every
      case image embeds the runtime, so all 24 x86_64 image pins change; the
      compiler's role pin for that source (`seed/79-native-cdci.kotoba`) and
      the policy follow: the Kotoba native gate image `39fac666…` to
      `528d3d35…`, its source `e4097e7c…` to `98c1fc51…`;
    - `bin/amu` (`native-product.json`, `seed/compiler-core.json`,
      [native public entry](native-public-entry.md)), which is the complete
      x86_64 compiler: `23e714db…` to `68f1f3db…`. Its qualification flags
      are pending until the exact-head CI receipt is recorded.
  - The controller is unchanged. Main's compiler reproduces all 24 old gate
    pins, and this one the 24 new ones.
- **The runtime checks with the new root.**
  - `check-io-read.py` passes its 12 cases (`io-read.json`). `wire-not-granted`
    writes the wire 41 line. `malformed-request`, a granted wire's bad request,
    does not write it.
  - `check-durable-sleep.py` passes its 9 cases (`durable-sleep.json`), with the
    wire 7 line.
  - `check-spawn-runtime.py` passes its 18 grant cases and 31 wire cases
    (`spawn-runtime.json`), with the wire 20 line.
  - `check-static-launcher.py` passes: 30 receipt cases, 14 runs, 15 refusals
    (`static-launcher.json`).
- **Both targets** (`targets.json`). A guest writes `before|` on wire 37 and
  then reads wire 41. With `KEXE_ALLOW=37` it exits 120 after
  `before|`, the `KEXE_CAP` line and the trap, on aarch64-linux and on
  x86_64-linux. With `37,41` it reads 3 bytes and exits 0.
  - x86_64 ran under qemu-user without its seccomp filter.
  - **Negative control.** The same guest built by the previous root traps with
    no `KEXE_CAP` line, on both targets.

## What stays open

- **x86_64.** seed/76 has the same change. Here it ran only under
  qemu-user. `check-native-clock-entropy.py` now requires the line for its
  two no-grant cases (wires 7 and 23), so the selfhost-native CI's x86_64 job
  checks it on a native x86_64 kernel.
- **Native x86_64 and CI.** CI run 40082886869, on the head before the gate
  fixture was regenerated, ran on a native x86_64 kernel: the complete
  compiler's fixed point (F1=F2=F3 = that head's `bin/amu`, cross-built here)
  and the clock check, whose no-grant cases require the named line, passed;
  its controller step stopped at the stale gate pins (`CDCI:E4002`). The
  exact-head CI qualifies the final `bin/amu`, controller and aliases.
