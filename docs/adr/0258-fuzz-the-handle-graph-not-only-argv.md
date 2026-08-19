# ADR 0258: the native fuzz target covers the handle graph, not only argv

Status: accepted

## Context

`amu-native-fuzz` was reported and cited as the memory-safety gate for the
KEXE native path. It ran 20,000 sanitized cases and it passed, so the receipt
read like coverage of the loader.

It was not. `LLVMFuzzerTestOneInput` called exactly four functions:

    parse_u64  parse_ulong_decimal  parse_i64  parse_allow

All four decode one argv token into an integer or a bitmask. Nothing else in
`kexe_loader.c` was ever entered. Untouched were: the whole `checked_*` context
ABI a guest reaches at run time, `resolve_string_bytes`, the four `inspect_*`
result decoders, the typed capability boundary, the dataspace provider, and the
two argv parsers that mint pairs and write the string pool.

The gap matters most in the supervisor. `inspect_string_result` and its three
siblings run **after** the sandboxed child exits — outside seccomp, outside the
macOS sandbox profile — and every byte they walk (pair table, string pool,
result handle) is what the guest left behind. That is the one place in the
design where guest-controlled data is parsed by an unsandboxed process, and it
had no fuzz coverage at all.

## Decision

One target, three sub-surfaces. `fuzz_parsers` still runs on **every** input,
because the committed corpus was selected for it and routing inputs away would
silently drop that coverage; the first input byte then selects one of the two
new sub-targets.

| Sub-target | Reaches |
| --- | --- |
| parsers | the original four, plus `parse_variant_profile` and `parse_guest_arg` |
| handle graph | all 19 `checked_*` callbacks, `resolve_string_bytes`, `checked_typed_cap_call`, the dataspace provider |
| result inspection | `inspect_string_result` / `_record_` / `_tagged_i64_` / `_variant_`, `valid_string_handle`, `peek_pair`, `valid_utf8` |

Three properties make this faithful rather than merely loud.

**Traps unwind, they do not return.** Every `checked_*` helper answers a bad
handle with `raise(SIGILL)`, and `trap_handler` ends the process with
`_exit(120)` — the raise never returns. `checked_string_equal` depends on that:
it memcmp's two `resolve_string_bytes` results with no NULL test, which is
sound only because NULL is unreachable. A handler that returned would
manufacture a crash production cannot have. So the harness siglongjmp's out
past the rest of the trapping helper, then rewinds the arena watermarks — the
state the next operation sees is one a shorter input could have produced, never
a torn intermediate.

**Operands are plausible.** Uniform 64-bit words are rejected by the first
bound they meet. Handles are drawn mostly from live arena entries, pair cells
from a bounded word generator, and half of all code regions are ASCII so
`valid_utf8` admits them — with a minority raw draw, which is what a
miscompiled or hostile guest actually leaves in a register.

**The unallocated pair tail is ASan-poisoned, and the string pool is not.**
Every pair accessor in the loader bounds the handle by `pair_used`, so reading
an unallocated pair slot is a defect no capacity check would catch.
`peek_string_bytes` and `resolve_string_bytes` deliberately bound the pool by
its CAPACITY while `inspect_string_result` bounds it by the watermark and says
so in its own comment; reading above the watermark is intended and safe, since
`main` zeroes the shared region and the pool is append-only. Poisoning it
reported `valid_string_handle` as a use-after-poison on the first run — a
property of the harness, not of the loader.

The arena is heap-allocated per input and the code region is allocated at its
exact length, unlike the real loader's page-rounded mapping. A read one byte
past `code_length` merely reads padding there; it is a defect either way, since
`code_length` is the entire bound the string paths are given.

## The reach floor

The target prints a `:kotoba.fuzz-reach/v1` line at exit and
`scripts/fuzz-native.cljs` refuses a run in which any counter is zero.

This is not decoration. The first draft of this change drew the result handle
as a raw 64-bit word, so it landed inside the 32-entry pair table roughly
never, and a deliberately broken `inspect_string_result` **survived all 20,000
cases**. A fuzz target that cannot reach the function it names answers "no
defect" for the same reason a check with no input does, and is
indistinguishable from the outside. Measured 2026-08-19 on arm64, 20,000
deterministic cases, the free-form pair layout decoded a record exactly once —
which is why a cons-chain layout mode was added.

The floor is presence and non-zero, not a tuned threshold: a number invented
without a measurement would be the same defect in a new place. The per-arch
`min-cov`/`min-features`/`min-corpus` floors in
`fuzz/baselines/native-parser.edn` are **unchanged**, because they apply to the
libFuzzer path and this workstation and the current fleet are both macOS. They
are floors, so more coverage still passes; raising them without a Linux
measurement would be inventing numbers.

## Corpus

Random bytes never spell `r:`, `s:`, `v:`, `o:`, `e:` or `variant:`, so the new
parser coverage needed seeds and would otherwise have been dead. Measured: with
`parse_guest_arg`'s field-count bound removed, the deterministic engine over
20,000 cases found **nothing**; with `record-fields-over-limit` in the corpus it
reported `index 128 out of bounds for type 'int64_t[128]'` on the seed itself.
Eight seeds added, covering record chains at and over the field limit, valid
and invalid UTF-8 hex strings, variant profiles, and the option/result forms.

## Evidence

`tools/kexe_loader.c` is **not modified**; its baseline sha256 is unchanged and
still fresh. No defect was found in the loader.

Each sub-surface was shown to discriminate — the gate was broken in the thing
it claims to test, and the report named that thing:

| Break | Reported |
| --- | --- |
| `inspect_string_result` code bound `+64` | heap-buffer-overflow in `valid_utf8` ← `inspect_string_result` |
| `resolve_string_bytes` code bound `+64` | heap-buffer-overflow in `valid_utf8` ← `checked_string_substring` |
| `parse_guest_arg` field-count bound removed | UBSan `index 128 out of bounds` (seed only; not found without it) |
| `inspect_record_result` watermark → capacity | use-after-poison in `inspect_record_result` |
| result handle drawn as a raw word (the first draft) | `nothing reached :string-result — refusing to report a pass` |

Unmodified, 20,000 deterministic ASan/UBSan cases pass with every reach counter
non-zero.

`scripts/fleet-ci/gates/amu-native-fuzz-check.cljs` could not be run end to end
on the authoring workstation: npm 11.12.1 breaks `npx --yes nbb <args>`, the
known local defect. The wrapper's own assertions were exercised with `npx`
swapped for the local `nbb` and passed; the wrapper itself is unchanged and the
fleet nodes run it.

## What this does NOT claim

- that the emitted machine code is verified — the loader still maps raw bytes
  and jumps in; trust remains in the producer plus `kotoba-verifier` plus the
  sandbox
- coverage of the KEXE artifact container, ELF/Mach-O emission, or the aiueos
  kernel and user targets
- anything about `kexe_loader_windows.c`, which has its own cross-build gate
- new libFuzzer coverage floors
