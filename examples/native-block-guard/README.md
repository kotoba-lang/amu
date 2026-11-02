# Native block guard candidate (JUN-767)

This isolated pure Kotoba example models a small, fail-closed subset of the
host's target-bound destructive operation policy. It checks an eight-word
session/target/geometry/expiry/approval ticket against independently supplied
host observation, rejects internal, mounted and nonexclusive devices, consumes
one ticket and validates a bounded sector range without offset addition or size
multiplication overflow. Session and identity components are opaque positive
numbers here, not real disk identities or cryptographic tokens.

This is **not an authorization mechanism** until a native host owns both
records, independently obtains and revalidates device identity and exclusive
access, obtains a trusted human decision, and prevents a guest from providing,
modifying, reusing or fabricating either record. Consuming a mutable vector in
this single-threaded fixture is not atomicity under races or across processes.
There is no raw-device I/O, capability grant, trusted prompt, locking,
flush, reopen, cache protection or app integration here. Do
not use this candidate to write to any disk. A passing fixture cannot qualify
JUN-767 or prove the safety of attached SSDs.

Run `AMU=/absolute/path/to/bin/amu TMPDIR=/workspace/scratch ./check.sh`. The
actual selfhost native Kotoba program runs 21 positive/refusal assertions; two
independently compiled mutants must be detected. This is a component check only.

## Scoped regular-file exercise

`TMPDIR=/workspace/scratch ./check-file-host.sh` compiles the exact guard and
a synthetic host fixture using the pinned native macOS Amu root, extracts and
packages the generated code, ad-hoc signs it and executes it with a fresh
FD3-scoped directory per case. An external observer checks the file itself:
the synthetic allowed case writes four bytes, and nine synthetic denials plus
a missing or non-directory FD3 produce no fixture file. These records and choices are created
by the test program itself: they are not trusted user approval, device identity
or an OS authorization boundary. This exercises a real regular-file effect,
not arbitrary-offset block I/O or physical storage. The public CLI still
does not grant its ordinary guests filesystem or device access.
