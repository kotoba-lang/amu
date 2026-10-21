# Native compiler source recovery (JUN-198)

The 27 native `.kotoba` compiler/Form modules present at
`d83c5b4660bedfddcb22ee54b3e42e4904d44368` were absent from main
`6c474c81a869a019f082a36ebf1cb2ec1654c75d`, although the former commit is an
ancestor of the latter. A later merge/revert removed the files. Restore those
exact blobs and their 29 removed fixtures/documentation; do not replace them
with the earlier, pre-review `3fdfe65e` baseline.

This retains the reviewed fixes for decimal rounding, native `.cljc` entry
handling, exact export detection, the signed hexadecimal i64 boundary,
duplicate map keys, bounded reader form counts and the v2 component target
spelling. Filesystem confinement continues to depend on the selected host's
capability enforcement. No default launcher or authority changes here.

`scripts/seed/check-native-source-recovery.sh` takes an explicit native
compiler image, loader and fresh output directory. It compiles and links a
six-module fixture from these sources, then executes five regression checks:
v2 target spelling, exact decimal `1.0`, minimum hexadecimal i64, duplicate map
refusal and form-count refusal. It preserves source/tool digests and raw logs.

Source recovery and those checks are prerequisites for the public native CLI
migration in [JUN-198](https://linear.app/com-junkawasaki/issue/JUN-198), not a
claim that the full historical CLI or every target is selfhost-qualified. The
old 59-module semantic closure still needs its frontend dependencies and
reproducible build graph reconciled. Wasm/Web codegen and package/command parity
must be qualified before replacing the public launcher or dropping CLJ gates.
