# Amu selfhost CDCI gate pin refresh — 2026-11-01

The exact-head native bootstrap CI found that the compiler built the Amu selfhost CDCI gate from the current `seed/CORE-STATIC-MANIFEST`, but the policy still pinned the previous gate image.

## Reproduction

- Current `CORE-STATIC-MANIFEST` unity: 2,870,927 bytes, SHA-256 `9072acd746b37b67930d6278a1a531ca5d807f6b4c119596d36a71b684e6907e`.
- Amu selfhost Linux ARM F1 compiler image: 4,002,304 bytes, SHA-256 `3928c726700f0d32889e884986f505c93a312c811d81e7e5ed3eff3a2d248195`. Its compiler container SHA-256 is `7f667efeaaf354e50dc55c454ae9df454a571d94be647e2ea3c8085b855eba10` (3,686,803 bytes).
- Run `F1.elf compile core-static.kotoba --target x86_64-linux --output amu-selfhost-gate.elf --format static` inside the Linux VM with `KEXE_CAP_RESOURCES_35` scoped to the output directory.
- Repeated the build twice with the same compiler and input. Both outputs were byte-identical.

## Measured artifact

- Format: x86_64-linux static image.
- Bytes: 8,348,160.
- SHA-256: `4f8b3fb5d967d8276c70387f3996b5753410feae7d63cd08bc13154ff96c7569`.
- Old `seed/cdci/policy.json` pin: `027dd8e20326d1a7a1597b4f99560b2af848f59f129bfe6d941a98c4ec97b44f`.

The measured policy pin and matching embedded words in `seed/cdci/controller.kotoba` are refreshed. This records deterministic build identity only; the native CDCI controller verdict remains unqualified until the full current-head gate passes.
