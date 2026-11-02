# Mac runtime: legacy wire-35 text requests (JUN-593)

`seed/macos-fs2-runtime-packager.kotoba` now gives the `fs2-cli-stdio-general`
mode a wire-35 helper for the Linux `kxrt-fs` text grammar that
`kotoba.hata` (`store_io`) sends. Before this, those requests reached the FS2
chain, which accepts only `NUL FS2 NUL` frames, and trapped.

`fs35.derivation.s` is the one-time derivation of the 442 words emitted by
`fs35-helper-words`; it is review evidence, not a build input. Two words are
patched by the packager: word 33 (`bl` to the bounded string-span resolver) and
word 439 (`b` to the existing chain entry).

## Grammar and answers

| request | answer |
|---|---|
| `<path>` | the file's bytes; trap if it cannot be opened or read |
| `<path>EXISTS_SEP` | `"1"` / `"0"` |
| `<path>WRITE_SEP<data>` | create/truncate and write all; answers `<data>`; trap on failure |
| `<path>FSYNC_SEP` | `"1"` / `"0"` (files and directories) |
| `<from>RENAME_SEP<to>` | `"1"` / `"0"` |
| `<path>FLOCK_SEP` | `"1"` / `"0"`; one nonblocking exclusive lock per process, released by death |
| `<path>UNLOCK_SEP` | `"1"` / `"0"`; only the held lock's path |

Any other `*_SEP` token (APPEND, RANGE, STAT, ...) or trailing bytes after a
terminal token trap. Requests that are not wire 35, not string->string,
ungranted, or start with NUL go unchanged to the FS2 chain (so the compiler's
own FS2 frames and KSL1 source locks are untouched).

## Scope

A path is `/c1/c2/...` beneath FD 3: every component non-empty, not `.` or
`..`, no NUL, at most 1023 bytes. Opens use `openat(3, ...)` with
`O_NOFOLLOW_ANY | O_RESOLVE_BENEATH | O_CLOEXEC`; rename uses
`renameatx_np(3, from, 3, to, RENAME_NOFOLLOW_ANY)`. This is stricter than the
Linux runtime, which normalizes `..` inside its granted roots; here `..` is
refused. Lock state lives at ctx+13312 (fd+1), +13320 (path length) and
+13328 (path bytes).

## Evidence (Apple M1 Max, 2026-10-29)

`scripts/seed/check-macos-fs35.py` (staged packager rebuilt from this source):
`PASS_MACOS_FS35`. Four answer cases (round trip, durable replace with file and
directory fsync, lock/unlock, path refusals including `..`, `.`, empty
components, relative paths and a symlink planted to point out of the scope),
five trap cases, a cross-process lock (a second process is refused; process
death releases), and the file outside the scope unchanged in every case. The
negative control is the same program packaged by a packager whose general mode
does not branch to the helper: it traps.

With this runtime, `kotoba.hata`'s quorum test and broker driver run on the
Mac (`prepare` 1, `replica-create` 3, re-create refused), which is what
JUN-593 needs before the hata gate gets a Darwin branch.
