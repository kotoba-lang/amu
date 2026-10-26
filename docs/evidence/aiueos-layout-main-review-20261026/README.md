# Combined AIUEOS layout and current-main review

The reviewed layout-v2 / user-v4 stack includes the llm-v1 checker and cumulative
E7104 diagnostic, plus main be60ae0c (runtime profiles, closed measurement factory,
result observer and retained-record audit). The CLI conflict preserves both the
Linux runtime-profile flag and the two versioned kernel targets.

Native Apple Silicon rebuilt all47 modules to identical F1/F2 containers
`6d5b83a66125817f31a4049144d4d90b45e2ebae064fa69585dffdb882c8a0df`
from source `0c24d2019b21e4d1135f01592d0b7ba220b6fd026ba35014290b02178a039e18`.
The selected core G1/G2/G3 reproduced the adopted source and native image.
Mac-produced Linux candidates are recorded in mac-cross.json. Their generation
alone does not qualify native Linux execution.

The root, public and Mac pins describe this combined graph. Current ARM/x86,
uncached full provenance, controller, locks, browser and final-head CI are pending.
Old successful runs and old failures remain bound to their own immutable heads.
No release, physical hardware, current-core performance, real model or agent-loop
qualification is claimed. Raw source, images and process records remain in the
review workspace; CI uploads its own raw observations.
