# Full Amu Mac diagnostic: bytes copy and UTF-8 construction

The successor Kotoba packagers install ABI v11 `bytes_from_vector` (slot 360)
and `string_from_utf8` (slot 352) on top of the earlier Darwin argv, string,
and bounded vector runtime. `bytes_from_vector` checks the source handle,
length, item arena, and each value's 0–255 range before it copies the words
to a new vector slice. `string_from_utf8` checks the same bounds and byte
range, copies bytes into the string pool, creates a string view, then invokes
the existing whole-string UTF-8 validator before returning that view. Empty
strings are admitted. Invalid input traps; this diagnostic route does not yet
reproduce the full loader's named value-trap reasons.

The emitted machine words are literal Kotoba data in
[`seed/macos-bytes-runtime-packager.kotoba`](../../../seed/macos-bytes-runtime-packager.kotoba)
and
[`seed/macos-utf8-runtime-packager.kotoba`](../../../seed/macos-utf8-runtime-packager.kotoba).
The adjacent `.s` files document one-time word derivation only. Neither an
assembler nor its object files participate in the Kotoba/Amu packaging or Mac
execution path. The final 1,252-byte helper text is byte-identical to the
derivation and has SHA-256
`1cbb73d57a2a44133b72b7f6249e4c40a72306561b10e0991ce5a6ab8bee2d27`.

The pinned Amu native root compiled the packagers and four fixtures in a
network-disabled ARM Linux container. The full Mac image was emitted twice
with identical bytes. On Apple Silicon macOS, signed execution returned 42
for the bytes copy fixture, including a source mutation that leaves the bytes
copy unchanged. A vector item of 256 trapped in the checked helper. The
canonical UTF-8 fixture (`Aé€🙂` and the empty string) returned 42; an
overlong `C0 80` sequence trapped in the existing UTF-8 validator. The
earlier bytes fixtures also retained their expected outcomes in the final
image.

The full compiler still returns byte-identical no-argument usage (exit 2).
With `check seed/macos-utf8-main.kotoba`, it now passes the bytes and UTF-8
slots and reaches typed capability wire 35 (`fs/app-data`) at raw return
offset `0x2f80`. The current diagnostic typed helper traps before file I/O;
it has no wire-35 service. This is the next concrete Mac compiler boundary.

The independent [`receipt.json`](receipt.json) pins source, artifact, helper,
admission, image-repeat, signed-process, and live crash evidence. Re-run its
observer against the pinned artifacts with:

```sh
python3 scripts/seed/check-macos-bytes-utf8-probe.py \
  --artifacts /Users/junkawasaki/github/workspaces/codex/amu-full-mac-probe-20261025 \
  --output /Users/junkawasaki/github/workspaces/codex/amu-full-mac-probe-20261025/bytes-utf8-observer-v2
```

The full `check` and `compile` commands, Mac F1=F2=F3 self-rebuild,
Linux-free AIUEOS build producer, and physical/release qualification remain
open. The fixed `cli-stderr` mode is a diagnostic grant, not trusted user
approval. Native file I/O must preserve declared path authority and refusal
semantics before the compiler can read or write project files on Mac.
