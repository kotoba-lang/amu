# Native Embench preparation: 26 October 2026

This record is preparation for KOTOBA-140. It contains no timing score.

`one-body/native-build.json` and `one-body/raw/` record actual execution on
Linux x86_64 using the public compiler pinned by `native-product.json` at
repository base `57d18c983c449979cf92e592fb24167f26ed09cb`.

* The complete 47-module compiler rebuilt itself twice. F1=F2=F3 has SHA-256
  `881c26ff74ec67cb0e6a1885bd185f203657c33bbb5e3cc43c1e5f141fe80292`.
* That same compiler built the checked-in native KX64 runner and all 19
  source-locked workload projects.
* Each original workload library was copied byte-for-byte, retaining every
  declaration and export. A separate canonical entry imported `bench-verify`.
* All 19 `bench-verify 1` executions returned the native result 1 with exit 0
  and empty stderr. No workload was omitted.
* The record includes all 41 process calls and the digests of all 82 raw logs.
  The download archive SHA-256 was
  `f98951adb77be972e7e3ce45341d7926c3e052c6425c74dae6e4562fb814c274`.

Child process `PATH` was `/nonexistent`. The compiler received only its
declared source/output grants; workload grants were empty. ELF inspection
found no dynamic segment or interpreter in the native compiler and runner.
The first run did not include a process trace; the separately traced run below
adds that observation for the one-body preparation closure.

The generated compiler and workload artifacts were also downloaded into the
task's retained artifact storage. Byte-level readback confirmed both F2/F3
compiler images, the native runner, source unity, all19 KX64 containers and
all19 payloads against the manifest. Artifact archive SHA-256:
`73b25442c0fb9dabd847d3c64a4aeb25d444fb648127ba993baed66699d03548`.

## Full-count diagnostic result

`full-counts/native-build.json` and its `raw/` logs retain the separate terminal
M104-count probe. All19 source-locked projects compiled. None completed under
the fixed diagnostic execution profile (30-second wall limit, 1e12 fuel).

| Observation | Workloads |
| --- | --- |
| Native `vector-table-exhausted` / `budget/cells :arena :vectors` | `aha-mont64` |
| Native `SIGALRM` at the diagnostic wall bound | other18 |

The runtime declares `KXRT-VECTORS=4194304` in
`seed/76-x86_64-static-rt.kotoba`. The historical M104 accounting at the same
aha-mont64 count recorded 50,266,113 vectors. That is a concrete native
capacity mismatch to resolve with reviewed lifetime/accounting semantics.
The wall-bound observations establish only that those probes did not complete
within the declared diagnostic limit; they are not incorrect-output findings
and supply no relative C speed measurement. No timing aggregate is reported.

All original source bytes and registered iteration counts are retained. The
full-count record archive SHA-256 is
`ae9c7b4555e6f43fa6e14d456cc48dd8df2b343592c321d936f4a4135d419863`.
The compiler/runtime qualification work is tracked in KOTOBA-144, a blocker
of the repeated measurement task KOTOBA-140.

## Observed execution closure

`traced/execution-closure.trace` covers a fresh complete native preparation
run, including selfbuild and all19 one-body probes. `strace -f` recorded both
`execve` and `execveat`. The 42 observed executions are exactly Python for
staging/observation, the pinned native compiler and its F2/F3 generations,
and the Amu-built native workload runner. There are no other executable
paths or `execveat` calls. All19 probes again returned result1 and exit0.

The trace contains syscall-observation infrastructure, including Python and
strace, outside the compiler/workload execution closure. It does not describe
a C-free implementation of those host tools, a timing campaign, or all seven
required benchmark negative controls. The traced record archive SHA-256 is
`da49283d0d19f73da4789721e5dcafa1acc7a49c3e3eb9ca7a7e44981c435ff8`.

Frozen `.source.txt` files retain the exact observation script versions named
by each manifest's `preparationScript` digest. They are non-executable evidence;
the maintained tool remains `bench/embench/proof-v1/native_build.py`.

Check all retained records, raw hashes, counts and trace paths offline:

```sh
python3 bench/embench/proof-v1/verify_native_records.py
```

This verifies observation consistency and reports performance as unqualified.

Earlier preparation attempts refused malformed CLI order, source-locked
`static` output, a root exporting non-entry functions, and unsorted KSL1 file
records. Their raw outputs remain in the task's isolated observation storage.
The completed route uses the existing locked `kx64-v1` project linker and a
separate entry without editing or dropping the original workload's exports.

Still required: resolve the full-count refusals and qualify correctness,
independently checked benchmark/verify fuel and arena counters, runtime timing
instrumentation, same-host C comparator, complete ABBA/BAAB timing,
executable negative controls, and independent reruns. This one-body record
does not establish any of those results.
