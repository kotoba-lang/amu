# Seed R0: fixed point and first Embench measurement (2026-10-02)

**Label: seed R0, a selfhost-built subset compiler. This is NOT an official Embench score.**
The seed is the Kotoba-written compiler in `seed/` (MANIFEST unity file, 4,840 lines). Stage-0 is `build/native-image/amu-native` (sha256 `d2cb84f6…`, JVM-built, BOOTSTRAP-REFERENCE). Stage-0 is used only to build seed-0 and is never in the seed's process tree.

## Result

| Gate | Result (measured on this host) |
| --- | --- |
| G4 fixed point | `seed-1.bin == seed-2.bin`, 187,186 bytes, sha256 `fe2c20aefa02f4f91f5b8394c8ad8a31e75325242050aaf7964b0eab73a39dd6`. seed-0 (stage-0-built) is 146,455 bytes. The seed writes each container itself (`compile --output`) and extracts `main` with its own `extract-native`. |
| G1 (ports) | 19/19 return 1 under the C loader and kexe-benchmark, for both seed-0 and seed-1. |
| G2 (corpus) | 63/66 are equal to stage-0 with both compilers. 3 are refused by the seed front end as before: 022 and 023 use `true`/`false`, and 060 uses an i64 `if` test. |
| G3/G4 containers | seed-0 and seed-1 give byte-identical containers on all 82 programs (19 ports + 63 corpus). |
| G5 no host processes | `scripts/seed/no-host-processes.sh` ran 60 packaged-seed commands: the self-compile, extract and check, plus check/compile/extract for all 19 ports. It logged **0** exec/posix_spawn/system/popen calls. There were 60 forks, one per command: that is the loader's own supervisor fork, and no exec follows it. The command has an empty PATH. `otool -L` shows only libSystem. Wire 20 (spawn) is not granted. The self-compiled `main` equals seed-1.bin. |
| Embench (19 ports) | All 19 correctness exports return 1. The compiler under test is the packaged seed-1 (`build/seed/seed`, a KEXE_EMBEDDED build of `tools/kexe_loader.c` + seed-1.bin). |

### How G5 was measured

`scripts/selfhost-wall/no-host-processes.sh` needs dtruss, which needs sudo, and SIP is enabled on this host. So the new script uses a dyld `__interpose` library (execve/execv*/posix_spawn*/fork/vfork/system/popen) instead. It fails closed:

- A canary built with cc must be caught (posix_spawn, fork, execve: 3 calls were caught).
- Every seed process must log that the interposer loaded (60/60 did).

## Embench measurement

The runner is `bench/embench/run_native_qualification.py`, run unchanged with its defaults: 5 check samples, 5 compile samples and 5 executions per port, medians reported.

- **Seed evidence:** `bench/embench/evidence-seed-r0/` (`qualification.json`, `summary.csv`, `seed-provenance.json`, `seed-package.info`, per-port artifacts).
- **Same-host stage-0 comparison:** `evidence-seed-r0/stage0-same-host/`. This is the same runner on the same host with `SEED_COMPILER=amu-native`.

### Host and load

- Apple M1 Max, 10 cores, 32 GB, macOS 26.4.
- The host was **loaded**: 1-minute load average 45.0 at the start and 46.5 at the end of the seed run, and 51.3 / 49.9 for the stage-0 run.
- The 2026-09-29 numbers (REPORT-20260929.md) come from a different host (MacBook Air, M4) that was not reported as loaded. Execution times across hosts are therefore not comparable, so the same-host stage-0 column is the fair reference.

### Upstream commit

This host has no embench-iot checkout, and none was downloaded. `scripts/seed/embench_declared_upstream.py` answers only the runner's `git rev-parse HEAD` of the upstream. It returns the commit declared by the 2026-09-29 run, `09c2ed8c…`, and the string itself says "declared … not re-verified". The runner reads nothing else from the checkout, because the ports are the repo's own `bench/embench/ports` (identical to amu-embench's).

### Medians per port

Compile and check include process startup.

| Workload | Fidelity | Correct (seed / stage-0 / 09-29) | Compile ms seed / stage-0 / 09-29 | Execute seed / stage-0 / 09-29 | Raw code bytes seed / stage-0 / 09-29 |
| --- | --- | --- | ---: | ---: | ---: |
| aha-mont64 | full | 1 / 1 / 1 | 18.2 / 154.0 / 104.5 | 15 µs / 11 µs / 7 µs | 3,532 / 3,240 / 3,240 |
| crc32 | full | 1 / 1 / 1 | 18.3 / 576.2 / 388.9 | 33 µs / 42 µs / 29 µs | 4,248 / 17,796 / 17,796 |
| depthconv | full | 1 / 1 / 1 | 17.7 / 467.3 / 300.2 | 42 µs / 42 µs / 29 µs | 2,648 / 4,996 / 4,996 |
| edn | adapted | 1 / 1 / 1 | 18.2 / 127.9 / 83.6 | 63 µs / 64 µs / 45 µs | 1,432 / 1,940 / 1,940 |
| huffbench | adapted | 1 / 1 / 1 | 18.7 / 75.0 / 48.4 | 8 µs / 9 µs / 5 µs | 840 / 564 / 564 |
| matmult-int | full | 1 / 1 / 1 | 18.5 / 955.5 / 657.9 | 76 µs / 49 µs / 32 µs | 7,160 / 29,864 / 29,864 |
| md5sum | full | 1 / 1 / 1 | 19.3 / 246.1 / 161.7 | 46 µs / 27 µs / 19 µs | 8,488 / 8,604 / 8,604 |
| nettle-aes | adapted | 1 / 1 / 1 | 18.5 / 130.1 / 84.7 | 15 µs / 13 µs / 8 µs | 2,264 / 1,684 / 1,684 |
| nettle-sha256 | full | 1 / 1 / 1 | 19.4 / 272.0 / 199.8 | 23 µs / 18 µs / 12 µs | 9,516 / 9,948 / 9,948 |
| nsichneu | adapted | 1 / 1 / 1 | 20.6 / 85.1 / 57.6 | 33 µs / 17 µs / 10 µs | 792 / 524 / 524 |
| picojpeg | adapted | 1 / 1 / 1 | 21.0 / 83.5 / 50.8 | 11 µs / 8 µs / 5 µs | 1,012 / 652 / 652 |
| qrduino | adapted | 1 / 1 / 1 | 20.6 / 109.0 / 68.0 | 10 µs / 10 µs / 4 µs | 968 / 1,612 / 1,612 |
| sglib-combined | adapted | 1 / 1 / 1 | 20.2 / 97.8 / 61.7 | 36 µs / 21 µs / 13 µs | 1,604 / 1,600 / 1,600 |
| slre | adapted | 1 / 1 / 1 | 19.7 / 93.4 / 59.9 | 11 µs / 9 µs / 4 µs | 1,333 / 1,336 / 1,336 |
| statemate | adapted | 1 / 1 / 1 | 20.1 / 71.5 / 44.7 | 10 µs / 9 µs / 5 µs | 652 / 448 / 448 |
| tarfind | full | 1 / 1 / 1 | 21.2 / 125.6 / 78.3 | 50 µs / 33 µs / 20 µs | 1,928 / 1,800 / 1,800 |
| ud | full | 1 / 1 / 1 | 20.7 / 281.5 / 192.5 | 16 µs / 15 µs / 9 µs | 5,692 / 6,596 / 6,596 |
| wikisort | adapted | 1 / 1 / 1 | 19.6 / 177.9 / 120.1 | 1556 µs / 823 µs / 482 µs | 3,592 / 3,312 / 3,312 |
| xgboost | full | 1 / 1 / 1 | 25.1 / 292.9 / 202.2 | 2.439 s / 2.390 s / 1.894 s | 56,732 / 55,960 / 55,960 |
| **sum** | | 19 / 19 / 19 | 376 / 4423 / 2965 | | 114,433 / 152,476 / 152,476 |

### Comparison

**Correctness:** all 19 return 1 with the seed, as with stage-0 and on 2026-09-29.

**Compile time:**
- The seed's compile median is 17.7–25.1 ms per port, 376 ms summed over the 19 ports.
- Stage-0 on the same host takes 4,423 ms summed, and the 2026-09-29 run took 2,965 ms on the M4.
- The seed is 4–52× faster per port than same-host stage-0.
- The seed's check median is 17.7–22.0 ms, against 12.7–49.9 ms on 2026-09-29.

**Raw code bytes:**
- The seed totals 114,433 and stage-0 152,476. Stage-0's per-port sizes are identical to 2026-09-29, so its code generation did not change.
- The seed is smaller on crc32 (0.24×), matmult-int (0.24×), depthconv, edn, qrduino and ud.
- The seed is larger on the small adapted probes (huffbench, nsichneu, picojpeg, statemate: about 1.5×) and on aha-mont64, nettle-aes, tarfind and wikisort.
- The two figures are defined differently. The seed's extract writes the whole code plus literal pool. Stage-0's figure is the prefix up to the selected export.

**Execution time (same host, medians of 5):**
- The geometric mean of seed / stage-0 is 1.25×, ranging from 0.79× (crc32) to 1.94× (nsichneu). wikisort is 1.89× and xgboost 1.02× (2.439 s vs 2.390 s).
- The seed has no optimizer: stack SIR, every temp in the frame, fuel checks on entry. That this gap is not larger is the measured finding.
- Against the M4 numbers of 2026-09-29 the ratios are 1.1–3.3×, but that mixes host, load and compiler differences.

## Changes that made this possible (commit 3d2c7e963)

- **Binary output.** The seed now writes binary files. `02-io` has `io-write-bytes` (merged from the snippet now that stage-0 admits a computed `:bytes` argument) and the new `io-read-bytes`.
- **New contract entries.** Keyword `:fs/app-data-bytes` (12) and head `vector-i64-from-bytes` (42), added to HEADS, 20-names, 21-check, 30-lower and ck_ref.py.
- **New commands.** `90-drv` adds `compile … --output <file>` and `extract-native`. `50-out` adds `out-load`.
- **Loader token defect.** A defect found on the way: the loader's wire 35 searches the whole request, content included, for its tokens, and refuses a write whose content contains `WRITE_SEP`. The seed's literal pool is part of every container it writes, so seed-0 trapped (SIGILL) writing seed-1. All wire-35 tokens are now built at run time (`io-sep`).
- **Build route.** `build.sh` uses the binary route by default. Nothing is decoded with xxd, and no extraction is done in shell.

## Tests run

- **Unit tests:** `unit.sh` passes for 00-ns, 01-mem, 02-io, 10-lex, 11-read, 30-lower, 41-a64gen, 42-layout, 50-out and 90-drv.
- **io_bytes_check:** 4/4 (n = 0, 1, 256, 100000).
- **ck-gate:**
  - Spellings: 74/74.
  - The new cases `ok-01-forms` (`:fs/app-data-bytes`, `vector-i64-from-bytes`) and `err-2115-bytes-old-wire` behave as intended.
  - The reference model agrees on 243/244. The one difference is the display of a non-ASCII byte in `conf/values/string_symbol`, which predates this work.
  - The gate still reports FAIL for the 3 known corpus refusals and because there is no golden file yet.
- **Gates:** `g4.sh` (G1+G2+G4) and `no-host-processes.sh` (G5) pass.

## Open risks

- **Not a quiet-host measurement.** Load was about 45–51. Rerun `SEED_ALLOW_LOADED= scripts/seed/embench.sh` on a quiet host before quoting times. Without that variable the script refuses to run above load 4.
- **Upstream commit not verified.** It is declared, not re-verified. Rerun with `EMBENCH_UPSTREAM=<embench-iot checkout>` to record a verified commit.
- **G5 is user-space interposition.** It is not a kernel trace: a static binary or raw syscall would evade it. The seed is dynamically linked, and the guest has no spawn grant. dtruss/eslogger need root.
- **extract-native has no length check.** It reads the container length from its own header, because Seed-0 has no `vector-count`. A non-container input can trap (non-zero exit) instead of reporting E5003.
- **Programs containing a wire-35 token cannot be written to a file.** Any compiled program whose string literals contain a wire-35 token (e.g. `"WRITE_SEP"`) cannot be written with `--output`; the loader traps. Hex output (`-`) still works.
- **Corpus programs 022, 023 and 060** remain outside Seed-0. They belong in `neg/`, or Seed-0 needs boolean literals.
