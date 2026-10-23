# Native TCP/spawn integration (JUN-292)

The static runtime provides opt-in `:process/spawn` (20) and native TCP
`43..47` on AArch64 and x86_64 Linux. The shared product frontend admits
numeric, keyword and friendly TCP forms as `:string -> :string`. The
adopted compiler, static compiler and combined compiler share that frontend.
Receipts and qualification limits are in
[`evidence/tcp-spawn-native-20261023/integration.json`](evidence/tcp-spawn-native-20261023/integration.json).

The runtime changes preserve the staged TCP/spawn work from
`jun784/jun-292-static-spawn-tcp`, reconciled with complete18 owning main and
the combined compiler. The original worktree and branch remain untouched.
Historical loader implementations specify the grammar; no removed loader
executes in the replacement build or runtime.

## Authority and compatibility

- TCP grants exact IPv4 addresses separately for listen (43) and dial (45).
  Handles are local to an execution, with 16 slots, 16 KiB IO and bounded
  timeouts. The network syscall set enters seccomp only when a TCP wire is
  granted. Source cannot call runtime primitives directly.
- Spawn copies the program/env-name grant into a helper before the guest's
  limits and filter. The helper validates every request. The guest cannot
  fork or exec; it only exchanges bounded frames with that helper.
- Existing spawn authority and limits are retained: any admitted argv of a
  granted program, selected host environment variables, stdin EOF, stdout
  16 KiB and a 10-second deadline. The child is an ordinary host process,
  as the catalog specifies. It is not the guest sandbox.
- Wire 47 uses compiler-internal effect **bit 48**. Legacy `:state` keeps
  **bit 47**; wires 0..46 retain their old bits. Wire IDs and runtime grant
  bitmaps do not change. A `#{:state}` effect ceiling does not admit TCP.
- Project capability declarations and diagnostics recognize spawn and all
  five TCP wires. Explicit/bare `--policy` remains refused with E2170;
  admission does not enable an unqualified policy checker.

The catalog names `:amu-selfhost-static` separately from the historical
hosted `:linux-static` packager and removed `:kexe-loader`.

## Verification

The evidence publisher checks source pins against the checkout before
recording adoption/root identities. Native compilation uses Amu-produced
compilers throughout, without a C compiler/loader, hosted compiler or
emulation.

| Gate | Result recorded by the evidence package |
| --- | --- |
| Static root | S2 = S3 = S4 |
| Complete18 adopted core | C0 → G1 = G2 = G3; independent prior-native packed lineage agrees |
| Packed adopted core | Standalone source self-rebuild agrees |
| Combined compiler | F1 = F2 = F3, identical self-packing, core and Linux routes |
| TCP, each native architecture | 30 frontend admission/effect cases, 13 startup cases, 29 runtime cases |
| Spawn, each native architecture | 18 startup/grant cases, 21 runtime cases |
| Existing runtime boundary | 125 refusal/no-image cases, 24 runtime cases |
| Exact source-lock project route | 6 declared positives, 12 E2176 refusals; 2 E2170 policy refusals |
| Full19 corpus | Native code, stdout and arena telemetry agree with prior complete18 main |

TCP uses the unmodified product compiler for admission. Source-mutated
compilers appear only as explicit negative controls for kernel seccomp
enforcement. Both architectures enforce seccomp; x86_64 was exercised on an
owner-approved physical host, after every staged input digest was checked.
Its temporary test directory was removed after local receipt/archive
verification. Raw logs and input snapshots are retained in the task archive.
Fault injection for spawn's `isolation-unavailable` / `setup-failed` kernel
branches is not covered by the runtime corpus; each spawn receipt records
that limitation.

The combined manifest also includes both source-lock modules (`03` and
`59`), preserving the complete static core in dependency order. Omitting
them fails with E2101 for `ksl-check-bytes?`. Its diagnostic harness now
reads the selected adoption receipt from `compiler-core.json`.

## Qualification still open

These are local diagnostic receipts. Python stages bytes and orchestrates
native processes; it does not qualify as a native CDCI controller. This
change adds no Python CI steps. The public CLI, native controller and full
historical assertion parity remain separate gates; there is no new
performance measurement or score.

JUN-292's unary spawn API does not implement the persistent, bidirectional
container stdio channel adopted in JUN-298. That process/provider contract
belongs to JUN-288. Hata's complete native mon/Cell/conductor closure
(AWAI-22), actual node launch (JUN-287/288), and state loss/restoration through
kotobase commits and Yataverse blocks (JUN-296) remain unqualified. Key
custody (JUN-299) and head publication (JUN-300) are still undecided. No keys,
mount-based persistence, remote fallback or production route changes are
introduced here.

The next existing Hata P3 `wasm32-browser` host path was probed with the
combined native compiler and a minimal typed source. It refuses with
`E2 unsupported target (only aarch64-macos)` and produces no artifact
(`hata-host-target-probe.json`). A qualified host/compiler target is required
before that path can execute a Cell; this diagnostic is not Cell execution.
