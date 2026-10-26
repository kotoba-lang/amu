# Full Amu Mac diagnostic: bounded vector ABI

The Kotoba packager now installs ABI v11 slots `vector_alloc` (200),
`vector_count` (168), `vector_at` (176), and `vector_assoc_in_place` (208),
plus the ABI v9 direct vector pointers used by compiled inline operations.
It reserves separate anonymous arenas for 4 Mi vector handles and 16 Mi
zero-filled i64 items. Handles, counts, indices, and arena limits are checked
before host-side memory access. The earlier Darwin argv, UTF-8 code-point,
substring, string-pool, stderr, and pair routes remain in the image.

The checked machine words are embedded in
[`seed/macos-vector-runtime-packager.kotoba`](../../../seed/macos-vector-runtime-packager.kotoba).
[`vector-runtime.s`](vector-runtime.s) documents their one-time assembler
derivation; the assembler and object file are **not** in the packaging or
execution path. The extracted 680-byte text is identical to image bytes
`[5000,5680)` and has SHA-256
`5dad45a211fbad808d89111570d0571e493aad01bdc8bcff3f2ec3ce9497c857`.

The pinned Amu native root compiled the `.kotoba` packager and two fixture
programs in a network-disabled ARM Linux container. The packager emitted the
full Mac image twice with byte-identical output. On Apple Silicon macOS,
ad-hoc signed execution returned 42 for zero-filled allocation, count,
affine store, and indexed reads. The out-of-range index reached the generated
inline `udf` at raw offset `0x58` and exited with SIGILL. The full compiler's
no-argument usage still returns exit 2 with byte-identical stderr. Its
`check seed/macos-vector-main.kotoba` command passes the earlier string and
vector slots, then stops at the still-uninstalled `bytes_from_vector` slot
360 (raw return offset `0x2d78`, null callback PC).

[`receipt.json`](receipt.json) is the independent Mac observer result. The
observer pins the Kotoba sources, fixture containers and extracted functions,
full raw main, native build admissions, unsigned Mach-O images, vector helper
bytes, slot wiring, signed process results, live crash locations, and the
repeat image. Run it against the pinned artifacts with:

```sh
python3 scripts/seed/check-macos-vector-runtime-probe.py \
  --artifacts /Users/junkawasaki/github/workspaces/codex/amu-full-mac-probe-20261025 \
  --output /Users/junkawasaki/github/workspaces/codex/amu-full-mac-probe-20261025/vector-observer-v2
```

This is a diagnostic bootstrap result. The full Mac `check` and `compile`
commands, Mac F1=F2=F3 self-rebuild, and Linux-free AIUEOS build producer
remain open. The build-time `cli-stderr` mode is a fixed diagnostic grant,
not a trusted consent mechanism. The result does not qualify physical
hardware, a release image, or the AIUEOS daily OS scorecard.
