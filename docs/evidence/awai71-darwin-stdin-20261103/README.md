# Diagnostic Darwin wire 41 stdin candidate

The Mac diagnostic packager now has an explicit `fs2-cli-stdio-read` mode
with `:io/read` (wire 41). Existing modes retain their previous grant mask and
dispatch. A decimal request performs one bounded read of at most that many
bytes; an empty request reads through EOF. Both use the same OS stdin cursor.
Malformed requests, requests over 1 MiB, read-all streams over 1 MiB and read
errors trap rather than returning a successful truncated result. The count
parser itself is bounded to 20 decimal characters. This intentionally bounded
diagnostic profile is not yet a qualification of the complete catalog contract.

On the local macOS ARM64 host, the Amu-built diagnostic packager produced a
signed native fixture from `seed/tests/macos-stdin/fixture.kotoba`. With only
synthetic input, the tests observed:

- sequential `3`, `2`, read-all requests yielded `abc|de|fghi`;
- a zero-byte request left stdin unconsumed; EOF returned an empty string;
- embedded NUL bytes survived the split read and stdout;
- a read-all stream of 1,048,576 bytes returned its complete length, while
  1,048,577 bytes trapped without output;
- malformed and over-limit decimal counts trapped; the pre-existing general
  mode also trapped instead of granting wire 41;
- a pipe whose writer sent `ab` and waited for the first result demonstrated
  that a count of 3 may return the two currently available bytes before EOF;
- a test-only packager mutant with the wire-41 grant bit removed trapped
  before output, despite dispatching to the new provider.

Source and signed artifact SHA-256:

- packager source `ae0849313c8fd3bacd98a6da1f8e33c6273b82708afd617ea077fa0ccf0367c2`
- fixture source `663d5f4a37e1adb3f29a00d0fccc15cdfedb54a79a3b9529f6cbc72fbf3bdde4`
- diagnostic packager `37cc4348e95e80cc0682c8f13cfe8171f350674fff1810327d56528ae5011037`
- opt-in fixture `536c7845285aeea88cd631c7db813c67aebb15b2d359ebf775d3681cf08a44d1`
- previous general-mode control `4d62eefd255a3245c366803d6ffaec4acd4575daa9b032cd9cbcbffb1c48e95e`
- grant-removed control `392b4bc10464e9135c2877d672f0043ef3b136b1042b67f6cb57fee17ff52a91`
- Mac root compiler `920954769b8fdc51cf50dfcab5c44a4e56cf01f261806a153b21488ba81ac4e6`

This is a diagnostic packager mode, not the public Mac CLI or a released
runtime. Read bytes remain in the guest pool; no secret erasure, sender
authentication, process isolation, child lifetime, token provisioning or
Git/GH credential helper is provided. The tests do not establish behavior for
nonblocking descriptors, interrupted syscalls, terminal use or all possible
byte lengths. No real token, existing service, or deployment was used.
