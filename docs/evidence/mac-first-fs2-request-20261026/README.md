# Full Mac compiler: first live wire 35 request

This is an execution readback from the signed full-compiler Mac candidate,
not a successful filesystem operation. The current typed callback traps at
image-relative `0x6e4` because wire 35 has no provider. The independent
[LLDB observer](../../../scripts/seed/inspect-macos-first-fs2-request.py)
pins the image digest and signature, starts `check` on two different paths,
and reads the live callback arguments and exact request bytes at that stop.

Both runs reached `x1=35`, request kind `x2=1` (string), result kind `x3=1`
(string). Their first frame was `NUL FS2 NUL D <path> NUL`: the existing
source path had 34 bytes and a missing path had 25 bytes. The distinct path
bytes prove this is an argument-dependent request. The callback's pair handle
is `x4`; the descriptor used the arena encoded offset resolved by the
existing string span helper. See the [receipt](receipt.json) for exact bytes.

To repeat on Apple Silicon macOS, use the pinned signed image produced by
the pure-runtime evidence and a new scratch output file:

```sh
python3 scripts/seed/inspect-macos-first-fs2-request.py \
  --image "$SIGNED_FULL_MAC_IMAGE" \
  --expected-sha256 201257b4e767a69f9305371c4b168bfeb3e605c4602990697c6e3d4388f37631 \
  --output "$NEW_RECEIPT"
```

A wrong expected digest refuses before LLDB starts. No request is answered,
and the full compiler still does not complete `check` or `compile`. The next
runtime change must dispatch wire 35 with complete FS2 frame/kind validation,
the explicit root FD and bounded D/A/B/C operations; a D-only success does
not replace the remaining filesystem and source-lock cases.
