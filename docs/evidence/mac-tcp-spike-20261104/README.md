# Darwin direct-syscall TCP spike (2026-11-04, JUN-817)

`tcpspike.s` is a standalone arm64 program (assembled with the system `clang`, not by Amu, not part of any
pinned image) that listens on `127.0.0.1:18766` with direct `svc #0x80` calls only, accepts one connection,
reads up to 64 bytes and writes them back. It exists to turn the constants recalled in ADR 0408 D2 into
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
| Accepted socket and `read` | in this program the listener was non-blocking, `read` straight after `accept` failed with errno **35 (EAGAIN)** and the client saw a reset. Polling the connection for POLLIN first fixes it. (The second round shows the cause: the accepted socket follows the *listener's* blocking mode, it is not a general rule.) |

## Second round: the behaviours the first round left open

`measure.c` and `measure2.c` (libc wrappers, so the same kernel calls and header constants as the svc
program; loopback only; their output is `measure.out` and `measure2.out`). `measure.c` prints its stdio
buffer twice because a forked child flushes it; the saved output is the first copy.

| Fact | Result |
| --- | --- |
| Constants | POLLIN 1, POLLOUT 4, POLLERR 8, POLLHUP 16, POLLNVAL 32; F_GETFD 1, F_SETFD 2, FD_CLOEXEC 1; SO_ERROR 4103, SO_LINGER 128, **SO_NOSIGPIPE 0x1022** |
| errno | EAGAIN 35, EINPROGRESS 36, ECONNREFUSED 61, ECONNRESET 54, ENETUNREACH 51, EHOSTUNREACH 65, ETIMEDOUT 60, EPIPE 32, EADDRINUSE 48 |
| `FD_CLOEXEC` | a new socket has it clear (`F_GETFD` 0); `fcntl(F_SETFD, 1)` sets it (`F_GETFD` 1) |
| `getsockname`, port 0 | 16 bytes, `sin_len` 16, family 2, the kernel's port in network order |
| **Accepted-socket blocking mode** | follows the **listener**: a blocking listener gives a blocking accepted socket, a non-blocking listener (the first round's case) gives a non-blocking one. The first round's EAGAIN was that inheritance, not a general Darwin rule |
| Dial, non-blocking `connect` | returns -1 with **EINPROGRESS (36)** even on loopback. Nothing listening: `poll` returns 1 with revents **0x11 (POLLIN\|POLLHUP)** and `SO_ERROR` = **61 (ECONNREFUSED)**. A listener present: revents **0x4 (POLLOUT)**, `SO_ERROR` 0 |
| Orderly close by the peer | `poll` revents **0x11**, `read` returns 0, and keeps returning 0 |
| Reset (peer `SO_LINGER {1,0}` then close) | `poll` revents **0x11**, `read` returns -1 with **ECONNRESET (54)**. Same revents as an orderly close: only the `read` result tells them apart, so the runtime must read to decide `closed` versus `reset` |
| **Write to a closed peer** | with the default, the process is **killed by SIGPIPE** (signal 13): the first write succeeds, the second kills it. With `SO_NOSIGPIPE` set on the socket the second write returns -1 / **EPIPE (32)**. A direct-syscall runtime installs no signal handler, so every socket it creates or accepts needs `SO_NOSIGPIPE`, or one closed connection ends the guest silently |
| Partial writes | a non-blocking sender filled about 310 KB in 19 writes, one of them partial, then EAGAIN; the receiver drained 131072 bytes. `poll(POLLOUT)` reported writable shortly after the EAGAIN, because the kernel moves bytes on to the peer: POLLOUT does not promise the next write is whole, so the runtime writes, polls, and ends with the partial count when nothing moves for 1000 ms, as the Linux runtime specifies |

## Still not measured

`ENETUNREACH` / `EHOSTUNREACH` / `ETIMEDOUT` as actually produced by `connect` (they need an off-host
destination, which the loopback-only first release does not allow and this probe does not send to). Their
numbers are above; the mapping to `unreachable` and `timeout` follows the Linux runtime and is unverified here.
