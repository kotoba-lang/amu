# ADR 0404: macOS guests gain native TCP (wires 43..47)

Status: proposed (JUN-817); owner answered the four open questions on 2026-11-04 (recorded below). Design only: no runtime, packager, CLI or pin changes.

## Context

Wires 43..47 (`:net/listen` `:net/accept` `:net/dial` `:net/read` `:net/write`) are answered in the
Linux static runtime's own process (JUN-292, `seed/X86_64-LINUX-ABI`, `docs/native-tcp-spawn-integration-20261023.md`).
The decisions and refusal names are pure Kotoba and shared (`tools/kexe_loader_decisions.kotoba` ops 10..18,
`tools/kexe_loader_names.kotoba`); only the system calls and the sandbox are per platform.

On macOS they do not exist. Measured 2026-11-04 on `a4c16e7c4` (aarch64-macos):

* a guest that calls `:net/listen` passes `amu check`, **`amu compile` succeeds**, and both `amu run` and the
  compiled binary then trap (exit 133). `:io/read` (stdin) traps the same way; `:io/write` and `:cli/args` work.
* `docs/native-public-entry.md`: "Generated programs have only CLI/stdout/stderr grants", and `amu run`
  bounds a guest to 5 s.

The first consumer is torihiki's MT5 bridge (JUN-816 stage 4): an EA on the same machine dials out to a
loopback listener (MQL5 sockets are client-only), and the listener should be Kotoba, not Node or a C tool.

How the Mac runtime is built matters for the cost. Each runtime variant is a `seed/macos-*-runtime-packager.kotoba`
holding hand-derived AArch64 words as data ("the assembler was used once to derive these words"), selected and
invoked by `seed/macos-cli.kotoba`. `kotoba-packager-root.macho` and `amu-cli.macho` are pinned by SHA-256
(`seed/bootstrap/aarch64-macos/cli.json`, `root.json`), so any change to a runtime variant means a selfhost
rebuild and a re-pin, with the evidence chain that goes with it.

## Decision

D1. **A new Mac runtime variant provides wires 43..47**, with the same request grammar, bounds, answers and
refusal names as the Linux runtime (handles 1..16 lowest-free, 16 KiB per read/write, timeouts 0..30000 ms,
write ends with the partial count after 1000 ms of no progress, `timeout` `refused` `unreachable` `reset`
`closed`). It reuses ops 10..18 of the shared decisions file; it does not reimplement them. The Linux
behaviour is the specification, so one corpus can qualify both.

D2. **Darwin system calls**, direct (`svc #0x80`, number in `x16`, carry set on error, as the existing variants
do for `mmap`). Numbers read from xnu `bsd/kern/syscalls.master` on 2026-11-04:
`socket 97`, `setsockopt 105`, `getsockopt 118`, `bind 104`, `listen 106`, `accept 30`, `connect 98`,
`recvfrom 29`, `sendto 133`, `close 6`, `poll 230`, `fcntl 92`, `getsockname 32`. Calls are made only in the
one form each, mirroring the Linux filter: `socket(AF_INET, SOCK_STREAM, 0)`, then `fcntl` to
non-blocking and close-on-exec, `SO_REUSEADDR` before `bind`.
  *Recalled, not yet checked against the headers, and to be checked before code:* `sockaddr_in` is 16 bytes with
  a leading `sin_len` byte (BSD), `AF_INET = 2`, `SOCK_STREAM = 1`, `SOL_SOCKET = 0xffff`, `SO_REUSEADDR = 4`,
  `O_NONBLOCK = 4`, `F_GETFL = 3`, `F_SETFL = 4`, `F_SETFD = 2`, `FD_CLOEXEC = 1`, `POLLIN = 1`, `POLLOUT = 4`.

D3. **Grants are exact, content-identified (decision 1 below) and never baked into an artifact.** As on Linux, listen (43) and dial (45) are separate
exact `<ipv4>:<port>` lists; a listener request outside its list is `net/address-not-granted`. The grant is
supplied when the program is *run*, so a distributed binary cannot grant itself the network.

D4. **There is no kernel-level backstop on macOS.** Linux adds a seccomp filter that admits the net calls only
when a net wire is granted. Darwin has no seccomp; Seatbelt exists but is reached through libsystem or the
`__mac_syscall` path, and these images make direct syscalls. Enforcement is therefore the runtime's own code
plus the fact that the compiler emits no way for a guest to name a syscall. That is weaker than Linux and the
documentation must say so. To bound the damage, **the first release should accept loopback only**
(`127.0.0.1`), which also avoids the macOS firewall prompt for non-loopback listeners.

D5. **Compile should refuse what the runtime cannot provide.** Today `amu compile` accepts a source that calls
wires 43..47 and produces a binary that traps. Until the variant exists, and for every wire the Mac runtime
lacks, `compile` should refuse by name (`unsupported on aarch64-macos: :net/listen`), as the Linux packager
refuses wires it does not carry. This can land first and independently of the rest.

## Slices

1. **Refuse by name** (D5). Smallest; touches the packager root, so a re-pin, but no new machine code.
2. **Probe**: a packager that provides only `:net/listen` + `:net/accept` + `:net/read` + `:net/write` on
   `127.0.0.1`, fixed grant, no CLI change, as the stderr and fs2 variants began (`macos-stderr-runtime-packager`
   is "an execution probe, not a compiler image"). Qualifies D2's constants and the carry convention.
3. **Full variant**: wires 43..47, shared decisions, grant parsing, bounds and refusals.
4. **CLI**: how a grant and a longer deadline reach a run (open question 1 and 2).
5. **Qualification**: the Linux corpus (`scripts/seed/check-net-runtime.py`: 29 runtime cases per architecture
   in the JUN-292 receipt) ported to the Mac, with negative controls fired, then rebuild, re-pin and evidence.

Each slice is its own change; none is half of another.

## Decisions on the open questions (owner, 2026-11-04: "as recommended")

1. **Grant transport: the environment, as on Linux, but the grant is a content-addressed value** (amended
   2026-11-04 after the owner pointed out that Kotoba/Amu identify things by content, so a grant that decides
   what a program may reach should be identified by content too).
   What is true today: the *declared* policy is already content-addressed. Two spellings of one policy
   canonicalise to the same bytes and the same `:policy-sha256` (see `examples/capability-named.edn`), and the
   source is pinned by its KSL1 lock and Definition CIDs. What is not: Linux's runtime grant
   (`KEXE_CAP_RESOURCES_43` / `_45`) is a bare comma-separated string read from the environment, so two runs of
   one artifact can hold different authority and nothing records which.
   Decision for the Mac variant:
   * The grant is a canonical text: entries sorted, de-duplicated, comma-joined, exact `<ipv4>:<port>`, no
     whitespace; anything not in that form is refused at start (`net/setup-failed`), so one authority has one
     byte string.
   * The image computes the SHA-256 of that text with the shared pure implementation (`seed/03-source-sha256`)
     and **writes it on its first diagnostic line** (`KEXE_GRANT {:wire 43 :sha256 "..."}` to stderr), so a run's
     authority is recorded as a digest, as its source already is.
   * If the invoker also sets `KEXE_CAP_GRANT_SHA256_43` (resp. `_45`), the image **refuses to start** unless it
     equals the digest of the supplied text. That is the pinning form: an operator or a supervisor fixes the
     authority by content, and an environment variable that was altered in transit no longer matches.
   * The project-level declared policy stays the ceiling (`:policy-sha256`); a supplied grant outside the
     declared ceiling is refused. Declared policy is *what the program may ever ask for*; the grant is *what
     this run is given*; both are digests.
   * Still not baked into the artifact (D3): a digest identifies an authority, it does not confer one.
   Limits to state plainly: an environment variable remains ambient (the digest makes it auditable and
   pinnable, it does not authenticate who set it), and the Linux runtime has no digest line yet. Giving the two
   runtimes one canonical grant form is a small Linux change and is preferable to two forms; it is left to the
   slice that touches Linux, and to the owner's call whether the pin variable should be mandatory.
2. **Listener lifetime: direct execution.** A listener is a directly executed binary. `amu run` keeps its 5 s
   deadline and gains no flag.
3. **First release is loopback only.** Any entry other than `127.0.0.1:<port>` is refused at start with
   `net/address-not-granted`, even if granted. Widening it is a later ADR.
4. **Trust of a net-capable image.** The `run PROGRAM` check (recompile the embedded source, compare the whole
   signed image, run the regenerated image) is unchanged and still applies to `run`. A binary executed directly
   is, as for any executable the user starts, trusted only as far as the user trusts it; what limits it is that
   it holds no grant of its own (D3), reaches only the addresses its invoker names, and only on loopback (3).
   The wording of this paragraph is the part most in need of review.

## Consequences

* torihiki's MT5 listener can be written in Kotoba and run on the user's Mac, with the EA's loopback-only guard intact.
* The Mac and Linux runtimes share one specification and one corpus, which is what lets a disagreement be found.
* Cost: new hand-derived machine code, a packager re-pin and an evidence round. The change is real compiler-
  runtime work and ADR 0370's review order for the compiler lineage applies; it should not be mixed with
  unrelated feature work.
* Not provided here: UDP (`net/datagram` exists in the catalog and is out of scope), IPv6, DNS, TLS.
