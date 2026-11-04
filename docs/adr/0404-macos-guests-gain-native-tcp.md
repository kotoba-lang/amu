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
  *Measured 2026-11-04* with a standalone direct-syscall program (`docs/evidence/mac-tcp-spike-20261104/`):
  `sockaddr_in` is 16 bytes with a leading `sin_len` byte, `AF_INET = 2`, `SOCK_STREAM = 1`,
  `SOL_SOCKET = 0xffff`, `SO_REUSEADDR = 4`, `F_SETFL = 4`, `O_NONBLOCK = 4`, `POLLIN = 1`, `poll` takes
  `struct pollfd` { int32, int16, int16 }, and the carry-flag/errno convention holds.
  A second round (`measure.c`, `measure2.c`) measured the rest. What changes the design:
  * the accepted socket's blocking mode **follows the listener's**; the runtime keeps its listener
    non-blocking (so `accept` can time out through `poll`) and so must `poll` before every `read`;
  * **`SO_NOSIGPIPE` (0x1022) must be set on every socket**, listening and accepted and dialled: a write to a
    closed peer otherwise kills the process with SIGPIPE, and these images install no signal handler;
  * a closed peer and a reset peer look the same to `poll` (revents 0x11); `read` returning 0 versus -1
    ECONNRESET (54) is what distinguishes `closed` from `reset`;
  * a non-blocking `connect` returns EINPROGRESS (36) even on loopback; a refusal arrives as revents 0x11 and
    `SO_ERROR` 61, a success as revents 0x4 and `SO_ERROR` 0;
  * `POLLOUT` does not promise a whole write, so write, poll, and end with the partial count after 1000 ms of
    no progress, as the Linux runtime specifies;
  * `F_SETFD` = 2, `FD_CLOEXEC` = 1 work as expected; `getsockname` with port 0 returns the kernel's port.
  Not measured (needs an off-host destination): the errno that `connect` produces for `unreachable` and
  `timeout`; the numbers are ENETUNREACH 51, EHOSTUNREACH 65, ETIMEDOUT 60.

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
   * **The pin is mandatory** (owner, 2026-11-04). For each net wire it is granted, the image requires
     `KEXE_CAP_GRANT_SHA256_43` (resp. `_45`) to be set and equal to the digest of the supplied text, and
     **refuses to start otherwise**: `net/grant-unpinned` when the pin is absent, `net/grant-mismatch` when it
     differs. Both are new refusal names in `tools/kexe_loader_names.kotoba`'s net list (the stderr line and exit
     code follow the existing `KEXE_TRAP` form). A grant is therefore always named by content before it takes
     effect; there is no unpinned way to hold network authority.
     A person starting a listener by hand computes the digest once from the canonical text, for example
     `g=127.0.0.1:8765; KEXE_CAP_RESOURCES_43=$g KEXE_CAP_GRANT_SHA256_43=$(printf %s "$g" | shasum -a 256 | cut -d' ' -f1) ./listener`.
     The cost is that one extra variable; the gain is that nothing runs with an authority nobody wrote down.
   * The project-level declared policy stays the ceiling (`:policy-sha256`); a supplied grant outside the
     declared ceiling is refused. Declared policy is *what the program may ever ask for*; the grant is *what
     this run is given*; both are digests.
   * Still not baked into the artifact (D3): a digest identifies an authority, it does not confer one.
   Limits to state plainly: an environment variable remains ambient (the digest makes it auditable and
   pinnable, it does not authenticate who set it), and the Linux runtime has no digest line yet. Giving the two
   runtimes one canonical grant form is a small Linux change and is preferable to two forms; it is left to the
   slice that touches Linux. (Whether the pin is mandatory is decided above: it is.)
2. **Listener lifetime: direct execution.** A listener is a directly executed binary. `amu run` keeps its 5 s
   deadline and gains no flag.
3. **First release is loopback only.** Any entry other than `127.0.0.1:<port>` is refused at start with
   `net/address-not-granted`, even if granted. Widening it is a later ADR.
4. **Trust of a net-capable image.** The `run PROGRAM` check (recompile the embedded source, compare the whole
   signed image, run the regenerated image) is unchanged and still applies to `run`. A binary executed directly
   is, as for any executable the user starts, trusted only as far as the user trusts it; what limits it is that
   it holds no grant of its own (D3), reaches only the addresses its invoker names, and only on loopback (3).
   The wording of this paragraph is the part most in need of review.

## Implementation notes (from reading `seed/macos-fs2-runtime-packager.kotoba`, 2026-11-04)

* **The build loop is fast and reproduces.** `python3 scripts/seed/build-macos-cli.py --output DIR` rebuilds the
  packager and the CLI from source in about 12 s on this machine and asserts the packager fixed point
  (`root.json` `expectedFixedPoint.packagerUnsignedSha256`). So a change can be iterated, and a re-pin is a
  mechanical consequence of a passing build rather than a leap.
* **Guest images are the `amu-program` mode of that packager** (`amu compile` invokes the pinned packager as
  `amu-packager program.macho program.raw amu-program <offset> /source.kotoba`). A runtime helper is a block of
  AArch64 words placed at a fixed offset in the image and chained: each helper tests its wire and otherwise
  branches back to the previous helper.
* **The helper ABI**, read by disassembling the wire-39 (stderr) helper: `typed_cap(ctx=x0, wire=x1,
  request_kind=x2, result_kind=x3, handle=x4)`. The grant is a bit in the word at `[ctx+0x10]` (wire 39 tests
  `1<<39`); a request is a 1-based handle into a table at `[ctx+0x128]` (16-byte `{ptr,len}` entries, count at
  `*[ctx+0x120]`) and a bounded-span resolver turns it into a pointer; a result string is appended to the pool at
  `[ctx+0x190]` (used length at `[ctx+0x198]`, limit 256 MiB) and made a value by calling the function pointer at
  `[ctx+0x38]` with `(ctx, ~offset, length)`; every refusal today is `brk #0`. A net helper has the same shape;
  its answers are decimal handles or lowercase hex, so it needs hex encode/decode, which no existing helper has.
* **Work items** (each testable): (A) capture `envp` in the wrapper; (B) scan it for `KEXE_CAP_RESOURCES_43/45`
  and `KEXE_CAP_GRANT_SHA256_43/45`; (C) canonical-form and loopback-only checks; (D) SHA-256 in words (the
  pure Kotoba one in `seed/03-source-sha256.kotoba` is the reference; there is no compiled copy in the runtime);
  (E) the 16-slot handle table in `__DATA`; (F) wires 43..47 with their parsing, polls and answers; (G)
  `SO_NOSIGPIPE` on every socket; (H) the grant bits set in `[ctx+0x10]` only after (B)-(D) pass, and the
  `KEXE_TRAP` lines in place of `brk`; (I) the Mac port of `check-net-runtime.py` with negative controls;
  (J) the re-pin chain.
* **How the words are derived** is a decision for review. The existing helpers say "the assembler was used once to
  derive these words" from reviewed assembly. Handwriting roughly 600 instructions (D and F are most of it) in
  assembly is reviewable but slow; deriving them from freestanding C with `clang -S` and committing the assembly as
  the evidence file is faster to test but puts a C compiler in the derivation step. Either way the build path
  contains only the checked-in words.

## Consequences

* torihiki's MT5 listener can be written in Kotoba and run on the user's Mac, with the EA's loopback-only guard intact.
* The Mac and Linux runtimes share one specification and one corpus, which is what lets a disagreement be found.
* Cost: new hand-derived machine code, a packager re-pin and an evidence round. The change is real compiler-
  runtime work and ADR 0370's review order for the compiler lineage applies; it should not be mixed with
  unrelated feature work.
* Not provided here: UDP (`net/datagram` exists in the catalog and is out of scope), IPv6, DNS, TLS.
