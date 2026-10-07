# Timing host admission: retained setup proof

Copy `host-proof.tgz`, `host-proof.manifest.json` and `replay.py` into an empty
directory, then run `python3 replay.py --out ./replayed`. The publication owner
and root each independently copied only these three files and passed offline
replay. The reader uses the standard library and retained evidence; it does not
execute native code, a solver, network requests or new performance measurements.

The frozen source is `39cdbfa1`. Replay checks 737 selected files, eight owner
inventories, 56 retained setup outcomes and all nineteen complete immutable
native/C header arrays, offsets and build bindings (412 package inputs). It
checks the original timed loop, context and reset source; actual CPU admission
before RX; exact raw bytes/offset/ISA; and exact C bytes/symbol followed by a
private read-only embedded copy. This is a scoped single-thread host contract,
not a general context ABI ownership or security proof.

The original source-copy race, initial raw-only source gap, and the v2 diagnostic
classification failure are retained. Original inherited C compiler version and
flags remain unknown. Diagnostic elapsed fields are not timing samples. The
tiny trusted C controls establish setup behavior; this snapshot was frozen
before the planned 57 full benchmark preflight calls or performance campaign.
It must not be used to infer that those later executions occurred or passed.
