# Darwin TCP provider: porting boundary

The currently wired native TCP implementation in `seed/77-aarch64-static-rt.kotoba`
is a Linux runtime. `seed/macos-fs2-runtime-packager.kotoba` currently sends
wires 43–47 to the existing trap path. The two Darwin TCP controls under
`seed/macos-tcp-*-control-packager.kotoba` are isolated observations, not
providers. A Mac mini bot or gateway must not use them as a service.

A Darwin implementation must preserve the existing wire contract: exact
address grants for listen and dial, separate listener and connection handles,
a 16-handle budget, bounded payloads, timeout handling, close and named
refusals. Wire grants alone are not address grants. Caller-visible output and
refusal precedence must be compared against the canonical TCP contract and
existing fixtures, not inferred solely from the Linux source. Credentials,
peer identity and encryption are separate from TCP authority.

## Platform differences checked on the development Mac

The local macOS SDK defines `sockaddr_in` with byte `sin_len` before
`sin_family`; Linux's current `kxrt-net-sockaddr` writes family at byte 0.
A Darwin TCP address therefore cannot be produced by copying that function
unchanged. Port and IPv4 address must still be serialized in network byte
order. The Darwin control in
[evidence](evidence/awai153-mac-connect-deadline-20261103/) actually used
`sin_len=16`, `AF_INET=2` and loopback.

Darwin direct syscalls report errors in the carry flag and a positive errno;
the Linux runtime code expects negative errno in the return register. Darwin
SDK errno values include `EINPROGRESS=36`, `EAGAIN=35`, and
`ECONNREFUSED=61`. Treating positive errors as descriptors or applying Linux
negative codes would be incorrect. The local control checked carry and
`EINPROGRESS` explicitly.

The local SDK identifies socket/connect/fcntl/poll/getsockopt as syscalls
97/98/92/230/118. `F_SETFL` with `O_NONBLOCK` is 4/4; Darwin
`SOL_SOCKET=0xffff`, `SO_ERROR=0x1007`, and `POLLOUT=4`. `accept` is 30;
`bind`/`listen` are 104/106. These are source observations from this SDK, not
an assurance that direct syscall ABI is stable across supported macOS
versions. The one-host control exercised only socket/connect/fcntl/poll/
getsockopt/close, not bind/listen/accept or alternate platform versions.

The Linux source requests `SOCK_NONBLOCK|SOCK_CLOEXEC` atomically and uses
`MSG_NOSIGNAL`. On this SDK the Darwin headers expose `F_SETFD` / `FD_CLOEXEC`
and `SO_NOSIGPIPE`; their safe use, including failed setup and any race with
concurrent spawn, must be designed and tested. A raw fcntl sequence after
socket creation does not prove atomic close-on-exec. The existing one-shot
control does not establish either property.

## Work required for integration

The current compiler/runtime boundary uses private context, bounded string
pool and handle tables; a provider must validate its wire and types and call
into those mechanisms without giving a guest ambient socket access. Host-owned
exact grant loading and lifetime must be established before opening a socket.
Each allocated descriptor needs explicit cleanup on setup error, timeout,
close, host shutdown and interrupted operations; process death and descriptor
inheritance must be tested independently. The socket must remain nonblocking
for read/write, with partial-write and disconnect semantics matching the wire.
A monotonic deadline source and EINTR handling are needed so repeated signals
cannot restart a full timeout indefinitely. The 200 ms diagnostic poll is
only one observed wait, not an implementation of that contract.

After loopback positive, denial and resource-limit tests on the actual native
artifact, validate at least two Tailscale-connected Macs with authenticated
peer identity and confidentiality. Tailscale reachability or a message HMAC
alone does not prove application identity binding. Qualification of resource
governor and workload lifecycle remains a separate prerequisite for fleet
inference and production bot operation.
