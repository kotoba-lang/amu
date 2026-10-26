# Mac full compiler: bounded FS2 B/C diagnostic

This record advances JUN-417's Apple Silicon compiler probe. The Kotoba
[packager](../../../seed/macos-fs2-runtime-packager.kotoba) emits a signed
arm64 Mach-O candidate containing the full compiler, a scoped FS2 D/A/B/C
provider, CLI/stdio callbacks, and a fast validated ASCII codepoint path.
The package contains no dylib load commands. The live Mac compiler needs a
directory on FD3 for filesystem operations; it needs no screen sharing,
password, or interactive approval to run this diagnostic gate.

The final source SHA-256 is
`5c2eda41f802f69bb6a7bb3f2b295c9ba78ab9d95bec340c869005168fe3ac97`.
The pinned full-compiler raw input SHA-256 is
`164482b3310774e488e0cf84882ed05922fcaeec1f2a812e6440e1679e9fd09e`.
The Amu-built Linux ARM packager SHA-256 is
`5ab12231685cdad7894f53332e54c1d0b1702387128b7b979a409bf24e115576`;
the ad hoc signed Mac image SHA-256 is
`f020814d936e2bb316c27e39e34c3c05dfdda7f1f1daf536ea837a4ad7afb677`.

The [passwordless diagnostic gate](../../../scripts/seed/check_macos_fs2_bc.py)
checks the image digest and signature before launch. With a scratch directory
under `github/workspaces`, it checks the UTF-8 fixture, compiles the same
source to a static ARM ELF, verifies its exact 307,712-byte digest, and checks
two refusal cases. Its result was:

```json
{"check_exit":0,"compile_exit":0,"existing_output_exit":2,"gate":"mac-fs2-bc-diagnostic-v1","image_sha256":"f020814d936e2bb316c27e39e34c3c05dfdda7f1f1daf536ea837a4ad7afb677","ok":true,"output_bytes":307712,"output_sha256":"50bf68c6ea23a4b3325e7f29292fb132b90077f1eea15a4306d538190b4e6791","traversal_created_file":false,"traversal_exit":-5}
```

The two FS2 byte-write pieces were 262,144 and 45,568 payload bytes. The
complete output was byte-for-byte equal to an independent compile by the
pinned Linux ARM Amu root, with SHA-256
`50bf68c6ea23a4b3325e7f29292fb132b90077f1eea15a4306d538190b4e6791`.
The emitted ELF was then executed in a network-disabled ARM Linux container
and returned the fixture's expected status 42. The comparison and execution
are checks of the generated Linux target; the compiler process itself ran on
macOS. `codesign --verify --strict` passed and `otool -L` listed no dylibs.

The one-time instruction derivations are archived as
[D/A](fs2-da.derivation.s), [B/C](fs2-bc.derivation.s), and
[codepoint](codepoint-fast.derivation.s) source. The B/C object's 194 literal
words matched the Kotoba source exactly before its single branch-target patch.
These files are review records, not build inputs.

The FS2 writer validates the byte vector and a bounded basename before I/O,
uses FD3 with `O_RESOLVE_BENEATH` and `O_NOFOLLOW_ANY`, and returns an FS2
acknowledgement vector. An existing output is refused by the compiler with
`E7100`; a `../` output traps before creating a file outside FD3. The latter
is a fail-closed diagnostic trap, not a finished user-facing error.

**Qualification boundary:** the Mac image was packaged by an Amu-built
Linux ARM producer in an offline container. One-time Apple assembler output
was transcribed into Kotoba word vectors; the assembler is not a packaging
input. This record proves the bounded Mac `check`/`compile` path only. It does
not establish a Mac-native F1=F2=F3 compiler rebuild, the remaining FS2
forms/source-lock behavior, the full native corpus, or AIUEOS boot/release
qualification. The diagnostic Python script only stages and observes the
execution; it is not part of the compiler or OS runtime.
