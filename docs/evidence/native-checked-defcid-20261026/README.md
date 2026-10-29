# Checked DefCID prototype evidence

The standalone local ARM gate executed69 process observations, including
fresh native builds and four successfully built/executed mutants. The native
producer and the independent hand-authored native payload oracle agree for
ordinary, binder, result/option, recursive and external-dependency fixtures.
All production FULL47/root/public pins remain unchanged. This bounded pure
KIR profile is outside FULL-MANIFEST and has not implemented persistent
objects, relocation or build reuse.

`local-arm-native.json` binds the exact modules, compiler, staged sources,
native images, authority snapshot, output digests and observations. Native
reader/version-drift checks and complete refusal/no-partial-output checks
are included. The separate x86/ARM workflow must pass before adoption.

`local-arm-prefix-abba.json` records the CPU-pinned native ARM ABBA experiment
on the SCC8 fixture. Both variants normalize members once; their staged
sources differ only in the production minimum-search call site (full payload
versus first differing member). All40320 permutations remain examined. This
experiment does not establish cold compiler or end-to-end CI speedup.

Reproduce the gate on its actual native Linux ISA with an adopted Amu-built
compiler:

```sh
python3 scripts/seed/native_build_queue.py --slot-dir /absolute/shared/slots -- \
  python3 scripts/seed/check-checked-definition-native.py \
  --compiler /absolute/native/compiler --output /absolute/new/output
```

Python stages bytes and records observations. Native Kotoba owns checking,
normalization, canonical encoding, hashing, SCC decisions and image emission.
