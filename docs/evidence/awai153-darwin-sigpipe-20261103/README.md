# Darwin TCP SIGPIPE control

On one local arm64 Mac, macOS 26.3.1 / Darwin 25.3.0, a test-only Python
observer created loopback TCP connections and a peer which reset each
connection with `SO_LINGER`. The child explicitly restored the default SIGPIPE
action, observed the reset with `recv`, and sent one byte. Three unprotected
children terminated with signal 13; three with `SO_NOSIGPIPE` set survived
and observed `EPIPE` (errno 32). The local SDK's `sys/socket.h` defines
`SO_NOSIGPIPE` as `0x1022`; the system Python socket module did not expose the
symbol, so the diagnostic used that SDK value directly.

The observer is test-only and uses no existing service or remote host. This is
an OS-level control, not the Kotoba Darwin TCP implementation: it does not
exercise the native direct-syscall path, setting the option in the provider,
SIGPIPE during setup, concurrent spawn, TLS, workload lifecycle, or other
macOS versions. It is not a replacement for full wire 43–47 qualification.
The provider must refuse setup if the option cannot be established; silent
fallback to signal-sensitive writes would not satisfy this observation.

Observer SHA-256
`05594031b2380c260c2894fcd4cdd88c40fbc057b91823c2623789b192d426f6`.
