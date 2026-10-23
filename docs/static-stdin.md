# Stdin in the static runtimes (JUN-354, JUN-357)

Two runtime changes give a static image's process tree a standard input, in
`seed/76-x86_64-static-rt.kotoba` and `seed/77-aarch64-static-rt.kotoba`.
murakumo's node agent needs them to give a container cell its input (JUN-298,
container stdio; JUN-289, a bot turn as a job).

## Wire 41 `:io/read` (JUN-354)

The checker and lowering already admitted wire 41 (seed/HEADS); the static
runtimes trapped on it. They now answer it when it is granted (`KEXE_ALLOW`
holds 41):
- **An empty request** reads fd 0 to end of file, straight into the string
  pool, as wire 35 reads a file.
- **A decimal n** is one `read` of at most n bytes. It answers `""` only at
  end of file, so a reader can stop when it has what it needs, and the
  kernel's file offset is the one cursor. A read that stops inside a UTF-8
  sequence is completed from fd 0, at most 3 more bytes, so an answer never
  splits a character. `0` answers `""`.
- **The answer is a `:string`.** Stdin that is not UTF-8 traps, as every
  `:string` answer does.
- **Seccomp.** The filter admits `read(0)` only with wire 41 granted. A wire
  that is not granted traps, as every capability wire does.

## Wire 20 `:process/spawn`: a stdin payload (JUN-357)

The request grammar gains an optional last part:
`<program>[ARG_SEP<arg>]...[STDIN_SEP<stdin>]`.
- **Splitting.** The first `STDIN_SEP` ends the argv part, so no argument
  contains it. The bytes after it are the child's stdin, and may contain
  `ARG_SEP`.
- **Bounds.** The argv rules (count, bytes, NUL) apply to the argv part only.
  The whole request stays within the existing 65536 bytes.
- **Delivery.** The helper writes the payload to the child's stdin pipe, then
  closes it. Without `STDIN_SEP` the child still sees end of file at once.
- **No hanging, no dying.** The pipe is non-blocking and the writing runs
  against the existing 10 s deadline, so a child that does not read cannot
  hold the helper. A child that exits or closes stdin first ends the writing
  with EPIPE, because the helper ignores SIGPIPE; what it did not read is
  dropped. The child restores SIGPIPE to its default before `execve`, so the
  program starts as before.

The capability catalog (`resources/kotoba/lang/capability-catalog.edn`)
records the grammar and the child's stdin rule. The other hosts that answer
wire 20 (the kbb js host; the removed kexe loader) do not take `STDIN_SEP`.

## The compiler's string table

Each static runtime's source is one string literal of the compiler, so its
text, comments included, counts in the lexer's LITB table. Before #1523 the
combined compiler's unity sat within about 2 KB of the static profile's
524288 bytes, and this change alone failed with `E101 compiler table full:
region 3`. #1523 (JUN-353) raised `MM-LITB-CAP` to 1048576, so this change
needs no capacity edit, and the root on main compiles it directly.

## Verification

Measured on 2026-10-23 on arm64 Linux, in the podman machine (Fedora CoreOS,
rootless podman). No C compiler or loader, no hosted compiler and no
emulation were used. Receipts are in
[`evidence/static-stdin-20261023/`](evidence/static-stdin-20261023/).

- **The root** (`root-chain.json`).
  1. The previous root (`1d54a108…`) compiled `seed/FULL-MANIFEST` from this
     source to F1 and packed it.
  2. F1 rebuilt itself to F2. The container is the same; the runtime wrapper
     is new, because the previous runtime packed F1.
  3. F2 rebuilt itself to F3 = F2. F2 is the pinned root, `048244b3…`
     (`seed/bootstrap/aarch64-linux-static-root.json`).
- **`selfhost-bootstrap.py --tier pr`** from the new root
  (`selfhost-bootstrap-pr.json`) passes:
  - F1 = root;
  - F's core route gives the adoption image;
  - the runtime boundary corpus, the 24 runtime cases, hardening and
    capabilities;
  - the wasm32-browser compile.
- **`check-io-read.py`** (`io-read.json`), 12 cases:
  - **To end of file.** UTF-8 text arrives whole from a file and from a pipe.
    An empty stdin gives `""`, and 2 MiB arrives in one read. After end of
    file, a second read gives `""`.
  - **In pieces of 2.** `aこんb` arrives as `aこ|ん|b|`: each piece is
    extended to a whole character. A request of `0` gives `""`.
  - **Traps.** Stdin that is not UTF-8, a request `x`, and a wire that is not
    granted each trap.
  - **Control.** A compiler without the `read(0)` seccomp rule dies of
    SIGSYS.
- **`check-spawn-runtime.py`** (`spawn-runtime.json`): 18 grant cases and 31
  wire cases, all of the existing ones included.
  - **Payload delivery.**
    - `cat` echoes the payload;
    - `tr` uppercases it, so arguments and a payload combine;
    - a payload with `ARG_SEP` inside it arrives unchanged;
    - an empty payload gives end of file;
    - `STDIN_SEP` ends the argv part (`echo a` with payload `b` prints `a`).
  - **40 KiB.** `wc -c` counts 40960. A child that exits at once, and one
    that sleeps without reading, both answer exit 0 without a hang.
  - **SIGPIPE.** The child starts with SIGPIPE at its default (bit 12 of
    `SigIgn` clear). A control compiler that keeps the helper's ignored
    SIGPIPE in the child shows bit 12 set. The seccomp control (no read rule
    for the helper's answer fd) still dies of SIGSYS.

## Open

- **x86_64 execution.** The x86_64 runtime carries the same change with its
  own syscall numbers (read 0, write 1, fcntl 72, ppoll 271), and is
  cross-built only. Running it needs an owner-approved x86_64 host
  (JUN-316/317/318).
- **The payload's deadline path.** A request holds at most 65536 bytes,
  which a default 64 KiB pipe takes whole, so no case blocks the writing.
- **Read errors** other than EINTR, and stdin closing inside a sequence
  that a piece read completes.
- **A persistent, bidirectional container channel.** Wire 20 is still
  unary: one payload, then end of file.
