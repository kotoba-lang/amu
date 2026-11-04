# Darwin direct-syscall TCP spike (2026-11-04, JUN-817)

`tcpspike.s` is a standalone arm64 program (assembled with the system `clang`, not by Amu, not part of any
pinned image) that listens on `127.0.0.1:18766` with direct `svc #0x80` calls only, accepts one connection,
reads up to 64 bytes and writes them back. It exists to turn the constants recalled in ADR 0404 D2 into
measured ones before any machine code goes into a runtime variant.

Run on macOS arm64 (`uname -m` = arm64), started in the background, a loopback Python client connected,
sent `hello-from-client` and received `hello-from-client`; the program printed `ready`, `OK` and exited 0;
no listener remained.

## Measured

| Fact | Result |
| --- | --- |
| Convention | number in `x16`, `svc #0x80`; carry set on error with errno in `x0` |
| `socket(2, 1, 0)` | AF_INET = 2, SOCK_STREAM = 1 |
| `setsockopt(fd, 0xffff, 4, &1, 4)` | SOL_SOCKET = 0xffff, SO_REUSEADDR = 4 |
| `sockaddr_in` | 16 bytes: `[0]=len 16, [1]=family 2, [2..3]=port big endian, [4..7]=address`, rest zero; `bind` accepted it |
| `fcntl(fd, 4, 4)` | F_SETFL = 4, O_NONBLOCK = 4 |
| `poll` = 230 | `struct pollfd` { int32 fd; int16 events; int16 revents }, POLLIN = 1; returned 0 on timeout and 1 on a pending connection |
| `accept` = 30, `read` = 3, `write` = 4, `close` = 6, `listen` = 106, `bind` = 104, `socket` = 97, `setsockopt` = 105 | all worked as numbered |
| **Accepted sockets inherit O_NONBLOCK** | `read` straight after `accept` failed with errno **35 (EAGAIN)** (exit code of an errno variant), and the client saw a reset. Polling the connection for POLLIN first fixes it. A Darwin runtime must `poll` before every `read`; it cannot rely on a blocking accepted socket as the Linux `accept4` form allows |

## Not yet measured

`FD_CLOEXEC` via `fcntl(F_SETFD)`, `POLLOUT = 4` and partial writes, `connect` for `:net/dial`
(refused / unreachable / timeout answers), orderly shutdown versus reset on read (`closed` versus `reset`),
`getsockname` for a port-0 bind. These are the next probe's job.
