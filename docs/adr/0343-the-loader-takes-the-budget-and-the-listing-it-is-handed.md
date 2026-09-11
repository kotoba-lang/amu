# ADR-0343: The loader takes the budget and the listing it is handed

- Status: accepted
- Date: 2026-09-07
- Relates: superproject `ADR-2609051100` (kbb native backend), `ADR-2609062200`
  (kbb js backend oracle), superproject CLAUDE.md "kbb-first" (owner,
  2026-09-07), kotoba-lang/artifact `runtime_identity.cljc` (loader identity
  `147b0344fabaedc9cc9740f7ab87a785344f6b074a39ebca69ac8f256433a3a0`)

## Context

The owner's rule for operational tooling is kbb-first: new ops scripts are
written for `bin/kbb`, and what kbb lacks is added on the kbb side, never by
shrinking the guest. An agent (E14, 2026-09-07) tried to port one nbb
detector to kbb and stopped at three measured walls in the NATIVE backend --
the KEXE loader this repository owns -- with receipts committed in aiueos
`os/aiueos/tools/kbb-probes/` and `kbb-migration-gaps.edn`:

1. **Fuel was a compile-time constant.** `shared->context.fuel = 512`, printed
   as `:initial 512` by every structured report. A byte-walk of a 14,789-byte
   source trapped SIGTRAP at 512 steps; kotoba's shim refused `--fuel` on
   native by name because accepting it would have been a knob that did
   nothing.
2. **Wire id 34 (`:fs/browse`) was the identity stub.** The shim refused
   `--backend native` for any script granting it (exit 3, "does not host
   [:fs/browse]"); the js host answered 11 entries for the same directory.
3. **A file larger than one guest string could not be read at all.** The
   whole-file read form interns the whole file (65,536-byte pool); the corpus
   has an 83,691-byte source. Every top-level form in it fits one string, so a
   bounded window suffices and the whole file does not.

The loader is decision-free mechanism C under a SHA-256 review pin. Each of
the three is a number or a list the loader can *enforce* without *deciding*
anything: the budget, the scope, the window.

## Decision

Three changes to `tools/kexe_loader.c`, each its own commit, each measured
RED on the base loader and GREEN after on identical guest bytes, each with a
JVM-free check in `scripts/jdk-free-native-conformance.cljk` (the JVM suite
cannot run until the artifact identity pin moves; this gate can).

**KEXE_FUEL.** The loader reads a positive decimal budget from `KEXE_FUEL`
(absent = 512) and enforces it; the report prints the budget that was in
force (`:fuel {:initial N :remaining M}`), so a report that still says 512
means the knob did nothing. Zero, negative and non-decimal values are refused
with exit 2 before the guest starts. RLIMIT_CPU and the supervisor alarm are
unchanged -- fuel bounds the guest's steps, the rlimits bound the child.

**Wire id 34.** `fs_browse_provider`: one absolute directory inside
`KEXE_CAP_RESOURCES_34` (same colon-separated, parent-realpath'ed form as the
wire-35 scope) answers its entry names sorted bytewise and newline-joined,
`.` and `..` excluded, the empty string for an empty directory -- the shape
kotoba's js host answers. `O_DIRECTORY|O_NOFOLLOW`, contained like a file,
bounded at 4096 names and the string pool, refused rather than truncated.
Seatbelt grants `file-read*` (subpath) per entry; seccomp admits
`getdents64` only when that scope is set. On Linux the listing is read with
the raw `getdents64` syscall rather than libc's `DIR`: measured with strace on
glibc 2.39, `fdopendir` issues `fcntl(F_GETFL)` and then
`fcntl(F_SETFD, FD_CLOEXEC)`, and the second one trips the filter (`SIGSYS`);
admitting `fcntl` for that is more surface than parsing the records the
kernel already returns. macOS keeps `fdopendir`/`readdir` (Seatbelt filters
paths, not syscalls). The scope code the two wire-35
providers each carried is one `struct kexe_scope` with init / admit /
contains-fd helpers.

**Range form.** `<path>RANGE_SEP<offset>:<length>` on wire id 35 answers
exactly that window: the window must lie inside the file (no short read is
ever answered), `length` must fit the pool, the token must occur once, and
the result passes the typed dispatch's UTF-8 check like every string result,
so a window that cuts a code point traps. `WRITE_SEP` is tested first, so
written content may contain `RANGE_SEP`.

## Measured

- Fuel, identical guest bytes (E14's `nl_count` over a 1,800-byte ASCII file,
  37 newlines): base loader `{:status :trap :exit 120 :fuel {:initial 512
  :remaining 0}}` with `KEXE_FUEL=100000000` ignored; this loader `{:status
  :ok :result 37 :fuel {:initial 100000000 :remaining 99998196}}`; the js
  backend answers 37.
- Browse, a `:string` main calling `typed-cap-call :fs/browse` over
  `os/aiueos/native`: base loader `:result 90` (the stub echoing the 90-byte
  request path); this loader the 231-byte listing, equal to the js host's 231
  and to `ls -A | sort`. No scope, a scope elsewhere, an allow list without
  34, a regular file: SIGILL. Empty directory: `""`.
- Range, `tcp_stream.kotoba` (83,691 bytes) through kotoba's `kbb.fs`
  (`read-range` -> `write-file` -> `cmp` against `dd`): `[0, 4096)` and
  `[80000, +3691)` byte-identical on native and js. Past EOF and a window
  cutting U+2500: js refused by name, native SIGILL. Whole-file read: still
  refused on both.
- The conformance gate, run with the base loader source swapped in, fails by
  name at the first new check (`KEXE_FUEL=100000 was not the budget in force
  ... :initial 512`), and passes on each of the three commits.
- ASan/UBSan build clean; `tools/kexe_parser_fuzz.c` still includes the
  source. Linux (x86_64, gcc 13.3, glibc 2.39, a tailnet host): gcc
  `-Werror` clean, the listing byte-exact, the three refusals SIGILL, the
  wire-35 read and range reads and the fuel report unchanged, the
  filesystem/network/process probes still `SIGSYS`. The PR's Ubuntu checks
  caught two things first: a GCC `-Wunused-parameter` clang never saw, and
  the `fdopendir` `fcntl` above -- both measured on that host, not guessed.

## What this does not land, measured

- **The next wall behind fuel is the pair arena.** E14's byte walk spends two
  pair handles per byte (the substring view and the `"\n"` literal), so a
  2,609-byte file exhausts the 4096 handles: `:heap {:capacity 4096 :used
  4096}` -> SIGILL. Raising that bound is a separate decision with its own
  fail-closed argument (artifact `runtime_identity.cljc` says so) and is not
  made here. kotoba's `bin/kbb` receipt now carries `:kotoba.kbb/fuel`.
- **`lib/kbb/browse.kotoba` still cannot compile for native.** Its
  `count-separators` uses `string-index-of`, which the native backend does
  not lower (`aggregate ABI rejected: call-abi-not-admitted`, kotoba-native
  `reject-unextracted-call!`); `string-split-count` is refused too. So E14's
  `browse_count` probe now fails one layer later, at the compiler, and
  kotoba's shim keeps `:auto` routing `:fs/browse` scripts to js while
  honouring an explicit `--backend native`. A UTF-8-safe newline count is not
  expressible in the guest without one of those two ops; the fix is in the
  native backend, not the loader.
- **E14's gap "byte-step trips the code-point boundary" is mis-attributed.**
  On the js backend the walk fails on pure-ASCII files too, from about 3,000
  bytes: kotoba-script's `stringSubstring` wraps `TextDecoder` in a catch-all
  that relabels *any* exception -- here the JavaScript call stack overflowing
  under the guest's self-recursion -- as `string-substring-code-point-
  boundary`. The 14,789-byte walk never reached the U+2500.
- The Windows loader has no filesystem providers at all and is untouched.

## Consequences

- `kotoba-lang/artifact` PR #23 (merged) carried the first identity; the
  Linux `-Wunused-parameter` fix moved it once more (see the follow-up PR
  named in the amu PR). amu's `deps.edn` pin on `io.github.kotoba-lang/artifact` must
  move to that commit with this loader, or `kototama.native.executor/
  build-runtime!` refuses the source before any guest starts. That pin is
  deliberately not moved on this branch (another agent owns deps.edn today);
  until it moves, the JVM `test` check on the PR is red for that reason and no
  other.
- kotoba's `bin/kbb_shim.cljs` passes `--fuel` through as `KEXE_FUEL`,
  registers `:fs/browse` as native-hosted with `KEXE_CAP_RESOURCES_34`, and
  `lib/kbb/fs.kotoba` gains `read-range` / `read-range-spec` / `i64->text`
  (kotoba PR, same day).
