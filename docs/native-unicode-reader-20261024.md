# Native Form reader Unicode correction

`string-code-point-at` takes a UTF-8 byte offset. `number-or-symbol` eagerly
read the second and last **byte** of a token as code-point boundaries. Japanese
symbols and a final multibyte scalar therefore trapped before classification.

The second point is now read only after an ASCII first point. The final point
is found by walking scalar boundaries. Numeric classification and the existing
UTF-16 source-column contract are retained. The stale CLJK/bootstrap-host
prerequisite comment is replaced by the current canonical-source contract.

## Native evidence

The current main root at `dd35c6379e3b87f024bf685fa8d61af0aa07cea1`, SHA-256
`688324e0fdc7a93a664ae55fe0ad417e7a980ab844656f3f97889812363c9479`, compiled
and packed each test into a loaderless ARM Linux executable. Guest processes
had `PATH=/nonexistent` and explicit grants. No retired language host ran.

- The dedicated fixture checks eleven Unicode symbol spellings, signed and
  mixed tokens, integer/f64 regression, collection/keyword/string data, and
  UTF-16 columns across an astral scalar and a newline.
- The same fixture built with the unchanged previous reader
  `8ebba608f9c735e2b43d35b8ad61d922f1c17e7c7134d1685e371546f18ecda7`
  exits120 with SIGILL. The corrected reader exits0.
- Owning CBOR main's complete 2,367-value corpus and 2,000 random values pass.
  All previously documented representation corrections and noncanonical
  cases remain recorded; no input was omitted or changed.
- Owning osaho main's ten unchanged frozen Definition identity vectors,
  alpha normalization, tagged-boundary, effect and lock controls pass.

Receipts are in `docs/evidence/native-unicode-reader-20261024/`.
`test/native_unicode_reader_gate.py` stages exact input locks and processes;
all semantic assertions execute in the Kotoba fixture. It accepts a pinned
previous reader for the executable negative control.

This corrects the Form reader used by native CID/lock metadata consumers.
It does not qualify Unicode symbols in the adopted compiler's source lexer,
all twelve public CLI executions, general FS fault/race coverage, x86
execution of this fixture, or a new complete compiler image. Those remain
separate work in AWAI-24/43/48/52. No workflow, protection, service or route
changes are part of this patch.
