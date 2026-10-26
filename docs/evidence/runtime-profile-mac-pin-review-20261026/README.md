# Runtime-profile Mac pin review

The fixed `6a870761` candidate's Mac workflow was not automatically created.
A manual run [40277060046](https://github.com/kotoba-lang/amu/actions/runs/40277060046)
refused before compilation because its bootstrap descriptor still named the
previous FULL47 source `8a07d4dd...` and compiler fixed point `e3402652...`.

The existing pinned native Mac compiler and packager rebuilt the complete
current 47 modules through two identical generations. The actual source is
3,478,533 bytes, SHA256 `702e8cb3954b8fce5291e6f9a7417cc94bca0119f9f84de8c67945b8db64b761`;
the compiler container fixed point is
`93d9f55c2c37609ba97cf5e45040af513a5389b0e413122a50ff467a47450fc6`.
Only these measured descriptor fields change. Bootstrap compiler/packager
images, packager fixed point, production ARM/x86 images and their qualification
boundaries retain their existing values.

The default descriptor-bound gate then passed independently, including native
packager self-rebuild, scalar user ELF/slot, existing-output/missing/oversize,
undeclared-effect and entry-parameter refusals, and the FS2 raw-byte product.
The user-v3 ELF remains `108174e8...` and is refused under v2.

The descriptor-bound Mac compiler produced the exact staged Linux ARM root
`97d7297f...` and public x86 image `c20eb5b1...`. This cross-build report says
`MAC_NATIVE_CROSS_ARTIFACTS_UNEXECUTED`: native Linux execution and final-head
CI are separate gates. No JVM, Node/NBB or C compiler/loader route was used.
A candidate report without the default descriptor binding was correctly
refused by the cross-build gate; the successful run uses the fresh default
report included here.

The first-files path-filter limitation is tracked in JUN-358. The current
review requires explicit fixed-head Mac/native cross results, not an absent
registered check. Kit execution, agent/model semantics, release and physical
hardware remain unqualified.
