# One compiler: the adopted core plus the Linux targets (2026-10-23, JUN-331)

ADR 0370 asks for one semantic compiler. Before this change there were two
closures:

- the Linux selfhost closure (`seed/X86_64-LINUX-SELFHOST-MANIFEST`): 11 core
  modules plus the static emitters;
- the 16-module core (`seed/MANIFEST`).

`seed/FULL-MANIFEST` combines them: the core with the static-profile
namespace (`00-ns-static`) and without `99-entry`, plus seeds 70, 71, 75, 76,
77, 80 and 74. Its entry, `seed/78-full-entry.kotoba`, dispatches as follows:

- `compile … --target aarch64-linux | x86_64-linux | x86_64-aiueos-kernel-v1`
  goes to that target's emitter;
- every other command goes to the core driver, unchanged.

## Route (all C-free, from source)

`scripts/seed/check-one-compiler.py` takes a `selfhost-bootstrap.py` output:

1. P (the packed core from step 3b) compiles `CORE-STATIC-MANIFEST` → Kw.
   S3 packs Kw → **Pw**, the optimized core with static-profile capacities.
   Pw rebuilds Kw exactly. The core's own capacities are not enough for the
   combined unity: it overflows LITB with E101 region 3.
2. Pw compiles `FULL-MANIFEST` → F1, and S3 packs it.
3. F1 compiles the same source → F2 and packs F2 itself. F2 → F3.
4. The script requires F1 = F2 = F3, and that the image F packs equals the
   image S3 packed.
5. F compiles `seed/MANIFEST` to the adoption image.
6. F's Linux targets emit the same bytes as S3:
   - the 24 runtime cases as aarch64-linux static images, which then run
     against the pinned results;
   - the Linux selfhost closure as an x86_64 static compiler, equal to the
     bootstrap's `S-x86_64.elf`.

The packed combined compiler is about 2.87 MB. The whole check takes about
10 minutes on an Apple-silicon arm64 Linux VM. The local receipt is in
`docs/evidence/one-compiler-20261023/`.

## Not yet

- The bootstrap still derives everything from the Linux selfhost closure
  first. Making F the compiler that the root reproduces is a later step.
- F runs on aarch64 Linux. The x86_64 counterpart is tracked in JUN-330.
- A missing function in a large unity makes `check` trap instead of
  reporting E2103 (JUN-334).
