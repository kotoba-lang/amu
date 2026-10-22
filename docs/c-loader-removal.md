# C loader removal (2026-10-22)

Owner decision 2026-10-22: remove the C loader; compile, build and run only
through Amu selfhost. This record is the scoreboard entry for everything the
removal made unreachable (AGENTS.md: unreachable files stay on the
scoreboard as refused, with the reason).

## What replaces it

* **Build and rebuild.** `scripts/seed/selfhost-bootstrap.py` starts from
  the pinned Amu-produced root `seed/bootstrap/aarch64-linux-static-root.elf`
  and runs on arm64 Linux with no C compiler or loader. It covers:
  * S1 = S2 = S3 = root;
  * runners and the x86_64 compiler;
  * the pinned adopted AArch64 compiler, rebuilt to its adoption fixed point
    through the C-free runner;
  * the runtime cases;
  * seccomp and the resource limits.

  Receipt: `docs/evidence/selfhost-bootstrap-aarch64-20261022/`.
* **Executing a program.** Compile it to a loaderless image:
  `compile SOURCE --target aarch64-linux|x86_64-linux --output NEW --format static`.
  The image carries its own Kotoba runtime (`seed/76`, `seed/77`):
  * context ABI v11;
  * wires 35, 37, 38 and 39;
  * seccomp and rlimits.
* **Executing a KX64V1 / adopted AArch64 payload.** Use the C-free runner
  (`--format kx64-runner` or `--format runner`). It takes the old loader's
  command line.

## Removed

| path | what it was |
|---|---|
| `seed/bootstrap/adopted-loader-20261012.c`, `adopted-parser-fuzz-20261012.c`, `tools/seed-x86_64-linux-loader.c` | seed bootstrap loader (amu #1459; see `scripts/seed/RETIRED.md`) |
| `tools/kexe_loader.c`, `tools/kexe_loader.classification.edn`, `tools/kexe_parser_fuzz.c` | product loader (context ABI v12) built by kotoba-native's executor from `--loader-source-dir` |
| `tools/kexe_loader_windows.c` | Windows loader |
| `tools/kexe_gpu_vulkan.c`, `tools/kexe_gpu_metal.m`, `tools/test_kexe_gpu_metal.m` | GPU brokers of the loader |
| `runtime/ios/` | C host linked with `package-ios` / `package-macos` objects |
| `test/kotoba/compiler/{kexe_loader_forms,loader_source_classpath,string_simd_loader}_test.cljk` | tests of the loader source itself |
| `scripts/{fuzz-native,sanitizer,test-fuel-differential,test-loader-file-scope,test-loader-http-scope,test-net-broker,windows-loader-cross-compile,windows-profile-conformance,ios-aot-conformance,ios-simulator-conformance}.cljk`, `scripts/test-gpu-*.cljk`, `scripts/gpu-subgroup-reduce-chunksweep-pinned-3696ca0d.cljk` | scripts that built or exercised the removed C sources |

`tools/kexe_loader_decisions.kotoba`, `_names.kotoba` and `_boundary.kotoba`
stay. They are Kotoba sources: the linux-static packaging, the capability
catalog and the runner models cite them.

## Refused (kept, not runnable until ported)

`bin/amu` refuses these by name with exit 2 and the reason. `bin/kotoba`
delegates to it.

* `run`
* `measure-runtime`
* `package-ios`
* `package-macos`
* `test --native-prepare`, `test --native-runtime` and `test --loader-source-dir`

The `:gpu/compute` capability (wire 42) is refused as well. Its only provider
was the GPU broker inside the loader. The checker refuses it (E2115) and the
static runtime has no provider for it. ADR 0371 proposes the replacement route.

These still exist but executed programs through kotoba-native's loader
executor. They now fail when it tries to build the removed source, and stay
here until they are ported onto static images:

* scripts:
  * `conformance.cljk`
  * `jdk-free-native-conformance.cljk`
  * `package-command.cljk` and `test-package-command.cljk`
  * `test-execution-v2-{native,native-providers,providers,targets}.cljk`
  * `test-nbb-run.cljk`
  * `dual-backend-equivalence.cljk --with-native`
* JVM tests:
  * `clock_native_kexe_oracle`
  * `dataspace_native_aot`
  * `f32_native_execution`
  * `isa_execution`
  * `native_allocation_budget`
  * `native_executor`
  * `native_hiccup_node`
  * `stored_closure`
  * `ui_native_aot`
* nbb tests:
  * `test/nbb/native_word_ops.cljk`
  * `test/nbb/state_ability.cljk`
* `src/kotoba/compiler/limits.cljk` still names `tools/kexe_loader*.c` as the
  historical authority of some limits. The values remain; the files do not.

Note: on 2026-10-22, before this change, `run-tests.cljk` already stopped
at load time on main (`Could not find namespace:
kotoba.compiler.accelerator-targets-test`). That legacy suite therefore gave no
regression baseline for this removal.
