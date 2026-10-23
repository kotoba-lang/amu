# The adopted core as an x86_64 static image (2026-10-23, JUN-330)

The receipt comes from Actions run 39887118185, job `qualify-x86_64`, on a
native x86_64 kernel (Linux 6.17.0-1022-azure) with no emulation and no C
compiler or loader. `check-x86_64-native.py` step 6 did the following:

1. X2 built `seed/CORE-STATIC-MANIFEST` as X0.elf: 7,913,984 bytes,
   `18061319…`.
2. X0 compiled `seed/MANIFEST` in **1,036.4 s**.
3. `extract-native` gave `9deed950…`, the `adoption-20261022.json` image.
   The container (`29197f18…`) is byte-identical to the bootstrap's G3.
