# Effects / port16 compiler review

The signed native Mac root rebuilt the current 48-module source to F1=F2
(container, extracted code and unsigned image). The default descriptor gate
passed; `review-mac-selfhost.json` is that receipt. `cross.json` binds the same
source to deterministic ARM and x86 Linux compiler candidates. Their actual
bytes and descriptors were updated together; identity preflight passed.

Cross generation is not native Linux execution. Native ARM/x86 fixed points,
controller, public aliases and the full unchanged native corpus remain required
CI checks before merge. Release, physical hardware and broader compatibility
remain unqualified. No JVM, NBB, C compiler or loader fallback was used.

`mac-selfhost.json` and `source-pin.json` retain the earlier source-only
candidate observation; they do not describe the updated root adoption.
The GUI consumer is kotoba-lang/kotoba#965.

Review additionally found that adding stub declarations affected old v1/v2
output bytes. The three new intrinsics are now limited to v3; both v1/v2
outputs compare exactly with the pinned old compiler. `kernel-v3.json` is the
unchanged strict layout/guest/admission gate (including legacy byte equality).
The Mac producer also builds the selfhost-subset compiler; no dependency on
project-only helpers was added to that subset.

`gui-compiler-equivalence.json` shows that the repaired final compiler emits
the same native GUI kernel bytes as the fully observed review image. Final
native Linux/controller/full-corpus CI remains mandatory before merge.
