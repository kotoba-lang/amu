# Diagnostic macOS pure runtime callbacks

This evidence belongs to the Amu full-compiler macOS arm64 diagnostic lane.
It does not qualify a Mac selfhost compiler or the AIUEOS Linux-free build.

`seed/macos-pure-runtime-packager.kotoba` adds four ABI-v11 callbacks to the
previous Darwin Mach-O image: persistent `vector_conj` (slot 160), persistent
`vector_assoc` (184), `string_index_of` (216), and `string_compare` (240).
The package emits 211 AArch64 words from Kotoba literals. The adjacent
[`pure-runtime.s`](pure-runtime.s) records the one-time instruction derivation;
it is not an input to the image build. The producer for this experiment was
the pinned Amu native AArch64 Linux root in a network-disabled container.
That Linux producer is the remaining disqualifier for the final Mac build
closure, even though the resulting Mach-O runs on macOS without libc.

The independent [observer](../../../scripts/seed/check-macos-pure-runtime-probe.py)
checks source/artifact digests, native build admissions, the Kotoba literal
against packaged helper bytes, unchanged full compiler raw code, and a byte
identical full image repeat. The only changed full image locations versus
the previous UTF-8 image are the wrapper call and the previously unused
helper region (751 changed bytes). The positive fixture has direct callsites
for all four callbacks. Signed Mac execution returns 42; empty-needle and
out-of-range vector fixtures reach the checked trap. Replacing each callback
entry with `brk` makes the same positive fixture stop at that exact entry.
See [receipt.json](receipt.json) for hashes, process results, crash offsets,
and admissions.

The full compiler's no-argument CLI still returns its expected usage error.
With `check seed/macos-utf8-main.kotoba`, it reaches `typed_cap_call` wire 35
and traps at image-relative PC 1764: the FS2 `fs/app-data` provider is absent.
No full Mac `check`, `compile`, F1=F2=F3 self-rebuild, AIUEOS Mac media build,
release, or physical-machine acceptance is claimed here.

To repeat the observation on Apple Silicon, use the exact pinned artifacts
in the scratch directory from the receipt and a fresh output directory:

```sh
python3 scripts/seed/check-macos-pure-runtime-probe.py \
  --artifacts /Users/junkawasaki/github/workspaces/codex/amu-full-mac-probe-20261025 \
  --output /Users/junkawasaki/github/workspaces/codex/amu-full-mac-probe-20261025/pure-observer-repeat
```
