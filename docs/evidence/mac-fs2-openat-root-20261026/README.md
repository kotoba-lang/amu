# Darwin FS2 root descriptor syscall control

This is a one-time Apple Silicon macOS ABI control for the next native Amu
FS2 provider. It does **not** implement wire 35, parse an FS2 frame, run the
full compiler, or qualify a Mac selfhost build. The control is assembled with
Apple clang and linked with libSystem only to observe Darwin syscalls; neither
is a permitted dependency of the final Amu product build.

The parent explicitly opens a directory and passes it as FD 3. The test
program calls `openat(3, path, O_RESOLVE_BENEATH | O_NOFOLLOW_ANY |
O_NONBLOCK | O_CLOEXEC, 0)` using the Darwin raw syscall ABI, then reads one
byte. These flag values come from the installed macOS SDK's `sys/fcntl.h`.
The combined flag word is `0x21001004`; `O_NOFOLLOW` is deliberately absent.
Apple's [XNU VFS implementation](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/vfs/vfs_vnops.c)
rejects the combination of `O_NOFOLLOW` and `O_NOFOLLOW_ANY` with `EINVAL`.

The [receipt](receipt.json) records nine actual child-process results. Files
inside the grant return the expected byte; a file symlink and a symlinked
directory return `ELOOP` (62); `../` and an absolute path return
`ENOTCAPABLE` (107). A missing file returns `ENOENT` (2), an absent FD 3
returns `EBADF` (9), and a regular file passed as FD 3 returns `ENOTDIR`
(20). The exit codes are the raw syscall errors propagated by the control.
Two separately compiled negative controls remove one flag at a time:
without `O_RESOLVE_BENEATH`, `../outside.txt` opens and reads `K`; without
`O_NOFOLLOW_ANY`, the file symlink opens and reads `K`. Thus the observed
refusals depend on the two named controls, rather than on a bad FD or an
unreadable fixture.

Reproduce with a fresh scratch directory on Apple Silicon macOS:

```sh
python3 docs/evidence/mac-fs2-openat-root-20261026/control.py \
  --output /Users/junkawasaki/github/workspaces/codex/amu-full-mac-probe-20261025/mac-fs2-openat-repeat
```

The product provider must still validate the entire FS2 frame and kind,
bound request and response sizes, use the inherited directory grant without
an ambient cwd or environment fallback, check the opened file type and size,
implement acknowledged D/A reads and B/C writes, and prove refusal behavior
through an Amu-built Mach-O. This control only removes uncertainty about
Darwin's root-relative `openat` flags and negative results.
