# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

This project has no formal release process yet: there are no git tags, and
neither `package.json` nor `deps.edn` carries a version field (confirmed
2026-07-18). Entries below are therefore dateless/version-less at the top
(`[Unreleased]`) rather than numbered, since numbering would imply a release
scheme that does not exist.

This file starts now (2026-07-18). The "Unreleased" section below is a
snapshot of accumulated capability, not a diff against a prior tagged
release — there is no prior release to diff against. The dated entries under
"History" summarize real, chronologically-ordered milestones reconstructed
from `git log` (263 commits, 2026-07-11 through 2026-07-18 at the time of
writing) grouped by day; they are an honest summary of that log, not an
entry-by-entry reconstruction of every commit, and no commit before this
file's own addition was written with a changelog in mind.

## [Unreleased]

### Status

The compiler is **experimental alpha, not production-safe**
(`docs/architecture.md:124`). General allocation, tracing GC, and a
production-strength VM sandbox remain absent.

### Current capabilities (state so far)

- **Wire 35 MTIME form** (2026-09-16, artifact #47) — `"<path>MTIME_SEP"`
  answers the modification time as seconds since 1970 (`""` when the path
  cannot be stat'ed), under STAT's confinement. Its own form rather than a
  fifth STAT field: org-ieee-du reads STAT's fourth field to the end of the
  string, so a fifth field would have turned every directory into a file
  there. For `stat -f %m` (measured). test-package-command sets a file's
  mtime to a known value and reads it back; the ungranted binary traps;
  control with the form unrouted is red.
- **`:hash/sha256` (wire 3) has a real provider** (2026-09-16, artifact #46)
  — the request bytes' SHA-256 as 64 hex characters, FIPS 180-4 in the
  loader as mechanism, where the switch had fallen through to identity and
  a guest asking for a digest got its input back (`shasum -a 256` is 612 of
  1,268,018 measured agent Bash calls). Pure and scopeless; the grant bit is
  the gate. test-package-command checks the `"abc"` / empty vectors, a
  24,576-byte input against node's crypto, and the ungranted trap; control
  with the provider unrouted is red on two.
- **`:clock/now` has a text form** (2026-09-16, artifact #45) — the
  clock-v1 record codec is admitted on the JVM route and the typed Wasm
  route but not on the JVM-free native route a packaged command is built by
  (`only-native-word-typed-features?` admits typed-cap-call for
  string / i64 / option / result shapes only), so `date` could not read a
  clock: the loader's fall-through echoed the request and a guest printed
  `wall`. Wire 7 now answers `"wall"` (unix milliseconds) and `"monotonic"`
  (nanoseconds) as decimal text under the same grant bit; an unknown
  request traps. test-package-command checks the wall answer against the
  harness clock (±5 s), monotonic non-regression, the unknown-request trap
  and the ungranted trap; control with the provider unrouted is red on
  three.
- **Wire 41, `:io/read`: a command reads its standard input** (2026-09-16,
  kotoba-lang #697, kotoba-sema #85, artifact #43) — measured over
  1,268,018 Bash calls in 558 agent transcripts, head is invoked as a LATER
  pipeline segment 97% of the time, tail 94%, cut 97%, tr 99%, sort 97%,
  uniq 99%, wc 84%, awk 81%, grep 67%; a later segment reads stdin, and a
  command built on wires 35/37/38 could only be the first. Two request
  forms, one cursor: `""` answers everything to EOF; a decimal answers at
  most that many unread bytes, the empty string at EOF (what `head` needs
  so that `yes | head` ends). read(2) is handed the string pool's free
  tail, so input is copied once by the kernel; input past the pool budget
  is refused (SIGILL) rather than answered short. No scope: Seatbelt does
  not mediate read(2) on an inherited descriptor (measured under the
  loader's own profile), so the allow-mask bit is the whole grant and
  `scripts/test-package-command.cljk` packages the same guest with and
  without it (the ungranted call traps SIGTRAP — kotoba-native's emitted
  mask check, ADR 0084 — before the loader's own SIGILL check is reached).
  Control with the wire unrouted: three checks red, the identity echo
  visible. POSIX loader only; the Windows and iOS hosts serve none of the
  command wires. The decimal form answers WHOLE CODE POINTS: an incomplete
  trailing UTF-8 sequence (at most three bytes) is held back for the next
  answer, since a chunk cut mid-sequence trapped the guest's next validating
  string operation (control: 日本語 four bytes at a time, SIGILL).
- **A reader that goes away is not a trap** (2026-09-16) — `grep e big | head -1`
  is the single most frequent pipeline shape in agent tool use (8,593 of
  1,268,018 Bash calls measured over 558 Claude Code transcripts,
  superproject ADR-2609161710), and until now a packaged command in that
  position printed `KEXE_TRAP {:kind :supervisor :reason
  :unhandled-child-signal}` and exited 123: the child died of SIGPIPE at
  write(2), exactly as `/usr/bin/grep` does, and the supervisor reported the
  death it did not recognise. The supervisor now dies the same death
  (default disposition, `raise(SIGPIPE)`, else 141), stderr silent.
  `scripts/test-package-command.cljk` checks both directions on one `flood`
  guest (393,216 bytes into `head -c 1` → 141 and nothing on stderr; into
  `wc -c` → 0 and every byte); the check was seen red against the previous
  loader with the old reason literal.
- **Context ABI v10: two range operations that take no view and mint
  none** (2026-09-16) — `string-find-byte` 336 (the first offset at or
  after a boundary holding an ASCII byte; a line walk's newline or
  delimiter search without a needle handle or a region) and
  `string-append-range` 344 (an accumulator with a range of a string
  appended; one call where a view and a concat were two). A 33 MB
  `cut -f2` had spent 44% of its time minting views. kotoba-gmir 3350ad2
  / kotoba-mir 944b5d3 / osaho 85ed11b / kotoba-sema d46897d (grammar
  digest 8a2913b8) / kotoba-native a9f8a3c / kotoba-verifier e56795f /
  artifact c5862d7. `examples/range-slots.kotoba` executes both under the
  loader in `jdk-free-native-conformance` (319352; the append over a range
  of itself; byte 200 refused). Measured on the commands, 33 MB: cut
  `-f2` 0.19 → **0.13** s (its fast walk cuts over the text by offsets,
  no line view), uniq 0.13 → 0.10, grep `e` 0.17 → 0.15, awk 0.25 → 0.23,
  sort 0.66 → 0.62.
- **A pool string range must lie within the bytes that exist** (2026-09-16)
  — `resolve_string_bytes` bounded a pool range by the budget, so a pair a
  guest builds by hand could name a range past `string_pool_used`; the
  sanitized fuzz arm found it (with the v10 cases in the mix) as a memcpy
  whose source overlapped `string_concat`'s destination. Refused once, for
  every string slot, in both loaders; artifact identities advanced.
- **Context ABI v9: five handle operations emitted in line** (2026-09-16,
  owner decision, kotoba-native ADR 0084) — six data pointers at 288–328
  (the pair-used counter, the pair table, the validated flags, the
  vector-used counter, the vector table, the item arena), written once by
  the loader before the guest starts, through which kotoba-native ed534e3
  emits `pair-first` / `pair-second` (`string-byte-length`) /
  `vector-count` / `vector-at` / `vector-assoc!` as the range check, one
  table read and one access, failing with `udf` / `ud2` = the SIGILL the
  C twin raises. Searches, comparisons and concatenations stay host calls.
  `examples/inline-handles.kotoba` executes the inline path under the
  loader both ways in `jdk-free-native-conformance` (4590616 in range,
  SIGILL out of range) — and caught the first cut's clobbered value
  register on AArch64 before it landed. `string_compare_lines` resolves
  and validates a string once when both lines are in it. kotoba-verifier
  c657b65 admits version 9 and refuses a v8 table by name; artifact
  4082c9b pins the loader identities. Measured on org-ieee-sort's index
  merge sort over 33 MB: 0.77 s → **0.66 s** user (uutils 0.18,
  `/usr/bin/sort` 0.38).
- **Vector arenas as per-run budgets; `vector-item-limit` 2^24** (2026-09-16,
  owner decision) — `KEXE_VECTORS` / `KEXE_VECTOR_ITEMS` and
  `package-command --vectors` / `--vector-items` name the two vector
  arenas for one run (defaults the 4096 / 65536 they always were; mmap'd
  maxima 2^22 handles / 2^27 words, refused above before the guest
  starts), and the per-vector length the loader re-derives from
  `kotoba.kir.value/vector-item-limit` is 2^24 (osaho #93, the argument
  in its docstring: a vector is bounded again by each host's budget).
  `examples/vector-alloc-limit.kotoba` measures the limit at its boundary
  under an arena one word wider than it in `jdk-free-native-conformance`
  (16777216 admitted, 16777217 refused). What it buys: an index merge
  sort — `org-ieee-sort` keeps a vector of line offsets and orders the
  offsets in place — 33 MB in **0.77 s** where the text merge took 2.69
  (uutils 0.19). Two loader changes measured on it: `string_compare_lines`
  compares eight bytes at a time in one pass (differentially tested
  against the memchr/memcmp reference, 0 mismatches over 79,524 offset
  pairs; a tab below a newline is why memcmp alone cannot answer it), and
  `string_concat` validates its inputs so its result inherits validity
  (an accumulator started from a literal had made the write that read it
  re-scan every batch). artifact 92c35d4 pins both loader identities.
- **Context ABI v8: the two line heads as host slots** (2026-09-16) —
  `string-index-of-from` 272 (the first occurrence of a needle at or after
  a byte-offset boundary, ABSOLUTE, -1 when none: every line walk had been
  cutting a view — a handle — to search from an offset) and
  `string-compare-lines` 280 (byte order of the newline-terminated line of
  A at I against the line of B at J; a line ends at the first newline,
  excluded, or the end; the byte length names the empty line: sort's merge
  and uniq cut two views per comparison). The second is the first
  four-argument runtime call: kotoba-mir 2c4793d carries its fourth
  argument in r8 / x4, the loader's fifth C parameter, and
  `examples/line-slots.kotoba` executes it under the loader in
  `jdk-free-native-conformance` (231132) — so the convention is measured,
  not read. kotoba-gmir 790a729 / osaho 7dfafd7 / kotoba-sema b8b01d0
  (grammar resynced to kotoba-lang 72648a8, digest 9e0eca1e) /
  kotoba-native d2f1dca / kotoba-verifier 72ba0f4 / artifact 61f5d38.
  The write providers' decimal count is written by hand rather than
  `snprintf` — a third of a 100 ns write, and a write is one capability
  call per line in every line-oriented command. Fuzz harness reaches
  both; Windows loader in step.
- **Context ABI v7: the four text heads as host slots** (2026-09-16) —
  `string-compare` 240 (byte order over the common prefix, the shorter
  first: code point order for canonical UTF-8, answered by one memcmp),
  `string-fold-ascii` 248 (A–Z lowered into a fresh pool string, one byte
  to one byte so an offset into the folded text is the same offset into
  the original), `string-find-blank` 256 and `string-skip-blank` 264
  (space `\t` `\n` `\v` `\f` `\r`, FROM a boundary in [0, len]). These
  replace the per-code-point guest loops sort (comparison), grep `-i`
  (26-pass fold), wc / awk / cut (field walk) were paying for. kotoba-gmir
  2f4ee3a / kotoba-mir a51dbab name the arities and offsets, osaho
  1f07f39 answers the reference semantics, kotoba-sema 4422b1f types them
  (grammar resynced to kotoba-lang 9ecd9dbc, which now declares
  `arena-scope` and the four heads), kotoba-native dc853ff emits the
  slot calls, kotoba-verifier fb402bf admits version 7 and refuses a v6
  table by name. `examples/text-slots.kotoba` puts each head's answer in
  its own decimal place over the operands a wrong host gets wrong and is
  executed under the loader by `jdk-free-native-conformance` (21337441).
  Fuzz harness reaches all four; Windows loader in step; artifact
  ba2bd6e pins both loader identities.
- **memchr-first memmem behind `string-index-of`** (2026-09-16) — the
  POSIX loader's memmem shim called `memcmp` at every haystack offset, a
  function call per byte, sampled at 54% of a 33 MB sort whose merge asks
  for the next newline once per line per level. It is now `memchr` for
  the needle's first byte and one `memcmp` per candidate, the shape the
  Windows loader already had, and one definition on every platform. The
  same sort went from 10.96 s to 3.09 s user with no other change.
- **Context ABI v6: `(arena-scope body)`, the region reset** (2026-09-16,
  superproject ADR-2609160044) — `arena_enter` / `arena_leave` at 224 /
  232 push and pop the four arena marks (pairs, pool, vectors, vector
  items), so every handle and byte a scalar-typed body allocates is
  released when it returns. The safety argument is the type rule held by
  kotoba-sema 31826c1 and re-derived on shape by kotoba-verifier 8f6ee07;
  kotoba-native d259b18 (ADR 0083) emits the pair only as the head's
  lowering, osaho 1863a8d answers the identity. `examples/arena-scope.kotoba`
  runs the same 20,000-iteration loop both ways under the loader's DEFAULT
  budgets in `jdk-free-native-conformance`: scoped answers 200000, unscoped
  traps. The fuzz harness reaches the pair unpaired, so the depth-0 leave
  and the depth bound are fuzzed. Windows loader in step.
- **string-concat tail append** (2026-09-15) — when the first operand is
  the string pool's last allocation, `checked_string_concat` copies and
  charges only the second and answers a longer view of the same bytes
  (nothing an existing handle covers changes). A guest that keeps its
  accumulator at the tail and appends views to it now has an O(1)-per-byte
  string builder; `examples/tail-append.kotoba` (20,000 appends under a
  1 MiB pool) answers 200000 in `jdk-free-native-conformance` where the
  loader before it traps. Windows loader in step.
- **ABI v5: `string-index-of` is a host slot** (2026-09-15) — context
  offset 216, `checked_string_index_of` (memmem; an empty needle traps as
  in the reference interpreter), `kexe_context_v5`, every `checked_*`
  refusing any other version, the Windows loader in step (memchr +
  memcmp). kotoba-native 9a98c3e emits the call and rewrites
  `string-contains?` / `string-replace-all` onto it (its ADR 0082);
  kotoba-verifier a0d0799 admits version 5 with `:string-index-of-offset
  216` and refuses v4 by name; gmir 8e57296 / mir 1a6424c carry the arity
  and the offset. Measured before: a packaged grep at 75 ns/byte, SIGILL
  after 2 MB of a 3.3 MB file with the 4 Mi-handle arena spent one handle
  per byte. `examples/string-index-of.kotoba` executes the host's answer
  against the near-miss rows in `jdk-free-native-conformance`.
- **Buffered command output, CPU/wall budgets, larger arena ceilings**
  (2026-09-15) — the native loader buffers wire 37 (`:io/write`) in 64 KiB
  and flushes before every wire-39 diagnostic and on every exit path
  including a trap, so a count the wire answered is never a count of bytes
  that did not arrive. `KEXE_CPU_SECONDS` / `KEXE_WALL_SECONDS` (and
  `package-command.cljk --cpu-seconds / --wall-seconds`) turn the child's
  RLIMIT_CPU 1 s and alarm 3 s literals into budgets with unchanged
  defaults. `KEXE_PAIR_MAX` is 64 Mi handles and `KEXE_STRING_POOL_MAX`
  1 GiB (address space; defaults unchanged); `:fs/browse` has no entry-count
  bound beyond the string pool budget. `npm run test-package-command`
  measures the three behaviours in both directions; the unmodified loader
  fails two of its eight checks.
- **Explicit POSIX string SIMD** — checked native string equality retains its
  bounded-handle and canonical UTF-8 validation, then compares 16-byte chunks
  with NEON on AArch64 or SSE2 on x86-64. The loader identity, executor pin,
  dependency lock, assembly gate, and cross-ISA semantic vectors advance as
  one closure; Windows remains separately pinned and unchanged.
- **Multi-target ahead-of-time compilation** from a single `.kotoba` source
  pipeline (`source -> inert reader -> typed/effect HIR -> SSA-like KIR ->
  backend`) to `wasm32` / `wasm32-browser` / `wasm32-wasi`, `x86_64` (incl.
  `x86_64-windows`), `aarch64` (incl. `aarch64-android`, `aarch64-ios`,
  bare-metal `aarch64-aiueos-kernel-v1`), and `cljs` (KIR lowered to plain
  ClojureScript source), plus a restricted JavaScript/web target and a typed
  GPU accelerator KIR emitting WGSL, CUDA C, or Metal Shading Language.
- **Three independent safety gates** ahead of every backend: frontend
  admission (`kotoba.compiler.frontend` — subset/reader validation, forbidden
  heads), deny-by-default capability admission (`kotoba.compiler.admission`
  — capability calls fail closed unless explicitly allowed), and a
  structurally independent target verifier that decodes and re-checks every
  emitted instruction before an artifact is admitted, including against
  attacker-resealed KEXE containers.
- **Fuzzing infrastructure**: coverage- and sanitizer-guided (ASan/UBSan)
  fuzzing of the native loader and frontend parser, with corpus
  promotion/review tooling and CI coverage-regression gating
  (`scripts/fuzz-native.cljk`, `scripts/review-fuzz-corpus.cljk`).
- **nbb-native execution path**: `wasm32`/`wasm32-browser`/`wasm32-wasi`
  `compile`/`check` run entirely under `nbb` (ClojureScript on Node) with no
  JVM process spawned, sharing `.cljc` source with the JVM-compat path used
  by every other target and CLI subcommand.
- Signed, receipted execution evidence (Ed25519 artifact admission,
  executor-attested run receipts, reproducible platform coverage snapshots)
  and a supervised W^X loader on native targets (Linux seccomp sandboxing,
  macOS sandboxing, Windows restricted-token supervision).
- **Bounded substring search and case fold** (`string-contains?`,
  `string-fold-case`, ADR 0050): compose for case-insensitive substring
  search across the reference evaluator, restricted JavaScript, and typed
  Wasm. Not extended to the native (`aarch64`/`x86_64`) or `cljs-kotoba-v1`
  backends, matching `string-replace-all`'s existing scope.

## History (summarized from `git log`, not entry-by-entry)

### 2026-07-11 — Bootstrap: verified multi-target compiler core

- Multi-target compiler bootstrapped with wasm32, x86-64, and AArch64
  backends, each executing fuel-bounded runtime KIR under a supervised W^X
  loader.
- Deny-by-default capability admission and Ed25519 artifact admission added;
  executor-attested run receipts introduced.
- Linux native execution sandboxed with seccomp; native loader fuzzing
  (coverage + ASan/UBSan) and frontend fuzzing set up.
- Compiler exposed through `kotoba -M`; safety gates verified in CI.

### 2026-07-12 — Windows target, GPU kernels, browser host

- `x86_64-windows-kotoba-v1` sealed target added: verified KEXE execution
  under a Windows W^X supervisor with restricted impersonation tokens and
  owner ACLs on private outputs.
- Typed GPU accelerator KIR added, lowering bounded f32 kernels to WGSL,
  CUDA C, and Metal Shading Language.
- Deny-by-default browser Wasm host added, isolated in a closed worker host;
  browser Wasm matrix testing across three engines, including branded Safari
  conformance attestation.
- Reproducible, signed platform coverage reporting added
  (`bin/kotoba -M coverage`).
- Security gates migrated from babashka to nbb.

### 2026-07-13 — Mobile targets, per-architecture fuzz floors

- Hardened Android AArch64 NDK cross-build host added
  (`aarch64-android`).
- Verified iOS code packaged as a static AOT archive (`aarch64-ios`).
- Native fuzz coverage floors bound per architecture.

### 2026-07-14 — cljs backend, aiueos freestanding targets, language growth

- New `cljs` backend added (ADR-2607151500): KIR lowered to plain
  ClojureScript source text rather than machine code or a Wasm binary,
  including a `cap-call` host-dispatcher mechanism and a loud (not silent)
  arithmetic-overflow guard.
- `aiueos` freestanding kernel target contracts added; freestanding ELF64
  kernels and PE32+ EFI firmware packaging introduced.
- Language surface grew: `and`/`or`/`when`, keyword and map literals,
  `get`/`assoc`, destructuring, vector-as-data, and `loop`/`recur`
  (ADR-2607150000).

### 2026-07-15 — aiueos kernel export series

- A long series of small, individually-reviewed `aiueos` kernel exports
  landed (capability/journal/registry/PCI/syscall/storage planners and
  validators), each behind its own PR.
- A silent-`"nil"`-output bug in `compile --target cljs-kotoba-v1` fixed.

### 2026-07-16 — nbb-native wasm32 path, UEFI loader, iOS Simulator, x86 tail-call safety

- nbb-native `compile`/`check` path for `wasm32`/`wasm32-browser`/
  `wasm32-wasi` targets landed: no JVM process spawned for that path (#35).
- Embedded Kotoba kernel UEFI loader packaged; UEFI memory map wired into
  the kernel; kernel segment admission hardened.
- Real iOS Simulator execution of compiled `.kotoba` code added (no
  hardware/signing required) (#48).
- x86-64 tail recursion made stack-safe; tail jumps restricted to true tail
  positions.
- `aiueos` user-process ELF target, mediated user runtime ABI, and process/
  scheduler planner exports continued landing behind individual PRs.

### 2026-07-17 — Bare-metal AArch64 kernel target, `do` form, Kotoba Script backend

- `aarch64-aiueos-kernel-v1` bare-metal AArch64 kernel target added, with
  bounded `kernel-load-u32`/`kernel-store-u32` MMIO intrinsics.
- `do` sequencing form (ordered side effects, evaluated once) added to the
  language.
- Restricted Kotoba Script backend added, with a Java 17-compatible
  verifier (#49).
- Frontend admission extended: bounded namespace and function docstrings
  (#50, #51), closed top-level data constants (#52), capability-safe module
  exports (#53).

### 2026-07-18 — Web target typed strings, module linking, supply-chain sealing

- Explicit web library modules and bounded typed strings for the Kotoba web
  target added (#54, #55).
- Frontend hardened further: multi-body `when` and a catalog of forbidden
  heads (maturity P0/L2).
- Closed Kotoba module linking and embedded module-graph seals in ESM
  artifacts added (#57, #59).
- Aggregate project syntax and literals bounded (#60); verified
  supply-chain identity sealed (#61) — most recent commit at the time of
  writing.
