# Darwin nonblocking connection control

The Kotoba packager emits a test-only Mach-O which connects to a loopback port
using `fcntl(F_SETFL, O_NONBLOCK)`, `connect`, and a 200 ms `poll` when connect
returns `EINPROGRESS`. A ready result is accepted only after writable revents
and `getsockopt(SO_ERROR)` both indicate success. It attempts to close the socket on all
paths after creation; interruption or an unexpected result is refused rather
than retried. This one-shot control does not send data or implement network
capability wires.

One Darwin 25.3.0 ARM64 Mac observation returned 0 for a listening local
server (the server accepted), 1 for an unbound port and short input, and 2 for
a bound non-listening port after 0.208 s. The supervisor provided a separate
3 s process timeout. A test-only mutant that skips both the event check and
SO_ERROR incorrectly returned success for an unbound port. A mutant which
skipped SO_ERROR but retained the writable check still refused that particular
port; this observation does not establish that SO_ERROR is redundant.

`deadline.s` and `mutant.s` are independent test derivations, not operational
tooling. All 91 embedded words of the Kotoba source matched the independently
assembled `deadline.o`. `observe.py` is test-only and its temporary paths must
be adapted for a rerun. No external host, existing service, bot or credential
was touched. The 200 ms poll interval is not a hard real-time wall-clock
bound: scheduling, system calls and interruption have not been qualified.

Source SHA-256 `cfaa33f77dee204ef8aff99e31992bb8228a8dca5eb7b8b81cc3fc9fdcac9865`;
signed packager `61ac8bda3681d72283db141870ccb6699ee38493d60d5fc89f900c4d7e97ba92`;
signed control `e68e23054fe3ed1ad6c7695908bf5e0d54f0bd64b0982253d51b1e999beef905`;
independent object `69212313296c98ece8c2f15efce54b5a4da42ad74d058cb78f680ed92a238d8d`;
naive-poll mutant image `9a43c4bea266ea0f03d0b9c0806cdf8351b7fc59928bdc20d498c9f443ea24a0`.
The bootstrap compiler and diagnostic FS2 packager pins are the same as in
[the earlier control](../awai153-mac-tcp-control-20261103/).

This is a bounded diagnostic for one socket on one host, not a full TCP
provider, credential boundary, production runtime, bot service or multi-Mac
transport. It omits listener/accept, partial reads and writes, cancellation,
handle reuse, grants, secure peer identity and production process lifecycle.
