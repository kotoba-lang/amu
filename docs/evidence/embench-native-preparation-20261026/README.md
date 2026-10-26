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
These observations do not replace the separate process-trace gate.

Earlier preparation attempts refused malformed CLI order, source-locked
`static` output, a root exporting non-entry functions, and unsorted KSL1 file
records. Their raw outputs remain in the task's isolated observation storage.
The completed route uses the existing locked `kx64-v1` project linker and a
separate entry without editing or dropping the original workload's exports.

Still required: correctness at the registered full iteration counts,
independently checked benchmark/verify fuel and arena counters, runtime timing
instrumentation, same-host C comparator, complete ABBA/BAAB timing,
executable negative controls, and independent reruns. This one-body record
does not establish any of those results.
