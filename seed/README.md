# Adopted native seed compiler — 12 October 2026

This directory contains the complete 16-module source based on the adopted
compiler at `fc49cb2ee6fea1a41a5abbc8ed5b52aaa9f19471`, with an integration
safety fix: explicit `--policy` is refused with E2170 until structured policy
checking is qualified. No optimization module is changed. It includes the cumulative qualified AArch64 optimizations; it
excludes the pending descriptor witness, conditional-fallthrough vector view,
and bounded byte lookup candidates. It does not change `bin/amu`, publish a
release, or qualify the whole Amu component as Q9.

`MANIFEST` fixes the unity order. Concatenating each module followed by one
newline gives SHA-256
`3871578dbc64cb6ce29f8f3e461a90ddaf2e613a60d359cf21b0657f8a4ba3f5`.
`adoption-20261012.json` records all source pins, artifact provenance, the
correctness scope and measurement boundaries. `HEADS`, `MEMORY-MAP`, and `SIR`
are the corresponding compiler contracts, copied without changes.

## Native self-build

The source-derived, selfhost-built bootstrap image is
`bootstrap/adopted-20261012.bin` (macOS arm64, entry offset 0, arity 0). It is a
native code payload used by the pinned C loader, not a standalone OS executable.
The loader is trusted C bootstrap infrastructure; this is not a C-free claim.
The Python script orchestrates the native compiler and Clang loader build only;
it never compiles Kotoba through Python, Node, nbb, JVM or GraalVM.

Verify the immutable source and bootstrap pins on any host:

```sh
python3 scripts/seed/build-adopted.py --verify-only
```

On macOS arm64, rebuild three generations into a new, empty task workspace:

```sh
python3 scripts/seed/build-adopted.py \
  --output /Users/junkawasaki/github/workspaces/codex/seed-adopted-selfbuild-new
```

The script refuses existing outputs, places its host loader/logs outside the guest-writable artifacts directory,
refuses input or loader changes during an invocation, preserves original logs,
checks every generated native image against the adopted fixed-point digest,
and leaves compiler fuel disabled only for these self-build invocations.
This is correctness verification, not performance timing.

## Evidence and pause

The original adopted source passed 39 native-image reviews, 483 paired original
comparisons (95 profile, 76 low-fuel, 312 interaction), 68 fresh generic pairs,
and 32 bootstrap success pairs. Historical validation is tied to the exact
source and artifact hashes; it is not silently relabeled a new main run.

Round 83 measured all 19 workloads using the upstream Embench speed driver
and formula. Kotoba execution time / C execution time has geometric mean
2.936403450579294, so C is faster overall. This translated-port measurement is
exploratory, not a certified official Kotoba score. It is not a released-CLI
performance result, and there is no minimum-percent adoption cutoff.

The C-or-faster optimization goal remains **paused and unmet**. Main integration
is maintenance of already-adopted work, not a restart of optimization or timing.
Pending candidates and their evidence remain in separate preserved worktrees.

Public report: <https://kotoba-lang.org/ja/blog/embench-progress-20261012/>
