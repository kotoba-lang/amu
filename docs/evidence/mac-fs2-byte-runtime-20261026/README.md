# Mac FS2 byte callbacks and signed root transition

The prior diagnostic Mac wrapper left runtime slots 368 (`bytes-slice`) and
376 (`bytes-concat`) unset. A compiled `bytes-concat` probe crashed when it
called slot 376. After installing that callback, the real
`seed/tests/fs2-product.kotoba` raw case reached slot 368 and crashed at a
null instruction address. The callbacks now use the existing checked vector
count/allocate/at/associate ABI. The concat result is bounded to 8 MiB; slice
checks `0 <= start <= end <= count`. The readable one-time derivation records
are [concat](bytes-concat.s) and [slice](bytes-slice.s). The build uses only the
Kotoba word vectors in `seed/macos-fs2-runtime-packager.kotoba`; no assembler
is invoked by the selfhost gate.

Using the previous checked-in Mac compiler and packager, the changed Kotoba
packager source produced a new signed packager. It repackaged its own raw bytes
twice with identical unsigned output. That packager wrapped the unchanged
47-module full compiler raw bytes. The new signed compiler compiled the same
source to the same F1=F2 container SHA-256
`8f932700219ccd15b9ac980db8f978084a11577831f3114e3842ec9da074a638`.
The adopted root pins are:

- signed compiler: `27b04d2a94df9407a373259fa4f27c5e7ab0f97e4a649b065101a1f1d4db4ead`
- signed packager: `cf0d93f764d75047820033f16aa8c2fe9fe20a1a7401b1275e7673aa452eb6e5`
- packager source: `384f14c6e2d851b5480c573bb19603481eb76bf9df9f6d8ca24f6668e47c2c29`
- packager fixed-point unsigned image: `c6080e0a7974f459e36a0b5a4acd5c11dc51317d97adc3bd74eb3b543f042842`

The repository-default Mac selfhost gate passed from those roots, reaching
F1=F2, rebuilding the packager, emitting the checked AIUEOS user ELF and
refusing undeclared `:io/write`. Its new FS2 runtime step compiled the real
product fixture to a Mac executable, ran the `raw` case under the output-owned
FD3 root, and independently read back the three stored bytes `00 ff 80`.
The [source-bound receipt](mac-selfhost.json) records
`PASS_MAC_FS2_RAW_BYTES`. The gate launched no Linux, JVM, Node or C
compiler process.

This qualifies a bounded diagnostic Mac byte-vector path. Other FS2 forms,
complete Mac runtime parity, an AIUEOS guest, a registered Itonami turn,
release admission and physical hardware remain separate open gates.
