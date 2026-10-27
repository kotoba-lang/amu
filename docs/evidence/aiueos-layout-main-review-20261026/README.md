# Combined AIUEOS layout and current-main review

The reviewed layout-v2 / user-v4 stack includes the llm-v1 checker and cumulative
E7104 diagnostic, plus main be60ae0c (runtime profiles, closed measurement factory,
result observer and retained-record audit). The CLI conflict preserves both the
Linux runtime-profile flag and the two versioned kernel targets.

Native Apple Silicon rebuilt all47 modules to identical F1/F2 containers
`6d5b83a66125817f31a4049144d4d90b45e2ebae064fa69585dffdb882c8a0df`
from source `0c24d2019b21e4d1135f01592d0b7ba220b6fd026ba35014290b02178a039e18`.
The selected core G1/G2/G3 reproduced the adopted source and native image.
Mac-produced Linux candidates are recorded in mac-cross.json. Independent native ARM and x86 jobs reproduced all three compiler generations
from the same source in run40306876007; their source-bound receipts are included.

The root, public and Mac pins describe this combined graph. The current producer also re-emits exactly the controller and both gate images
qualified by native x86 full run40292548615; controller-composition.json binds
the unchanged core and role source bytes. This is an immutable artifact
composition proof, not a claim that the older full run exercised the new
combined compiler source. Integrated uncached full run40306976023 and
final-head native CI are mandatory merge conditions.
Old successful runs and old failures remain bound to their own immutable heads.
No release, physical hardware, current-core performance, real model or agent-loop
qualification is claimed. Raw source, images and process records remain in the
review workspace; CI uploads its own raw observations.

The current producer reproduced both locked old31/new35 kernel/user/slot/EFI
images. Normal old/new pairings succeeded; crossed pairings, changed user entry
and coherent RW address/extent changes refused E7111. The short-RW candidate
keeps filesz==memsz and succeeds under generic packaging, isolating the added
dual-layout refusal. Kernel-v1 still refuses the full35 source with cumulative
E7104 detail1070137 and no output. llm-v1 exact admission and E3004/no-artifact
controls also pass. The guest images match earlier QEMU receipts byte for byte;
this review does not claim a new QEMU run. Parent source containment is recorded.

Full workflow: https://github.com/kotoba-lang/amu/actions/runs/40306976023
Native Mac/ISA workflow: https://github.com/kotoba-lang/amu/actions/runs/40306876007

The integrated full ARM bootstrap completed126 fresh steps with cache reads
and writes disabled. C0 reproduced the selected18 core native image c5028498,
then Kw/Pw reproduced compiler container6d5b83a6. Three adopted-core generations
agree, all54 staged source/manifest entries match, and the one-compiler route
passes30 source-lock controls. The public product's three-alias90-control gate
is verified separately on x86. arm-full-readback.json records this completed
ARM phase; independent ISA and final-head workflow completion remain the
merge conditions above.
