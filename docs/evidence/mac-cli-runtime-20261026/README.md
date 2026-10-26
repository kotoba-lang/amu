# Darwin argument ABI diagnostic, 2026-10-26

The Amu-built Kotoba packager `seed/macos-cli-runtime-packager.kotoba`
emitted the signed test images recorded in [receipt.json](receipt.json).
The source SHA-256, Amu root, raw program, packager binary and output images
are pinned in that receipt. [cli-runtime.s](cli-runtime.s) is an assembly
derivation aid only; the image builder consumes the Kotoba word vectors.

The `:cli/args` wire reads actual Darwin `argc` and `argv` captured at
`LC_MAIN`. With the wire-38 grant, `check fixture.kotoba` reached the CLI
fixture's exit 42. Removing that grant or providing only the stderr grant
trapped before output. The independent observer checked that the two refusal
images differ from the allowed image only in the grant word. The stderr
control still wrote `diagnostic` and exited 42. A repeated full image was
byte-identical.

The full Amu program does **not** complete `check` yet. Both no-argument and
`check fixture.kotoba` runs reached a null call through context slot 144,
`string_code_point_at`, and crashed with SIGSEGV. The current crash reports,
return instruction and source ABI were matched by
`scripts/seed/check-macos-cli-runtime-probe.py`. That slot is the next runtime
implementation gate. The older comment above `typed-helper-words` in the
packager describes its inherited wire-38 stub; the current wire-38 route is
`cli-helper-words` and reads real process arguments.

This is a diagnostic executable produced using the current Linux-hosted
Amu root. It does not prove Mac self-rebuild, a trusted consent flow, a
successful full compiler command, or Linux-free build closure.
