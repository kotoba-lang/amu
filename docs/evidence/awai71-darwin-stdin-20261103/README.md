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

## Re-run on the integrated packager (2026-11-05, macOS ARM64)

The pins above describe the earlier standalone candidate. After merging
`origin/main` (the #1796 packager with amu-program, FS35, metal, general-command
and cwd modes) the diagnostic mode was rebuilt and re-observed with the same
fixture; the numbers below replace the pins above for the code in this branch.

- packager source `81dcac7f28b7d8d62a180be32f50b7957cfd9646feb3ff8112a6ba8433c2e6ea`
- fixture source `663d5f4a37e1adb3f29a00d0fccc15cdfedb54a79a3b9529f6cbc72fbf3bdde4`
- Mac root compiler (committed `amu-full-root.macho`) `68c7986d93ad35afa85b2cdd0dac7781997b5ac43280a941d69d864c85a7ab5a`
- diagnostic packager (built by that root) `558633eb4a50cfc8cc843a629f2ab1fe9676a4bbf01c410fd13314496d899ec5`
- `fs2-cli-stdio-read` fixture image `bc84eb08029f1b60f79c1ff94c134d72b77e4dc194302a475d83ee330368c43d`
- `fs2-cli-stdio-general` control image `896a2f921b655203dbe54c044ff3fce6d0437f8324ea11c727dcf3d9162f1dc0`

Observed (synthetic input only): `split` on `abcdefghi` printed `abc|de|fghi`;
`zero` printed `|abc` (a zero-byte request leaves stdin unconsumed); embedded
NULs survived (`a\0cde\0ghi` printed `a\0c|de|\0ghi`); read-all of 1,048,576
bytes printed `1048576`; read-all of 1,048,577 bytes, a malformed count and a
count over 1 MiB trapped (exit -5) without output; the general-mode control
trapped instead of granting wire 41. `check-macos-fs35.py` passes
(`PASS_MACOS_FS35`) with its negative control anchored on the merged condition.

Not re-run here: the pipe whose writer waits after `ab`, and the packager mutant
with the wire-41 grant bit removed; their earlier observations above apply only
to the earlier candidate.

## Known limits of this diagnostic mode (from review, not fixed here)

- A counted read stops exactly at the requested byte count, so a request that
  ends inside a multibyte UTF-8 character returns the incomplete prefix as a
  string. The established wire-41 runtime (`kxrt-io-read-some` in
  `seed/77-aarch64-static-rt.kotoba`) completes the character; this mode does not.
- Every request first checks for 1,048,577 bytes of dynamic-pool headroom, so once
  pool use exceeds 267,386,879 even a zero or one-byte request traps although
  it needs no space. The established runtime short-circuits a zero count.

Both are acceptable only because the mode is opt-in and diagnostic; qualifying it
as the wire-41 provider requires fixing them first.
