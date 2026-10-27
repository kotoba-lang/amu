# Darwin string ABI diagnostic, 2026-10-26

The Amu-built Kotoba packagers in `seed/macos-codepoint-runtime-packager.kotoba`
and `seed/macos-substring-runtime-packager.kotoba` emitted signed Mac test
images with real Darwin argv and native string ABI slots 144 and 136.
[receipt.json](receipt.json) pins the canonical sources, compiler root,
intermediate `.kseed`/raw files, packagers, images, helper bytes, build
admissions and eight independent signed process results. The assembly files
are derivation aids only; the packagers emit reviewed words from Kotoba.

The code-point fixture returned 42 for ASCII, two-, three- and four-byte
UTF-8 scalar reads. A continuation-byte read trapped. The substring fixture
returned 42 for both literal and pool-backed UTF-8 views and empty ranges;
a boundary inside a multibyte character trapped. Both full compiler images
showed usage and exit 2 with no arguments. Re-emitting each full image gave
identical bytes.

With `check fixture.kotoba`, the code-point image progressed to the missing
slot 136. Adding substring progressed the same full compiler to missing
slot 200, `vector_alloc`; the current Mac crash report matched the generated
`ldr`/`blr` at raw return offset `0x2d28`. Thus `check` has **not** completed.
The next implementation gate is the native vector ABI, followed by further
real full-compiler runs.

These diagnostic images were produced by the current Linux-hosted Amu root.
They do not establish Mac self-rebuild, trusted user consent, complete CLI
operation or Linux-free build closure.
