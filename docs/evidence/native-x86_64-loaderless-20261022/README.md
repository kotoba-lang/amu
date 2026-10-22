# Native x86_64 loaderless qualification (2026-10-22)

GitHub Actions run 39772917042 (`selfhost-native` workflow):

- `bootstrap-arm64` (ubuntu-24.04-arm, native): `selfhost-bootstrap.py` from the
  pinned root `27440856…0786`.
- `qualify-x86_64` (ubuntu-latest, Linux 7.0.0-1017-azure, native x86_64, no
  emulation, no C compiler or loader): `check-x86_64-native.py`.

Result `PASS_NATIVE_X86_64_LOADERLESS`:

- cross-built S-x86_64 = X2 = X3 (`0af23d42…7a47`, 1,573,376 bytes);
- 24 runtime cases match the pinned loader reference results;
- hardening with seccomp enforced (default required, filtered call → SIGSYS),
  SIGXCPU, SIGALRM and stack SIGSEGV trap with exit 120;
- KX64V1 runner fixed point G1 = G2 = G3 (`6ee42387…65f3` payload);
- scalar ELF suite: 55 programs, 14 refusals; aiueos objects: 4 objects,
  15 refusals.
